# src/app/nodes/filters.py
from __future__ import annotations
import os
from dataclasses import dataclass
from datetime import time, datetime, timedelta
from typing import List, Dict, Tuple, Set, Protocol, Optional

import httpx
from zoneinfo import ZoneInfo

from app.models.schemas import Trigger

# ---------- 카테고리 정의 ----------
ALL_CATEGORIES: List[str] = [
    "restaurant", "cafe", "bar",
    "activity", "attraction", "exhibit",
    "walk", "view", "nature",
    "shopping", "performance",
]

INDOOR_STRICT: Set[str] = {"restaurant", "cafe", "bar", "activity", "exhibit", "shopping", "performance"}
OUTDOOR_STRICT: Set[str] = {"walk", "nature"}
MIXED: Set[str] = {"view", "attraction"}
assert set(ALL_CATEGORIES) == INDOOR_STRICT | OUTDOOR_STRICT | MIXED

# ---------- 임계값 (env로 조정 가능) ----------
TEMP_HOT_C = float(os.getenv("RECO_TEMP_HOT_C", "30"))     # ≥ 덥다 → 확정 야외 제외
TEMP_COLD_C = float(os.getenv("RECO_TEMP_COLD_C", "0"))    # ≤ 춥다 → 확정 야외 제외
HUMIDITY_HIGH = int(os.getenv("RECO_HUMIDITY_HIGH", "85")) # ≥ 매우 습함 → 확정 야외 제외
LOCAL_TZ = os.getenv("WEATHER_TZ", "Asia/Seoul")           # time_window 해석 타임존

# ---------- 유틸 ----------
def _parse_hm(hm: str) -> Tuple[int, int]:
    h, m = hm.split(":")
    return int(h), int(m)

def window_now_to_end_local_strict(
    end_hm: str,
    tz: str = LOCAL_TZ,
) -> tuple[datetime, datetime]:
    """
    로컬 타임존 기준:
    - 시작: 지금(now)
    - 종료: 사용자가 설정한 종료 시각(HH:MM)
    - 종료가 지금보다 이르면 에러
    - 최소 길이/자정 넘김 이월 등 '자동 보정' 없음 (엄격)
    """
    now_local = datetime.now(ZoneInfo(tz))
    eh, em = _parse_hm(end_hm)
    end_local = now_local.replace(hour=eh, minute=em, second=0, microsecond=0)

    if end_local <= now_local:
        raise ValueError(
            f"end time must be later than now; now={now_local.strftime('%H:%M')}, end={end_hm}"
        )

    # UTC로 변환해서 반환
    return now_local.astimezone(ZoneInfo("UTC")), end_local.astimezone(ZoneInfo("UTC"))

# ---------- 예보 집계 DTO ----------
@dataclass
class WindowSummary:
    raining_any: bool
    hot_any: bool
    cold_any: bool
    humid_any: bool
    samples: int
    max_temp: Optional[float]
    min_temp: Optional[float]
    max_humidity: Optional[int]

# ---------- Provider 프로토콜 ----------
class ForecastProvider(Protocol):
    async def window_summary(self, *, lat: float, lon: float, start_dt: datetime, end_dt: datetime) -> WindowSummary: ...

# ---------- 무료 3시간 예보 Provider (/data/2.5/forecast) ----------
class Free3hForecastProvider:
    """
    5일/3시간 예보(무료)를 사용.
    도메인: https://api.openweathermap.org
    엔드포인트: /data/2.5/forecast
    """
    def __init__(self, api_key: Optional[str] = None) -> None:
        self.api_key = api_key or os.getenv("OPENWEATHER_API_KEY") or ""
        if not self.api_key:
            raise RuntimeError("OPENWEATHER_API_KEY missing")

    async def _get(self, *, lat: float, lon: float) -> List[dict]:
        url = "https://api.openweathermap.org/data/2.5/forecast"
        params = {"lat": lat, "lon": lon, "appid": self.api_key, "units": "metric"}
        async with httpx.AsyncClient(timeout=6.0) as client:
            r = await client.get(url, params=params)
            r.raise_for_status()
        data = r.json()
        return data.get("list", [])  # 각 item: {dt, main:{temp,humidity}, weather:[{main}], rain:{'3h':..}}

    async def window_summary(self, *, lat: float, lon: float, start_dt: datetime, end_dt: datetime) -> WindowSummary:
        items = await self._get(lat=lat, lon=lon)

        sel: List[dict] = []
        for it in items:
            # API의 dt는 UTC epoch(sec)
            t = datetime.utcfromtimestamp(int(it["dt"])).replace(tzinfo=ZoneInfo("UTC"))
            # 3시간 슬롯의 중심 시각으로 간주하고, 중심이 창구간에 걸리면 포함(간단 정책)
            if start_dt <= t <= end_dt:
                sel.append(it)

        if not sel:
            return WindowSummary(False, False, False, False, 0, None, None, None)

        def is_rain(it: dict) -> bool:
            wmain = ((it.get("weather") or [{}])[0].get("main") or "").lower()
            rain3h = (it.get("rain") or {}).get("3h", 0) or 0
            return ("rain" in wmain) or ("drizzle" in wmain) or (rain3h > 0)

        temps = [float(it["main"]["temp"]) for it in sel if "main" in it and "temp" in it["main"]]
        hums  = [int(it["main"]["humidity"]) for it in sel if "main" in it and "humidity" in it["main"]]

        return WindowSummary(
            raining_any = any(is_rain(it) for it in sel),
            hot_any     = any(t >= TEMP_HOT_C for t in temps) if temps else False,
            cold_any    = any(t <= TEMP_COLD_C for t in temps) if temps else False,
            humid_any   = any(h >= HUMIDITY_HIGH for h in hums) if hums else False,
            samples     = len(sel),
            max_temp    = max(temps) if temps else None,
            min_temp    = min(temps) if temps else None,
            max_humidity= max(hums)  if hums  else None,
        )

# ---------- 하드필터 코어 (LLM/그래프에 넘길 데이터만 산출) ----------
async def run_category_hard_filter(
    *,
    trigger: Trigger,
    weather_provider: ForecastProvider,
) -> Dict[str, object]:
    """
    반환(프론트 X): LLM/후속 노드 입력용 페이로드
    {
      "allowed_categories": [...],
      "excluded_categories": {cat: [reasons...]},
      "hardfilter_debug": {...}
    }
    """
    allowed = set(ALL_CATEGORIES)
    reasons: Dict[str, List[str]] = {c: [] for c in ALL_CATEGORIES}

    # 0) '지금 -> 종료시각' 창구간(로컬 → UTC, 종료가 지금보다 이르면 예외)
    lng, lat = trigger.start
    
    # trigger.time_window = (start_hm, end_hm) 라면, end만 사용
    end_hm = trigger.time_window[1]
    start_utc, end_utc = window_now_to_end_local_strict(end_hm, tz=LOCAL_TZ)

    # 1) 예보 집계(창구간과 겹치는 3시간 슬롯 ANY)
    summary = await weather_provider.window_summary(lat=lat, lon=lng, start_dt=start_utc, end_dt=end_utc)

    # 2) 날씨 규칙
    if summary.raining_any:
        for c in OUTDOOR_STRICT & allowed:
            allowed.discard(c)
            reasons[c].append("weather:rain(window)")

    if summary.hot_any:
        for c in OUTDOOR_STRICT & allowed:
            allowed.discard(c)
            reasons[c].append("weather:hot(window)")

    if summary.cold_any:
        for c in OUTDOOR_STRICT & allowed:
            allowed.discard(c)
            reasons[c].append("weather:cold(window)")

    if summary.humid_any:
        for c in OUTDOOR_STRICT & allowed:
            allowed.discard(c)
            reasons[c].append("weather:humid(window)")

    # 3) 오늘 술 의향
    if not trigger.drink_intent and "bar" in allowed:
        allowed.discard("bar")
        reasons["bar"].append("drink_intent:false")

    excluded = {c: rs for c, rs in reasons.items() if rs}

    return {
        "allowed_categories": sorted(allowed),
        "excluded_categories": excluded,
        "hardfilter_debug": {
            "window_utc": [start_utc.isoformat(), end_utc.isoformat()],
            "forecast_samples": summary.samples,
            "max_temp": summary.max_temp,
            "min_temp": summary.min_temp,
            "max_humidity": summary.max_humidity,
            "raining_any": summary.raining_any,
            "hot_any": summary.hot_any,
            "cold_any": summary.cold_any,
            "humid_any": summary.humid_any,
            "time_window": trigger.time_window,
            "drink_intent": trigger.drink_intent,
            "thresholds": {
                "TEMP_HOT_C": TEMP_HOT_C,
                "TEMP_COLD_C": TEMP_COLD_C,
                "HUMIDITY_HIGH": HUMIDITY_HIGH,
            },
        },
    }

# ---------- LangGraph 노드 어댑터 (state ↔ 함수 연결) ----------
async def node_category_hard_filter(
    state: dict,
    weather_provider: Optional[ForecastProvider] = None
) -> dict:
    provider = weather_provider or Free3hForecastProvider()
    result = await run_category_hard_filter(trigger=state["trigger"], weather_provider=provider)
    return {**state, **result}
