# src/app/core/settings.py
from __future__ import annotations
import os

WEATHER_TZ = os.getenv("WEATHER_TZ", "Asia/Seoul")

TEMP_HOT_C = float(os.getenv("RECO_TEMP_HOT_C", "30"))
TEMP_COLD_C = float(os.getenv("RECO_TEMP_COLD_C", "0"))
HUMIDITY_HIGH = int(os.getenv("RECO_HUMIDITY_HIGH", "85"))

OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY", "")
