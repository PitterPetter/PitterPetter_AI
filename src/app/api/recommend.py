# src/app/api/recommend.py  → 내부 어댑터로 전환 (라우터 삭제)
import os
from app.models.schemas import Trigger
from app.nodes.hardfilter_node import OpenWeatherProvider, run_category_hard_filter

provider = OpenWeatherProvider()

async def get_hardfilter_bundle_for_graph(trigger: Trigger) -> dict:
    """
    langGraph에서 호출해서 하드필터 결과만 state에 합침.
    """
    return await run_category_hard_filter(trigger=trigger, weather_provider=provider)