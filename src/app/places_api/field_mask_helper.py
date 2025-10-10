from typing import Optional, Sequence

# ===============================================================
# ✅ 기본 필드 세트 (Google Places API v1 기준)
# ===============================================================
DEFAULT_FIELDS = [
    "id", "displayName", "formattedAddress", "location",
    "primaryType", "businessStatus", "types",
    "rating", "userRatingCount", "priceLevel",
]

# 잘못 쓰기 쉬운 별칭 -> 정규 필드명 매핑
ALIASES = {
    "secondaryOpeningHours": "regularSecondaryOpeningHours",  # 잘못된 이름 교정
}

# ===============================================================
# 🔧 내부 정규화 유틸
# ===============================================================
def _normalize(f: str) -> str:
    """
    필드명을 Places API용 정규화.
    - 'places.' prefix 자동 추가
    - '*' 또는 'nextPageToken'은 그대로 유지
    """
    f = f.strip()
    if not f:
        return ""
    if f == "*":  # 개발용 전체 필드
        return "*"
    if f == "nextPageToken":  # 최상위 토큰은 접두어 없음
        return "nextPageToken"
    f = ALIASES.get(f, f)
    return f if f.startswith("places.") else f"places.{f}"

# ===============================================================
# 🧩 필드 마스크 생성 함수 (Nearby, TextSearch 등 공용)
# ===============================================================
def build_field_mask(
    fields: Optional[Sequence[str]] = None,
    default_mask: Optional[str] = None
) -> str:
    """
    Google Places API용 Field Mask 문자열 생성기.

    Args:
        fields: 반환할 필드 목록 (예: ["displayName", "location"])
        default_mask: 기본 fallback 마스크 문자열 (예: "places.id,places.displayName")

    Returns:
        콤마로 구분된 Field Mask 문자열
    """
    # ✅ fields가 지정되면 정규화 처리
    if fields:
        norm = [_normalize(x) for x in fields if x]
        if any(x == "*" for x in norm):
            return "*"  # 전체 필드 요청
        # 중복 제거
        dedup, seen = [], set()
        for x in norm:
            if x and x not in seen:
                dedup.append(x)
                seen.add(x)
        return ",".join(dedup)

    # ✅ default_mask 우선
    if default_mask:
        return default_mask

    # ✅ 완전 기본값 fallback
    return ",".join(_normalize(x) for x in DEFAULT_FIELDS)
