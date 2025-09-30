# src/app/filters/hardfilter.py
from __future__ import annotations
from typing import Dict, List, Set
from app.core.settings import WEATHER_TZ, TEMP_HOT_C, TEMP_COLD_C, HUMIDITY_HIGH
from app.utils.timewindow import window_now_to_end_local_strict
from app.models.schemas import Trigger
from app.utils.filters.categories import ALL_CATEGORIES, OUTDOOR_STRICT
from app.weather.types import ForecastProvider

async def run_category_hard_filter(*, trigger: Trigger, weather_provider: ForecastProvider) -> Dict[str, object]:
    allowed: Set[str] = set(ALL_CATEGORIES)
    reasons: Dict[str, List[str]] = {c: [] for c in ALL_CATEGORIES}

    # 시간창 계산 (now→end, strict)
    start_utc, end_utc = window_now_to_end_local_strict(trigger.time_window[1], tz=WEATHER_TZ)

    # 예보 요약
    lat = trigger.start[1]; lon = trigger.start[0]
    summary = await weather_provider.window_summary(lat=lat, lon=lon, start_dt=start_utc, end_dt=end_utc)

    # 규칙: 창구간 내 ANY면 실외 제외
    weather_map = {
    "raining_any": "weather:rain(window)",
    "hot_any": "weather:hot(window)",
    "cold_any": "weather:cold(window)",
    "humid_any": "weather:humid(window)",
    }

    for attr, reason in weather_map.items():
        if getattr(summary, attr):
            for c in OUTDOOR_STRICT & allowed:
                allowed.discard(c)
                reasons[c].append(reason)
                
    # 술 의향
    if not trigger.drink_intent and "bar" in allowed:
        allowed.discard("bar"); reasons["bar"].append("drink_intent:false")

    excluded = {c: rs for c, rs in reasons.items() if rs}
    return {
        "allowed_categories": sorted(allowed),
        "excluded_categories": excluded,
        "hardfilter_debug": {
            "window_utc": [start_utc.isoformat(), end_utc.isoformat()],
            "summary_flags": {
                "raining": summary.raining_any, "hot": summary.hot_any,
                "cold": summary.cold_any, "humid": summary.humid_any
            },
            "max_temp": summary.max_temp, "min_temp": summary.min_temp, "max_humidity": summary.max_humidity,
            "time_window_input": trigger.time_window, "drink_intent": trigger.drink_intent,
            "thresholds": {"TEMP_HOT_C": TEMP_HOT_C, "TEMP_COLD_C": TEMP_COLD_C, "HUMIDITY_HIGH": HUMIDITY_HIGH},
        },
    }
