from datetime import datetime, timedelta, timezone
from typing import List, Tuple, Dict, Optional

from sqlalchemy.orm import Session

from . import models, time_utils, interpolation

def get_max_poll_timestamp(db: Session) -> datetime:
    """
    Determines the 'current time' for the analysis by finding the latest
    timestamp in the store status polls.

    Returns:
        The latest UTC datetime from the polls, or the current system time in UTC
        if no polls exist.
    """
    max_timestamp = db.query(models.StoreStatusPoll.timestamp_utc).order_by(
        models.StoreStatusPoll.timestamp_utc.desc()
    ).first()
    
    return max_timestamp[0] if max_timestamp else datetime.now(timezone.utc)

def _get_relevant_business_hours(
    window_start_utc: datetime,
    window_end_utc: datetime,
    business_hours_db: List[models.BusinessHours],
    tz: timezone
) -> List[Tuple[datetime, datetime]]:
    """
    Calculates all active business hour intervals in UTC that overlap with the
    given observation window.
    """
    if not business_hours_db:
        # If no business hours are specified, the store is considered open 24/7.
        return [(window_start_utc, window_end_utc)]

    business_hours_map = {bh.day_of_week: bh for bh in business_hours_db}
    
    all_bh_intervals = []
    
    # Iterate through each day that could possibly overlap with the UTC window
    local_start_date = time_utils.convert_utc_to_local(window_start_utc, tz).date()
    local_end_date = time_utils.convert_utc_to_local(window_end_utc, tz).date()
    
    current_date = local_start_date
    while current_date <= local_end_date:
        day_of_week = current_date.weekday()
        business_hour = business_hours_map.get(day_of_week)
        
        if business_hour:
            daily_intervals = time_utils.get_business_hours_for_date(
                current_date,
                business_hour.start_time_local,
                business_hour.end_time_local,
                tz,
            )
            all_bh_intervals.extend(daily_intervals)
        current_date += timedelta(days=1)
        
    return all_bh_intervals

def _calculate_total_duration(
    status_intervals: List[Tuple[datetime, datetime, str]],
    business_hours_utc: List[Tuple[datetime, datetime]],
    target_status: str
) -> timedelta:
    """
    Calculates the total duration of a given status ('active' or 'inactive')
    by finding the intersection of status intervals and business hours.
    """
    total_duration = timedelta()
    
    for start, end, status in status_intervals:
        if status != target_status:
            continue
        
        for bh_start, bh_end in business_hours_utc:
            # Find the intersection between the status interval and the business hours interval
            overlap_start = max(start, bh_start)
            overlap_end = min(end, bh_end)
            
            if overlap_start < overlap_end:
                total_duration += overlap_end - overlap_start
                
    return total_duration

def calculate_store_report(
    store_id: str,
    now_utc: datetime,
    db: Session
) -> Dict[str, float]:
    """
    Computes the full uptime/downtime report for a single store.

    Args:
        store_id: The ID of the store to report on.
        now_utc: The reference 'current time' for the report.
        db: The SQLAlchemy database session.

    Returns:
        A dictionary containing the computed report metrics.
    """
    # 1. Define observation windows
    last_hour_window = (now_utc - timedelta(hours=1), now_utc)
    last_day_window = (now_utc - timedelta(days=1), now_utc)
    last_week_window = (now_utc - timedelta(weeks=1), now_utc)
    
    # 2. Fetch all necessary data for the store
    timezone_info = db.query(models.StoreTimezone).filter_by(store_id=store_id).first()
    store_tz = time_utils.get_store_timezone(
        timezone_info.timezone_str if timezone_info else "America/Chicago"
    )
    
    business_hours_db = db.query(models.BusinessHours).filter_by(store_id=store_id).all()
    
    # Fetch polls from a slightly wider window to handle interpolation at the edges
    polls = db.query(models.StoreStatusPoll).filter(
        models.StoreStatusPoll.store_id == store_id,
        models.StoreStatusPoll.timestamp_utc >= last_week_window[0] - timedelta(hours=1),
        models.StoreStatusPoll.timestamp_utc <= now_utc
    ).all()
    
    report = {}

    for window_name, window in {
        "last_hour": last_hour_window,
        "last_day": last_day_window,
        "last_week": last_week_window
    }.items():
        window_start, window_end = window
        
        # 3. Get continuous status timeline
        status_intervals = interpolation.get_status_intervals(polls, window_start, window_end)
        
        # 4. Get relevant business hours in UTC
        business_hours_utc = _get_relevant_business_hours(
            window_start, window_end, business_hours_db, store_tz
        )
        
        # 5. Calculate uptime and downtime by intersecting the two timelines
        uptime_duration = _calculate_total_duration(status_intervals, business_hours_utc, "active")
        downtime_duration = _calculate_total_duration(status_intervals, business_hours_utc, "inactive")
        
        if window_name == "last_hour":
            report["uptime_last_hour_minutes"] = uptime_duration.total_seconds() / 60
            report["downtime_last_hour_minutes"] = downtime_duration.total_seconds() / 60
        else:
            report[f"uptime_{window_name}_hours"] = uptime_duration.total_seconds() / 3600
            report[f"downtime_{window_name}_hours"] = downtime_duration.total_seconds() / 3600
            
    return report