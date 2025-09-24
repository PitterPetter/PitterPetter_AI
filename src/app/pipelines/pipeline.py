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
from nodes.data_ingestion import data_ingestion_node
from nodes.category_llm_node import (
    restaurant_agent_node,
    cafe_agent_node,
    bar_agent_node,
    activity_agent_node,
    attraction_agent_node,
    exhibit_agent_node,
    walk_agent_node,
    view_agent_node,
    nature_agent_node,
    shopping_agent_node,
    performance_agent_node,
)

# 라우팅 함수
def route_recommendation(state: State) -> str:
    # 검증 노드에서 True/False 결과에 따라 라우팅
    if state.current_judge:
        return "output_json"  # 검증 통과
    else:
        return "re_plan"  # 재계획 (카테고리 시퀀스 노드로 돌아감)

def route_parallel_agents(state: State) -> List[str]:
    # 시퀀스 LLM이 뱉어낸 카테고리 리스트를 바탕으로
    # 해당 카테고리 노드들로 병렬 라우팅
    if hasattr(state, 'recommended_sequence') and state.recommended_sequence:
        node_map = {
            "restaurant": "restaurant_agent",
            "cafe": "cafe_agent",
            "bar": "bar_agent",
            "activity": "activity_agent",
            "attraction": "attraction_agent",
            "exhibit": "exhibit_agent",
            "walk": "walk_agent",
            "view": "view_agent",
            "nature": "nature_agent",
            "shopping": "shopping_agent",
            "performance": "performance_agent",
        }
        return [node_map[cat] for cat in state.recommended_sequence if cat in node_map]
    return []  # 시퀀스가 없으면 아무것도 실행하지 않음


def build_workflow():
    print("🫵🫵 [LangGraph 워크플로 구축 시작] 🫵🫵")
    workflow = StateGraph(State)

    # 모든 노드 추가
    workflow.add_node("data_ingestion", data_ingestion_node)
    workflow.add_node("hard_filter", node_category_hard_filter)
    workflow.add_node("sequence_llm", sequence_llm_node)
    
    # 11개 카테고리 에이전트 노드 추가
    workflow.add_node("restaurant_agent", restaurant_agent_node)
    workflow.add_node("cafe_agent", cafe_agent_node)
    workflow.add_node("bar_agent", bar_agent_node)
    workflow.add_node("activity_agent", activity_agent_node)
    workflow.add_node("attraction_agent", attraction_agent_node)
    workflow.add_node("exhibit_agent", exhibit_agent_node)
    workflow.add_node("walk_agent", walk_agent_node)
    workflow.add_node("view_agent", view_agent_node)
    workflow.add_node("nature_agent", nature_agent_node)
    workflow.add_node("shopping_agent", shopping_agent_node)
    workflow.add_node("performance_agent", performance_agent_node)

    workflow.add_node("verification", verification_node)
    workflow.add_node("output_json", output_node)

    # 진입점 설정
    workflow.set_entry_point("data_ingestion")
    
    # 엣지 연결 (순서대로)
    workflow.add_edge("data_ingestion", "hard_filter")
    workflow.add_edge("hard_filter", "sequence_llm")

    # 병렬 처리를 위한 동적 엣지 연결
    workflow.add_conditional_edges(
        "sequence_llm",
        route_parallel_agents,
        path_map=None
    )

    # 병렬 노드들을 다시 verification 노드로 모으기 (핵심)
    parallel_agent_nodes = [
        "restaurant_agent", "cafe_agent", "bar_agent", "activity_agent",
        "attraction_agent", "exhibit_agent", "walk_agent", "view_agent",
        "nature_agent", "shopping_agent", "performance_agent"
    ]
    for agent_node in parallel_agent_nodes:
        workflow.add_edge(agent_node, "verification")
    
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
    return workflow