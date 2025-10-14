 # src/app/api/recommends.py
from fastapi import APIRouter, Depends, HTTPException, Request # 💡 Request 임포트 추가
from app.core.auth import verify_token
from app.models.lg_schemas import State
from app.pipelines.pipeline import build_workflow
from app.utils.filters.categories import ALL_CATEGORIES
import httpx
from config import AUTH_SERVICE_URL
router = APIRouter()

graph = build_workflow()
app = graph.compile()

@router.post("/recommends")
async def recommend_course(
    body: dict, 
    request: Request, # 💡 Request 객체를 인자로 받습니다.
    token_payload: dict = Depends(verify_token)
):
    """
    추천 코스 생성 API
    - Header: Authorization: Bearer <JWT>
    - Body: user_choice 정보
    """

    # 1️⃣ JWT에서 사용자 정보 추출
    user_id = token_payload.get("userId")
    couple_id = token_payload.get("coupleId")

    if not couple_id:
        raise HTTPException(status_code=401, detail="CoupleId 누락")
        
    # 💡 [수정 부분] 원본 요청의 Authorization 헤더 추출
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        # verify_token이 동작했다면 이미 헤더가 있었겠지만, 안전하게 처리
        raise HTTPException(status_code=401, detail="Authorization Header is missing in the request.")

    # 2️⃣ Auth 서비스에서 커플/유저 정보 요청
    async with httpx.AsyncClient() as client:
        auth_url = f"{AUTH_SERVICE_URL}/api/couples/{couple_id}/recommendation-data"
        
        # 💡 [수정 부분] 추출한 헤더를 Auth 서비스로 전달
        headers = {
            "Authorization": auth_header
        }
        
        response = await client.get(auth_url, headers=headers) # 💡 headers 인자 추가
        
        if response.status_code != 200:
            # 💡 실패 시 Auth 서비스의 상세 응답을 포함하여 로그에 남깁니다.
            error_detail = f"Auth 서비스 요청 실패. Status: {response.status_code}, Detail: {response.text}"
            print(f"ERROR: {error_detail}") 
            raise HTTPException(status_code=500, detail=error_detail)
            
        auth_data = response.json()

    # 3️⃣ Auth 응답 파싱
    user = auth_data.get("user", {})
    partner = auth_data.get("partner", {})
    couple_data = auth_data.get("couple", {})

    # 4️⃣ Body에서 user_choice 받기
    user_choice = body.get("user_choice", {})

    # 5️⃣ LangGraph 상태 초기화
    state: State = {
        "query": "데이트 추천",
        "user": user,
        "partner": partner,
        "user_choice": user_choice,
        "couple": couple_data,
        "poi_data": None,
        "available_categories": ALL_CATEGORIES,
        "recommended_sequence": [],
        "recommendations": [],
        "current_judge": None,
        "judgement_reason": None,
        "final_output": None,
        "check_count": 0
    }

    final_state = await app.ainvoke(state)

    return {
        "explain": "오늘 무드에 맞는 코스입니다~",
        "data": final_state.get("recommendations", []),
    }


#로컬 테스트용
'''
@router.post("/recommends")
async def recommend_course(request: dict):

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
        "available_categories": ALL_CATEGORIES,
        "recommended_sequence": [],
        "recommendations": [],
        "current_judge": None,
        "judgement_reason": None,
        "final_output": None,
        "check_count": 0
    }

    #final_state = app.invoke(state)
    final_state = await app.ainvoke(state) 

    # LLM/Agent가 만든 결과를 그대로 꺼내기
    return {
        "explain": "오늘 무드에 맞는 코스입니다~", 
        "allowed_categories": final_state.get("allowed_categories"),
        "excluded_categories": final_state.get("excluded_categories"),
        "debug_weather": final_state.get("hardfilter_debug"),  # 🌟 디버그용
        "data": final_state.get("recommendations", []),
    }
    '''