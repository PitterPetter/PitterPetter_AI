# src/app/weather/types.py
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol, List, Dict, Any

@dataclass
class WindowSummary:
    raining_any: bool
    hot_any: bool
    cold_any: bool
    humid_any: bool
    samples: int
    max_temp: float | None
    min_temp: float | None
    max_humidity: int | None
    raw_slots: List[Dict[str, Any]] | None = None

class ForecastProvider(Protocol):
    async def window_summary(self, *, lat: float, lon: float, start_dt: datetime, end_dt: datetime) -> WindowSummary: ...

