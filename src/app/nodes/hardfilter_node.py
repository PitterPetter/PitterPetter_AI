from __future__ import annotations
from typing import Dict, Optional
from app.utils.filters.hardfilter import run_category_hard_filter

from app.weather.kma import KmaForecastProvider
from app.weather.openweather import Free3hForecastProvider
from app.weather.types import ForecastProvider
import os


async def node_category_hard_filter(state: Dict, provider: Optional[ForecastProvider] = None) -> Dict:
    user_choice: dict = state["user_choice"]

    provider_name = os.getenv("WEATHER_PROVIDER", "openweather")
    if provider:
        p = provider
    elif provider_name == "openweather":
        p = Free3hForecastProvider()
    else:
        p = KmaForecastProvider()

    result = await run_category_hard_filter(user_choice=user_choice, weather_provider=p)
    return {**state, **result}
