import pytest
from datetime import datetime, time, timedelta, timezone
from collections import namedtuple

from store_monitoring import reporting, models

# Mock ORM models that include store_id
MockStoreTimezone = namedtuple("MockStoreTimezone", ["store_id", "timezone_str"])
MockBusinessHours = namedtuple("MockBusinessHours", ["store_id", "day_of_week", "start_time_local", "end_time_local"])

# A more robust mock for chained SQLAlchemy queries.
# This class holds its own state, preventing data from leaking between calls.
class MockQuery:
    def __init__(self, data):
        self._data = list(data)

    def filter_by(self, **kwargs):
        key, val = list(kwargs.items())[0]
        self._data = [d for d in self._data if getattr(d, key) == val]
        return self

    def filter(self, *args):
        # This mock doesn't implement the time-range filter for polls,
        # it just returns all polls provided for the test.
        return self

    def first(self):
        return self._data[0] if self._data else None

    def all(self):
        return self._data

# A mock DB session that uses the robust MockQuery.
# Each call to .query() returns a *new* MockQuery object, just like SQLAlchemy.
class MockDb:
    def __init__(self, data):
        self.data = data

    def query(self, model):
        if model == models.StoreTimezone:
            return MockQuery(self.data.get("timezones", []))
        if model == models.BusinessHours:
            return MockQuery(self.data.get("business_hours", []))
        if model == models.StoreStatusPoll:
            return MockQuery(self.data.get("polls", []))
        return MockQuery([])

# Define a fixed "now" for deterministic tests (a Wednesday)
NOW = datetime(2023, 1, 25, 18, 0, 0, tzinfo=timezone.utc)

def test_always_active_store():
    """Tests a store that is always active during its business hours."""
    store_id = "store_active"
    
    test_data = {
        "timezones": [MockStoreTimezone(store_id, "America/New_York")],
        "business_hours": [
            # Provide hours for both days in the 'last_day' window
            MockBusinessHours(store_id, 2, time(10, 0), time(20, 0)), # Wednesday
            MockBusinessHours(store_id, 1, time(10, 0), time(20, 0)), # Tuesday
        ],
        "polls": [
            models.StoreStatusPoll(
                store_id=store_id,
                timestamp_utc=NOW - timedelta(hours=24),
                status="active"
            )
        ]
    }
    mock_db = MockDb(test_data)
    
    report = reporting.calculate_store_report(store_id, NOW, mock_db)
    
    # Last hour (17-18 UTC) is 12-13 local, which is inside business hours (10-20).
    assert report["uptime_last_hour_minutes"] == pytest.approx(60)
    assert report["downtime_last_hour_minutes"] == pytest.approx(0)
    
    # Last day is 13:00 local Tue -> 13:00 local Wed.
    # Uptime is (13:00-20:00) on Tue (7 hrs) + (10:00-13:00) on Wed (3 hrs) = 10 hours.
    assert report["uptime_last_day_hours"] == pytest.approx(10)
    assert report["downtime_last_day_hours"] == pytest.approx(0)

def test_always_inactive_store_247():
    """Tests a store with no polls (inactive) that is open 24/7."""
    store_id = "store_inactive_247"
    
    test_data = {
        "timezones": [MockStoreTimezone(store_id, "America/Chicago")],
        "business_hours": [],  # No hours means 24/7
        "polls": []  # No polls means inactive
    }
    mock_db = MockDb(test_data)
    
    report = reporting.calculate_store_report(store_id, NOW, mock_db)
    
    assert report["uptime_last_hour_minutes"] == pytest.approx(0)
    assert report["downtime_last_hour_minutes"] == pytest.approx(60)
    assert report["downtime_last_day_hours"] == pytest.approx(24)
    assert report["downtime_last_week_hours"] == pytest.approx(24 * 7)

def test_mixed_status_store():
    """Tests a store that was active for part of the time."""
    store_id = "store_mixed"
    
    test_data = {
        "timezones": [MockStoreTimezone(store_id, "UTC")],
        "business_hours": [MockBusinessHours(store_id, NOW.weekday(), time(0, 0), time(23, 59))],
        "polls": [
            models.StoreStatusPoll(
                store_id=store_id,
                timestamp_utc=NOW - timedelta(minutes=45),  # at 17:15
                status="active"
            ),
            models.StoreStatusPoll(
                store_id=store_id,
                timestamp_utc=NOW - timedelta(minutes=15),  # at 17:45
                status="inactive"
            )
        ]
    }
    mock_db = MockDb(test_data)
    
    report = reporting.calculate_store_report(store_id, NOW, mock_db)
    
    # Last hour window (17:00 -> 18:00 UTC):
    # Active from 17:00 to 17:45 (45 mins).
    # Inactive from 17:45 to 18:00 (15 mins).
    assert report["uptime_last_hour_minutes"] == pytest.approx(45)
    assert report["downtime_last_hour_minutes"] == pytest.approx(15)