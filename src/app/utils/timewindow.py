# src/app/utils/timewindow.py
from __future__ import annotations
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

def parse_hm(hm: str) -> tuple[int, int]:
    h, m = hm.split(":")
    return int(h), int(m)

def window_now_to_end_local_strict(end_hm: str, *, tz: str) -> tuple[datetime, datetime]:
    """로컬TZ 기준: 시작=지금(now), 종료=end_hm; 종료가 과거면 예외."""
    now_local = datetime.now(ZoneInfo(tz))
    h, m = parse_hm(end_hm)
    end_local = now_local.replace(hour=h, minute=m, second=0, microsecond=0)
    if end_local <= now_local:
        raise ValueError(f"end time must be later than now; now={now_local:%H:%M}, end={end_hm}")
    return now_local.astimezone(ZoneInfo("UTC")), end_local.astimezone(ZoneInfo("UTC"))

def slot_overlaps(slot_start_utc: datetime, slot_hours: int, start_utc: datetime, end_utc: datetime) -> bool:
    slot_end = slot_start_utc + timedelta(hours=slot_hours)
    return (slot_start_utc < end_utc) and (slot_end > start_utc)
