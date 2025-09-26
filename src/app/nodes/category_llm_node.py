
# nodes/category_llm_node.py
import json, time, re
from typing import Dict, Any, List, Tuple,Optional
from langsmith import Client
from app.models.schemas import State
from config import llm, PLACES_API_FIELDS
from app.places_api.text_search_service import search_text
#from ..tests.test_data import initial_state 
from pydantic import BaseModel

try:
    client = Client()
except Exception as e:
    print(f"⚠️ LangSmith Client 초기화 실패. 오류: {e}")
    client = None

class POIItem(BaseModel):       # JSON 강제 구조 정의
    seq: Optional[int] = None
    name: str
    category: str
    lat: float
    lng: float
    indoor: Optional[bool] = None
    price_level: Optional[int] = None
    open_hours: Optional[Dict[str, str]] = None
    alcohol: Optional[int] = None
    mood_tag: Optional[str] = None
    food_tag: Optional[List[str]] = None
    rating_avg: Optional[float] = None
    link: Optional[str] = None

class AgentResponse(BaseModel): # LLM이 무조건 맞춰야 하는 최상위 스키마
    explain: str
    data: List[POIItem]



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


# --- 공통 함수: 구글 플레이스 API 호출 ---
def get_poi_data(
    query: str,
    location: Tuple[float, float],
    radius: int = 1000,
    language: str = "ko",
    page_delay_sec: float = 2.0,   # 다음 페이지 토큰 활성화 대기
) -> list:
    all_places: List[dict] = []

    result = search_text(
        text_query=query,
        location=location,
        radius=radius,
        fields=PLACES_API_FIELDS,
        language="ko",
    )
    all_places.extend(result.get("places", []))

    # next_page_token 루프
    next_page_token = result.get("nextPageToken")
    while next_page_token:
        time.sleep(page_delay_sec)
        result = search_text(
            text_query=query,
            location=location,
            radius=radius,
            fields=PLACES_API_FIELDS,
            language=language,
            page_token=next_page_token,
        )
        all_places.extend(result.get("places", []))
        next_page_token = result.get("nextPageToken")

    return all_places

# --- 공통 로직 ---
def _invoke_agent(
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

    trig = state.get("trigger_data", {})
    user = state.get("user_data", {})

    # 위치
    lat = trig.get("lat")
    lng = trig.get("lng")
    
    # fallback: start 배열에서 꺼내기
    if (lat is None or lng is None) and "start" in trig:
        start = trig.get("start")
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
        radius_m = trig.get("radius_m", 2000)

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
        "trigger": json.dumps(trig, ensure_ascii=False, indent=2),
        "question": state.get("query", ""),
        "poi_data": json.dumps(places, ensure_ascii=False),
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
    return _invoke_agent(state, "restaurant", "restaurant_prompt", "맛집 OR 레스토랑", idx=idx)

def cafe_agent_node(state: State, idx: int | None = None) -> Dict[str, Any]:
    return _invoke_agent(state, "cafe", "cafe_prompt", "카페", idx=idx)

def bar_agent_node(state: State, idx: int | None = None) -> Dict[str, Any]:
    return _invoke_agent(state, "bar", "bar_prompt", "바 OR 펍", idx=idx)

def activity_agent_node(state: State, idx: int | None = None) -> Dict[str, Any]:
    return _invoke_agent(state, "activity", "activity_prompt", "체험 액티비티", idx=idx)

def attraction_agent_node(state: State, idx: int | None = None) -> Dict[str, Any]:
    return _invoke_agent(state, "attraction", "attraction_prompt", "명소 관광지", idx=idx)

def exhibit_agent_node(state: State, idx: int | None = None) -> Dict[str, Any]:
    return _invoke_agent(state, "exhibit", "exhibit_prompt", "전시회 전시장", idx=idx)

def walk_agent_node(state: State, idx: int | None = None) -> Dict[str, Any]:
    return _invoke_agent(state, "walk", "walk_prompt", "산책로 공원 산책", idx=idx)

def view_agent_node(state: State, idx: int | None = None) -> Dict[str, Any]:
    return _invoke_agent(state, "view", "view_prompt", "야경 전망대 뷰맛집", idx=idx)

def nature_agent_node(state: State, idx: int | None = None) -> Dict[str, Any]:
    return _invoke_agent(state, "nature", "nature_prompt", "자연 경치 숲길", idx=idx)

def shopping_agent_node(state: State, idx: int | None = None) -> Dict[str, Any]:
    return _invoke_agent(state, "shopping", "shopping_prompt", "쇼핑몰 상가 쇼핑", idx=idx)

def performance_agent_node(state: State, idx: int | None = None) -> Dict[str, Any]:
    return _invoke_agent(state, "performance", "performance_prompt", "공연 연극 콘서트", idx=idx)
