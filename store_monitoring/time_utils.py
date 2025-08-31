from datetime import datetime, time, date, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from typing import List, Tuple

def get_store_timezone(timezone_str: str) -> ZoneInfo:
    """Safely returns a ZoneInfo object, defaulting to 'America/Chicago'."""
    try:
        return ZoneInfo(timezone_str)
    except ZoneInfoNotFoundError:
        return ZoneInfo("America/Chicago")

def convert_utc_to_local(utc_dt: datetime, tz: ZoneInfo) -> datetime:
    """Converts a timezone-aware UTC datetime to a local datetime."""
    if utc_dt.tzinfo is None:
        utc_dt = utc_dt.replace(tzinfo=timezone.utc)
    return utc_dt.astimezone(tz)

def get_business_hours_for_date(
    local_date: date, start_time: time, end_time: time, tz: ZoneInfo
) -> List[Tuple[datetime, datetime]]:
    """Calculates UTC business hour window(s) for a date, handling overnight schedules."""
    intervals = []
    local_start_dt = datetime.combine(local_date, start_time).replace(tzinfo=tz)
    if start_time <= end_time:
        local_end_dt = datetime.combine(local_date, end_time).replace(tzinfo=tz)
        intervals.append((local_start_dt, local_end_dt))
    else:
        end_of_day = datetime.combine(local_date, time(23, 59, 59, 999999)).replace(tzinfo=tz)
        intervals.append((local_start_dt, end_of_day))
        next_day_date = local_date + timedelta(days=1)
        start_of_next_day = datetime.combine(next_day_date, time(0, 0, 0)).replace(tzinfo=tz)
        local_end_dt = datetime.combine(next_day_date, end_time).replace(tzinfo=tz)
        intervals.append((start_of_next_day, local_end_dt))
    
    return [(s.astimezone(timezone.utc), e.astimezone(timezone.utc)) for s, e in intervals]