import json
import random
from typing import Dict, Any
from app.models.lg_schemas import State

EXPLAIN_CHOICES = [
    "오늘 기분에 꼭 맞춘 데이트 코스예요!",
    "이번 데이트는 이런 무드로 즐겨보세요!",
    "우리 둘만의 시간에 어울리는 코스를 골라봤어요.",
    "설레는 분위기를 이어갈 수 있는 추천 코스예요.",
    "데이터 기반으로 딱 맞춰본 맞춤형 일정입니다.",
    "지금 상황에 찰떡인 데이트 코스 조합이에요.",
    "분위기와 취향을 모두 고려한 추천 코스예요.",
    "오늘 하루를 특별하게 만들어줄 데이트 라인업입니다.",
    "무드와 취향을 반영해 정성껏 구성한 코스예요.",
    "함께 즐기기 좋은 스폿만 모은 데이트 코스예요.",
]

def output_node(state: State) -> Dict[str, Any]:
    """
    LangGraph 워크플로의 최종 결과를 JSON 형식으로 정리하여 반환합니다.
    """
    print("✅ 최종 JSON 출력 노드 실행")
    
    # 추천된 장소 리스트 (state.recommendations 에 들어있다고 가정)
    places = []
    for idx, rec in enumerate(state.recommendations, start=1):
        place_info = {
            "seq": idx,
            "name": rec.get("name"),
            "category": rec.get("category"),
            "lat": rec.get("lat"),
            "lng": rec.get("lng"),
            "indoor": rec.get("indoor", None),
            "price_level": rec.get("price_level", None),
            "open_hours": rec.get("open_hours", None),
            "alcohol": rec.get("alcohol", None),
            "mood_tag": rec.get("mood_tag", None),
            "food_tag": rec.get("food_tag", []),
            "rating_avg": rec.get("rating_avg", None),
            "link": rec.get("link", None)
        }
        places.append(place_info)

    # 최종 출력 데이터 구조
    final_output_data = {
        "explain": random.choice(EXPLAIN_CHOICES),
        "data": places
    }

    # JSON 문자열 변환 후 상태에 저장
    state.final_output = json.dumps(final_output_data, ensure_ascii=False, indent=4)
    
    return {"final_output": state.final_output}
