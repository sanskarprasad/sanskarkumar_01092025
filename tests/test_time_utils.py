import pytest
from datetime import datetime, date, time, timezone
from zoneinfo import ZoneInfo
from store_monitoring import time_utils

# Define some timezones for testing
TZ_NYC = ZoneInfo("America/New_York") # UTC-4/UTC-5
TZ_CHI = ZoneInfo("America/Chicago")   # UTC-5/UTC-6
TZ_UTC = timezone.utc

def test_get_store_timezone():
    """Tests that valid and invalid timezone strings are handled correctly."""
    assert time_utils.get_store_timezone("America/Los_Angeles") == ZoneInfo("America/Los_Angeles")
    # Test fallback to default
    assert time_utils.get_store_timezone("Invalid/Timezone") == TZ_CHI

def test_convert_utc_to_local():
    """Tests UTC to local time conversion."""
    utc_dt = datetime(2023, 1, 1, 12, 0, 0, tzinfo=TZ_UTC)
    nyc_dt = time_utils.convert_utc_to_local(utc_dt, TZ_NYC)
    assert nyc_dt.year == 2023
    assert nyc_dt.month == 1
    assert nyc_dt.day == 1
    assert nyc_dt.hour == 7 # 12:00 UTC is 07:00 in NYC in January
    assert nyc_dt.tzinfo == TZ_NYC

def test_get_business_hours_for_date_normal_schedule():
    """Tests business hour calculation for a standard, same-day schedule."""
    local_date = date(2023, 8, 29)
    start_time = time(9, 0)
    end_time = time(17, 0)
    
    intervals = time_utils.get_business_hours_for_date(local_date, start_time, end_time, TZ_NYC)
    
    assert len(intervals) == 1
    
    start_utc, end_utc = intervals[0]
    
    # Expected start: 2023-08-29 09:00:00 in NYC is 2023-08-29 13:00:00 UTC
    assert start_utc == datetime(2023, 8, 29, 13, 0, tzinfo=TZ_UTC)
    # Expected end: 2023-08-29 17:00:00 in NYC is 2023-08-29 21:00:00 UTC
    assert end_utc == datetime(2023, 8, 29, 21, 0, tzinfo=TZ_UTC)

def test_get_business_hours_for_date_overnight_schedule():
    """Tests business hour calculation for an overnight schedule."""
    local_date = date(2023, 8, 29)
    start_time = time(22, 0) # 10 PM
    end_time = time(4, 0)   # 4 AM (next day)
    
    intervals = time_utils.get_business_hours_for_date(local_date, start_time, end_time, TZ_CHI)
    
    assert len(intervals) == 2
    
    # Interval 1: 22:00 on Aug 29 to end of day
    start1_utc, end1_utc = intervals[0]
    # Expected start: 2023-08-29 22:00 CDT (UTC-5) -> 2023-08-30 03:00 UTC
    assert start1_utc == datetime(2023, 8, 30, 3, 0, tzinfo=TZ_UTC)
    
    # Interval 2: Start of Aug 30 to 04:00
    start2_utc, end2_utc = intervals[1]
    # Expected end: 2023-08-30 04:00 CDT (UTC-5) -> 2023-08-30 09:00 UTC
    assert end2_utc == datetime(2023, 8, 30, 9, 0, tzinfo=TZ_UTC)
    
    # Check that the intervals are contiguous
    assert end1_utc < start2_utc

def test_24_7_business_hours():
    """Tests the edge case of 24/7 business hours."""
    local_date = date(2023, 1, 1)
    start_time = time(0, 0)
    end_time = time(23, 59, 59) # Representing a full day
    
    intervals = time_utils.get_business_hours_for_date(local_date, start_time, end_time, TZ_NYC)
    
    assert len(intervals) == 1
    
    start_utc, end_utc = intervals[0]
    duration = end_utc - start_utc
    # Duration should be almost 24 hours
    assert duration.total_seconds() >= (24 * 3600 - 1)