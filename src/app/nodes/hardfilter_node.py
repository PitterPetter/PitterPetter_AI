# src/app/nodes/hardfilter_node.py
from __future__ import annotations
from typing import Dict, Optional
from app.models.schemas import Trigger
from app.filters.hardfilter import run_category_hard_filter
from app.weather.openweather import Free3hForecastProvider
from app.weather.types import ForecastProvider

async def node_category_hard_filter(state: Dict, provider: Optional[ForecastProvider] = None) -> Dict:
    trig: Trigger = state["trigger"]
    p = provider or Free3hForecastProvider()
    result = await run_category_hard_filter(trigger=trig, weather_provider=p)
    return {**state, **result}
