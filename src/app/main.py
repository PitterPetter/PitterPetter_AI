# main.py 또는 프로젝트의 시작점 파일
import sys
import os
import time
import requests
from places_api.text_search_service import search_text

if __name__ == "__main__":
    demo_query = "잠실 카페"
    jamsil_location = (37.5, 127.1)
    radius_m = 2000

    print("\n--- 텍스트 검색 예시 ---")
    print(f"'{demo_query}' (위도: {jamsil_location[0]}, 경도: {jamsil_location[1]}, 반경: {radius_m}m) 검색 중...")

    all_places = []

    # 🚩 최초 요청
    result = search_text(
        text_query=demo_query,
        location=jamsil_location,
        radius=radius_m,
        fields=[
            "id", "displayName", "formattedAddress", "location",
            "primaryType", "types", "businessStatus",
            "priceLevel", "rating", "userRatingCount",
            "currentOpeningHours", "regularOpeningHours",
            "reviews",
        ],
        language="ko",
    )
    all_places.extend(result.get("places", []))

    # 🚩 next_page_token 처리
    next_page_token = result.get("nextPageToken")  # Google API에서 주는 토큰
    while next_page_token:
        print("⏳ 다음 페이지 불러오는 중... (2초 대기)")
        time.sleep(2)  # 🚩 토큰 활성화 대기 (중요)

        # 같은 search_text에 pagetoken 넣어 다시 호출
        result = search_text(
            text_query=demo_query,
            location=jamsil_location,
            radius=radius_m,
            fields=[
                "id", "displayName", "formattedAddress", "location",
                "primaryType", "types", "businessStatus",
                "priceLevel", "rating", "userRatingCount",
                "currentOpeningHours", "regularOpeningHours",
                "reviews",
            ],
            language="ko",
            page_token=next_page_token,   # 🚩 다음 페이지 요청
        )
        places = result.get("places", [])
        all_places.extend(places)

        next_page_token = result.get("nextPageToken")  # 🚩 갱신

    print(f"\n총 {len(all_places)}건 수집 완료 🚩")

    have_hours = 0
    for i, p in enumerate(all_places, 1):
        name = (p.get("displayName") or {}).get("text")
        addr = p.get("formattedAddress")
        loc = p.get("location") or {}
        lat, lon = loc.get("latitude"), loc.get("longitude")
        rating, cnt = p.get("rating"), p.get("userRatingCount")

        pid = p.get("id")
        ptype = p.get("primaryType")
        types = p.get("types") or []
        price_level = p.get("priceLevel")

        ch = p.get("currentOpeningHours") or {}
        open_now = ch.get("openNow")
        week = ch.get("weekdayDescriptions") or []
        if ch:
            have_hours += 1
        today_hint = week[0] if week else "-"

        rweek = (p.get("regularOpeningHours") or {}).get("weekdayDescriptions") or []
        regular_hint = rweek[0] if rweek else "-"

        reviews = p.get("reviews") or []
        rev0 = reviews[0] if reviews else {}
        rev_rating = rev0.get("rating")
        rev_text_obj = rev0.get("text") or {}
        rev_text = (rev_text_obj.get("text") or "")[:80]

        print(
            f"{i}. {name} | ID:{pid} | {addr} | ({lat}, {lon}) | "
            f"타입:{(ptype or (', '.join(types) if types else '-'))} | "
            f"가격대:{price_level} | 평점 {rating} ({cnt}) | "
            f"영업중:{open_now} | 오늘:{today_hint} | 정규:{regular_hint} | "
            f"리뷰★{rev_rating if rev_rating is not None else '-'}: {rev_text}"
        )

    print(f"\n영업시간 포함된 장소: {have_hours}/{len(all_places)} 🚩")







# 현재 파일의 부모 디렉토리 (src)를 Python 경로에 추가
# 이 코드를 통해 'app' 폴더를 모듈의 루트로 인식시킵니다.
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# 이제부터 아래와 같이 절대 경로로 임포트할 수 있습니다.
from app.nodes.sequence_llm_node import sequence_llm_node
from app.tests.test_data import initial_state

# ... 그 외 다른 코드 ...
# ... 그 외 다른 코드 ...
# Get the absolute path of the project's root directory
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
# Add it to the Python path
sys.path.insert(0, project_root)
