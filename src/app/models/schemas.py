# src/app/models/schemas.py
from typing import Tuple, List, Dict, Optional
from pydantic import BaseModel, Field, root_validator

# ===== Request =====
class Trigger(BaseModel):
    start: Tuple[float, float] = Field(..., description="[lng, lat]")  #  처음 시작위치
    time_window: Tuple[str, str] = Field(..., description='["HH:MM","HH:MM"]')# 처음 시작 시간 ~ 데이트 종료 시간
    mode: Optional[str] = Field("walk", description='"walk" | "public"') # 뚜벅이냐 or 차가있냐
    drink_intent: bool = Field(..., description="오늘 술 의향") 
    
    @root_validator
    def _validate_time(cls, v):
        for hm in v["time_window"]:
            h, m = hm.split(":")
            int(h); int(m)
        return v

class RecommendRequest(BaseModel):
    trigger: Trigger

# ===== Response =====
class FilterResult(BaseModel):
    allowed: List[str]
    excluded: Dict[str, List[str]]
    debug: Dict[str, object]
