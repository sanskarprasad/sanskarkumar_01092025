from datetime import datetime, timedelta, timezone
from typing import List, Tuple, Dict
from sqlalchemy.orm import Session
from . import models, time_utils, interpolation

def get_max_poll_timestamp(db: Session) -> datetime:
    """Determines the 'current time' from the latest poll timestamp."""
    max_ts = db.query(models.StoreStatusPoll.timestamp_utc).order_by(
        models.StoreStatusPoll.timestamp_utc.desc()
    ).first()
    return max_ts[0] if max_ts else datetime.now(timezone.utc)

def _get_relevant_business_hours(
    window_start_utc: datetime, window_end_utc: datetime,
    business_hours_db: List[models.BusinessHours], tz: timezone
) -> List[Tuple[datetime, datetime]]:
    """Calculates all UTC business hour intervals that overlap with the window."""
    if not business_hours_db:
        return [(window_start_utc, window_end_utc)]

    bh_map = {bh.day_of_week: bh for bh in business_hours_db}
    all_bh_intervals = []
    
    local_start_date = time_utils.convert_utc_to_local(window_start_utc, tz).date()
    local_end_date = time_utils.convert_utc_to_local(window_end_utc, tz).date()
    
    current_date = local_start_date
    while current_date <= local_end_date:
        bh = bh_map.get(current_date.weekday())
        if bh:
            daily_intervals = time_utils.get_business_hours_for_date(
                current_date, bh.start_time_local, bh.end_time_local, tz
            )
            all_bh_intervals.extend(daily_intervals)
        current_date += timedelta(days=1)
    return all_bh_intervals

def _calculate_total_duration(
    status_intervals: List[Tuple[datetime, datetime, str]],
    business_hours_utc: List[Tuple[datetime, datetime]],
    target_status: str
) -> timedelta:
    """Calculates total duration of a status by intersecting with business hours."""
    total_duration = timedelta()
    for start, end, status in status_intervals:
        if status != target_status:
            continue
        for bh_start, bh_end in business_hours_utc:
            overlap_start = max(start, bh_start)
            overlap_end = min(end, bh_end)
            if overlap_start < overlap_end:
                total_duration += overlap_end - overlap_start
    return total_duration

def calculate_store_report(store_id: str, now_utc: datetime, db: Session) -> Dict[str, float]:
    """Computes the full uptime/downtime report for a single store."""
    windows = {
        "last_hour": (now_utc - timedelta(hours=1), now_utc),
        "last_day": (now_utc - timedelta(days=1), now_utc),
        "last_week": (now_utc - timedelta(weeks=1), now_utc),
    }
    
    tz_info = db.query(models.StoreTimezone).filter_by(store_id=store_id).first()
    store_tz = time_utils.get_store_timezone(tz_info.timezone_str if tz_info else "America/Chicago")
    
    business_hours_db = db.query(models.BusinessHours).filter_by(store_id=store_id).all()
    
    polls = db.query(models.StoreStatusPoll).filter(
        models.StoreStatusPoll.store_id == store_id,
        models.StoreStatusPoll.timestamp_utc >= now_utc - timedelta(weeks=1, hours=1),
        models.StoreStatusPoll.timestamp_utc <= now_utc
    ).all()
    
    report = {}
    for name, (start, end) in windows.items():
        status_intervals = interpolation.get_status_intervals(polls, start, end)
        bh_utc = _get_relevant_business_hours(start, end, business_hours_db, store_tz)
        
        uptime = _calculate_total_duration(status_intervals, bh_utc, "active")
        downtime = _calculate_total_duration(status_intervals, bh_utc, "inactive")
        
        if name == "last_hour":
            report["uptime_last_hour_minutes"] = uptime.total_seconds() / 60
            report["downtime_last_hour_minutes"] = downtime.total_seconds() / 60
        else:
            report[f"uptime_{name}_hours"] = uptime.total_seconds() / 3600
            report[f"downtime_{name}_hours"] = downtime.total_seconds() / 3600
            
    return report