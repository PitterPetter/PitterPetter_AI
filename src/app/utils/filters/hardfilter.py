from __future__ import annotations
from typing import Dict, List, Set
from app.core.settings import WEATHER_TZ, TEMP_HOT_C, TEMP_COLD_C, HUMIDITY_HIGH
from app.utils.timewindow import window_from_range_local_strict
from app.utils.filters.categories import ALL_CATEGORIES, OUTDOOR_STRICT
from app.weather.types import ForecastProvider


async def run_category_hard_filter(*, user_choice: dict, weather_provider: ForecastProvider) -> Dict[str, object]:
    allowed: Set[str] = set(ALL_CATEGORIES)
    reasons: Dict[str, List[str]] = {c: [] for c in ALL_CATEGORIES}

    # 시간창 계산 (사용자 지정 시작~종료)
    start_hm, end_hm = user_choice["time_window"]
    start_utc, end_utc = window_from_range_local_strict(start_hm, end_hm, tz=WEATHER_TZ)

    # 예보 요약
    lat = user_choice["start"][1]
    lon = user_choice["start"][0]
    summary = await weather_provider.window_summary(lat=lat, lon=lon, start_dt=start_utc, end_dt=end_utc)

    print("🌦️ [HARD FILTER] 날씨 요약:", summary)
    print("🌦️ [HARD FILTER] 입력 user_choice:", user_choice)

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
    if not user_choice["drink_intent"] and "bar" in allowed:
        allowed.discard("bar")
        reasons["bar"].append("drink_intent:false")

    excluded = {c: rs for c, rs in reasons.items() if rs}

    print("✅ [HARD FILTER] Allowed categories:", allowed)
    print("❌ [HARD FILTER] Excluded categories:", excluded)

    return {
        "allowed_categories": sorted(allowed),
        "excluded_categories": excluded,
        "hardfilter_debug": {
            "window_utc": [start_utc.isoformat(), end_utc.isoformat()],
            "summary_flags": {
                "raining": summary.raining_any,
                "hot": summary.hot_any,
                "cold": summary.cold_any,
                "humid": summary.humid_any,
            },
            "max_temp": summary.max_temp,
            "min_temp": summary.min_temp,
            "max_humidity": summary.max_humidity,
            "time_window_input": user_choice["time_window"],
            "drink_intent": user_choice["drink_intent"],
            "thresholds": {
                "TEMP_HOT_C": TEMP_HOT_C,
                "TEMP_COLD_C": TEMP_COLD_C,
                "HUMIDITY_HIGH": HUMIDITY_HIGH,
            },
        },
    }
