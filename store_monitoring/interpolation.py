from datetime import datetime
from typing import List, Tuple

from .models import StoreStatusPoll

def get_status_intervals(
    polls: List[StoreStatusPoll],
    window_start_utc: datetime,
    window_end_utc: datetime
) -> List[Tuple[datetime, datetime, str]]:
    """
    Generates a continuous timeline of status intervals within a given window,
    based on a list of discrete status polls.

    This function implements the following interpolation/extrapolation logic:
    1. Sorts the polls by timestamp.
    2. If no polls are in the window, the entire window is considered 'inactive'.
    3. The status of the first poll is carried backward to the start of the window.
    4. Between two consecutive polls, the status of the earlier poll is used.
    5. The status of the last poll is carried forward to the end of the window.

    Args:
        polls: A list of StoreStatusPoll ORM objects, pre-filtered for a store
               and relevant time period.
        window_start_utc: The UTC start time of the observation window.
        window_end_utc: The UTC end time of the observation window.

    Returns:
        A list of tuples, where each tuple represents a continuous status
        interval in the format (start_time_utc, end_time_utc, status).
    """
    if not polls:
        return [(window_start_utc, window_end_utc, "inactive")]

    # Ensure polls are sorted by timestamp
    polls.sort(key=lambda p: p.timestamp_utc)

    intervals = []
    current_time = window_start_utc

    # 1. Handle time from window start to the first poll (carry backward)
    first_poll_time = polls[0].timestamp_utc
    first_poll_status = polls[0].status
    if current_time < first_poll_time:
        intervals.append((current_time, first_poll_time, first_poll_status))
    current_time = first_poll_time

    # 2. Handle time between polls (carry forward)
    for i in range(len(polls) - 1):
        start_poll = polls[i]
        end_poll = polls[i+1]
        intervals.append(
            (start_poll.timestamp_utc, end_poll.timestamp_utc, start_poll.status)
        )
    current_time = polls[-1].timestamp_utc

    # 3. Handle time from the last poll to the window end (carry forward)
    if current_time < window_end_utc:
        last_poll_status = polls[-1].status
        intervals.append((current_time, window_end_utc, last_poll_status))

    # In the case of a single poll, the above logic might result in an empty list if the
    # poll is exactly at the window start. The final check ensures the full interval is returned.
    if not intervals and len(polls) == 1:
        return [(window_start_utc, window_end_utc, polls[0].status)]

    return intervals