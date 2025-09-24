import json
import time
import requests
from typing import Dict, Any
from models.schemas import State
from langsmith import Client
from config import llm, PLACES_API_FIELDS # 수정: PLACES_API_FIELDS 임포트
from places_api.text_search_service import search_text
import re

# LangSmith 클라이언트 초기화
try:
    client = Client()
except Exception as e:
    print(f"⚠️ LangSmith Client 초기화 실패. 오류: {e}")
    client = None

# --- 공통 함수: 구글 플레이스 API 호출 ---
def get_poi_data(query: str, location: tuple) -> list:
    """
    주어진 쿼리와 위치로 구글 플레이스 API를 호출하여 POI 데이터를 가져옵니다.
    """
    all_places = []
    
    # 최초 요청
    result = search_text(
        text_query=query,
        location=location,
        radius=2000,
        fields=PLACES_API_FIELDS, # 수정: PLACES_API_FIELDS 변수 사용
        language="ko",
    )
    all_places.extend(result.get("places", []))

    # 다음 페이지 토큰 처리
    next_page_token = result.get("nextPageToken")
    while next_page_token:
        time.sleep(1)
        result = search_text(
            text_query=query,
            location=location,
            radius=2000,
            fields=PLACES_API_FIELDS, # 수정: PLACES_API_FIELDS 변수 사용
            language="ko",
            page_token=next_page_token,
        )
        all_places.extend(result.get("places", []))
        next_page_token = result.get("nextPageToken")

    return all_places


# --- 공통 로직을 처리하는 헬퍼 함수 ---
def _invoke_agent(state: State, category: str, prompt_name: str, search_query: str) -> Dict[str, Any]:
    # ... (기존과 동일한 코드) ...
    print(f"✅ {category} 추천 에이전트 실행")
    
    location = (state.user_data.get("lat"), state.user_data.get("lng"))
    if not location[0]:
        print("⚠️ 위치 정보가 없어 잠실을 기준으로 검색합니다.")
        location = (37.5, 127.1)
        
    category_poi_data = get_poi_data(search_query, location)
    
    if not category_poi_data:
        print(f"⛔️ '{search_query}'에 대한 POI 데이터가 없습니다.")
        return {"recommendations": state.get("recommendations", [])}

    input_data = {
        "user_data": json.dumps(state.user_data, ensure_ascii=False),
        "trigger_data": json.dumps(state.trigger_data, ensure_ascii=False),
        "poi_data": json.dumps(category_poi_data, ensure_ascii=False)
    }

    try:
        if not client:
            raise Exception("LangSmith Client not initialized")
            
        prompt_template = client.pull_prompt(prompt_name)
        formatted_messages = prompt_template.format_prompt(**input_data).to_messages()
        llm_raw_result = llm.invoke(formatted_messages)
        response_text = getattr(llm_raw_result, "content", str(llm_raw_result)).strip()

        try:
            recommendation_data = json.loads(response_text)
            if "recommendations" not in state:
                state["recommendations"] = []
            state["recommendations"].append(recommendation_data)

            print(f"✔️ {category} 추천 완료")
            return {"recommendations": state["recommendations"]}
        
        except json.JSONDecodeError:
            print(f"⚠️ {category} LLM 응답 JSON 파싱 실패: {response_text}")
            return {"recommendations": state.get("recommendations", [])}
            
    except Exception as e:
        print(f"⛔️ {category} 노드 실행 중 오류 발생: {e}")
        return {"recommendations": state.get("recommendations", [])}

def restaurant_agent_node(state: State) -> Dict[str, Any]:
    return _invoke_agent(state, "restaurant", "restaurant_prompt")

def cafe_agent_node(state: State) -> Dict[str, Any]:
    return _invoke_agent(state, "cafe", "cafe_prompt")

def bar_agent_node(state: State) -> Dict[str, Any]:
    return _invoke_agent(state, "bar", "bar_prompt")

def activity_agent_node(state: State) -> Dict[str, Any]:
    return _invoke_agent(state, "activity", "activity_prompt")

def attraction_agent_node(state: State) -> Dict[str, Any]:
    return _invoke_agent(state, "attraction", "attraction_prompt")

def exhibit_agent_node(state: State) -> Dict[str, Any]:
    return _invoke_agent(state, "exhibit", "exhibit_prompt")

def walk_agent_node(state: State) -> Dict[str, Any]:
    return _invoke_agent(state, "walk", "walk_prompt")

def view_agent_node(state: State) -> Dict[str, Any]:
    return _invoke_agent(state, "view", "view_prompt")

def nature_agent_node(state: State) -> Dict[str, Any]:
    return _invoke_agent(state, "nature", "nature_prompt")

def shopping_agent_node(state: State) -> Dict[str, Any]:
    return _invoke_agent(state, "shopping", "shopping_prompt")

def performance_agent_node(state: State) -> Dict[str, Any]:
    return _invoke_agent(state, "performance", "performance_prompt")