# src/app/weather/urls.py
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
}