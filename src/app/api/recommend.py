# src/app/api/recommend.py
from fastapi import APIRouter
from app.models.schemas import State
from app.pipelines.pipeline import build_workflow

router = APIRouter()

graph = build_workflow()
app = graph.compile()

@router.post("/api/recommends/{coupleId}")
async def recommend_course(coupleId: str, request: dict):
    """
    데이트 코스 추천 API
    Request Body:
    {
      "user": {...},      # 첫 번째 유저
      "partner": {...},   # 두 번째 유저
      "couple": {...},    # 커플 데이터
      "trigger": {...}    # 트리거 데이터
    }
    """

    user1_data = request.get("user", {})
    user2_data = request.get("partner", {})
    couple_data = request.get("couple", {})
    trigger_data = request.get("trigger", {})

    # LangGraph 상태 초기화
    state: State = {
        "query": "데이트 추천",
        "user1_data": user1_data,
        "user2_data": user2_data,
        "trigger_data": trigger_data,
        "poi_data": None,
        "available_categories": [
            "restaurant", "cafe", "bar",
            "activity", "attraction", "exhibit",
            "walk", "view", "nature",
            "shopping", "performance",
        ],
        "recommended_sequence": [],
        "recommendations": [],
        "current_judge": None,
        "judgement_reason": None,
        "final_output": None,
        "check_count": 0,
        "couple_data": couple_data,
    }

    final_state = app.invoke(state)

    # LLM/Agent가 만든 결과를 그대로 꺼내기
    return {
        "explain": "오늘 무드에 맞는 코스입니다~",  # # # # # # #수정하겠습니다~
        "data": final_state.get("recommendations", []),
    }