from fastapi import APIRouter, Depends, HTTPException, Request
from app.core.auth import verify_token
from app.models.lg_schemas import State
from app.pipelines.pipeline import build_workflow
from app.utils.filters.categories import ALL_CATEGORIES
import httpx
from config import AUTH_SERVICE_URL


router = APIRouter()

graph = build_workflow()
app = graph.compile()


# ---------------------------
# 시간 문자열에서 HH:MM만 추출하는 헬퍼 함수
# ---------------------------
def extract_hh_mm(date_string: str | None) -> str | None:
    if not date_string:
        return None

    try:
        parts = date_string.split()
        time_with_seconds = parts[4]
        return time_with_seconds[:5]
    except (IndexError, AttributeError, TypeError) as e:
        print(f"[ERROR] 시간 문자열 파싱 실패: {date_string}, 오류: {e}")
        return None


# ---------------------------
# 추천 코스 생성 API
# ---------------------------
@router.post("/recommends")
async def recommend_course(
    body: dict,
    request: Request,
    token_payload: dict = Depends(verify_token)
):
    user_id = token_payload.get("userId")
    couple_id = token_payload.get("coupleId")

    if not couple_id:
        raise HTTPException(status_code=401, detail="CoupleId 누락")

    auth_header = request.headers.get("Authorization")
    if not auth_header:
        raise HTTPException(status_code=401, detail="Authorization Header is missing in the request.")

    async with httpx.AsyncClient() as client:
        auth_url = f"{AUTH_SERVICE_URL}/api/couples/{couple_id}/recommendation-data"
        headers = {"Authorization": auth_header}
        response = await client.get(auth_url, headers=headers)

    if response.status_code != 200:
        error_detail = f"Auth 서비스 요청 실패. Status: {response.status_code}, Detail: {response.text}"
        print(f"ERROR: {error_detail}")
        raise HTTPException(status_code=500, detail=error_detail)

    auth_data = response.json()
    user = auth_data.get("user", {})
    partner = auth_data.get("partner", {})
    couple_data = auth_data.get("couple", {})

    user_choice = body.get("user_choice", {})

    start_time_value = user_choice.get("startTime")
    end_time_value = user_choice.get("endTime")

    start_hh_mm = extract_hh_mm(start_time_value)
    end_hh_mm = extract_hh_mm(end_time_value)

    if not start_hh_mm or not end_hh_mm:
        print(f"[WARN] 시간 포맷 불일치: start={start_time_value}, end={end_time_value}")
        user_choice["time_window"] = ["10:00", "22:00"]
    else:
        user_choice["time_window"] = [start_hh_mm, end_hh_mm]

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
