import dotenv
dotenv.load_dotenv()

from langchain_chroma import Chroma
from langchain_core.output_parsers import StrOutputParser
from langchain.schema.runnable import RunnablePassthrough
from langchain import hub
from langchain.prompts import (
    PromptTemplate,
    SystemMessagePromptTemplate,
    HumanMessagePromptTemplate,
    ChatPromptTemplate,
)
from langchain_community.chat_models import ChatLiteLLM
from langchain.memory import ConversationBufferMemory
from langchain.chains import ConversationChain
from langchain_openai import ChatOpenAI
from langchain.globals import set_debug, set_verbose

set_debug(True)
set_verbose(True)

from src.app.rag.config import CONFIG
from src.app.rag.util import (
    init_embedding_func,
    get_input_from_cli,
)


def init_prompt(system_prompt_str):
    system_template=PromptTemplate( input_variables=["context"], template=system_prompt_str)
    system_prompt = SystemMessagePromptTemplate( prompt=system_template )

    human_template = PromptTemplate( input_variables=["question"], template="{question}" )
    human_prompt = HumanMessagePromptTemplate(prompt=human_template)

    messages = [system_prompt, human_prompt]
    chat_prompt_template = ChatPromptTemplate(  input_variables=["context", "question"],
                                                messages=messages )
    return chat_prompt_template


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
    
def build_memory_chain(db_path, collection_name, prompt_template, k, embedding, model, base_url=None):
    retriever = get_retriever(db_path, collection_name, k, embedding)
    chat_model = get_chat_model2(model, base_url)
    memory = ConversationBufferMemory(ai_prefix="AI Assistant")
    return ConversationChain(prompt=prompt_template, llm=chat_model, verbose=True, memory=memory)

def main():
    print('Initializing...')
    chain = build_chain(**CONFIG)
    while True:
        print(f"{'='*5} BASE_URL:{CONFIG['base_url']} Embedding:{CONFIG['embedding']} {'='*5}")
        question = get_input_from_cli('question: ', default="제 택배 배송 상황이 궁금합니다")
        print()
        if question is None:
            break
        result = chain.invoke(question)
        print(result)
        print()
    pass

if __name__ == "__main__":
    main()