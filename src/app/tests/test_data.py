# test_data.py

from typing import Dict, Any, List
from app.models.schemas import State, UserData, POIData

# 더미 사용자 데이터 (본인)
dummy_user_data: UserData = {
    "id": "user-123",
    "name": "김현수",
    "birthday": "1995-05-15",
    "gender": "male",
    "like_alcohol": False,
    "active": True,
    "food_preference": "한식, 일식",
    "date_cost": 50000,
    "preferred_atmosphere": "조용하고 분위기 좋은",
    "uuid": "abcdef123456",
    "status": "active",
    "created_at": "2024-01-01T10:00:00",
    "updated_at": "2024-05-20T15:30:00",
    "reroll": 1
}

# 더미 사용자 데이터 (파트너)
dummy_partner_data: UserData = {
    "id": "user-456",
    "name": "박지민",
    "birthday": "1996-11-02",
    "gender": "female",
    "like_alcohol": False,
    "active": False,
    "food_preference": "이탈리안, 디저트",
    "date_cost": 40000,
    "preferred_atmosphere": "로맨틱",
    "uuid": "uvwxyz987654",
    "status": "active",
    "created_at": "2024-01-05T09:00:00",
    "updated_at": "2024-06-10T12:00:00",
    "reroll": 0
}

# 커플 데이터
dummy_couple_data: Dict[str, Any] = {
    "id": "couple-001",
    "boyfriend_id": "user-123",
    "girlfriend_id": "user-456",
    "name": "현수♥지민"
}

# 더미 POI 데이터 (일부만)
dummy_poi_data: POIData = {
    "id": "poi-001",
    "updated_at": "2024-05-20T16:00:00",
    "name": "분위기 좋은 레스토랑",
    "category": "식당",
    "lat": 37.5665,
    "lng": 126.9780,
    "indoor": True,
    "price_level": 3,
    "open_hours": {},
    "alcohol": 1,
    "mood_tag": "데이트, 조용함",
    "food_tag": ["이탈리안", "파스타"],
    "rating_avg": 4.5,
    "created_at": "2024-04-10T12:00:00",
    "link": "http://example.com/restaurant"
}

# 더미 트리거 데이터
dummy_trigger_data: Dict[str, Any] = {
    # 위치/시간/모드
    "start": [126.9780,37.5665],        # [lng, lat]
    "time_window": ["12:00", "20:00"],
    "mode": "walk",
    "drink_intent": False,

    # 환경 컨텍스트
    "weather": "비옴",
    "temperature": 25,
    "humidity": 60,
    "is_raining": False
}


initial_state: State = {
    "query": "이번 주말에 데이트 코스 추천해줘",

    # 사용자 컨텍스트
    "user_data": dummy_user_data,
    "partner_data": dummy_partner_data,
    "couple_data": dummy_couple_data,

    # 실시간 트리거/컨텍스트
    "trigger_data": dummy_trigger_data,

    # POI/RAG
    "poi_data": {
        "restaurant": [dummy_poi_data],   # ← 기존 "식당"을 영문으로
        "cafe": [],
        "bar": [],
        "activity": [],
        "attraction": [],
        "exhibit": [],
        "walk": [],
        "view": [],
        "nature": [],
        "shopping": [],
        "performance": []
    },

    # 추천 파이프라인 상태
    "available_categories": [
        "restaurant",
        "cafe",
        "bar",
        "activity",
        "attraction",
        "exhibit",
        "walk",
        "view",
        "nature",
        "shopping",
        "performance"
    ],
    "recommended_sequence": [],
    "recommendations": [],
    "current_judge": None,
    "judgement_reason": None,
    "final_output": None
}

if __name__ == '__main__':
    print("--- 실험용 더미 데이터 구조 ---")
    print(f"User Data: {initial_state['user_data']}")
    print(f"Partner Data: {initial_state['partner_data']}")
    print(f"Couple Data: {initial_state['couple_data']}")
    print(f"Trigger Data: {initial_state['trigger_data']}")
    print(f"Initial State: {initial_state}")