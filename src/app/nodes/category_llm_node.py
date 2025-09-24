#nodes/category_llm_node.py
import json
from typing import Dict, Any
from models.schemas import State
from langsmith import Client
from config import llm
import re

# LangSmith 클라이언트 초기화
try:
    client = Client()
except Exception as e:
    print(f"⚠️ LangSmith Client 초기화 실패. 오류: {e}")
    client = None

# --- 개별 카테고리 에이전트 노드 ---

def _invoke_agent(state: State, category: str, prompt_name: str) -> Dict[str, Any]:
    """공통 로직을 처리하는 헬퍼 함수"""
    print(f"✅ {category} 추천 에이전트 실행")
    
    if not client:
        print(f"⛔️ LangSmith 클라이언트가 없어 {category} 노드를 건너뜁니다.")
        return {"recommendations": []}

    input_data = {
        "user_data": json.dumps(state.user_data, ensure_ascii=False),
        "trigger_data": json.dumps(state.trigger_data, ensure_ascii=False),
        # 카테고리별 POI 데이터를 동적으로 전달
        "poi_data": json.dumps(state.poi_data.get(category, []), ensure_ascii=False)
    }

    try:
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