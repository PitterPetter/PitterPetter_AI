# src/app/api/replace.py
from fastapi import APIRouter, HTTPException
from typing import Dict, Any, List, Tuple, Set
import asyncio

from app.models.schemas import ReplaceRequest, RerollResponse
from app.pipelines.pipeline import build_workflow

# 🧩 카테고리 에이전트 함수들을 직접 호출한다 (그래프 거치지 않음)
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
    - 리턴 포맷:
        {
          "explain": "선택한 카테고리 리롤 결과입니다.",
          "data": [ {seq, name, category, ...}, ... ]
        }
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
    async def reroll_one(poi: Dict[str, Any]) -> Dict[str, Any] | None:
        cat_raw = poi.get("category", "")
        seq = poi.get("seq")
        cat = _norm_cat(cat_raw)

        fn = AGENT_MAP.get(cat)
        if not fn:
            print(f"[WARN] Unknown category: {cat_raw}")
            return None

        # 🧠 category_llm_node가 기대하는 상태 구조
        state = {
            "query": f"{cat} 재추천 (seq={seq})",
            "user_data": user_data,
            "partner_data": partner_data,
            "couple_data": couple_data,
            "UserChoice_data": user_choice,        # 🚨 중요 포인트
            "available_categories": [cat],
            "exclude_pois": [poi],
            "previous_recommendations": previous_recommendations,
        }

        try:
            print(f"⚙️ {cat} 재추천 시작 (seq={seq})")
            result = await asyncio.to_thread(fn, state, (seq - 1) if isinstance(seq, int) else None)
        except Exception as e:
            print(f"[ERR] {cat} 실행 실패 (seq={seq}): {e}")
            return None

        recs: List[Dict[str, Any]] = (result or {}).get("recommendations", [])
        if not recs:
            print(f"[WARN] {cat} 결과 없음 (seq={seq})")
            return None

        # 🔁 중복 필터링 후 첫 후보 픽
        for cand in recs:
            cand["category"] = cat
            if _poi_key(cand) in taken:
                continue
            cand["seq"] = seq
            taken.add(_poi_key(cand))
            print(f"✅ {cat} 리롤 성공 (seq={seq}) → {cand.get('name')}")
            return cand

        print(f"[WARN] {cat} 후보 중 중복만 존재 (seq={seq})")
        return None

    # ============================================================
    # ⚡ 병렬 실행 (비동기 gather)
    # ============================================================
    tasks = [reroll_one(poi) for poi in exclude_pois]
    reroll_results = await asyncio.gather(*tasks)
    reroll_results = [r for r in reroll_results if r]

    # ============================================================
    # 🎁 결과 응답
    # ============================================================
    print(f"🎯 리롤 완료: {len(reroll_results)}개 성공 / {len(exclude_pois)}개 요청")

    return {
        "explain": "선택한 카테고리 리롤 결과입니다.",
        "data": reroll_results,
    }
