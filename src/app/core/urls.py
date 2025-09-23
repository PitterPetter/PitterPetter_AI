# src/app/core/urls.py
from __future__ import annotations
import os
from typing import Final

# 베이스 도메인은 .env로 덮어쓸 수 있게
OPENWEATHER_BASE: Final[str] = os.getenv("OPENWEATHER_BASE", "https://api.openweathermap.org")
OPENWEATHER_PRO_BASE: Final[str] = os.getenv("OPENWEATHER_PRO_BASE", "https://pro.openweathermap.org")

# 경로 상수 (도메인과 분리)
OPENWEATHER_PATHS = {
    # 무료 5일/3시간 예보
    "forecast3h": "/data/2.5/forecast",
    # 현재 날씨
    "current": "/data/2.5/weather",
    # One Call 3.0 (48h hourly) - 과금 유의
    "onecall": "/data/3.0/onecall",
    # Hourly 4 days (Pro 도메인) - 학생/유료
    "forecast_hourly_4d": "/data/2.5/forecast/hourly",
}

def ow_url(path_key: str, *, pro: bool = False) -> str:
    """
    OpenWeather endpoint 빌더.
    ex) ow_url("forecast3h") -> "https://api.openweathermap.org/data/2.5/forecast"
        ow_url("forecast_hourly_4d", pro=True) -> "https://pro.openweathermap.org/data/2.5/forecast/hourly"
    """
    base = OPENWEATHER_PRO_BASE if pro else OPENWEATHER_BASE
    path = OPENWEATHER_PATHS[path_key]
    return f"{base}{path}"
