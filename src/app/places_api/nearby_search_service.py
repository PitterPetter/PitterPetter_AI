# places_api/nearby_search_service.py

"""
Google Places API 주변 검색 서비스 모듈

이 모듈은 Google Places API (v1)의 '주변 검색(Nearby Search)' 엔드포인트에
대한 요청을 처리하는 단일 함수 `search_nearby`를 제공합니다.
주변 검색은 특정 위치(위도/경도)를 중심으로 지정된 반경 내의 장소를 찾을 때 사용됩니다.

주요 기능:
-   `search_nearby()`: 주어진 중심점(위도, 경도)과 반경 내에서 장소를 검색합니다.
    -   **키워드 필터링**: 선택적으로 키워드를 지정하여 검색 결과를 특정 유형의 장소로
        필터링할 수 있습니다 (예: "카페", "식당").
    -   **필드 마스크(Field Mask)**: 응답에서 받고자 하는 필드를 명시적으로 지정하여
        API 비용을 최적화하고 네트워크 트래픽을 줄일 수 있습니다.
        주변 검색의 경우 필드 경로는 항상 `places.` 접두사로 시작해야 합니다.
        예: `["places.displayName", "places.types"]`
    -   **언어 코드(Language Code)**: 응답 메시지의 언어를 지정할 수 있습니다 (예: "ko" for 한국어).

사용법:
1.  `config.py` 파일에 Google Places API 키가 올바르게 설정되어 있는지 확인합니다.
2.  이 모듈의 `search_nearby` 함수를 다른 스크립트(예: `main.py`)에서 임포트하여 사용합니다.
    `from places_api.nearby_search_service import search_nearby`
3.  함수 호출 시 `location`은 필수이며, `radius`, `keyword`, `fields`, `language`, `api_key`는 선택 사항입니다.
4.  API 호출 중 HTTP 오류(예: 4xx, 5xx 상태 코드)가 발생하면 `requests.HTTPError`가 발생합니다.
    이를 적절히 `try-except` 블록으로 처리하여 오류 상황에 대응해야 합니다.

예시:
    from places_api.nearby_search_service import search_nearby

    result = search_nearby(
        location=(37.5665, 126.9780), # 서울 시청 근처
        radius=500, # 500m 반경
        keyword="서점",
        fields=["places.displayName", "places.formattedAddress"],
        language="ko"
    )
    for place in result.get("places", []):
        print(f"이름: {place.get('displayName', {}).get('text')}, 주소: {place.get('formattedAddress')}")

필수 라이브러리:
-   `requests`: HTTP 요청을 보내는 데 사용됩니다. (`pip install requests`)
-   `config`: API 키 설정을 위해 사용됩니다.
-   `field_mask_helper`: 필드 마스크 생성을 위해 사용됩니다.
"""

from typing import Optional, Sequence, Tuple, Dict, Any
import requests

# 상위 디렉토리의 config 모듈에서 API 키를 임포트합니다.
from config import API_KEY
# 같은 패키지 내의 field_mask_helper 모듈에서 필드 마스크 생성 함수를 임포트합니다.
from .field_mask_helper import build_field_mask


def search_nearby(
    location: Tuple[float, float],
    radius: int = 1000,
    keyword: Optional[str] = None,
    fields: Optional[Sequence[str]] = None,
    language: Optional[str] = None,
    api_key: Optional[str] = None,
) -> Dict[str, Any]:
    """Places API (v1)에 대해 주변 검색 요청을 수행합니다.

    Args:
        location: (위도, 경도) 형태의 중심점입니다.
        radius: 검색 반경 (미터 단위)입니다. 기본값은 1000m (1km)입니다.
        keyword: 결과를 필터링할 선택적 키워드 (예: ``"카페"``)입니다.
        fields: 반환할 필드 경로의 선택적 목록입니다 (``places.`` 접두사 포함).
        language: 응답을 위한 선택적 언어 코드입니다.
        api_key: 사용할 API 키입니다. 제공되지 않으면 `config.API_KEY`를 기본값으로 사용합니다.

    Returns:
        파싱된 JSON 응답 (딕셔너리 형태). 성공적이지 않은 상태 코드의 경우 ``requests.HTTPError``를 발생시킵니다.
    """
    key = api_key or API_KEY
    url = "https://places.googleapis.com/v1/places:searchNearby"
    
    # 주변 검색의 기본 필드 마스크를 정의합니다.
    default_mask = "places.id,places.displayName,places.location"
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": key,
        "X-Goog-FieldMask": build_field_mask(fields, default_mask),
    }
    
    # 요청 본문(payload)을 구성합니다.
    payload: Dict[str, Any] = {
        "locationRestriction": {
            "circle": {
                "center": {"latitude": location[0], "longitude": location[1]},
                "radius": radius,
            }
        }
    }
    if keyword:
        payload["keyword"] = keyword
    if language:
        payload["languageCode"] = language
    
    # HTTP POST 요청을 보냅니다.
    response = requests.post(url, headers=headers, json=payload, timeout=10)
    response.raise_for_status()
    return response.json()