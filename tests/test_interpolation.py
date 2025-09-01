import pytest
from datetime import datetime, timedelta, timezone
from collections import namedtuple

from store_monitoring.interpolation import get_status_intervals

MockPoll = namedtuple("MockPoll", ["timestamp_utc", "status"])

BASE_TIME = datetime(2023, 1, 1, 12, 0, 0, tzinfo=timezone.utc)

def test_standard_interpolation():
    """Tests a typical scenario with multiple polls within the window."""
    window_start = BASE_TIME
    window_end = BASE_TIME + timedelta(hours=1)
    
    polls = [
        MockPoll(BASE_TIME + timedelta(minutes=15), "inactive"),
        MockPoll(BASE_TIME + timedelta(minutes=45), "active"),
    ]
    
    intervals = get_status_intervals(polls, window_start, window_end)
    
    assert len(intervals) == 3
    assert intervals[0] == (window_start, polls[0].timestamp_utc, "inactive")
    assert intervals[1] == (polls[0].timestamp_utc, polls[1].timestamp_utc, "inactive")
    assert intervals[2] == (polls[1].timestamp_utc, window_end, "active")

def test_no_polls_in_window():
    window_start = BASE_TIME
    window_end = BASE_TIME + timedelta(hours=1)
    
    intervals = get_status_intervals([], window_start, window_end)
    
    assert len(intervals) == 1
    assert intervals[0] == (window_start, window_end, "inactive")

def test_single_poll_in_window():
    window_start = BASE_TIME
    window_end = BASE_TIME + timedelta(hours=1)
    
    polls = [MockPoll(BASE_TIME + timedelta(minutes=30), "active")]
    
    intervals = get_status_intervals(polls, window_start, window_end)
    
    assert len(intervals) == 2
    assert intervals[0] == (window_start, polls[0].timestamp_utc, "active")
    assert intervals[1] == (polls[0].timestamp_utc, window_end, "active")

def test_poll_at_window_start():
    """Tests when a poll's timestamp is exactly at the window start."""
    window_start = BASE_TIME
    window_end = BASE_TIME + timedelta(hours=1)
    
    polls = [
        MockPoll(window_start, "active"),
        MockPoll(window_start + timedelta(minutes=30), "inactive"),
    ]
    
    intervals = get_status_intervals(polls, window_start, window_end)
    
    assert len(intervals) == 2
    assert intervals[0] == (polls[0].timestamp_utc, polls[1].timestamp_utc, "active")
    assert intervals[1] == (polls[1].timestamp_utc, window_end, "inactive")

def test_poll_at_window_end():
    """Tests when a poll's timestamp is exactly at the window end."""
    window_start = BASE_TIME
    window_end = BASE_TIME + timedelta(hours=1)
    
    polls = [
        MockPoll(window_start + timedelta(minutes=30), "inactive"),
        MockPoll(window_end, "active"),
    ]
    
    intervals = get_status_intervals(polls, window_start, window_end)
    
    assert len(intervals) == 2
    assert intervals[0] == (window_start, polls[0].timestamp_utc, "inactive")
    assert intervals[1] == (polls[0].timestamp_utc, window_end, "inactive")

def test_unsorted_polls():
    """Tests that the function correctly sorts polls before processing."""
    window_start = BASE_TIME
    window_end = BASE_TIME + timedelta(hours=1)
    
    polls = [
        MockPoll(BASE_TIME + timedelta(minutes=45), "active"),
        MockPoll(BASE_TIME + timedelta(minutes=15), "inactive"),
    ]
    
    intervals = get_status_intervals(polls, window_start, window_end)
    
    sorted_p1_time = BASE_TIME + timedelta(minutes=15)
    sorted_p2_time = BASE_TIME + timedelta(minutes=45)
    
    assert len(intervals) == 3
    assert intervals[0] == (window_start, sorted_p1_time, "inactive")
    assert intervals[1] == (sorted_p1_time, sorted_p2_time, "inactive")
    assert intervals[2] == (sorted_p2_time, window_end, "active")