from pathlib import Path
from fastapi.testclient import TestClient
from store_monitoring.main import app

client = TestClient(app)

def test_ingest_endpoint_starts_successfully(tmp_path: Path):
    """
    Tests that the POST /ingest endpoint returns a 200 OK and the correct
    message indicating that the background task has started.
    """
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    # Create dummy files; their content doesn't matter for this test
    (data_dir / "store_status.csv").touch()
    (data_dir / "menu_hours.csv").touch()
    (data_dir / "timezones.csv").touch()

    response = client.post("/ingest", json={"path": str(data_dir)})

    # 1. Check that the request was accepted
    assert response.status_code == 200

    # 2. Check that the response message is correct for a background task
    json_response = response.json()
    assert "started in the background" in json_response["message"]


def test_ingest_endpoint_dir_not_found():
    """
    Tests that the endpoint still immediately rejects a non-existent directory.
    This check happens before the background task is created.
    """
    response = client.post("/ingest", json={"path": "/non/existent/path"})
    assert response.status_code == 404
    assert "Directory not found" in response.json()["detail"]