# src/app/models/schemas.py
from typing import Tuple, List, Dict, Optional, Any, TypedDict
from pydantic import BaseModel, Field, model_validator

# ===== Request =====
class UserChoice(BaseModel):
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
    open_hours: Optional[Dict[str, str]]
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


# 리롤 할 때 쓰일 데이터 구조
class POI(BaseModel):
    seq: int
    name: str
    category: str

class ReplaceRequest(BaseModel):
    exclude_pois: List[POI]
    previous_recommendations: List[POI]
    user_choice: Optional[Dict[str, Any]] = None

class RerollResponse(BaseModel):
    explain: str
    data: List[Dict[str, Any]]