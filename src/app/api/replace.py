# src/app/api/replace.py
from fastapi import APIRouter, HTTPException
from typing import Dict, Any, List, Tuple, Set
import asyncio
from collections import defaultdict

from app.models.schemas import ReplaceRequest, RerollResponse
from app.pipelines.pipeline import build_workflow

# 🧩 카테고리 에이전트 함수들을 직접 호출 (그래프 거치지 않음)
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

# ============================================================
# ⚙️ Router 및 Workflow 설정
# ============================================================
router = APIRouter()

graph = build_workflow()
app = graph.compile()

# ============================================================
# 🧭 카테고리 → 함수 매핑 (소문자 기준)
# ============================================================
AGENT_MAP: Dict[str, Any] = {
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

# ============================================================
# 🔧 유틸 함수
# ============================================================
def _norm_cat(cat: str) -> str:
    """카테고리 문자열 정규화"""
    return (cat or "").strip().lower()

def _poi_key(p: Dict[str, Any]) -> Tuple[str, str]:
    """POI 중복 판정 키"""
    return ((p.get("name") or "").strip().lower(), _norm_cat(p.get("category") or ""))

# ============================================================
# 🚀 리롤 API
# ============================================================
@router.post(
    "/recommends/replace",
    response_model=RerollResponse,
    summary="특정 seq(카테고리 위치) 리롤(재추천) API",
)
async def replace_recommendations(body: ReplaceRequest):
    """
    특정 seq(카테고리 위치) 리롤(재추천) API  
    - Auth 연동 없이 body로 user/partner/couple 직접 입력 가능  
    - exclude_pois 목록 내 각 seq별로 병렬 리롤 실행  
    - 이전 추천 및 제외 리스트를 기반으로 중복 필터링  
    - 같은 카테고리 내에서는 순차 실행하여 중복 방지  
    """

    # ✅ 입력 데이터 파싱
    user_data   = body.user or {}
    partner_data= body.partner or {}
    couple_data = body.couple or {}
    user_choice = body.user_choice or {}

    exclude_pois = [poi.dict() for poi in body.exclude_pois]
    previous_recommendations = [poi.dict() for poi in body.previous_recommendations]

    # ---------------- 검증 ----------------
    if not user_data or not couple_data:
        raise HTTPException(status_code=400, detail="user 또는 couple 데이터 누락")
    if not exclude_pois:
        raise HTTPException(status_code=400, detail="exclude_pois 누락")

    # 🙅‍♂️ 중복 필터용 셋 (이전 + 제외)
    taken: Set[Tuple[str, str]] = set()
    for p in previous_recommendations:
        taken.add(_poi_key(p))
    for p in exclude_pois:
        taken.add(_poi_key(p))

    # ============================================================
    # 🎯 개별 리롤 실행 함수 (비동기 스레드로)
    # ============================================================
    already_selected_pois: List[Dict[str, Any]] = []
    lock = asyncio.Lock()  # 병렬 접근 제어용

    async def reroll_one(poi: Dict[str, Any]) -> Dict[str, Any] | None:
        """단일 POI 재추천 실행"""
        cat_raw = poi.get("category", "")
        seq = poi.get("seq")
        cat = _norm_cat(cat_raw)
        fn = AGENT_MAP.get(cat)
        if not fn:
            print(f"[WARN] Unknown category: {cat_raw}")
            return None

        # 🧠 state 구성 — 현재 global memory 포함
        state = {
            "query": f"{cat} 재추천 (seq={seq})",
            "user_data": user_data,
            "partner_data": partner_data,
            "couple_data": couple_data,
            "UserChoice_data": user_choice,
            "available_categories": [cat],
            "exclude_pois": [poi],
            "previous_recommendations": previous_recommendations,
            "already_selected_pois": already_selected_pois,  # ✅ 병렬 공유
        }

        try:
            result = await asyncio.to_thread(fn, state, (seq - 1) if isinstance(seq, int) else None)
        except Exception as e:
            print(f"[ERR] {cat} 실행 실패 (seq={seq}): {e}")
            return None

        recs: List[Dict[str, Any]] = (result or {}).get("recommendations", [])
        if not recs:
            return None

        for cand in recs:
            async with lock:
                # 중복 확인 (이전 + 이번 라운드)
                name_key = (cand.get("name") or "").strip().lower()
                if any(name_key == (p.get("name") or "").strip().lower() for p in already_selected_pois):
                    continue
                cand["seq"] = seq
                cand["category"] = cat
                already_selected_pois.append(cand)
                return cand
        return None

    # ============================================================
    # ⚡ 카테고리별 그룹화 후 실행 (같은 카테고리는 순차, 다른 건 병렬)
    # ============================================================
    cat_groups = defaultdict(list)
    for poi in exclude_pois:
        cat_groups[_norm_cat(poi.get("category"))].append(poi)

    reroll_results: List[Dict[str, Any]] = []

    async def run_category_group(cat: str, pois: List[Dict[str, Any]]):
        """같은 카테고리 그룹 순차 실행"""
        for poi in pois:
            result = await reroll_one(poi)
            if result:
                reroll_results.append(result)

    # 🧵 서로 다른 카테고리는 병렬 실행
    cat_tasks = [run_category_group(cat, pois) for cat, pois in cat_groups.items()]
    await asyncio.gather(*cat_tasks)

    # ============================================================
    # 🔎 최종 중복 필터링 (이름 유사도 포함)
    # ============================================================
    unique_results = []
    seen_names = set()
    for r in reroll_results:
        key = r["name"].replace(" ", "").lower()
        if any(key in s or s in key for s in seen_names):
            continue
        seen_names.add(key)
        unique_results.append(r)
    reroll_results = unique_results

    # ============================================================
    # 🎁 결과 응답
    # ============================================================
    print(f"🎯 리롤 완료: {len(reroll_results)}개 성공 / {len(exclude_pois)}개 요청")

    return {
        "explain": "선택한 카테고리 리롤 결과입니다.",
        "data": reroll_results,
    }
