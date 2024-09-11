import os
from langchain_community.embeddings import SentenceTransformerEmbeddings
from langchain_openai import OpenAIEmbeddings
from src.app.rag.config import *

def get_datetime_str():
    import datetime
    return datetime.datetime.now().strftime('%Y.%m.%d_%H%M')

def append_time_to_path(filename, dt):
    parts = filename.split('.')
    parts[-2] = parts[-2] + '_' + dt

    return '.'.join(parts)

def init_embedding_func(model_name):
    if model_name == OPENAI_EMBEDDING:
        return OpenAIEmbeddings(model=OPENAI_EMBEDDING)
    else:
        return SentenceTransformerEmbeddings(model_name=model_name)

def get_input_from_cli(prompt, default):
    query = ''
    try:
        query = input(prompt)
    except:
        return None

    if query.strip() in ['exit', 'quit']:
        return None
    if not query.strip():
        query = default
        print(f"Use default query: '{query}'")
    return query