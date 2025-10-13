# 🌌 PitterPetter_AI
> 연인의 심장 박동처럼, 두 사람의 취향을 맞춘 **AI 데이트 코스 플래너**

AI-powered Date Course Recommendation Service  
**FastAPI × LangGraph × LLM Agents**

👥 **팀원:** 민재, 재현, 용완

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
│   ├── api/                  # FastAPI 엔드포인트 (추천 API 등)
│   │   └── recommend.py
│   ├── core/                 # 공통 유틸/설정 (DB, 캐시, 예외처리 등)
│   │   └── logger.py
│   ├── filters/              # 하드필터/카테고리 필터 로직
│   │   ├── categories.py
│   │   └── hardfilter.py
│   ├── models/               # 스키마 (Pydantic, LangGraph State 등)
│   │   ├── schemas.py
│   │   └── lg_schemas.py
│   ├── nodes/                # LangGraph 노드 (LLM 호출, 검증, 출력)
│   │   ├── category_llm_node.py
│   │   ├── sequence_llm_node.py
│   │   ├── verification_node.py
│   │   └── output_node.py
│   ├── pipelines/            # LangGraph 파이프라인 정의
│   │   └── pipeline.py
│   ├── places_api/           # Google Places API 연동 모듈
│   │   ├── text_search_service.py
│   │   ├── place_details_service.py
│   │   └── nearby_search_service.py
│   ├── utils/
│   │   └── field_mask_helper.py
│   ├── weather/              # 날씨 API 연동 (OpenWeather 등)
│   │   └── weather_service.py
│   └── __init__.py
├── server.py                 # FastAPI 엔트리포인트
├── main.py                   # 실행용 진입점 (uvicorn)
├── config.py                 # 설정 (LLM, API 키 등)
└── tests/                    # 테스트 (pytest)
    ├── test_api.py
    ├── test_data.py
    └── test_filters.py

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

Data Source: Google Places API, Opne Weather API

Infra: Docker, GitHub Actions , ....

📌 Roadmap

 Hard Filter → AI Agent → Validation → Output JSON 완성


🚀 Quickstart
# 1. 가상환경 생성 & 활성화
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

# 2. 패키지 설치
pip install -r requirements.txt

# 3. 서버 실행 (FastAPI + LangGraph)
PYTHONPATH=src uvicorn src.app.server:app —reload
