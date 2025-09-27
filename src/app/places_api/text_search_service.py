from typing import Optional, Sequence, Tuple, Dict, Any
import requests

from config import GOOGLE_PLACES_API_KEY                 # 상대 import 말고 절대 import
from .field_mask_helper import build_field_mask  # 같은 패키지 내부는 . 로 import

TEXT_SEARCH_URL = "https://places.googleapis.com/v1/places:searchText"

## 🚩 api 조사 🚩
def search_text(
    text_query: str,
    location: Optional[Tuple[float, float]] = None,   # (lat, lon)
    radius: Optional[int] = None,                     # meters
    fields: Optional[Sequence[str]] = None,
    language: str = "ko",
    api_key: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Google Places Text Search (v1)
    - FieldMask 헤더 필수
    - POST + JSON 바디 사용
    """
    api_key = api_key or GOOGLE_PLACES_API_KEY
    if not api_key:
        raise RuntimeError("GOOGLE_PLACES_API_KEY가 설정되지 않았습니다. .env 또는 환경변수 확인하세요.")

    field_mask = build_field_mask(fields)

    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": api_key,
        "X-Goog-FieldMask": field_mask,
    }

    body: Dict[str, Any] = {
        "textQuery": text_query,
        "languageCode": language,
    }

    if location and radius:
        lat, lon = location
        body["locationBias"] = {
            "circle": {
                "center": {"latitude": float(lat), "longitude": float(lon)},
                "radius": float(radius),  # meters
            }
        }

    resp = requests.post(TEXT_SEARCH_URL, headers=headers, json=body, timeout=30)

    # 400 디버깅을 쉽도록 에러 내용을 그대로 보여줌
    if not resp.ok:
        try:
            detail = resp.json()
        except Exception:
            detail = resp.text
        raise requests.HTTPError(
            f"TextSearch 실패 (status={resp.status_code})\n"
            f"headers={headers}\nbody={body}\nresponse={detail}"
        )

    return resp.json()
