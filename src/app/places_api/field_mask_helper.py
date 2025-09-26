# places_api/field_mask_helper.py
from typing import Optional, Sequence

# Text Search에서 자주 쓰는 안전 기본 세트 (Pro/Enterprise 포함)
DEFAULT_FIELDS = [
    "id", "displayName", "formattedAddress", "location",
    "primaryType", "businessStatus", "types",
    "rating", "userRatingCount", "priceLevel",
]

# 잘못 쓰기 쉬운 별칭 -> 정규 필드명 매핑
ALIASES = {
    "secondaryOpeningHours": "regularSecondaryOpeningHours",  # 잘못된 이름 교정
}

def _normalize(f: str) -> str:
    f = f.strip()
    if not f:
        return ""
    if f == "*":                 # 개발용 전체 필드
        return "*"
    if f == "nextPageToken":     # 최상위 토큰은 places. 접두어 없음
        return "nextPageToken"
    f = ALIASES.get(f, f)
    # 이미 places.로 시작하면 그대로 두고, 아니면 붙여준다
    return f if f.startswith("places.") else f"places.{f}"

def build_field_mask(fields: Optional[Sequence[str]] = None) -> str:
    items = list(fields) if fields else DEFAULT_FIELDS
    norm = [_normalize(x) for x in items if x is not None]
    if any(x == "*" for x in norm):
        return "*"                        # * 이 섞여 있으면 그대로 *
    # 빈 값 제거하고 중복 제거
    dedup = []
    seen = set()
    for x in norm:
        if x and x not in seen:
            dedup.append(x); seen.add(x)
    return ",".join(dedup)
