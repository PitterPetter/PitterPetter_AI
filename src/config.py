import os
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.tools import Tool

# .env 파일에서 환경 변수 로드
load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY", "dev_secret")  # 기본값은 dev용
ALGORITHM = "HS256"

GOOGLE_PLACES_API_KEY = os.getenv("GOOGLE_PLACES_API_KEY")
# 2) LLM 초기화
llm = ChatGoogleGenerativeAI(
    model="gemini-2.0-flash",
    temperature=0.7,
)

PLACES_API_FIELDS = [
    "id", "displayName", "formattedAddress", "location",
    "primaryType", "types", "priceLevel", "rating", "userRatingCount",
    "regularOpeningHours", "reviews"
]

