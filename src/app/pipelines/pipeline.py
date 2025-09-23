import json
from langgraph.graph import StateGraph, END, START
from typing import Any, Dict, List
from models.schemas import State  # 기존의 State 스키마를 사용
from config import llm, tools # 필요한 LLM 및 도구
import traceback
import re
from langgraph.checkpoint.base import BaseCheckpointSaver

from nodes.hardfilter_node import node_category_hard_filter
from nodes.sequence_llm_node import sequence_llm_node
from nodes.verification_node import verification_node
from nodes.output_node import output_node

# -------------------------------nodes/~~~.py로 구현예정(프로토타입 제외)---------------------------------
# 1. 데이터 수집 및 정제 노드 (미구현)
def data_ingestion_node(state: State) -> Dict[str, Any]:
    # TODO: Google Place API 호출 및 데이터 정제 로직 구현
    # LLM 보정 Agent는 별도의 노드 또는 함수로 분리 가능
    print("✅ 데이터 수집 및 정제 노드 실행")
    # ... 데이터 수집 및 정제 로직 ...
    # 예시: state.poi_data = {"restaurants": [...], "cafes": [...]}
    return {"status": "data_ingested"}
# -------------------------------------------------------------------------------------------------

# 4. 개별 카테고리 에이전트 노드 (12개)

# 여기서는 예시로 하나만 구현 - > nodes/restaurant_agent_node.py로 옮길 예정
def restaurant_agent_node(state: State) -> Dict[str, Any]:
    print("✅ 식당 추천 에이전트 실행")
    # TODO: 식당 추천 로직 구현 (LLM, RAG 등 활용)
    # state.poi_data에서 식당 데이터 활용
    recommendation = {"category": "restaurant", "details": "근처 분위기 좋은 식당"}
    # 결과를 state.recommendations 리스트에 추가
    if not hasattr(state, 'recommendations'):
        state.recommendations = []
    state.recommendations.append(recommendation)
    return {"recommendations": state.recommendations}
#------------------------------------------------------------------------------------------

# 라우팅 함수
def route_recommendation(state: State) -> str:
    # 검증 노드에서 True/False 결과에 따라 라우팅
    if state.current_judge:
        return "output_json" # 검증 통과
    else:
        return "re_plan" # 재계획 (카테고리 시퀀스 노드로 돌아감)

def route_parallel_agents(state: State) -> List[str]:
    # 시퀀스 LLM이 뱉어낸 카테고리 리스트를 바탕으로
    # 해당 카테고리 노드들로 병렬 라우팅
    if hasattr(state, 'recommended_sequence') and state.recommended_sequence:
        node_map = {
            "restaurant": "restaurant_agent",
            "cafe": "cafe_agent",
            "activity": "activity_agent"
            # TODO: 나머지 9개 카테고리 매핑 추가
        }
        return [node_map[cat] for cat in state.recommended_sequence if cat in node_map]
    return [] # 시퀀스가 없으면 아무것도 실행하지 않음

def build_workflow():
    print("🫵🫵 [LangGraph 워크플로 구축 시작] 🫵🫵")
    workflow = StateGraph(State)

    # 노드 추가
    workflow.add_node("data_ingestion", data_ingestion_node)
    workflow.add_node("hard_filter", node_category_hard_filter)
    workflow.add_node("sequence_llm", sequence_llm_node)

    # 병렬 에이전트 노드들 추가 (12개 중 예시 3개)
    workflow.add_node("restaurant_agent", restaurant_agent_node)
    workflow.add_node("cafe_agent", cafe_agent_node) # TODO: cafe_agent_node 함수 구현
    workflow.add_node("activity_agent", activity_agent_node) # TODO: activity_agent_node 함수 구현

    workflow.add_node("verification", verification_node)
    workflow.add_node("output_json", output_node)

    # 진입점 설정
    workflow.set_entry_point("data_ingestion")
    
    # 엣지 연결
    workflow.add_edge("data_ingestion", "hard_filter")
    workflow.add_edge("hard_filter", "sequence_llm")

    # 병렬 처리를 위한 동적 엣지 연결
    # 시퀀스 LLM 노드에서 나온 결과를 바탕으로 여러 노드로 분기
    workflow.add_conditional_edges(
        "sequence_llm",
        route_parallel_agents,
        path_map=None # path_map은 동적 라우팅 시 None으로 설정
    )

    # 병렬로 실행된 노드들이 한 곳으로 다시 모임
    # 여기서는 병렬 노드들이 모두 완료되면 verification 노드로 이동
    workflow.add_edge("restaurant_agent", "verification")
    workflow.add_edge("cafe_agent", "verification")
    workflow.add_edge("activity_agent", "verification")
    # TODO
    
    # 검증 노드에서 결과에 따라 분기
    workflow.add_conditional_edges(
        "verification",
        route_recommendation,
        {
            "output_json": "output_json",
            "re_plan": "sequence_llm"
        }
    )

    # 최종 출력 노드에서 끝
    workflow.add_edge("output_json", END)

    # 재계획(re_plan) 시퀀스로 돌아오는 엣지 추가
    # 이는 위 conditional_edges의 "re_plan"이 "sequence_llm"로 연결되는 것으로 대체 가능
    
    return workflow