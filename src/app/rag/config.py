# JSON keys
DEFAULT_EMBEDDING = "all-MiniLM-L6-v2"
OPENAI_EMBEDDING = "text-embedding-3-small"
BESPIN_EMBEDDING = "bespin-global/klue-sroberta-base-continue-learning-by-mnr"
MPNET_EMBEDDING = "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"
SOBERTA_EMBEDDING = "jhgan/ko-sroberta-multitask"

GPT3_5_TURBO = "gpt-3.5-turbo-0125"

LANGSMITH_PROJECT='HANJIN'

SYSTEM_PROMPT_STR_KO = """당신은 한진택배의 온라인 고객 상담원입니다.
    한진택배의 택배 서비스에 대하여 텍스트 메신저로 고객 문의에 친절하게 응대하는 업무를 담당하고 있습니다.
    아래의 context로 제공된 정보를 기반으로 답변을 해주세요.
    가능한 자세히 답변을 해주고, 제공된 context에 포함되지 않은 정보를 만들어 내어서 답변하면 안됩니다.
    정확한 답변을 알 수 없을 때는 모른다고 하세요.

    {context}
    """
SYSTEM_PROMPT_STR_EN = """You are an online customer service representative for Hanjin Express. 
    Your job is to kindly respond to customer inquiries about Hanjin Express’s delivery services via text messenger. 
    Please answer based on the information provided in the context below. 
    Provide as detailed a response as possible, and do not create information that is not included in the provided context. 
    If you do not know the exact answer, say that you do not know.

    {context}
    """

DB_BASE_PATH = './.volumes/db/hanjin-chroma-2024.9.11'

DB_CONFIG = {
    'qa_path': './data/csv/qa_sorted_rev1_rewritten.csv',
    'links_path': './data/csv/links.txt',
    'actions_path': './data/csv/qa_actions.csv', # REST API endpoint
    'embedding': SOBERTA_EMBEDDING,
    'host': 'http://192.168.0.24:8000'
}

def inject_embedding_to_dbpath(base, embedding):
    return '_'.join(base.split('-')[:-1] + [embedding.replace('/', '-')] + base.split('-')[-1:])

CONFIG = {
    'db_path': inject_embedding_to_dbpath(DB_BASE_PATH, DB_CONFIG['embedding']),
    'collection_name': 'HANJIN',
    'prompt_template': SYSTEM_PROMPT_STR_EN,
    'k': 5,
    'embedding': DB_CONFIG['embedding'],
    'model': GPT3_5_TURBO,
    'base_url': 'http://192.168.0.24:8080',
}
