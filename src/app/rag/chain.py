import dotenv
dotenv.load_dotenv()

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

from src.app.rag.config import CONFIG
from src.app.rag.util import (
    init_embedding_func,
    get_input_from_cli,
)

g_history = {}
def get_session_history(session_id: str) -> BaseChatMessageHistory:
    if session_id not in g_history:
        g_history[session_id] = InMemoryChatMessageHistory()
    return g_history[session_id]

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
    embedding_func = init_embedding_func(embedding_model)
    db = Chroma( persist_directory=db_path,
                collection_name=collection_name,
                embedding_function=embedding_func)
    return db.as_retriever(k=k)

def get_chat_model(model, base_url=None):
    if base_url:
        return ChatOpenAI(model=model, temperature=0, base_url=base_url)
    return ChatOpenAI(model=model, temperature=0)

def get_chat_model2(model, base_url=None):
    if base_url:
        return ChatLiteLLM(model=model, temperature=0, base_url=base_url)
    return ChatLiteLLM(model=model, temperature=0)

def build_chain(db_path, collection_name, prompt_template, k, embedding, model, base_url=None):
    chat_prompt = init_prompt(prompt_template)
    retriever = get_retriever(db_path, collection_name, k, embedding)
    chat_model = get_chat_model(model, base_url)
    chain = (
        {"context": retriever, "question": RunnablePassthrough()}
        | chat_prompt
        | chat_model
        | StrOutputParser()
    )
    return chain
    
def build_history_chain(db_path, collection_name, prompt_str, k, embedding, model, base_url=None):
    history_prompt = init_prompt(prompt_str, history=True)
    retriever = get_retriever(db_path, collection_name, k, embedding)
    chat_model = get_chat_model(model, base_url)
    # prompt must include a variable 'context'.
    history_chain = create_stuff_documents_chain(chat_model, history_prompt)
    rag_chain = create_retrieval_chain(retriever, history_chain)

    history_rag_chain = RunnableWithMessageHistory(
        rag_chain,
        get_session_history,
        input_messages_key="input",
        history_messages_key="history",
        output_messages_key="answer",
    )
    history_rag_chain = history_rag_chain

    return history_rag_chain

def remove_special_tokens(s):
    s = s[:s.find('<|im_')]
    if s[-1]=='|':
        s = s[:-1]
    return s

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