# src/app/weather/openweather.py
from __future__ import annotations
from datetime import datetime
from zoneinfo import ZoneInfo
import httpx
from typing import List, Dict, Any

from app.core.settings import OPENWEATHER_API_KEY, TEMP_HOT_C, TEMP_COLD_C, HUMIDITY_HIGH
from app.core.urls import OpenWeatherEndpoint, openweather_url
from app.utils.timewindow import slot_overlaps
from app.weather.types import ForecastProvider, WindowSummary

class Free3hForecastProvider(ForecastProvider):
    """
    무료 5일/3시간 예보 사용. URL은 core.urls 모듈에서 주입.
    """
    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = api_key or OPENWEATHER_API_KEY
        if not self.api_key:
            raise RuntimeError("OPENWEATHER_API_KEY missing")

    async def _get(self, *, lat: float, lon: float) -> List[Dict[str, Any]]:
        url = openweather_url(OpenWeatherEndpoint.FORECAST_3H)
        params = {"lat": lat, "lon": lon, "appid": self.api_key, "units": "metric"}
        async with httpx.AsyncClient(timeout=7.0) as client:
            r = await client.get(url, params=params)
            r.raise_for_status()
        return r.json().get("list", [])

    async def window_summary(self, *, lat: float, lon: float, start_dt: datetime, end_dt: datetime) -> WindowSummary:
        slots = await self._get(lat=lat, lon=lon)
        sel = []
        for it in slots:
            slot_start = datetime.utcfromtimestamp(int(it["dt"])).replace(tzinfo=ZoneInfo("UTC"))
            if slot_overlaps(slot_start, 3, start_dt, end_dt):
                sel.append(it)

        if not sel:
            return WindowSummary(False, False, False, False, 0, None, None, None, raw_slots=[])

        temps = [float(x["main"]["temp"]) for x in sel]
        hums  = [int(x["main"]["humidity"]) for x in sel]
        conds = [((x.get("weather") or [{}])[0].get("main","")).lower() for x in sel]

        raining = any(("rain" in c) or ("drizzle" in c) for c in conds)
        hot     = any(t >= TEMP_HOT_C for t in temps)
        cold    = any(t <= TEMP_COLD_C for t in temps)
        humid   = any(h >= HUMIDITY_HIGH for h in hums)

        return WindowSummary(
            raining_any=raining, hot_any=hot, cold_any=cold, humid_any=humid,
            samples=len(sel), max_temp=max(temps), min_temp=min(temps), max_humidity=max(hums),
            raw_slots=sel,
        )
