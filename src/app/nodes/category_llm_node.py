# nodes/category_llm_node.py
import json, time, re
from typing import Dict, Any, List, Tuple, Optional
from langsmith import Client
from app.models.lg_schemas import AgentResponse
from app.models.lg_schemas import State
from app.places_api.placeApi import get_poi_data
from config import llm, PLACES_API_FIELDS

# ✅ 추가: 타임아웃용
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError

# LLM 동기 호출 타임아웃 실행기 (필요에 따라 max_workers 조정)
_LLM_EXECUTOR = ThreadPoolExecutor(max_workers=4)

def _invoke_with_timeout(fn, *args, timeout: float = 10.0, **kwargs):
    """동기 함수 fn(*args, **kwargs)를 별도 스레드에서 실행하고 timeout초 내 결과를 받음.
    제한 초과 시 None 반환."""
    fut = _LLM_EXECUTOR.submit(fn, *args, **kwargs)
    try:
        return fut.result(timeout=timeout)
    except FuturesTimeoutError:
        return None

try:
    client = Client()
except Exception as e:
    print(f"⚠️ LangSmith Client 초기화 실패. 오류: {e}")
    client = None


def simplify_places(raw_places: list[dict]) -> list[dict]:
    simplified = []
    for p in raw_places:
        open_hours = {}

        hours_info = p.get("regularOpeningHours", {})

        # 우선 weekdayDescriptions 사용
        weekday_desc = hours_info.get("weekdayDescriptions", [])
        if weekday_desc:
            # ["월요일: 09:00 – 18:00", ...] 그대로 매핑
            days = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
            for i, desc in enumerate(weekday_desc):
                if i < len(days):
                    open_hours[days[i]] = desc.split(":", 1)[-1].strip()
        else:
            # periods 기반 파싱 (day 숫자 → 요일 매핑)
            periods = hours_info.get("periods", [])
            days = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
            for period in periods:
                open_day = period.get("open", {})
                close_day = period.get("close", {})
                d = open_day.get("day")
                if d is not None:
                    open_time = f"{open_day.get('hour',0):02d}:{open_day.get('minute',0):02d}"
                    close_time = f"{close_day.get('hour',0):02d}:{close_day.get('minute',0):02d}"
                    open_hours[days[d]] = f"{open_time}-{close_time}"

        simplified.append({
            "id": p.get("id"),
            "name": (p.get("displayName") or {}).get("text"),
            "address": p.get("formattedAddress"),
            "lat": (p.get("location") or {}).get("latitude"),
            "lng": (p.get("location") or {}).get("longitude"),
            "price_level": p.get("priceLevel"),
            "rating": p.get("rating"),
            "review_count": p.get("userRatingCount"),
            "type": p.get("primaryType"),
            "review": ((p.get("reviews") or [{}])[0].get("text") or {}).get("text"),
            "open_hours": open_hours,
        })
    return simplified


# ✅ 추가: open_hours 키 고정 + 기본값 채우기
def _normalize_open_hours(oh: Optional[dict]) -> dict:
    days = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
    out = {}
    if isinstance(oh, dict) and oh:
        # 문자열 그대로 복사 (없으면 rand)
        for d in days:
            v = oh.get(d)
            if isinstance(v, str) and v.strip():
                out[d] = v
            else:
                out[d] = "rand"
    else:
        # 통째로 없으면 전부 rand
        for d in days:
            out[d] = "rand"
    return out


# ✅ 추가: LLM 실패/타임아웃 시 스키마에 맞는 기본값 생성
def _fallback_from_first_place(category: str, places: list[dict], seq_idx: Optional[int]):
    """실패 시 최소한의 상태 정보만 반환"""
    return {
        "status": "failed",
        "category": category,
        "seq": (seq_idx + 1) if seq_idx is not None else None
    }
    
    
# 🚩 함수명 -> 카테고리 별 poi 선별 로직 
def category_poi_get(
    state: State,
    category: str,
    prompt_name: str,
    search_query: str | None = None,
    *,
    search_location: Tuple[float, float] | None = None,
    radius_m: int | None = None,
    language: str = "ko",
    idx: int | None = None,   # ✅ 시퀀스 인덱스 추가
) -> Dict[str, Any]:
    print(f"✅ {category} 추천 에이전트 실행")

    user_choice = state.get("user_choice", {})
    user = state.get("user", {})
    partner = state.get("partner", {})
    couple = state.get("couple", {})
    
    lat = user_choice.get("lat")
    lng = user_choice.get("lng")

    # fallback: start 배열에서 꺼내기
    if (lat is None or lng is None) and "start" in user_choice:
        start = user_choice.get("start")
        if isinstance(start, (list, tuple)) and len(start) == 2:
            lng, lat = start  # [lng, lat]
            print(f"📍 trigger.start 사용 → lat={lat}, lng={lng}")

    if search_location is None:
        if lat is None or lng is None:
            print("⚠️ 위치 정보 없음 → 기본값 (잠실) 사용")
            search_location = (37.5, 127.1)
        else:
            search_location = (lat, lng)

    # 파라미터 기본값
    if not search_query:
        search_query = category
    if radius_m is None:
        radius_m = user_choice.get("radius_m", 2000)

    raw_places = get_poi_data(
        query=search_query,
        location=search_location,
        radius=radius_m,
        language=language,
        page_delay_sec=2.0,
    )
    if not raw_places:
        print(f"⛔️ '{search_query}' POI 데이터 없음")
        return {"recommendations": [], "poi_data_delta": {category: []}}
    
    poi_delta = {category: raw_places}
    places = simplify_places(raw_places)     
    
    # LLM 입력 (필요 변수만)
    input_data = {
        "var2": json.dumps(state.get("available_categories", []), ensure_ascii=False, indent=2),
        "user1": json.dumps(user, ensure_ascii=False, indent=2),
        "user2": json.dumps(partner, ensure_ascii=False, indent=2),
        "couple": json.dumps(couple, ensure_ascii=False, indent=2),
        "trigger": json.dumps(user_choice, ensure_ascii=False, indent=2),
        "question": state.get("query", ""),
        "poi_data": json.dumps(places, ensure_ascii=False),
    }

    try:
        if not client:
            raise Exception("LangSmith Client not initialized")

        prompt = client.pull_prompt(prompt_name)
        messages = prompt.format_prompt(**input_data).to_messages()

        # ✅ JSON 스키마 강제 + 10초 타임아웃
        llm_with_schema = llm.with_structured_output(AgentResponse)
        result: Optional[AgentResponse] = _invoke_with_timeout(
            llm_with_schema.invoke, messages, timeout=10.0
        )

        payload = []
        if result and getattr(result, "data", None):
            for rec in result.data:
                rec_dict = rec.dict()
                if idx is not None:
                    rec_dict["seq"] = idx + 1
                rec_dict["category"] = category

                # open_hours 보정: mon~sun 보장
                rec_dict["open_hours"] = _normalize_open_hours(rec_dict.get("open_hours"))

                payload.append(rec_dict)
        else:
            # ⏰ 타임아웃/오류 → 첫 POI 기반 fallback
            payload = _fallback_from_first_place(category, places, idx)

        print(f"📤 {category} 응답 with idx={idx}:")
        print(json.dumps(payload, ensure_ascii=False, indent=2))

        print(f"✔️ {category} 추천 완료 (개수 {len(payload)})")
        return {"recommendations": payload, "poi_data_delta": poi_delta}

    except Exception as e:
        print(f"⛔️ {category} 노드 실행 오류: {e}")
        return {
            "recommendations": [],
            "poi_data_delta": {category: []},
            "status": "failed"
        }

# --- 카테고리별 노드 ---
def restaurant_agent_node(state: State, idx: int | None = None) -> Dict[str, Any]:
    return category_poi_get(state, "restaurant", "restaurant_prompt", "맛집 OR 레스토랑", idx=idx)

def cafe_agent_node(state: State, idx: int | None = None) -> Dict[str, Any]:
    return category_poi_get(state, "cafe", "cafe_prompt", "카페", idx=idx)

def bar_agent_node(state: State, idx: int | None = None) -> Dict[str, Any]:
    return category_poi_get(state, "bar", "bar_prompt", "바 OR 펍", idx=idx)

def activity_agent_node(state: State, idx: int | None = None) -> Dict[str, Any]:
    return category_poi_get(state, "activity", "activity_prompt", "체험 액티비티", idx=idx)

def attraction_agent_node(state: State, idx: int | None = None) -> Dict[str, Any]:
    return category_poi_get(state, "attraction", "attraction_prompt", "명소 관광지", idx=idx)

def exhibit_agent_node(state: State, idx: int | None = None) -> Dict[str, Any]:
    return category_poi_get(state, "exhibit", "exhibit_prompt", "전시회 전시장", idx=idx)

def walk_agent_node(state: State, idx: int | None = None) -> Dict[str, Any]:
    return category_poi_get(state, "walk", "walk_prompt", "산책로 공원 산책", idx=idx)

def view_agent_node(state: State, idx: int | None = None) -> Dict[str, Any]:
    return category_poi_get(state, "view", "view_prompt", "야경 전망대 뷰맛집", idx=idx)

def nature_agent_node(state: State, idx: int | None = None) -> Dict[str, Any]:
    return category_poi_get(state, "nature", "nature_prompt", "자연 경치 숲길", idx=idx)

def shopping_agent_node(state: State, idx: int | None = None) -> Dict[str, Any]:
    return category_poi_get(state, "shopping", "shopping_prompt", "쇼핑몰 상가 쇼핑", idx=idx)

def performance_agent_node(state: State, idx: int | None = None) -> Dict[str, Any]:
    return category_poi_get(state, "performance", "performance_prompt", "공연 연극 콘서트", idx=idx)
