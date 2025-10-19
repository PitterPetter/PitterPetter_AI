import json
import re
from math import atan2, cos, radians, sin, sqrt
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


# ✅ 다국어 상호명에서 한글명을 우선 선택
_HANGUL_PATTERN = re.compile(r"[\u1100-\u11FF\u3130-\u318F\uAC00-\uD7AF]")


def _candidate_name_segments(raw_text: str) -> List[str]:
    segments: List[str] = []
    for chunk in re.split(r"[\n/|]+", raw_text):
        chunk = chunk.strip()
        if not chunk:
            continue
        for piece in re.split(r"[()\[\]]+", chunk):
            piece = piece.strip()
            if piece:
                segments.append(piece)
    return segments or [raw_text.strip()]


def _prefer_korean_name(display_name: Optional[Dict[str, Any]]) -> Optional[str]:
    if not display_name:
        return None

    raw_text = (display_name.get("text") or "").strip()
    if not raw_text:
        return None

    for segment in _candidate_name_segments(raw_text):
        if _HANGUL_PATTERN.search(segment):
            return segment

    return _candidate_name_segments(raw_text)[0]


# ✅ Google Places → 단순 POI 정제 함수
def simplify_places(raw_places: list[dict]) -> list[dict]:
    simplified = []
    for p in raw_places:
        display = p.get("displayName") or {}
        simplified.append({
            "id": p.get("id"),
            "name": _prefer_korean_name(display),
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
# Google Places API v1 Nearby Search - Trendy Mapping (<=5 each)
# Google Places API v1 Nearby Search - 데이트 코스 추천용으로 수정 및 검증된 매핑
TYPE_MAP = {
    "restaurant": [
        "restaurant",  # 'restaurant' 하나로 검색하는 것이 가장 넓고 안정적입니다.
    ],
    "cafe": [
        "cafe", "bakery", "ice_cream_shop",
    ],
    "bar": [
        "bar", "night_club",  # pub, wine_bar는 검색용 타입이 아니므로 bar로 통합 검색합니다.
    ],
    "activity": [
        "amusement_center", "bowling_alley", "gym", "spa", "movie_theater", "performing_arts_theater",
    ],  # 공연 카테고리를 통합하여 실내 활동의 폭을 넓혔습니다.
    "attraction": [
        "tourist_attraction", "museum", "art_gallery", "aquarium", "zoo",
    ],
    "exhibit": [
        "museum", "art_gallery",  # 이 카테고리는 명확해서 그대로 사용합니다.
    ],
    "walk": [
        "park",  # trailhead, plaza 등은 검색 불가. 'park'로 검색하는 것이 가장 적합합니다.
    ],
    "view": [
        "tourist_attraction", # '전망'은 장소 유형이 아니므로, '관광 명소'로 검색 후 LLM이 판단하게 하는 것이 좋습니다. (아래 추가 제안 참고)
    ],
    "nature": [
        "park", "tourist_attraction", # mountain, lake 등 자연물은 검색 불가. '공원', '관광 명소'가 최선입니다.
    ],
    "shopping": [
        "shopping_mall", "department_store", "book_store", "market",
    ],
    # 'performance'는 activity에 통합하거나, 그대로 두어도 좋습니다.
    "performance": [
        "movie_theater", "performing_arts_theater", "stadium",
    ],
}

# ✅ 허버사인 거리를 미터 단위로 계산
def _distance_meters(origin: tuple[float, float], target: tuple[float, float]) -> float:
    lat1, lng1 = origin
    lat2, lng2 = target

    lat1_rad, lat2_rad = radians(lat1), radians(lat2)
    dlat = radians(lat2 - lat1)
    dlng = radians(lng2 - lng1)

    a = sin(dlat / 2) ** 2 + cos(lat1_rad) * cos(lat2_rad) * sin(dlng / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))

    return 6371000.0 * c  # 지구 반지름 (미터)


def _filter_places_within_radius(
    raw_places: List[Dict[str, Any]],
    center: tuple[float, float],
    radius_m: float,
) -> tuple[List[Dict[str, Any]], int]:
    filtered: List[Dict[str, Any]] = []
    removed = 0

    for place in raw_places:
        loc = place.get("location") or {}
        plat = loc.get("latitude")
        plng = loc.get("longitude")

        try:
            if plat is not None and plng is not None:
                distance = _distance_meters(center, (float(plat), float(plng)))
                if distance <= radius_m:
                    filtered.append(place)
                else:
                    removed += 1
            else:
                filtered.append(place)
        except (TypeError, ValueError):
            filtered.append(place)

    return filtered, removed


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
            lat,lng = start  # [lng, lat] → (lat, lng)
            print(f"📍 trigger.start 사용 → lat={lat}, lng={lng}")

    if lat is None or lng is None:
        print("⚠️ 위치 정보 없음 → 기본값 (잠실) 사용")
        lat, lng = 37.5, 127.1

    radius_source_km = False
    radius_candidate = radius_m
    if radius_candidate is None:
        radius_candidate = user_choice.get("radius_m")
    if radius_candidate is None and "radius_km" in user_choice:
        radius_candidate = user_choice.get("radius_km")
        radius_source_km = True

    try:
        radius_m_float = float(radius_candidate)
        if radius_source_km:
            radius_m_float *= 1000
    except (TypeError, ValueError):
        radius_m_float = 1000.0

    if radius_m_float <= 0:
        radius_m_float = 1000.0

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
    type_candidates = TYPE_MAP.get(category)
    if not type_candidates:
        type_candidates = [category]
    elif isinstance(type_candidates, str):
        type_candidates = [type_candidates]

    radius_request_value = int(radius_m_float)

    print(
        f"📡 Google Places Nearby Search 실행: {type_candidates}, 반경={radius_request_value}m, 위치=({lat}, {lng})"
    )

    try:
        raw_resp = search_nearby(
            location=search_location,
            radius=radius_request_value,
            included_types=type_candidates,
            language=language,
        )
        raw_places = raw_resp.get("places", [])
    except Exception as e:
        print(f"⛔️ Google Nearby API 호출 실패: {e}")
        return {"recommendations": [], "poi_data_delta": {category: []}}

    if not raw_places:
        print(f"⛔️ '{type_candidates}' 카테고리 POI 없음")
        return {"recommendations": [], "poi_data_delta": {category: []}}

    center = (float(search_location[0]), float(search_location[1]))
    raw_places, removed_count = _filter_places_within_radius(raw_places, center, radius_m_float)

    if removed_count:
        print(f"✂️ 반경 초과 POI 제외: {removed_count}개 (반경 {radius_m_float}m)")

    if not raw_places:
        print("⛔️ 반경 내 유효한 POI 없음")
        return {"recommendations": [], "poi_data_delta": {category: []}}

    poi_delta = {category: raw_places}
    places = simplify_places(raw_places)

    already_selected = state.get("already_selected_pois", []) or []
    previous_recs = state.get("previous_recommendations", []) or []
    exclude_pois = state.get("exclude_pois", []) or []

    def _poi_key(p: Dict[str, Any]) -> tuple:
        name = (p.get("name") or "").strip().lower()
        lat_val = p.get("lat")
        lng_val = p.get("lng")
        # 위치가 없을 수 있으므로, 이름만 일치하면 중복으로 간주
        return (
            name,
            round(float(lat_val), 6) if isinstance(lat_val, (int, float)) else None,
            round(float(lng_val), 6) if isinstance(lng_val, (int, float)) else None,
        )

    seen_keys = {
        _poi_key(p)
        for p in (*already_selected, *previous_recs, *exclude_pois)
        if p
    }

    filtered_places: List[Dict[str, Any]] = []
    for place in places:
        key = _poi_key(place)
        if key in seen_keys:
            continue
        filtered_places.append(place)
        seen_keys.add(key)

    if not filtered_places:
        print("⚠️ 모든 후보가 기존 추천과 중복되어 필터링됨")
        filtered_places = places  # 마지막 방어: LLM이 맥락 보고 판단하게 한다

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
        "poi_data": json.dumps(filtered_places, ensure_ascii=False),
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
