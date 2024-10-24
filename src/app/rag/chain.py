import dotenv
dotenv.load_dotenv()

import re
from langchain_chroma import Chroma
from langchain.schema.runnable import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from langchain_core.chat_history import (
    BaseChatMessageHistory,
    InMemoryChatMessageHistory
)
from langchain_core.runnables.history import RunnableWithMessageHistory

from langchain.chains.retrieval import create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain.prompts import (
    PromptTemplate,
    SystemMessagePromptTemplate,
    HumanMessagePromptTemplate,
    ChatPromptTemplate,
    MessagesPlaceholder
)
from langchain_community.chat_models import ChatLiteLLM
from langchain_openai import ChatOpenAI
from langchain.globals import set_debug, set_verbose

set_debug(True)
set_verbose(True)

from src.app.rag.config import SYSTEM_PROMPT_STR_KO, tool_prompt
from src.app.rag.config import CHAIN_TYPE_CONTEXT, CHAIN_TYPE_TOOL
from src.app.rag.config import CONFIG
from src.app.rag.util import (
    init_embedding_func,
    get_input_from_cli,
)

g_history = {}
g_retriever = None
def insert_message_to_history(session_id: str, message):
    if session_id in g_history:
        g_history[session_id].add_message(message)
    else:
        g_history[session_id] = InMemoryChatMessageHistory()
        g_history[session_id].add_message(message)

def get_session_history(session_id: str) -> BaseChatMessageHistory:
    if session_id not in g_history:
        g_history[session_id] = InMemoryChatMessageHistory()
    return g_history[session_id]

def remove_special_tokens_from_str(s:str) -> str:
    if s:
        index = s.find('<|im_')
        if index > -1:
            s = s[:index]
            if s and s[-1]=='|':
                s = s[:-1]
    return s.strip()

def print_history(session_id: str):
    if session_id in g_history:
        print(f"\n\nSession ID:{session_id} History:")
        for m in g_history[session_id].messages:
            print(f"{m}\n")
        for m in g_history[session_id].messages:
            m.content = remove_special_tokens_from_str(m.content)
        for m in g_history[session_id].messages:
            print(f"{m}\n")
    else:
        print(f"\n\nSession ID:{session_id}: No history")

def init_prompt(system_prompt_str, history):
    '''
    system_prompt_str must contain "{context}" as a placeholder
    '''
    if history:
        return ChatPromptTemplate.from_messages(
                [   ("system", system_prompt_str),
                    MessagesPlaceholder("history"),
                    ("human", "{input}"),
                ])
    else:
        return ChatPromptTemplate.from_messages(
                [   ("system", system_prompt_str),
                    ("human", "{question}"),
                ])

def get_retriever(db_path, collection_name, k, embedding_model):
    global g_retriever
    embedding_func = init_embedding_func(embedding_model)
    db = Chroma( persist_directory=db_path,
                collection_name=collection_name,
                embedding_function=embedding_func)
    #return db.as_retriever(k=k)
    g_retriever = db.as_retriever(search_kwargs={"k": k})
    return g_retriever

def get_retriever_with_score(db_path, collection_name, score, embedding_model):
    global g_retriever
    embedding_func = init_embedding_func(embedding_model)
    db = Chroma( persist_directory=db_path,
                collection_name=collection_name,
                embedding_function=embedding_func)
    g_retriever = db.as_retriever( search_type="similarity_score_threshold", search_kwargs={'score_threshold': score})
    return g_retriever

def get_chat_model(model, base_url=None):
    if base_url:
        return ChatOpenAI(model=model, temperature=0, base_url=base_url)
    return ChatOpenAI(model=model, temperature=0)

def get_chat_model2(model, base_url=None):
    if base_url:
        return ChatLiteLLM(model=model, temperature=0, base_url=base_url)
    return ChatLiteLLM(model=model, temperature=0)

def build_chain(db_path, collection_name, prompt_template, k, embedding, model, base_url=None):
    global g_retriever
    chat_prompt = init_prompt(prompt_template)
    g_retriever = get_retriever(db_path, collection_name, k, embedding)
    chat_model = get_chat_model(model, base_url)
    chain = (
        {"context": g_retriever, "question": RunnablePassthrough()}
        | chat_prompt
        | chat_model
        | StrOutputParser()
    )
    return chain, g_retriever, CHAIN_TYPE_CONTEXT

def build_history_chain(db_path, collection_name, prompt_str, k, score, embedding, model, base_url=None):
    global g_retriever
    history_prompt = init_prompt(prompt_str, history=True)
    #retriever = get_retriever(db_path, collection_name, k, embedding)
    g_retriever = get_retriever_with_score(db_path, collection_name, score, embedding)
    chat_model = get_chat_model(model, base_url)
    # prompt must include a variable 'context'.
    history_chain = create_stuff_documents_chain(chat_model, history_prompt)
    rag_chain = create_retrieval_chain(g_retriever, history_chain)

    history_rag_chain = RunnableWithMessageHistory(
        rag_chain,
        get_session_history,
        input_messages_key="input",
        history_messages_key="history",
        output_messages_key="answer",
    )
    history_rag_chain = history_rag_chain

    return history_rag_chain, g_retriever, CHAIN_TYPE_CONTEXT

def format_docs(docs):
    for doc in docs:
        print(f"{'='*5}{'='*5}")
        print(doc.page_content)
        print()
    #return "\n\n".join(doc.page_content for doc in docs)
    #return "\n\n".join([d.page_content for d in docs])
    return "\n\n".join([d.metadata['answer'] for d in docs])

def build_history_chain_LECL(db_path, collection_name, prompt_str, k, score, embedding, model, base_url=None):
    global g_retriever
    history_prompt = init_prompt(prompt_str, history=True)
    chat_model = get_chat_model(model, base_url)

    if prompt_str.find("{context}") > -1:
        rag_chain_from_docs = (
            {   "input": lambda x: x["input"],  # input query
                "history": lambda x: x["history"],  # chat history
                "context": lambda x: format_docs(x["context"]),  # context
            }
            | history_prompt  # format query and context into prompt
            | chat_model  # generate response
            | StrOutputParser()  # coerce to string
        )
        g_retriever = get_retriever_with_score(db_path, collection_name, score, embedding)
        retrieve_docs = (lambda x: x["input"]) | g_retriever
        rag_chain = RunnablePassthrough.assign(context=retrieve_docs).assign(answer=rag_chain_from_docs)
    else:
        rag_chain_from_docs = (
            {   "input": lambda x: x["input"],  # input query
                "history": lambda x: x["history"],  # chat history
            }
            | history_prompt  # format query and context into prompt
            | chat_model  # generate response
            | StrOutputParser()  # coerce to string
        )
        rag_chain = RunnablePassthrough.assign(answer=rag_chain_from_docs)

    history_rag_chain = RunnableWithMessageHistory(
        rag_chain,
        get_session_history,
        input_messages_key="input",
        history_messages_key="history",
        output_messages_key="answer",
    )
    return history_rag_chain, g_retriever, CHAIN_TYPE_CONTEXT

def filter_tool_call(msg, retriever):
    docs = retriever.invoke(msg)
    if docs:
        intent = docs[-1].metadata['intent']
        print(f"\n{'#'*20}")
        print(f"intent: {docs[-1].metadata['intent']}")
        print(f"msg: {msg}")
        #if intent == 'H1_배송조회':
        if re.search(r'\d{8,12}', msg):
            print("CHAIN_TYPE_TOOL")
            return CHAIN_TYPE_TOOL

        print("CHAIN_TYPE_CONTEXT")
        print(f"{'#'*20}\n\n")
    return CHAIN_TYPE_CONTEXT

def rebuild_chain(msg, retriever, current_chain):
    if filter_tool_call(msg, retriever)==CHAIN_TYPE_CONTEXT:
        return current_chain

    prompt_str = SYSTEM_PROMPT_STR_KO + tool_prompt
    chain, _, _ = build_history_chain_LECL(
                            CONFIG['db_path'], 
                            CONFIG['collection_name'], 
                            prompt_str, 
                            CONFIG['k'], 
                            CONFIG['score'], 
                            CONFIG['embedding'], 
                            CONFIG['model'], 
                            CONFIG['base_url'])
    return chain

def main():
    print('Initializing...')
    chain = build_history_chain(**CONFIG)
    while True:
        print(f"{'='*5} BASE_URL:{CONFIG['base_url']} Embedding:{CONFIG['embedding']} {'='*5}")
        question = get_input_from_cli('input: ', default="제 택배 배송 상황이 궁금합니다")
        print()
        if question is None:
            break
        result = chain.invoke(question)
        print(result)
        print()
    pass

if __name__ == "__main__":
    main()