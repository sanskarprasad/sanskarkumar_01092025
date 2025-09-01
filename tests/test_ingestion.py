from pathlib import Path
from fastapi.testclient import TestClient
from store_monitoring.main import app

client = TestClient(app)

def test_ingest_endpoint_starts_successfully(tmp_path: Path):
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    (data_dir / "store_status.csv").touch()
    (data_dir / "menu_hours.csv").touch()
    (data_dir / "timezones.csv").touch()

    response = client.post("/ingest", json={"path": str(data_dir)})

    assert response.status_code == 200

    json_response = response.json()
    assert "started in the background" in json_response["message"]


def test_ingest_endpoint_dir_not_found():
    response = client.post("/ingest", json={"path": "/non/existent/path"})
    assert response.status_code == 404
    assert "Directory not found" in response.json()["detail"]