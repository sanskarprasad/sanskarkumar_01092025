from pathlib import Path
from fastapi.testclient import TestClient

from store_monitoring import models
from store_monitoring.main import app
from .test_database import test_db, override_get_db

client = TestClient(app)


def test_ingest_endpoint_success(test_db, tmp_path: Path):
    """
    Tests the POST /ingest endpoint with valid sample data.
    Uses the `test_db` fixture to ensure the database is created and torn down.
    """
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    (data_dir / "store_status.csv").write_text(
        "store_id,status,timestamp_utc\n"
        "store1,active,2024-01-25 10:00:00.000000 UTC\n"
        "store1,inactive,2024-01-25 10:30:00.000000 UTC\n"
    )
    # THIS FILENAME MUST BE 'menu_hours.csv'
    (data_dir / "menu_hours.csv").write_text(
        "store_id,dayOfWeek,start_time_local,end_time_local\n"
        "store1,0,09:00:00,17:00:00\n"
    )
    (data_dir / "timezones.csv").write_text(
        "store_id,timezone_str\n"
        "store1,America/New_York\n"
    )

    response = client.post("/ingest", json={"path": str(data_dir)})
    
    assert response.status_code == 200
    json_response = response.json()
    assert json_response["message"] == "Data ingestion successful."
    assert json_response["counts"]["store_status_polls"] == 2
    assert json_response["counts"]["business_hours"] == 1
    assert json_response["counts"]["store_timezones"] == 1

    db = next(override_get_db())
    assert db.query(models.StoreStatusPoll).count() == 2
    assert db.query(models.BusinessHours).count() == 1
    assert db.query(models.StoreTimezone).count() == 1
    db.close()


def test_ingest_endpoint_dir_not_found():
    response = client.post("/ingest", json={"path": "/non/existent/path"})
    assert response.status_code == 404
    assert "Directory not found" in response.json()["detail"]


def test_ingest_endpoint_file_not_found(tmp_path: Path):
    (tmp_path / "store_status.csv").write_text("store_id,status,timestamp_utc\n")
    
    response = client.post("/ingest", json={"path": str(tmp_path)})
    assert response.status_code == 404
    assert "Required data file not found" in response.json()["detail"]