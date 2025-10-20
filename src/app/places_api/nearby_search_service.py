"""
Google Places API v1 Nearby Search 모듈
---------------------------------------

이 모듈은 Google Places API (v1)의 `places:searchNearby` 엔드포인트를 사용하여
특정 위치를 중심으로 반경 내의 장소를 검색하는 기능을 제공합니다.

주요 기능:
-   `search_nearby()`: 주어진 위치(lat, lng)와 반경(radius) 내의 장소 검색
-   `includedTypes`: 검색할 장소 유형 지정 (예: ["restaurant"], ["cafe"])
-   `FieldMask`: 필요한 필드만 선택적으로 요청 (요금 절감 및 속도 향상)
-   `languageCode`: 결과 언어 설정 (예: "ko" for 한국어)

공식 문서: https://developers.google.com/maps/documentation/places/web-service/search-nearby
"""

from typing import Optional, Sequence, Tuple, Dict, Any
import requests
from config import GOOGLE_PLACES_API_KEY as API_KEY
from .field_mask_helper import build_field_mask


def search_nearby(
    location: Tuple[float, float],
    radius: int = 1600,
    included_types: Optional[Sequence[str]] = None,
    fields: Optional[Sequence[str]] = None,
    language: Optional[str] = "ko",
    max_result_count: int = 20,
    api_key: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Google Places API v1 Nearby Search를 호출합니다.

    Args:
        location: (위도, 경도) 튜플 — 검색 중심점
        radius: 검색 반경 (미터 단위, 기본=1600m)
        included_types: 포함할 장소 유형 리스트 (예: ["restaurant"])
        fields: 반환할 필드 목록 (예: ["displayName", "location", "rating"])
        language: 결과 언어 코드 (기본 "ko")
        max_result_count: 반환할 최대 장소 수 (기본=20)
        api_key: 명시적 API 키 (없으면 .env의 GOOGLE_PLACES_API_KEY 사용)

    Returns:
        dict: Google Places API JSON 응답
    """
    key = api_key or API_KEY
    if not key:
        raise RuntimeError("❌ GOOGLE_PLACES_API_KEY 누락됨 (.env 확인 필요)")

    url = "https://places.googleapis.com/v1/places:searchNearby"

    # ✅ 기본 필드마스크
    default_mask = (
        "places.id,places.displayName,places.formattedAddress,"
        "places.location,places.primaryType,places.types,"
        "places.rating,places.userRatingCount,places.priceLevel"
    )
    field_mask = build_field_mask(fields, default_mask)

    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": key,
        "X-Goog-FieldMask": field_mask,
    }

    # ✅ 요청 본문
    payload: Dict[str, Any] = {
        "maxResultCount": max_result_count,
        "locationRestriction": {
            "circle": {
                "center": {"latitude": location[0], "longitude": location[1]},
                "radius": radius,
            }
        },
    }

    # ✅ 유형 설정 (예: ["restaurant"])
    if included_types:
        payload["includedTypes"] = included_types

    if language:
        payload["languageCode"] = language

    # ✅ 요청 실행
    print(f"📡 Google Places Nearby Search 실행: {included_types}, 반경={radius}m, 위치={location}")
    response = requests.post(url, headers=headers, json=payload, timeout=10)

    # ✅ 오류 출력 및 예외 발생
    if not response.ok:
        print(f"⛔️ Google Nearby API 호출 실패: {response.status_code} {response.text}")
        response.raise_for_status()

    return response.json()
