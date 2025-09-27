from pydantic import BaseModel, Field, model_validator
from typing import Tuple, List, Dict, Optional, Any, TypedDict
from app.models.schemas import POIData

# LangGraph State 스키마

class State(TypedDict):
    """LangGraph의 상태를 나타내는 TypedDict."""
    query: str # 사용자의 초기 요청 (예: "강남에서 데이트 코스 추천해줘")
    user_data: Dict[str, Any] # 사용자의 유저 데이터 (온보딩 및 기존 데이터)
    UserChoice_data: Dict[str, Any] # 날씨, 음주 등 트리거 데이터
    poi_data: Optional[Dict[str, List[POIData]]] # Google Place API에서 수집한 정제된 POI 데이터
    available_categories: List[str] # 하드 필터링 후 남은 카테고리
    recommended_sequence: List[str] # LLM이 추천한 카테고리 시퀀스 (예: "식당", "카페")
    recommendations: List[Dict[str, Any]] # 각 카테고리 에이전트의 추천 결과
    current_judge: Optional[bool] # 검증 LLM의 판단 결과
    judgement_reason: Optional[str] # 검증 LLM의 판단 이유
    final_output: Optional[str] # 최종 JSON 형식의 출력
    check_count: int # 재시도 횟수 (선택적)

# Response 스키마

class POIResopnse(BaseModel):       # JSON 강제 구조 정의
    seq: Optional[int] = None
    name: str
    category: str
    lat: float
    lng: float
    indoor: Optional[bool] = None
    price_level: Optional[int] = None
    open_hours: Optional[Dict[str, str]] = None
    alcohol: Optional[int] = None
    mood_tag: Optional[str] = None
    food_tag: Optional[List[str]] = None
    rating_avg: Optional[float] = None
    link: Optional[str] = None

class AgentResponse(BaseModel): # LLM이 무조건 맞춰야 하는 최상위 스키마
    explain: str
    data: List[POIResopnse]