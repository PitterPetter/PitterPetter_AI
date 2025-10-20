
import time
from typing import List, Tuple
from app.models.lg_schemas import State
from config import PLACES_API_FIELDS
from app.places_api.text_search_service import search_text


# --- 공통 함수: 구글 플레이스 API 호출 ---
def get_poi_data(
    query: str,
    location: Tuple[float, float],
    radius: int = 1600,
    language: str = "ko",
    page_delay_sec: float = 2.0,   # 다음 페이지 토큰 활성화 대기
) -> list:
    
    all_places: List[dict] = []

    result = search_text(
        text_query=query,
        location=location,
        radius=radius,
        fields=PLACES_API_FIELDS,
        language="ko",
    )
    all_places.extend(result.get("places", []))

    # next_page_token = result.get("nextPageToken")
    # while next_page_token:
    #     time.sleep(page_delay_sec)
    #     result = search_text(
    #         text_query=query,
    #         location=location,
    #         radius=radius,
    #         fields=PLACES_API_FIELDS,
    #         language=language,
    #         page_token=next_page_token,
    #     )
    #     all_places.extend(result.get("places", []))
    #     next_page_token = result.get("nextPageToken")

    return all_places
