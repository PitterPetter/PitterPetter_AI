import os
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.tools import Tool

# .env 파일에서 환경 변수 로드
load_dotenv()

# 환경 변수에서 API 키를 가져옵니다.
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

if not GOOGLE_API_KEY:
    raise ValueError("GOOGLE_API_KEY 환경 변수가 설정되지 않았습니다.")

# --- LLM 초기화 (Gemini) ---
# LangGraph에서 사용할 Gemini LLM을 초기화합니다.
llm = ChatGoogleGenerativeAI(
    model="gemini-1.5-flash",  # 원하는 Gemini 모델명으로 변경 (예: gemini-1.0-pro)
    temperature=0.7,
    google_api_key=GOOGLE_API_KEY
)

# --- 도구(Tools) 초기화 ---
# LangGraph에서 사용할 도구들을 정의합니다.
def google_search(query: str) -> str:
    """구글 검색을 실행하는 더미 함수. 실제 구현으로 대체해야 합니다."""
    # TODO: 
    
    return f"'{query}'에 대한 검색 결과입니다."

google_search_tool = Tool(
    name="google_search",
    description="최신 정보나 웹에서 정보를 찾을 때 사용됩니다.",
    func=google_search
)

# 프로젝트에 필요한 모든 도구를 리스트에 추가합니다.
tools = [
    google_search_tool,
    # TODO: 다른 도구들 추가 (예: DB 검색, 날씨 API 등)
]