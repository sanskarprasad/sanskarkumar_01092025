from datetime import datetime, time, date, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from typing import List, Tuple, Optional

def get_store_timezone(timezone_str: str) -> ZoneInfo:
    """
    Safely returns a ZoneInfo object for a given timezone string.
    Defaults to 'America/Chicago' if the timezone is invalid or not found.
    """
    try:
        return ZoneInfo(timezone_str)
    except ZoneInfoNotFoundError:
        return ZoneInfo("America/Chicago")

def convert_utc_to_local(utc_dt: datetime, tz: ZoneInfo) -> datetime:
    """
    Converts a timezone-aware UTC datetime to a local datetime.
    """
    if utc_dt.tzinfo is None:
        utc_dt = utc_dt.replace(tzinfo=timezone.utc)
    return utc_dt.astimezone(tz)

def get_business_hours_for_date(
    local_date: date,
    start_time: time,
    end_time: time,
    tz: ZoneInfo
) -> List[Tuple[datetime, datetime]]:
    """
    Calculates the business hour window(s) for a specific local date,
    handling overnight schedules correctly.
    """
    intervals = []
    
    # Combine date and time, then make the naive datetime timezone-aware.
    local_start_dt = datetime.combine(local_date, start_time).replace(tzinfo=tz)

    if start_time <= end_time:
        # Normal same-day schedule
        local_end_dt = datetime.combine(local_date, end_time).replace(tzinfo=tz)
        intervals.append((local_start_dt, local_end_dt))
    else:
        # Overnight schedule
        # First part: from start time to end of the day
        end_of_day = datetime.combine(local_date, time(23, 59, 59, 999999)).replace(tzinfo=tz)
        intervals.append((local_start_dt, end_of_day))
        
        # Second part: from start of the next day to the end time
        next_day_date = local_date + timedelta(days=1)
        start_of_next_day = datetime.combine(next_day_date, time(0, 0, 0)).replace(tzinfo=tz)
        local_end_dt = datetime.combine(next_day_date, end_time).replace(tzinfo=tz)
        intervals.append((start_of_next_day, local_end_dt))
        
    # Convert all local intervals to UTC for consistent comparison
    utc_intervals = [
        (start.astimezone(timezone.utc), end.astimezone(timezone.utc))
        for start, end in intervals
    ]
    
    return utc_intervals