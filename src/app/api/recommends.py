from fastapi import APIRouter, Depends, HTTPException, Request
from app.core.auth import verify_token
from app.models.lg_schemas import State
from app.pipelines.pipeline import build_workflow
from app.utils.filters.categories import ALL_CATEGORIES
from config import AUTH_SERVICE_URL

import httpx
import re
from datetime import datetime
from typing import Tuple


router = APIRouter()

# LangGraph 파이프라인 초기화
graph = build_workflow()
app = graph.compile()


# ---------------------------
# 시간 문자열에서 HH:MM 추출 (브라우저 로컬 or ISO 모두 지원)
# ---------------------------
def extract_hh_mm(date_string: str | None) -> str | None:
    """
    가능한 포맷 모두 처리:
    - "Tue Oct 14 2025 15:41:51 GMT+0900 (한국 표준시)"
    - "2025-10-14T06:43:54.081Z"
    - "2025-10-14T15:41:51+09:00"
    """
    if not date_string:
        return None

    s = str(date_string)

    # 1) "HH:MM:SS" 패턴이 포함되어 있다면 그대로 추출
    m = re.search(r'(\d{2}:\d{2}):\d{2}', s)
    if m:
        return m.group(1)

    # 2) ISO 포맷 처리
    try:
        if "T" in s:
            iso = s.replace("Z", "+00:00") if s.endswith("Z") else s
            dt = datetime.fromisoformat(iso)
            return dt.strftime("%H:%M")
    except Exception as e:
        print(f"[DEBUG] ISO 파싱 실패: {s} -> {e}")

    # 3) 브라우저 Date.toString() 형태 처리
    parts = s.split()
    if len(parts) >= 5:
        try:
            time_with_seconds = parts[4]
            if re.match(r'^\d{2}:\d{2}:\d{2}$', time_with_seconds):
                return time_with_seconds[:5]
        except Exception:
            pass

    print(f"[WARN] 알 수 없는 시간 포맷: {s}")
    return None


# ---------------------------
# 좌표 정규화: [lat, lon]인지 [lon, lat]인지 자동 판단
# ---------------------------
def normalize_lat_lon(coords) -> Tuple[float | None, float | None]:
    """
    coords: [a, b]
    반환: (lat, lon)
    """
    if not coords or len(coords) != 2:
        return None, None

    try:
        a = float(coords[0])
        b = float(coords[1])
    except Exception:
        return None, None

    # 위도는 ±90을 넘지 않음. 경도는 ±180까지.
    if abs(a) > 90 and abs(b) <= 90:
        lat, lon = b, a  # swap
    else:
        lat, lon = a, b

    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        print(f"[WARN] 정규화 후 범위 벗어남: lat={lat}, lon={lon}")
        return None, None

    return lat, lon


# ---------------------------
# 추천 코스 생성 API
# ---------------------------
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

    # 1️⃣ JWT에서 사용자 정보 추출
    user_id = token_payload.get("userId")
    couple_id = token_payload.get("coupleId")

    if not couple_id:
        raise HTTPException(status_code=401, detail="CoupleId 누락")

    auth_header = request.headers.get("Authorization")
    if not auth_header:
        raise HTTPException(status_code=401, detail="Authorization Header is missing in the request.")

    # 2️⃣ Auth 서비스 호출
    async with httpx.AsyncClient() as client:
        auth_url = f"{AUTH_SERVICE_URL}/api/couples/{couple_id}/recommendation-data"
        headers = {"Authorization": auth_header}
        try:
            response = await client.get(auth_url, headers=headers)
        except httpx.ConnectError:
            raise HTTPException(status_code=502, detail="Auth 서비스 연결 실패 (ConnectError)")

    if response.status_code != 200:
        error_detail = f"Auth 서비스 요청 실패. Status: {response.status_code}, Detail: {response.text}"
        print(f"ERROR: {error_detail}")
        raise HTTPException(status_code=500, detail=error_detail)

    auth_data = response.json()
    user = auth_data.get("user", {})
    partner = auth_data.get("partner", {})
    couple_data = auth_data.get("couple", {})

    # 3️⃣ user_choice 파싱
    user_choice = body.get("user_choice", {}) or {}

    # (1) 시간 파싱
    start_time_value = user_choice.get("startTime")
    end_time_value = user_choice.get("endTime")

    start_hh_mm = extract_hh_mm(start_time_value)
    end_hh_mm = extract_hh_mm(end_time_value)

    if not start_hh_mm or not end_hh_mm:
        print(f"[WARN] 시간 포맷 불일치: start={start_time_value}, end={end_time_value}")
        user_choice["time_window"] = ["10:00", "22:00"]  # fallback
    else:
        user_choice["time_window"] = [start_hh_mm, end_hh_mm]

    # (2) 좌표 정규화
    start_coords = user_choice.get("start")
    lat, lon = normalize_lat_lon(start_coords)
    if lat is None or lon is None:
        print(f"[ERROR] start 좌표가 유효하지 않음: {start_coords}")
        raise HTTPException(status_code=400, detail=f"유효하지 않은 좌표 형식: {start_coords}")
    else:
        user_choice["start"] = [lat, lon]

    # 4️⃣ LangGraph 상태 초기화
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

    # 5️⃣ LangGraph 실행
    final_state = await app.ainvoke(state)

    return {
        "explain": "오늘 무드에 맞는 코스입니다~",
        "data": final_state.get("recommendations", []),
    }
