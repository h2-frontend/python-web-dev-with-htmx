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
    제공된 context에 포함되지 않은 정보를 만들어 내어서 답변하면 안됩니다.
    고객의 질문이 배송 서비스와 관련이 없을 때는 배송 서비스에 대한 질문만 답변할 수 있다고 친절하게 알려주세요
    정확한 답변을 알 수 없을 때는 모른다고 하세요.

    context: {context}


    """
SYSTEM_PROMPT_STR_EN = """You are an online customer service representative for Hanjin Express. 
    Your job is to kindly respond to customer inquiries about Hanjin Express’s delivery services via text messenger. 
    Please answer based on the information provided in the context below. 
    Do not create information that is not included in the provided context. 
    If the customer's question is not related to the provided context, politely respond that you only answer queries related to the delivery service.
    If you do not know the exact answer, say that you do not know.

    배송조회를 위해서는 10자리의 숫자로 구성된 택배 운송장 번호를 고객에게 요청해야합니다.
    고객이 제공한 운송장 번호가 10자리 숫자가 아니면 정확한 운송장 번호를 입력하라고 요청하세요.
    배송 조회를 하기 위해서는 다음과 같은 형식의 문구에 운송장 번호를 채워 넣어서 답변하세요(다른 문구를 덧붙이지 말고 아래의 형식으로만 답변하세요).

    [Tool]track_package
    [Tool Input]"tracking_number"

    context: {context}


    """
temp = '''    To track a shipment, you need to request the delivery tracking number from the customer. 
    The tracking number is a 10-digit number. 
    If the tracking number provided by the customer is not a 10-digit number, ask them to enter the correct tracking number. 
    Only when you have already received a tracking number in the correct format from the customer, then respond by filling in the tracking number in the following format (do not add any other phrases, respond only in the format below).

    <Tool>track_package</Tool>
    <Tool_Input>"tracking_number"</Tool_Input>

    배송조회를 위해서는 10자리의 숫자로 구성된 택배 운송장 번호를 고객에게 요청해야합니다.
    고객이 제공한 운송장 번호가 10자리 숫자가 아니면 정확한 운송장 번호를 입력하라고 요청하세요.
    고객으로부터 운송장 번호를 제공 받은 후, 배송 조회를 하려면 다음과 같은 형식의 문구에 운송장 번호를 채워 넣어서 답변하세요(다른 문구를 덧붙이지 말고 아래의 형식으로만 답변하세요).

    <Tool>track_package</Tool>
    <Tool_Input>"tracking_number"</Tool_Input>
    

    '''
    
    

#DB_BASE_PATH = './.volumes/db/hanjin-chroma-2024.9.25-tool_close'
DB_BASE_PATH = './.volumes/db/hanjin-chroma-2024.9.30-debug'

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
    'prompt_str': SYSTEM_PROMPT_STR_KO,
    'k': 2,
    'embedding': DB_CONFIG['embedding'],
    'model': GPT3_5_TURBO,
    'base_url': 'http://192.168.0.24:8080',
}

APIS = {
    'track_package': "http://192.168.0.24:8003/track_package_by_tracking_number/",
    'find_reservation': "http://192.168.0.24:8003/find_reservation/",
}

VOC = {
    "tracking_number": "운송장 번호",
    "reservation_number": "예약번호",
    "status": "배송상태",
    "r_status": "예약상태",
    "content": "상품명",
    "sender": "보내는 분",
    "receiver": "받는 분",
    "delivered_to": "배달지",
    "office": "집배점",
    "staff": "배송직원",
}