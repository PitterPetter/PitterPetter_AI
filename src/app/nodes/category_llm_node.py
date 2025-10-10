# nodes/category_llm_node.py
import json, time, re
from typing import Dict, Any, List, Tuple,Optional
from langsmith import Client
from app.models.lg_schemas import AgentResponse
from app.models.lg_schemas import State
from app.places_api.placeApi import get_poi_data
from config import llm, PLACES_API_FIELDS

try:
    client = Client()
except Exception as e:
    print(f"⚠️ LangSmith Client 초기화 실패. 오류: {e}")
    client = None
    
# 장소 데이터 응답 스키마
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
            "review": ((p.get("reviews") or [{}])[0].get("text") or {}).get("text"),
        })
    return simplified

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

    user_choice = state.get("UserChoice_data", {})
        # trig = state.get("trigger_data", {})

    user = state.get("user_data", {})
    
    lat = user_choice.get("lat")
    lng = user_choice.get("lng")
    
    # fallback: start 배열에서 꺼내기
    if (lat is None or lng is None) and "start" in user_choice:
        start = user_choice.get("start")
        if isinstance(start, (list, tuple)) and len(start) == 2:
            lng, lat = start  # 🚩 [lng, lat] 순서였으니까 이렇게 언팩
            print(f"📍 trigger.start 사용 → lat={lat}, lng={lng}")

    if search_location is None:
        if lat is None or lng is None:
            print("⚠️ 위치 정보 없음 → 기본값 (잠실) 사용")
            search_location = (37.5, 127.1)
        else:
            search_location = (lat, lng)  # (lat, lng)

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
    
    # (선택) 카테고리별 POI를 러너가 병합할 수 있도록 delta 반환
    poi_delta = {category: raw_places}       # 원본은 state에 보관
    places = simplify_places(raw_places)     
    
    # LLM 입력 (필요 변수만)
    input_data = {
        "var2": json.dumps(state.get("available_categories", []), ensure_ascii=False, indent=2),
        "user1": json.dumps(user, ensure_ascii=False, indent=2),
        "user2": json.dumps(state.get("partner_data", state.get("user_partner_data", {})), ensure_ascii=False, indent=2),
        "couple": json.dumps(state.get("couple_data", {}), ensure_ascii=False, indent=2),
        "trigger": json.dumps(user_choice, ensure_ascii=False, indent=2),
        "question": state.get("query", ""),
        "poi_data": json.dumps(places, ensure_ascii=False),
        "previous_recommendations": json.dumps(state.get("previous_recommendations", []), ensure_ascii=False, indent=2),  # ✅ 기존 유지
        "already_selected_pois": json.dumps(state.get("already_selected_pois", []), ensure_ascii=False, indent=2),       # ✅ 추가
    }

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

        # 🪄 디버깅 출력
        print(f"📤 {category} 응답 with idx={idx}:")
        print(json.dumps(payload, ensure_ascii=False, indent=2))

        print(f"✔️ {category} 추천 완료 (개수 {len(payload)})")
        return {"recommendations": payload, "poi_data_delta": poi_delta}

    except Exception as e:
        print(f"⛔️ {category} 노드 실행 오류: {e}")
        return {"recommendations": [], "poi_data_delta": {category: []}}


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