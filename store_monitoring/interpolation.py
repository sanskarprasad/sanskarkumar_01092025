from datetime import datetime
from typing import List, Tuple
from .models import StoreStatusPoll

def get_status_intervals(
    polls: List[StoreStatusPoll], window_start_utc: datetime, window_end_utc: datetime
) -> List[Tuple[datetime, datetime, str]]:
    """Generates continuous status intervals from discrete polls using interpolation."""
    if not polls:
        return [(window_start_utc, window_end_utc, "inactive")]

    polls.sort(key=lambda p: p.timestamp_utc)
    intervals = []
    current_time = window_start_utc
    first_poll = polls[0]
    
    if current_time < first_poll.timestamp_utc:
        intervals.append((current_time, first_poll.timestamp_utc, first_poll.status))
    
    for i in range(len(polls) - 1):
        start_poll = polls[i]
        end_poll = polls[i+1]
        intervals.append((start_poll.timestamp_utc, end_poll.timestamp_utc, start_poll.status))
    
    last_poll = polls[-1]
    if last_poll.timestamp_utc < window_end_utc:
        intervals.append((last_poll.timestamp_utc, window_end_utc, last_poll.status))
    
    if not intervals and polls:
        return [(window_start_utc, window_end_utc, polls[0].status)]
        
    return intervals