from langgraph.graph import StateGraph, END
from typing import Any, Dict, List, Callable ,Tuple
from app.models.lg_schemas import State
from langgraph.checkpoint.base import BaseCheckpointSaver
from concurrent.futures import ThreadPoolExecutor, as_completed

# 정제 / 필터 노드는 테스트에서 제외
from app.nodes.hardfilter_node import node_category_hard_filter
# from app.nodes.data_ingestion import data_ingestion_node

from app.nodes.sequence_llm_node import sequence_llm_node
#from app.nodes.verification_node import verification_node
from app.nodes.output_node import output_node
from app.nodes.category_llm_node import (
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

# 카테고리 → 에이전트 함수 매핑
AGENT_MAP: Dict[str, Callable[[State], Dict[str, Any]]] = {
    "restaurant": restaurant_agent_node,
    "cafe": cafe_agent_node,
    "bar": bar_agent_node,
    "activity": activity_agent_node,
    "attraction": attraction_agent_node,
    "exhibit": exhibit_agent_node,
    "walk": walk_agent_node,
    "view": view_agent_node,
    "nature": nature_agent_node,
    "shopping": shopping_agent_node,
    "performance": performance_agent_node,
}

from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, Any, List

from collections import defaultdict
def agent_runner_node(state: State) -> Dict[str, Any]:
    """
    sequence_llm가 만든 recommended_sequence를 기반으로
    카테고리별 agent를 병렬로 실행하되,
    같은 카테고리끼리는 순차적으로 실행 (LLM 중복 방지)
    """
    seq: List[str] = state.get("recommended_sequence", [])
    if not seq:
        print("🧩 agent_runner: 실행할 카테고리 없음")
        state["recommendations"] = []
        return {"recommendations": []}

    acc: List[Dict[str, Any]] = state.get("recommendations", [])

    # ✅ 카테고리별 그룹화
    cat_groups = defaultdict(list)
    for idx, cat in enumerate(seq):
        cat_groups[cat].append((idx, cat))

    already_selected_pois: List[Dict[str, Any]] = []
    print(f"🧩 agent_runner: {len(seq)}개 카테고리 중 {len(cat_groups)}종 병렬 실행 (같은 카테고리는 직렬)")

    def run_category_group(cat: str, group: List[Tuple[int, str]]):
        """같은 카테고리 그룹 순차 실행"""
        for idx, _ in group:
            fn = AGENT_MAP.get(cat)
            if not fn:
                continue
            try:
                result = fn(state, idx)
                recs = (result or {}).get("recommendations", [])
                for r in recs:
                    # 🔹 같은 카테고리 내 중복 방지
                    if any(r["name"] == a.get("name") for a in already_selected_pois):
                        continue
                    r["seq"] = idx + 1
                    acc.append(r)
                    already_selected_pois.append(r)
            except Exception as e:
                print(f"[ERR] {cat} 실행 실패 (seq={idx}): {e}")

    # ✅ 다른 카테고리는 병렬 실행
    with ThreadPoolExecutor(max_workers=min(4, len(cat_groups))) as ex:
        futures = [ex.submit(run_category_group, cat, group) for cat, group in cat_groups.items()]
        for _ in as_completed(futures):
            pass

    state["recommendations"] = acc
    print(f"🧩 agent_runner 완료 — 총 {len(acc)}개 추천 생성")
    return {"recommendations": acc}
def route_recommendation(state: State) -> str:
    MAX_RETRY = 2
    ok = state.get("current_judge")  # True/False or None

    if ok is True:
        return "output_json"

    retry = state.get("retry_count", 0)
    if retry < MAX_RETRY:
        state["retry_count"] = retry + 1
        return "re_plan"   # sequence_llm로 재계획

    # 안전장치: 실패/None이든 캡 도달하면 종료
    return "output_json"
'''
def route_parallel_agents(state: State) -> List[str]:
    if hasattr(state, "recommended_sequence") and state["recommended_sequence"]:
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
        return [node_map[cat] for cat in state["recommended_sequence"] if cat in node_map]
    return []
'''
def build_workflow():
    print("🫵🫵 [LangGraph 워크플로 구축 시작] 🫵🫵")
    workflow = StateGraph(State)

    # 시퀀스 노드
    workflow.add_node("hardfilter", node_category_hard_filter)  # --- IGNORE ---
    workflow.add_node("sequence_llm", sequence_llm_node)
    workflow.add_node("agent_runner", agent_runner_node)     
    # 카테고리 에이전트 노드
    '''
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
    '''
   

    # 검증 + 출력
    #workflow.add_node("verification", verification_node)
    workflow.add_node("output_json", output_node)

    # 진입점: 바로 시퀀스 노드부터 시작
    workflow.set_entry_point("hardfilter")  # --- IGNORE ---

   
   # 단순 직렬 흐름
    workflow.add_edge("hardfilter", "sequence_llm") 
    workflow.add_edge("sequence_llm", "agent_runner")
    #workflow.add_edge("agent_runner", "verification")
    '''
    # 병렬 에지
    workflow.add_conditional_edges(
        "sequence_llm",
        route_parallel_agents,
        path_map=None,
    )
    # 병렬 노드 → 검증
    parallel_agent_nodes = [
        "restaurant_agent", "cafe_agent", "bar_agent", "activity_agent",
        "attraction_agent", "exhibit_agent", "walk_agent", "view_agent",
        "nature_agent", "shopping_agent", "performance_agent"
    ]
    for agent_node in parallel_agent_nodes:
        workflow.add_edge(agent_node, "verification")
    '''
    '''
    # 검증 → 분기
    workflow.add_conditional_edges(
        "verification",
        route_recommendation,
        {
            "output_json": "output_json",
            "re_plan": "sequence_llm"
        },
    )

    '''
    
    workflow.add_edge("output_json", END)
    return workflow


