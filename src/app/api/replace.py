from fastapi import APIRouter, HTTPException, Depends, Request
from typing import Dict, Any, List, Tuple, Set
import asyncio
from collections import defaultdict
import traceback
import httpx
import json

from app.core.auth import verify_token
from config import AUTH_SERVICE_URL

from app.models.schemas import ReplaceRequest, RerollResponse
from app.pipelines.pipeline import build_workflow

# 🧩 카테고리 노드 import
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
# 🧭 카테고리 → 함수 매핑
# ============================================================
AGENT_MAP: Dict[str, Any] = {
    "restaurant": restaurant_agent_node, "cafe": cafe_agent_node, "bar": bar_agent_node,
    "activity": activity_agent_node, "attraction": attraction_agent_node, "exhibit": exhibit_agent_node,
    "walk": walk_agent_node, "view": view_agent_node, "nature": nature_agent_node,
    "shopping": shopping_agent_node, "performance": performance_agent_node,
}

# ============================================================
# 🔧 유틸 함수
# ============================================================
def _norm_cat(cat: str) -> str:
    """카테고리 문자열 정규화"""
    return (cat or "").strip().lower()

def _poi_key(p: Dict[str, Any]) -> Tuple[str, ...]:
    """POI 중복 판정을 위한 고유 키 생성"""
    name = (p.get("name") or "").strip().lower()
    category = _norm_cat(p.get("category") or "")
    return (name, category)

def _build_reroll_state(
    poi_to_exclude: Dict[str, Any],
    user: Dict,
    partner: Dict,
    couple: Dict,
    user_choice: Dict,
    previous_recommendations: List[Dict]
) -> Dict[str, Any]:
    """리롤 실행용 LangGraph state 구성"""
    category = _norm_cat(poi_to_exclude.get("category", ""))
    seq = poi_to_exclude.get("seq")
    return {
        "query": f"seq={seq} 위치의 '{poi_to_exclude.get('name')}' 대신 새로운 {category} 장소를 추천해줘.",
        "user": user,
        "partner": partner,
        "couple": couple,
        "user_choice": user_choice,
        "available_categories": [category],
        "exclude_pois": previous_recommendations,
        "previous_recommendations": previous_recommendations,
    }

# ============================================================
# 🚀 리롤 API
# ============================================================
@router.post(
    "/recommends/replace",
    response_model=RerollResponse,
    summary="[인증 필요] 특정 seq 리롤 API",
)
async def replace_recommendations(
    body: ReplaceRequest,
    request: Request,
    token_payload: dict = Depends(verify_token)
):
    print("\n===============================")
    print("📡 [AI-Service] Replace API 호출 시작")
    print("===============================")

    # 1️⃣ 토큰 정보
    user_id = token_payload.get("userId")
    couple_id = token_payload.get("coupleId")
    print(f"🔐 토큰 payload = {token_payload}")
    if not couple_id:
        raise HTTPException(status_code=401, detail="coupleId 누락")

    # 2️⃣ Auth 서비스 데이터 요청
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        raise HTTPException(status_code=401, detail="Authorization 헤더 누락")

    auth_url = f"{AUTH_SERVICE_URL}/api/couples/{couple_id}/recommendation-data"
    print(f"🌐 Auth 서비스 URL: {auth_url}")

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            res = await client.get(auth_url, headers={"Authorization": auth_header})
            if res.status_code != 200:
                print(f"⚠️ Auth 실패 응답: {res.text[:300]}")
                raise HTTPException(status_code=res.status_code, detail=f"Auth 요청 실패: {res.text}")
            auth_data = res.json()
            print("✅ Auth 데이터 수신 완료")
            print(f"👤 Auth 응답 데이터: {json.dumps(auth_data, ensure_ascii=False)[:400]}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Auth 서비스 호출 실패: {e}")

    # 3️⃣ Auth 데이터 파싱
    data_block = auth_data.get("data", {})
    user = data_block.get("user", {})
    partner = data_block.get("partner", {})
    couple = data_block.get("couple", {})

    # 4️⃣ 요청 바디 파싱
    user_choice = body.user_choice.dict() if hasattr(body.user_choice, "dict") else (body.user_choice or {})
    # Territory 지역락 기능 제거: 더 이상 잠금 검증 수행 안 함
    exclude_pois = [poi.dict() for poi in getattr(body, "exclude_pois", [])]
    previous_recommendations = [poi.dict() for poi in getattr(body, "previous_recommendations", [])]

    if not exclude_pois:
        raise HTTPException(status_code=400, detail="exclude_pois 데이터 누락")

    # 🆕 ✅ 프론트에서 category 필드는 별도로 안 옴 → exclude_pois에서 자동 추출
    categories = list({ _norm_cat(p.get("category")) for p in exclude_pois })
    print(f"📂 추출된 카테고리 목록: {categories}")

    # 5️⃣ 중복 필터 세팅
    taken: Set[Tuple[str, ...]] = set()
    for p in previous_recommendations + exclude_pois:
        taken.add(_poi_key(p))

    # ============================================================
    # 🎯 단일 리롤 함수
    # ============================================================
    async def reroll_one(poi: Dict[str, Any]) -> List[Dict[str, Any]]:
        category = _norm_cat(poi.get("category", ""))
        fn = AGENT_MAP.get(category)
        if not fn:
            print(f"⚠️ Unknown category: {category}")
            return []

        # 🆕 ✅ category는 exclude_pois 내부 값으로만 세팅됨
        state = _build_reroll_state(poi, user, partner, couple, user_choice, previous_recommendations)
        try:
            result_state = await asyncio.to_thread(fn, state)
            candidates = (result_state or {}).get("recommendations", [])
            for c in candidates:
                c["seq"] = poi.get("seq")
                c["category"] = category
            return candidates
        except Exception as e:
            print(f"❌ {category} 실행 오류 (seq={poi.get('seq')}): {e}")
            traceback.print_exc()
            return []

    # ============================================================
    # ⚡ 병렬 실행
    # ============================================================
    tasks = [reroll_one(p) for p in exclude_pois]
    results = await asyncio.gather(*tasks)

    reroll_results: List[Dict[str, Any]] = []
    for original_poi, candidates in zip(exclude_pois, results):
        for cand in candidates:
            if _poi_key(cand) not in taken:
                reroll_results.append(cand)
                taken.add(_poi_key(cand))
                break

    print(f"🎯 리롤 완료: {len(reroll_results)}개 성공 / {len(exclude_pois)}개 요청")
    print("===============================\n")

    # 기존 추천 목록을 유지하되, 성공한 seq만 새 후보로 교체
    reroll_by_seq = {poi.get("seq"): poi for poi in reroll_results}
    final_recommendations: List[Dict[str, Any]] = []
    for prev in previous_recommendations:
        seq = prev.get("seq")
        replacement = reroll_by_seq.get(seq)
        if replacement:
            # 카테고리가 빠져있으면 원본 값으로 보완
            if prev.get("category") and not replacement.get("category"):
                replacement = {**replacement, "category": prev["category"]}
            final_recommendations.append(replacement)
        else:
            final_recommendations.append(prev)

    return RerollResponse(
        explain="선택한 장소를 새로운 장소로 변경했어요!",
        data=final_recommendations,
    )
