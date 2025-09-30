# src/app/api/recommend.py
from fastapi import APIRouter, Depends, HTTPException
from app.core.auth import verify_token  # JWT 검증 함수
from app.models.lg_schemas import State
from app.pipelines.pipeline import build_workflow

router = APIRouter()

graph = build_workflow()
app = graph.compile()

@router.post("/api/recommends/{coupleId}")
async def recommend_course(
    coupleId: str,
    body: dict,
    token_payload: dict = Depends(verify_token)  # JWT 토큰에서 user_id, couple_id 확인
):
    """
    추천 코스 생성 API
    - Header: Authorization: Bearer <JWT>
    - Body: user_choice 정보
    """

    # JWT에서 사용자 정보 확인
    user_id = token_payload.get("user_id")
    token_couple_id = token_payload.get("couple_id")

    if str(token_couple_id) != coupleId:
        raise HTTPException(status_code=403, detail="토큰의 couple_id와 요청 경로 불일치")

    # 스프링 서버에서 user / partner 데이터 가져오기 (TODO: 연동 필요)
    # 여기서는 일단 더미로 처리
    user = {"id": user_id, "name": "홍길동"}  
    partner = {"id": 2, "name": "김영희"}  
    couple_data = {"id": coupleId, "boyfriend_id": user_id, "girlfriend_id": 2}

    # Body에서 user_choice 받기
    user_choice = body.get("user_choice", {})

   # 로컬 request test용
   # user = request.get("user", {})
   # partner = request.get("partner", {})
   # couple_data = request.get("couple", {})
   # user_choice = request.get("user_choice", {})

    #langgraph 초기상태
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