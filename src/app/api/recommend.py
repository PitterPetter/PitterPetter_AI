# src/app/api/recommend.py
from fastapi import APIRouter
from app.models.schemas import State
from app.pipelines.pipeline import build_workflow

router = APIRouter()

graph = build_workflow()
app = graph.compile()

@router.post("/api/recommends/{coupleId}")
async def recommend_course(coupleId: str, request: dict):

    user = request.get("user", {})
    partner = request.get("partner", {})
    couple_data = request.get("couple", {})
    user_choice = request.get("user_choice", {})

    state: State = {
        "query": "데이트 추천",
        "user": user,
        "partner": partner,
        "user_choice": user_choice,
        "couple": couple_data,
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
        "check_count": 0
    }

    final_state = app.invoke(state)





    # LLM/Agent가 만든 결과를 그대로 꺼내기
    return {
        "explain": "오늘 무드에 맞는 코스입니다~", 
        "data": final_state.get("recommendations", []),
    }