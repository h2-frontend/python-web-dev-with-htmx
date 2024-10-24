from dataclasses import dataclass
from typing import AsyncGenerator, Any
from collections import deque
import json
import re

import bcrypt
import requests
from fastapi import HTTPException
from markdown import markdown
from sqlalchemy import ScalarResult, func, select
from sqlalchemy.orm import selectinload

from langchain.globals import set_debug, set_verbose
from langchain_teddynote import logging as log_langsmith
from langchain_core.messages.ai import AIMessage

from src.app import schemas
from src.app.db import AsyncSession, models
import logging
logging.basicConfig(filename='./log/messages.log', level=logging.INFO)

from src.app.rag.config import LANGSMITH_PROJECT
from src.app.rag.config import APIS
from src.app.rag.config import VOC
from src.app.rag.chain import print_history
from src.app.rag.chain import insert_message_to_history

log_langsmith.langsmith(LANGSMITH_PROJECT, set_enable=True)

from src.app.rag.stream_parser import StreamParser
from src.app.rag.chain import rebuild_chain

set_debug(True)
set_verbose(True)

SUCCESS = 0
INVALID_NUMBER = 1
NOT_FOUND = 2

def generate_output(d):
    output = ''
    for k, v in d.items():
        output += f'* {VOC[k]}: {v}\n'

    return output

def call_api(tool, input):
    response = requests.get(f'{APIS[tool]}{input}')
    data = json.loads(response.text)
    result = data.pop('result')
    msg = ''
    if result == SUCCESS:
        if tool == 'track_package':
            msg += f"배송 조회 결과를 알려드립니다.\n\n"
        elif tool == 'find_reservation':
            msg += f'예약 정보 조회 결과를 알려드립니다.\n\n'
        elif tool == 'find_contact': 
            msg += f'연락처 조회 결과를 알려드립니다.\n\n'
        output = msg + generate_output(data)
    else:
        if tool == 'track_package':
            if input != 'tracking_number':
                msg += f"운송장번호 {input}에 대한 배송 정보를 찾을 수 없습니다. 운송장 번호를 확인하신 후 다시 조회해보세요.\n"
        elif tool == 'find_reservation':
            if input != 'reservation_number':
                msg += f"예약번호 {input}에 대한 예약정보를 찾을 수 없습니다. 예약 번호를 확인하신 후 다시 조회해보세요.\n"
        elif tool == 'find_contact': 
            msg += f'알려주신 주소에 대한 집배점/배송사원 연락처를 찾을 수 없습니다. 주소를 확인하신 후 다시 조회해보세요.\n'
        output = msg
    print(f'\n\nREST API result: {result}\n\n')
    return output

@dataclass
class AppService:
    """
    Service class for handling application logic.
    """

    session: AsyncSession

    async def get(self) -> ScalarResult[models.User]:
        """
        Get a list of users.

        Returns:
            ScalarResult[models.User]: A scalar result of users.
        """
        session = self.session
        async with session.begin():
            result: ScalarResult[models.User] = await self.session.scalars(
                select(models.User).limit(20)
            )
        return result

    async def create_user(self, data: schemas.Signup) -> models.User:
        """
        Create a new user.

        Args:
            data (schemas.Signup): The signup data.

        Returns:
            models.User: The created user.
        """
        hashed_password = bcrypt.hashpw(data.password.encode(), bcrypt.gensalt())

        user = models.User(
            username=data.username, hashed_password=hashed_password.decode()
        )

        async with self.session.begin():
            self.session.add(user)
        return user

    async def login(self, daat: schemas.Login) -> models.User:
        """
        Login a user.

        Args:
            daat (schemas.Login): The login data.

        Returns:
            models.User: The logged in user.

        Raises:
            HTTPException: If the user is not found or the password is invalid.
        """
        user = await self.session.scalar(
            select(models.User).where(models.User.username == daat.username)
        )

        if user is None:
            raise HTTPException(status_code=404, detail="User not found")

        if not bcrypt.checkpw(daat.password.encode(), user.hashed_password.encode()):
            raise HTTPException(status_code=400, detail="Invalid password")

        return user

    async def get_user_by_id(self, id: int) -> models.User | None:
        """
        Get a user by ID.

        Args:
            id (int): The ID of the user.

        Returns:
            models.User: The user with the specified ID.
        """
        async with self.session.begin():
            user = await self.session.scalar(
                select(models.User).where(models.User.id == id)
            )

        return user

    async def get_all_chats(self, user: models.User) -> ScalarResult[models.Chat]:
        """
        Get all chats for a user.

        Args:
            user (models.User): The user.

        Returns:
            ScalarResult[models.Chat]: A scalar result of chats.

        """
        session = self.session
        async with session.begin():
            subquery = (
                select(
                    models.ChatMessage.chat_id,
                    func.max(models.ChatMessage.create_date).label("max_date"),
                )
                .where(models.ChatMessage.chat_id == models.Chat.id)
                .group_by(models.ChatMessage.chat_id)
                .alias()
            )
            chats = await self.session.scalars(
                select(models.Chat)
                .where(models.Chat.user_id == user.id)
                .join(subquery, models.Chat.id == subquery.c.chat_id)
                .order_by(subquery.c.max_date.desc())
                .options(selectinload(models.Chat.messages))
            )

        return chats

    # async def get_chats(self, user: models.User) -> list[models.Chat]:
    #     async with self.session.begin():
    #         chats = await self.session.scalars(
    #             select(models.Chat)
    #             .where(models.Chat.user_id == user.id)
    #             .options(selectinload(models.Chat.messages))
    #         )
    #     return chats

    async def get_chat_by_id(
        self, chat_id: int, user: models.User
    ) -> models.Chat | None:
        """
        Get a chat by ID for a user.

        Args:
            chat_id (int): The ID of the chat.
            user (models.User): The user.

        Returns:
            models.Chat: The chat with the specified ID.

        Raises:
            HTTPException: If the chat is not found.
        """
        async with self.session.begin():
            chat = await self.session.scalar(
                select(models.Chat)
                .where(models.Chat.id == chat_id and models.Chat.user_id == user.id)
                .options(selectinload(models.Chat.messages))
            )
        return chat

    async def create_chat(
        self, user: models.User, data: schemas.CreateChat
    ) -> models.Chat:
        """
        Create a new chat for a user.

        Args:
            user (models.User): The user.
            data (schemas.CreateChat): The chat data.

        Returns:
            models.Chat: The created chat.
        """
        chat = models.Chat(name=data.message, user_id=user.id)

        message = models.ChatMessage(kind="human", content=data.message)

        chat.messages.append(message)

        async with self.session.begin():
            self.session.add(chat)
        return chat

    async def delete_chat(self, chat_id: int, user: models.User) -> None:
        """
        Delete a chat.

        Args:
            chat_id (int): The ID of the chat.
            user (models.User): The user.

        Raises:
            HTTPException: If the chat is not found.
        """
        async with self.session.begin():
            chat = await self.session.scalar(
                select(models.Chat)
                .where(models.Chat.id == chat_id and models.Chat.user_id == user.id)
                .options(selectinload(models.Chat.messages))
            )

            if chat is None:
                raise HTTPException(status_code=404, detail="Chat not found")

            await self.session.delete(chat)

    async def add_message(
        self, user: models.User, data: schemas.AddMessage, chat_id: int
    ) -> models.ChatMessage:
        """
        Add a message to a chat.

        Args:
            user (models.User): The user.
            data (schemas.AddMessage): The message data.
            chat_id (int): The ID of the chat.

        Returns:
            models.ChatMessage: The added message.

        Raises:
            HTTPException: If the chat is not found.
        """
        async with self.session.begin():
            chat = await self.session.scalar(
                select(models.Chat).where(models.Chat.id == chat_id)
            )

            if chat is None:
                raise HTTPException(status_code=404, detail="Chat not found")

            message = models.ChatMessage(
                kind="human", content=data.message, chat_id=chat.id
            )

            self.session.add(message)
        return message

    async def generate(self, chat_id: int, chain: Any, retriever: Any) -> AsyncGenerator[dict, None]:
        """
        Generate a response for a chat.

        Args:
            chat_id (int): The ID of the chat.

        Yields:
            dict: A dictionary containing the generated response.

        Raises:
            HTTPException: If the chat is not found.
        """
        async with self.session.begin():
            chat = await self.session.scalar(
                select(models.Chat)
                .where(models.Chat.id == chat_id)
                .options(
                    selectinload(models.Chat.messages),
                )
            )

        if chat is None:
            raise HTTPException(status_code=404, detail="Chat not found")

        messages: list[dict] = []

        for message in chat.messages:
            if message.kind == "human":
                messages.append({"role": "user", "content": message.content})
            else:
                messages.append({"role": "assistant", "content": message.content})

        print('\n\nMessages')
        for m in messages:
            print(f"Message: {m}", flush=True)
        print('\n\n')
        
        chain = rebuild_chain(messages[-1]["content"], retriever, chain)

        print("\n\nPrint History before chain.astream")
        print_history(str(chat_id))
        response = chain.astream({"input":messages[-1]["content"]}, 
                                 config={"configurable": {"session_id": str(chat_id)}})
        print("\n\nPrint History after chain.astream")
        print_history(str(chat_id))
        print('\n\n')

        res = ""
        valid_response = True
        stream_parser = StreamParser()
        try:
            async for chunk in response:
                #print(f"\n\n{'*'*50}\ntype(chunk):{type(chunk)}\nchunk: {chunk}\n\n", flush=True)
                if valid_response:
                    state, answer = stream_parser.parse_stream(chunk.get('answer'))
                    if state==stream_parser.END:
                        valid_response = False
                    elif state==stream_parser.TOOLING:
                        continue
                    elif state==stream_parser.TOOLCALL:
                        print(f"\n\n{'*'*50}\nToolcall: {answer}\n\n", flush=True)
                        output = call_api(*answer)
                        aim = AIMessage(content=output)
                        insert_message_to_history(str(chat_id), aim)
                        res += output
                        valid_response = False
                    #elif state==stream_parser.CONTROL:
                    #    continue
                    elif state==stream_parser.START:
                        res += answer
                    
                    #res = re.sub('hanjiin', 'hanjin', res)
                    #print(f'\n{res}')
                    res = res.replace('hanjiin', 'hanjin')
                    #print(f'\n{res}\n')
                    s = f"""
                    <div id="ai-sse" class="prose prose-sm w-full flex flex-col [&>*]:flex-grow">
                        {markdown(res, extensions=["fenced_code"])}
                    </div>
                    """
                    yield {"event": "message", "id": "id", "data": s}
        except GeneratorExit:
            print("GeneratorExit")


        async with self.session.begin():
            gen_message = models.ChatMessage(
                kind="assistant", content=res, chat_id=chat.id
            )
            self.session.add(gen_message)

        s = f"""
        <div class="prose prose-sm w-full flex flex-col [&>*]:flex-grow">
            {markdown(res, extensions=["fenced_code"])}
        </div>

        <div id="stream" hx-swap-oob="true" hx-swap="outerHTML"></div>
        """
        yield {"event": "message", "id": "id", "data": s}
