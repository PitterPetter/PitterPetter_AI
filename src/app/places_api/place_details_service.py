"""
Google Places API 장소 상세 정보 서비스 모듈

이 모듈은 Google Places API (v1)의 '장소 상세 정보(Place Details)' 엔드포인트에
대한 요청을 처리하는 단일 함수 `get_place_details`를 제공합니다.
장소 상세 정보는 특정 장소 ID를 사용하여 해당 장소에 대한 풍부하고 자세한 정보를
조회할 때 사용됩니다.

주요 기능:
-   `get_place_details()`: 고유한 장소 ID를 기반으로 단일 장소의 모든 상세 정보를 검색합니다.
    -   **장소 ID(Place ID)**: 텍스트 검색이나 주변 검색 결과에서 얻은 장소 ID를 사용하여
        해당 장소의 상세 정보를 조회합니다.
    -   **필드 마스크(Field Mask)**: 응답에서 받고자 하는 필드를 명시적으로 지정하여
        API 비용을 최적화하고 네트워크 트래픽을 줄일 수 있습니다.
        장소 상세 정보의 경우 필드 경로는 `places.` 접두사 없이 직접 필드 이름을 사용합니다.
        예: `["displayName", "formattedAddress", "rating", "currentOpeningHours"]`
    -   **언어 코드(Language Code)**: 응답 메시지의 언어를 지정할 수 있습니다 (예: "ko" for 한국어).

사용법:
1.  `config.py` 파일에 Google Places API 키가 올바르게 설정되어 있는지 확인합니다.
2.  이 모듈의 `get_place_details` 함수를 다른 스크립트(예: `main.py`)에서 임포트하여 사용합니다.
    `from places_api.place_details_service import get_place_details`
3.  함수 호출 시 `place_id`는 필수이며, `fields`, `language`, `api_key`는 선택 사항입니다.
4.  API 호출 중 HTTP 오류(예: 4xx, 5xx 상태 코드)가 발생하면 `requests.HTTPError`가 발생합니다.
    이를 적절히 `try-except` 블록으로 처리하여 오류 상황에 대응해야 합니다.

예시:
    from places_api.place_details_service import get_place_details

    # 예시 장소 ID (실제 유효한 ID로 교체해야 합니다)
    example_place_id = "ChIJj61dQgK6j4AR4GeTYWZsKWw"

    details = get_place_details(
        place_id=example_place_id,
        fields=["displayName", "formattedAddress", "rating", "currentOpeningHours", "websiteUri"],
        language="ko"
    )
    if details:
        print(f"장소 이름: {details.get('displayName', {}).get('text')}")
        print(f"주소: {details.get('formattedAddress')}")
        print(f"평점: {details.get('rating')}")

필수 라이브러리:
-   `requests`: HTTP 요청을 보내는 데 사용됩니다. (`pip install requests`)
-   `config`: API 키 설정을 위해 사용됩니다.
-   `field_mask_helper`: 필드 마스크 생성을 위해 사용됩니다.
"""

from typing import Optional, Sequence, Dict, Any
import requests

# 상위 디렉토리의 config 모듈에서 API 키를 임포트합니다.
from config import API_KEY
# 같은 패키지 내의 field_mask_helper 모듈에서 필드 마스크 생성 함수를 임포트합니다.
from .field_mask_helper import build_field_mask


def get_place_details(
    place_id: str,
    fields: Optional[Sequence[str]] = None,
    language: Optional[str] = None,
    api_key: Optional[str] = None,
) -> Dict[str, Any]:
    """단일 장소에 대한 상세 정보를 검색합니다.

    Args:
        place_id: 전체 또는 짧은 장소 ID (예: ``"ChIJj61dQgK6j4AR4GeTYWZsKWw"``)입니다.
        fields: 반환할 필드의 선택적 목록입니다. 장소 상세 정보의 경우 필드 경로는
            Place 객체를 직접 참조하므로 `places.` 접두사를 사용하지 않습니다.
            기본값은 이름, 위치, 평점, 평점 수, 가격 수준 및 현재 영업 시간을 반환합니다.
        language: 응답을 위한 선택적 언어 코드입니다.
        api_key: 사용할 API 키입니다. 제공되지 않으면 `config.API_KEY`를 기본값으로 사용합니다.

    Returns:
        파싱된 JSON 응답 (딕셔너리 형태). 성공적이지 않은 상태 코드의 경우 ``requests.HTTPError``를 발생시킵니다.
    """
    key = api_key or API_KEY
    # 장소 상세 정보의 경우 필드 경로는 Place 객체를 직접 참조합니다.
    # 기본 필드 마스크를 정의합니다.
    default_mask = (
        "displayName,location,rating,userRatingCount,priceLevel,currentOpeningHours"
    )
    headers = {
        "X-Goog-Api-Key": key,
        "X-Goog-FieldMask": build_field_mask(fields, default_mask),
    }
    
    # GET 요청의 쿼리 파라미터를 구성합니다.
    params: Dict[str, Any] = {}
    if language:
        params["languageCode"] = language
    
    # URL 경로에 place_id를 포함합니다.
    url = f"https://places.googleapis.com/v1/places/{place_id}"
    
    # HTTP GET 요청을 보냅니다.
    response = requests.get(url, headers=headers, params=params, timeout=10)
    response.raise_for_status()
    return response.json()
