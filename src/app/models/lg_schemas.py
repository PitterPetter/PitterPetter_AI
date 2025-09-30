from pydantic import BaseModel
from typing import List, Optional

class OpenHours(BaseModel):
    mon: str
    tue: str
    wed: str
    thu: str
    fri: str
    sat: str
    sun: str

class POIResponse(BaseModel):       # JSON 강제 구조 정의
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
