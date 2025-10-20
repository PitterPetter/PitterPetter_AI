# 🌌 Loventure_AI
> 연인의 심장 박동처럼, 두 사람의 취향을 맞춘 **AI 데이트 코스 플래너**

AI-powered Date Course Recommendation Service  
**FastAPI × LangGraph × LLM Agents**

---

## 🖤 About

두 사람의 무드·예산·활동성·선호(음식/음주 등)를 반영해  
**식당 → 카페 → 산책** 같은 코스를 자동으로 생성합니다.  

Google Places API와 날씨(비/기온/습도 등) 데이터를 함께 고려하여  
**상황 맞춤형 데이트 코스**를 제안합니다.

---

## 🔮 주요 기능

- **LLM 기반 추천 시퀀스 생성**  
  LangGraph로 카테고리 시퀀스를 동적으로 구성 (예: 식당 → 카페 → 산책)
- **POI 검색 + 필터링**  
  Google Places API 연동 후 하드필터/카테고리 필터 적용
- **LangGraph Agent Runner**  
  카테고리별 LLM Agent 병렬 실행 → 빠르고 유연한 추천
- **커플 데이터 최적화**  
  user, partner, couple 정보를 함께 고려하여 코스 품질 향상

---

## 🏗 프로젝트 구조
```bash
src/
├── app/
│   ├── api/                  # FastAPI 엔드포인트 (추천, 헬스체크 등)
│   │   ├── health.py
│   │   ├── recommends.py
│   │   └── replace.py
│   ├── core/                 # 인증/환경 설정 유틸
│   │   ├── auth.py
│   │   ├── jwt_key.py
│   │   └── settings.py
│   ├── models/               # Pydantic / LangGraph 상태 스키마
│   │   ├── __init__.py
│   │   ├── lg_schemas.py
│   │   └── schemas.py
│   ├── nodes/                # LangGraph 노드 (LLM, 검증, 변환)
│   │   ├── category_llm_node.py
│   │   ├── data_ingestion.py
│   │   ├── hardfilter_node.py
│   │   ├── output_node.py
│   │   ├── sequence_llm_node.py
│   │   └── verification_node.py
│   ├── pipelines/            # LangGraph 플로우 정의
│   │   └── pipeline.py
│   ├── places_api/           # Google Places API 연동 모듈
│   │   ├── field_mask_helper.py
│   │   ├── nearby_search_service.py
│   │   ├── placeApi.py
│   │   ├── place_details_service.py
│   │   └── text_search_service.py
│   ├── tests/                # pytest 기반 테스트
│   │   ├── test_api_smoke.py
│   │   ├── test_data.py
│   │   └── test_filters.py
│   ├── utils/                # 공통 유틸리티
│   │   ├── filters/
│   │   │   ├── categories.py
│   │   │   └── hardfilter.py
│   │   └── timewindow.py
│   ├── weather/              # 날씨 데이터 어댑터
│   │   ├── kma.py
│   │   ├── openweather.py
│   │   ├── types.py
│   │   └── weather_urls.py
│   ├── convert_coord.py
│   ├── main.py               # uvicorn 진입점
│   └── server.py             # FastAPI 앱 팩토리
├── config.py                 # LLM/외부 API 설정
└── requirements.txt

📡 API Example
Request
POST /api/recommends/{coupleId}
{
  "user": {...},
  "partner": {...},
  "couple": {...},
  "trigger": {...}
  ....
}


Response
{
  "explain": "오늘 무드에 맞는 코스입니다~",
  "data": [
    {
      "seq": 1,
      "name": "러반로제레스토랑",
      "category": "restaurant",
      "lat": 37.5101,
      "lng": 127.1062,
      "mood_tag": "로맨틱",
      "food_tag": ["이탈리안"],
      "rating_avg": 4.5
      ....
    }
  ]
}

🤝 Tech Stack

Backend: FastAPI, Pydantic

AI/LLM: LangGraph, LangChain, LangSmith

Data Source: Google Places API, OpenWeather API

Infra: Docker, GitHub Actions

## ⚙️ 환경 변수

`src/config.py`와 `src/app/core/settings.py`에서 `.env`를 바로 읽어옵니다. 최소한 아래 값들을 설정해야 합니다.

```bash
SECRET_KEY=your-jwt-secret
GOOGLE_PLACES_API_KEY=your-google-places-api-key
OPENWEATHER_API_KEY=your-openweather-api-key
KMA_API_KEY=optional-kma-api-key
```

프로덕션에서는 LangChain/LLM 관련 API 키도 `.env`에 함께 배치하세요.
Auth 서비스 주소는 기본적으로 `src/config.py`에 하드코딩되어 있으니, 환경별로 다르면 값을 수정하세요.

📌 Roadmap

 Hard Filter → AI Agent → Validation → Output JSON 완성


🚀 Quickstart
# 0. 환경 변수 설정
# 프로젝트 루트에 .env 파일을 만들고 위 섹션의 키를 채웁니다

# 1. 가상환경 생성 & 활성화
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

# 2. 패키지 설치
pip install -r requirements.txt

# 3. 서버 실행 (FastAPI + LangGraph)
PYTHONPATH=src uvicorn app.server:app --reload
