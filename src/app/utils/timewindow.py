# src/app/utils/timewindow.py
from __future__ import annotations
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

def parse_hm(hm: str) -> tuple[int, int]:
    h, m = hm.split(":")
    return int(h), int(m)

def window_now_to_end_local_strict(end_hm: str, *, tz: str) -> tuple[datetime, datetime]:
    """
    로컬 TZ 기준으로:
      - 시작: 현재(now_local)
      - 종료: end_hm (오늘 또는 다음날)
    현재시간이 이미 end_hm 이후라면 자동으로 다음날로 이월.
    """
    tzinfo = ZoneInfo(tz)
    now_local = datetime.now(tzinfo)
    h, m = parse_hm(end_hm)

    # 종료시각 구성
    end_local = now_local.replace(hour=h, minute=m, second=0, microsecond=0)

    # ✅ 현재시간보다 이전이면 다음날 같은 시각으로 롤오버
    if end_local <= now_local:
        end_local += timedelta(days=1)

    # UTC로 변환
    start_utc = now_local.astimezone(timezone.utc)
    end_utc = end_local.astimezone(timezone.utc)
    return start_utc, end_utc

def window_from_range_local_strict(start_hm: str, end_hm: str, *, tz: str) -> tuple[datetime, datetime]:
    """사용자 정의 시작/종료 시각을 기준으로 UTC 창 계산."""

    tzinfo = ZoneInfo(tz)
    now_local = datetime.now(tzinfo)

    sh, sm = parse_hm(start_hm)
    eh, em = parse_hm(end_hm)

    start_local = now_local.replace(hour=sh, minute=sm, second=0, microsecond=0)
    end_local = now_local.replace(hour=eh, minute=em, second=0, microsecond=0)

    if start_local < now_local:
        start_local += timedelta(days=1)

    while end_local <= start_local:
        end_local += timedelta(days=1)

    start_utc = start_local.astimezone(timezone.utc)
    end_utc = end_local.astimezone(timezone.utc)
    return start_utc, end_utc


def slot_overlaps(slot_start_utc: datetime, slot_hours: int, start_utc: datetime, end_utc: datetime) -> bool:
    slot_end = slot_start_utc + timedelta(hours=slot_hours) 
    return (slot_start_utc < end_utc) and (slot_end > start_utc)
