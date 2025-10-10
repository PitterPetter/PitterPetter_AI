import json
from typing import Dict, Any, List, Optional
from langsmith import Client
from app.models.lg_schemas import AgentResponse, State
from config import llm, PLACES_API_FIELDS
from app.places_api.nearby_search_service import search_nearby  # ✅ 교체 핵심

# ✅ LangSmith 클라이언트 초기화
try:
    client = Client()
except Exception as e:
    print(f"⚠️ LangSmith Client 초기화 실패. 오류: {e}")
    client = None


# ✅ Google Places → 단순 POI 정제 함수
def simplify_places(raw_places: list[dict]) -> list[dict]:
    simplified = []
    for p in raw_places:
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
        })
    return simplified


# ✅ Google Places 타입 매핑 (category → included_types)
TYPE_MAP = {
    "restaurant": "restaurant",
    "cafe": "cafe",
    "bar": "bar",
    "walk": "park",
    "exhibit": "museum",
    "attraction": "tourist_attraction",
    "view": "tourist_attraction",
    "nature": "natural_feature",
    "shopping": "shopping_mall",
    "performance": "movie_theater",
    "activity": "point_of_interest",
}


# ✅ 공통 POI 검색 및 LLM 처리 함수
def category_poi_get(
    state: State,
    category: str,
    prompt_name: str,
    keyword: Optional[str] = None,
    *,
    radius_m: Optional[int] = None,
    language: str = "ko",
    idx: Optional[int] = None,
) -> Dict[str, Any]:

    print(f"✅ {category} 추천 에이전트 실행")

    # -----------------------------
    # 위치 추출
    # -----------------------------
    user_choice = state.get("user_choice", {})
    lat, lng = None, None
    if "start" in user_choice:
        start = user_choice["start"]
        if isinstance(start, (list, tuple)) and len(start) == 2:
            lng, lat = start  # [lng, lat] → (lat, lng)
            print(f"📍 trigger.start 사용 → lat={lat}, lng={lng}")

    if lat is None or lng is None:
        print("⚠️ 위치 정보 없음 → 기본값 (잠실) 사용")
        lat, lng = 37.5, 127.1

    if radius_m is None:
        radius_m = user_choice.get("radius_m", 2000)

    # ✅ 반드시 추가
    search_location = (lat, lng)

    # -----------------------------
    # 🔒 지역 잠금 처리 (추후 확장용)
    # -----------------------------
    unlocked_districts = user_choice.get("districts_unlocked", [])  # 예: ["송파구", "강남구"]
    # TODO: 나중에 reverse geocoding으로 실제 구 단위 잠금 처리 가능

    # -----------------------------
    # Google Places Nearby Search 호출
    # -----------------------------
    included_type = TYPE_MAP.get(category, category)
    print(f"📡 Google Places Nearby Search 실행: {included_type}, 반경={radius_m}m, 위치=({lat}, {lng})")

    try:
        raw_resp = search_nearby(
            location=search_location,
            radius=radius_m,
            included_types=[included_type],
            language=language,
        )
        raw_places = raw_resp.get("places", [])
    except Exception as e:
        print(f"⛔️ Google Nearby API 호출 실패: {e}")
        return {"recommendations": [], "poi_data_delta": {category: []}}

    if not raw_places:
        print(f"⛔️ '{included_type}' 카테고리 POI 없음")
        return {"recommendations": [], "poi_data_delta": {category: []}}

    poi_delta = {category: raw_places}
    places = simplify_places(raw_places)

    # -----------------------------
    # LLM 입력 데이터 구성
    # -----------------------------
    input_data = {
        "var2": json.dumps(state.get("available_categories", []), ensure_ascii=False, indent=2),
        "user1": json.dumps(state.get("user", {}), ensure_ascii=False, indent=2),
        "user2": json.dumps(state.get("partner", {}), ensure_ascii=False, indent=2),
        "couple": json.dumps(state.get("couple", {}), ensure_ascii=False, indent=2),
        "trigger": json.dumps(state.get("user_choice", {}), ensure_ascii=False, indent=2),
        "question": state.get("query", ""),
        "poi_data": json.dumps(places, ensure_ascii=False),
        "previous_recommendations": json.dumps(
            state.get("previous_recommendations", []), ensure_ascii=False, indent=2
        ),
        "already_selected_pois": json.dumps(
            state.get("already_selected_pois", []), ensure_ascii=False, indent=2
        ),
    }

    # -----------------------------
    # LLM 실행
    # -----------------------------
    try:
        if not client:
            raise Exception("LangSmith Client not initialized")

        prompt = client.pull_prompt(prompt_name)
        messages = prompt.format_prompt(**input_data).to_messages()

        # ✅ JSON 스키마 강제
        llm_with_schema = llm.with_structured_output(AgentResponse)
        result: AgentResponse = llm_with_schema.invoke(messages)

        payload = []
        if result and result.data:
            for rec in result.data:
                rec_dict = rec.dict()
                if idx is not None:
                    rec_dict["seq"] = idx + 1
                rec_dict["category"] = category
                payload.append(rec_dict)

        print(f"📤 {category} 응답 with idx={idx}:")
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        print(f"✔️ {category} 추천 완료 (개수 {len(payload)})")

        return {"recommendations": payload, "poi_data_delta": poi_delta}

    except Exception as e:
        print(f"⛔️ {category} LLM 실행 오류: {e}")
        return {"recommendations": [], "poi_data_delta": {category: []}}


# ✅ 개별 카테고리 에이전트 노드 정의
def restaurant_agent_node(state: State, idx: Optional[int] = None) -> Dict[str, Any]:
    return category_poi_get(state, "restaurant", "restaurant_prompt", "맛집 OR 레스토랑", idx=idx)

def cafe_agent_node(state: State, idx: Optional[int] = None) -> Dict[str, Any]:
    return category_poi_get(state, "cafe", "cafe_prompt", "카페", idx=idx)

def bar_agent_node(state: State, idx: Optional[int] = None) -> Dict[str, Any]:
    return category_poi_get(state, "bar", "bar_prompt", "바 OR 펍", idx=idx)

def activity_agent_node(state: State, idx: Optional[int] = None) -> Dict[str, Any]:
    return category_poi_get(state, "activity", "activity_prompt", "체험 액티비티", idx=idx)

def attraction_agent_node(state: State, idx: Optional[int] = None) -> Dict[str, Any]:
    return category_poi_get(state, "attraction", "attraction_prompt", "명소 관광지", idx=idx)

def exhibit_agent_node(state: State, idx: Optional[int] = None) -> Dict[str, Any]:
    return category_poi_get(state, "exhibit", "exhibit_prompt", "전시회 전시장", idx=idx)

def walk_agent_node(state: State, idx: Optional[int] = None) -> Dict[str, Any]:
    return category_poi_get(state, "walk", "walk_prompt", "산책로 공원 산책", idx=idx)

def view_agent_node(state: State, idx: Optional[int] = None) -> Dict[str, Any]:
    return category_poi_get(state, "view", "view_prompt", "야경 전망대 뷰맛집", idx=idx)

def nature_agent_node(state: State, idx: Optional[int] = None) -> Dict[str, Any]:
    return category_poi_get(state, "nature", "nature_prompt", "자연 경치 숲길", idx=idx)

def shopping_agent_node(state: State, idx: Optional[int] = None) -> Dict[str, Any]:
    return category_poi_get(state, "shopping", "shopping_prompt", "쇼핑몰 상가 쇼핑", idx=idx)

def performance_agent_node(state: State, idx: Optional[int] = None) -> Dict[str, Any]:
    return category_poi_get(state, "performance", "performance_prompt", "공연 연극 콘서트", idx=idx)
