from __future__ import annotations
import os
import httpx
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from typing import List, Dict, Any

from app.weather.types import ForecastProvider, WindowSummary
from app.core.settings import KMA_SERVICE_KEY
from app.weather.weather_urls import KMA_ENDPOINT

# ✅ 위경도 → 기상청 격자 변환 함수
def latlon_to_grid(lat: float, lon: float) -> tuple[int, int]:
    # 기상청 공식 변환식 (LCC DFS 좌표계)
    import math
    RE = 6371.00877  # 지구 반경(km)
    GRID = 5.0       # 격자 간격(km)
    SLAT1 = 30.0
    SLAT2 = 60.0
    OLON = 126.0
    OLAT = 38.0
    XO = 43
    YO = 136

    DEGRAD = math.pi / 180.0
    re = RE / GRID
    slat1 = SLAT1 * DEGRAD
    slat2 = SLAT2 * DEGRAD
    olon = OLON * DEGRAD
    olat = OLAT * DEGRAD

    sn = math.tan(math.pi * 0.25 + slat2 * 0.5) / math.tan(math.pi * 0.25 + slat1 * 0.5)
    sn = math.log(math.cos(slat1) / math.cos(slat2)) / math.log(sn)
    sf = math.tan(math.pi * 0.25 + slat1 * 0.5)
    sf = math.pow(sf, sn) * math.cos(slat1) / sn
    ro = math.tan(math.pi * 0.25 + olat * 0.5)
    ro = re * sf / math.pow(ro, sn)

    ra = math.tan(math.pi * 0.25 + lat * DEGRAD * 0.5)
    ra = re * sf / math.pow(ra, sn)
    theta = lon * DEGRAD - olon
    if theta > math.pi:
        theta -= 2.0 * math.pi
    if theta < -math.pi:
        theta += 2.0 * math.pi
    theta *= sn

    x = int(ra * math.sin(theta) + XO + 0.5)
    y = int(ro - ra * math.cos(theta) + YO + 0.5)
    return x, y


class KmaForecastProvider(ForecastProvider):
    """한국 기상청 동네예보 기반 Provider"""

    async def window_summary(self, *, lat: float, lon: float, start_dt: datetime, end_dt: datetime) -> WindowSummary:
        nx, ny = latlon_to_grid(lat, lon)

        # 요청 기준 시간: API 특성상 현재 시간 기준 가장 최근 발표 시각으로 맞춰야 함
        base_date = start_dt.strftime("%Y%m%d")
        base_time = (start_dt - timedelta(hours=1)).strftime("%H00")

        params = {
            "serviceKey": KMA_SERVICE_KEY,
            "pageNo": 1,
            "numOfRows": 1000,
            "dataType": "JSON",
            "base_date": base_date,
            "base_time": base_time,
            "nx": nx,
            "ny": ny,
        }

        async with httpx.AsyncClient(timeout=7.0) as client:
            r = await client.get(KMA_ENDPOINT, params=params)
            r.raise_for_status()
            items = r.json().get("response", {}).get("body", {}).get("items", {}).get("item", [])

        # 필요한 데이터 추출
        temps, hums, conds = [], [], []
        for it in items:
            fcst_time = datetime.strptime(it["fcstDate"] + it["fcstTime"], "%Y%m%d%H%M").replace(
                tzinfo=ZoneInfo("Asia/Seoul")
            )
            if not (start_dt <= fcst_time <= end_dt):
                continue

            category = it["category"]
            val = it["fcstValue"]

            if category == "TMP":  # 기온
                temps.append(float(val))
            elif category == "REH":  # 습도
                hums.append(int(val))
            elif category in ("PTY", "SKY"):  # 강수형태, 하늘상태
                conds.append(val)

        if not temps and not hums and not conds:
            return WindowSummary(False, False, False, False, 0, None, None, None, raw_slots=[])

        raining = any(v != "0" for v in conds)  # PTY 0 = 없음
        hot = any(t >= 30 for t in temps)
        cold = any(t <= 0 for t in temps)
        humid = any(h >= 80 for h in hums)

        return WindowSummary(
            raining_any=raining, hot_any=hot, cold_any=cold, humid_any=humid,
            samples=len(temps), max_temp=max(temps) if temps else None,
            min_temp=min(temps) if temps else None,
            max_humidity=max(hums) if hums else None,
            raw_slots=items,
        )
