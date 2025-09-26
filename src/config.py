import os
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.tools import Tool

# .env 파일에서 환경 변수 로드
load_dotenv()

# 환경 변수에서 API 키를 가져옵니다.
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GOOGLE_PLACES_API_KEY = os.getenv("GOOGLE_PLACES_API_KEY")
if not GOOGLE_API_KEY:
    raise ValueError("GOOGLE_API_KEY 환경 변수가 설정되지 않았습니다.")

# --- LLM 초기화 (Gemini) ---
# LangGraph에서 사용할 Gemini LLM을 초기화합니다.
llm = ChatGoogleGenerativeAI(
    model="gemini-2.0-flash",  # 원하는 Gemini 모델명으로 변경 (예: gemini-1.0-pro)
    temperature=0.7,
    google_api_key=GOOGLE_API_KEY
)
PLACES_API_FIELDS = [
    "id", "displayName", "formattedAddress", "location",
    "primaryType", "types", "priceLevel", "rating", "userRatingCount",
    "regularOpeningHours", "reviews"
]