import json
from typing import Dict, Any
from app.models.lg_schemas import State

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
        "explain": "오늘 무드에 맞는 코스입니다~",
        "data": places
    }

    # JSON 문자열 변환 후 상태에 저장
    state.final_output = json.dumps(final_output_data, ensure_ascii=False, indent=4)
    
    return {"final_output": state.final_output}