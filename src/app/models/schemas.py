# src/app/models/schemas.py
from typing import Tuple, List, Dict, Optional
from pydantic import BaseModel, Field, model_validator

# ===== Request =====
class Trigger(BaseModel):
    start: Tuple[float, float] = Field(..., description="[lng, lat]")
    time_window: Tuple[str, str] = Field(..., description='["HH:MM","HH:MM"]')
    mode: Optional[str] = Field("walk", description='"walk" | "public"')
    drink_intent: bool = Field(..., description="오늘 술 의향")

    @model_validator(mode="after")
    def _validate_time(self):
        for hm in self.time_window:
            h, m = hm.split(":")
            int(h); int(m)
        return self

from typing import TypedDict, List, Any, Optional

# 수정된 POI 데이터 구조 (제공된 테이블 스키마에 맞춤)
class POIData(TypedDict):
    id: str # 'id'는 string 또는 int가 될 수 있지만, 일반적으로 uuid를 사용하므로 string으로 가정
    updated_at: str # 'updated_at'은 datetime이므로 string으로 처리
    name: str # '장소명'
    category: str # '장소타입'
    lat: float # '위도'
    lng: float # '경도'
    indoor: bool # '실내외'
    price_level: int # '가격대'
    open_hours: Any # '요일별 영업시간'은 복잡한 객체일 수 있으므로 Any로 처리
    alcohol: int # '음주 정도'
    mood_tag: str # '무드 태그'는 string 또는 List[str]일 수 있으므로 string으로 처리
    food_tag: List[str] # '음식 태그'는 string 배열이므로 List[str]
    rating_avg: float # '평점 평균'
    created_at: str # '생성일'은 datetime이므로 string으로 처리
    link: str # '링크'
    
# 수정된 사용자 데이터 구조 \
class UserData(TypedDict):
    id: str # 'id'는 string 또는 int가 될 수 있지만, 일반적으로 string으로 가정
    name: str # '이름'
    birthday: str # '생년월일'은 date이므로 string으로 처리
    gender: str # '성별'은 enum이므로 string으로 처리
    like_alcohol: bool # '술 좋아하는지 여부'
    active: bool # '활동적'
    food_preference: str # '좋아하는 음식' 
    date_cost: int # '평소 데이트 비용' 
    preferred_atmosphere: str # '선호 분위기'
    uuid: str # '사용자 매칭용 UUID'는 long이므로 string으로 처리
    status: str # '계정 활성화 여부'는 enum이므로 string으로 처리
    created_at: str # '생성일'은 datetime이므로 string으로 처리
    updated_at: str # '수정일'은 datetime이므로 string으로 처리
    reroll: int # '재추천 횟수'는 long이므로 int로 처리

# LangGraph의 상태를 정의하는 메인 스키마
class State(TypedDict):
    """LangGraph의 상태를 나타내는 TypedDict."""
    query: str # 사용자의 초기 요청 (예: "강남에서 데이트 코스 추천해줘")
    user_data: Dict[str, Any] # 사용자의 유저 데이터 (온보딩 및 기존 데이터)
    trigger_data: Dict[str, Any] # 날씨, 음주 등 트리거 데이터
    poi_data: Optional[Dict[str, List[POIData]]] # Google Place API에서 수집한 정제된 POI 데이터
    available_categories: List[str] # 하드 필터링 후 남은 카테고리
    recommended_sequence: List[str] # LLM이 추천한 카테고리 시퀀스 (예: "식당", "카페")
    recommendations: List[Dict[str, Any]] # 각 카테고리 에이전트의 추천 결과
    current_judge: Optional[bool] # 검증 LLM의 판단 결과
    judgement_reason: Optional[str] # 검증 LLM의 판단 이유
    final_output: Optional[str] # 최종 JSON 형식의 출력
    check_count: int # 재시도 횟수 (선택적)


class RecommendRequest(BaseModel):
    trigger: Trigger

# ===== Response =====
class FilterResult(BaseModel):
    allowed: List[str]
    excluded: Dict[str, List[str]]
    debug: Dict[str, object]
