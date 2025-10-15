# src/app/api/recommends.py
from fastapi import APIRouter, Depends, HTTPException, Request
from app.core.auth import verify_token
from app.models.lg_schemas import State
from app.pipelines.pipeline import build_workflow
from app.utils.filters.categories import ALL_CATEGORIES
from config import AUTH_SERVICE_URL
import httpx
import traceback
import json

router = APIRouter()

graph = build_workflow()
app = graph.compile()

@router.post("/recommends")
async def recommend_course(
    body: dict,
    request: Request,
    token_payload: dict = Depends(verify_token)
):
    """
    추천 코스 생성 API
    - Header: Authorization: Bearer <JWT>
    - Body: user_choice 정보
    """
    print("\n===============================")
    print("📡 [AI-Service] Recommend API 호출 시작")
    print("===============================")

    # 1️⃣ JWT에서 사용자 정보 추출
    user_id = token_payload.get("userId")
    couple_id = token_payload.get("coupleId")
    print(f"🔐 토큰 payload = {json.dumps(token_payload, ensure_ascii=False)}")
    print (f"👤 userId={user_id}, coupleId={couple_id}")
    
    if not couple_id:
        print("❌ CoupleId 누락")
        raise HTTPException(status_code=401, detail="CoupleId 누락")

    # 💡 Authorization 헤더 추출
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        print("❌ Authorization 헤더 없음")
        raise HTTPException(status_code=401, detail="Authorization Header is missing in the request.")

    # 2️⃣ Auth 서비스 요청 URL 구성
    auth_url = f"{AUTH_SERVICE_URL}/api/couples/{couple_id}/recommendation-data"
    headers = {"Authorization": auth_header}
    print(f"🌐 Auth 서비스 URL: {auth_url}")
    print(f"📬 전송 헤더: {headers}")

    # 3️⃣ Auth 서비스 호출 (디버깅용 로그 포함)
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(auth_url, headers=headers)
            print(f"✅ Auth 응답 상태코드: {response.status_code}")
            if response.status_code != 200:
                print(f"⚠️ Auth 응답 본문: {response.text[:500]}")
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Auth 요청 실패: {response.text}"
                )
            auth_data = response.json()
            print("✅ Auth 데이터 수신 완료")
            print(f"👤 Auth 응답 데이터: {json.dumps(auth_data, ensure_ascii=False)[:500]}")

    except httpx.ConnectError as e:
        print("❌ [ConnectError] Auth 서비스 연결 실패:", str(e))
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Auth 연결 실패: {str(e)}")

    except httpx.ReadTimeout:
        print("❌ [Timeout] Auth 서비스 응답 지연 (10초 초과)")
        raise HTTPException(status_code=504, detail="Auth 응답 지연 (Timeout)")

    except httpx.RequestError as e:
        print(f"❌ [RequestError] {type(e)}: {str(e)}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Auth 요청 중 예외 발생: {str(e)}")

    except Exception as e:
        print(f"❌ [Unexpected Error] {type(e)}: {str(e)}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"예상치 못한 오류: {str(e)}")

    # 4️⃣ Auth 응답 파싱
    try:
        data_block = auth_data.get("data", {}) 
        user = auth_data.get("user", {})
        partner = auth_data.get("partner", {})
        couple_data = auth_data.get("couple", {})
        print(f"👤 user={bool(user)}, partner={bool(partner)}, couple={bool(couple_data)}")

    except Exception as e:
        print("❌ Auth 응답 파싱 실패:", str(e))
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Auth 응답 파싱 실패")

    # 5️⃣ Body에서 user_choice 받기
    user_choice = body.get("user_choice", {})
    print(f"🧭 user_choice = {json.dumps(user_choice, ensure_ascii=False)}")
    
    
        # user_choice에 startTime/endTime이 있고 time_window 없으면 자동 변환
    if "time_window" not in user_choice:
        if user_choice.get("startTime") and user_choice.get("endTime"):
            from datetime import datetime

            try:
                start_str = datetime.fromisoformat(user_choice["startTime"].replace("Z", "+00:00")).strftime("%H:%M")
                end_str = datetime.fromisoformat(user_choice["endTime"].replace("Z", "+00:00")).strftime("%H:%M")
                user_choice["time_window"] = [start_str, end_str]
            except Exception as e:
                print(f"⚠️ time_window 변환 실패: {e}")
                user_choice["time_window"] = ["00:00", "23:59"]


    # 6️⃣ LangGraph 파이프라인 실행
    try:
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

        print("⚙️ LangGraph 실행 시작...")
        final_state = await app.ainvoke(state)
        print("✅ LangGraph 실행 완료")

    except Exception as e:
        print("❌ LangGraph 실행 중 오류 발생:", str(e))
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"LangGraph 실행 오류: {str(e)}")

    # 7️⃣ 최종 응답
    print("🎯 추천 결과 개수:", len(final_state.get("recommendations", [])))
    print("===============================\n")

    return {
        "explain": "오늘 무드에 맞는 코스입니다~",
        "data": final_state.get("recommendations", []),
    }


'''
#로컬 테스트용

@router.post("/recommends")
async def recommend_course(request: dict):

    user = request.get("user", {})
    partner = request.get("partner", {})
    couple_data = request.get("couple", {})
    user_choice = request.get("user_choice", {})
    
    
    # user_choice에 startTime/endTime이 있고 time_window 없으면 자동 변환
    if "time_window" not in user_choice:
        if user_choice.get("startTime") and user_choice.get("endTime"):
            from datetime import datetime

            try:
                start_str = datetime.fromisoformat(user_choice["startTime"].replace("Z", "+00:00")).strftime("%H:%M")
                end_str = datetime.fromisoformat(user_choice["endTime"].replace("Z", "+00:00")).strftime("%H:%M")
                user_choice["time_window"] = [start_str, end_str]
            except Exception as e:
                print(f"⚠️ time_window 변환 실패: {e}")
                user_choice["time_window"] = ["00:00", "23:59"]


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