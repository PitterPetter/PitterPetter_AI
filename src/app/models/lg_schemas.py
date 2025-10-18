from pydantic import BaseModel, Field, model_validator
from typing import Tuple, List, Dict, Optional, Any, TypedDict
from app.models.schemas import POIData

# LangGraph State 스키마

class State(TypedDict):
    """LangGraph의 상태를 나타내는 TypedDict."""
    query: str # 사용자의 초기 요청 (예: "강남에서 데이트 코스 추천해줘")
    user: Dict[str, Any]               # 사용자 데이터
    partner: Dict[str, Any]            # 파트너 데이터
    couple: Dict[str, Any]             # 커플 상태 데이터
    user_choice: Dict[str, Any]   
    poi_data: Optional[Dict[str, List[POIData]]] # Google Place API에서 수집한 정제된 POI 데이터
    available_categories: List[str] # 하드 필터링 후 남은 카테고리
    recommended_sequence: List[str] # LLM이 추천한 카테고리 시퀀스 (예: "식당", "카페")
    recommendations: List[Dict[str, Any]] # 각 카테고리 에이전트의 추천 결과
    previous_recommendations: Optional[List[Dict[str, Any]]]
    already_selected_pois: Optional[List[Dict[str, Any]]]
    exclude_pois: Optional[List[Dict[str, Any]]]
    current_judge: Optional[bool] # 검증 LLM의 판단 결과
    judgement_reason: Optional[str] # 검증 LLM의 판단 이유
    final_output: Optional[str] # 최종 JSON 형식의 출력
    check_count: int # 재시도 횟수 (선택적)

# Response 스키마

from pydantic import BaseModel
from typing import List, Optional

class OpenHours(BaseModel):
    mon: Optional[str] = ""
    tue: Optional[str] = ""
    wed: Optional[str] = ""
    thu: Optional[str] = ""
    fri: Optional[str] = ""
    sat: Optional[str] = ""
    sun: Optional[str] = ""

class POIResponse(BaseModel):
    seq: Optional[int] = None
    name: str
    category: str
    lat: float
    lng: float
    indoor: Optional[bool] = None
    price_level: Optional[int] = None
    open_hours: OpenHours
    alcohol: Optional[int] = None
    mood_tag: Optional[str] = None
    food_tag: Optional[List[str]] = None
    rating_avg: Optional[float] = None
    link: Optional[str] = None

class POIResponse(BaseModel):
    seq: Optional[int] = None
    name: str
    category: str
    lat: float
    lng: float
    indoor: Optional[bool] = None
    price_level: Optional[int] = None
    open_hours: OpenHours
    alcohol: Optional[int] = None
    mood_tag: Optional[str] = None
    food_tag: Optional[List[str]] = None
    rating_avg: Optional[float] = None
    link: Optional[str] = None

class AgentResponse(BaseModel): # LLM이 무조건 맞춰야 하는 최상위 스키마
    explain: str
    data: List[POIResponse]
