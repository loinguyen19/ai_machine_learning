import pytest
from fastapi.testclient import TestClient
from ai_agent_video_generation.claude.app.main import app
from unittest.mock import patch, AsyncMock

client = TestClient(app)

def test_health():
    r = client.get("/health")
    assert r.status_code == 200

def test_request_invalid_concept():
    r = client.post("/videos/request", json={"concept": "explain quantum gravity"})
    assert r.status_code == 422

def test_request_valid_concept_returns_pending():
    with patch("app.routers.videos.run_pipeline", new_callable=AsyncMock):
        r = client.post("/videos/request", json={"concept": "How does the pH scale work?"})
    assert r.status_code == 202
    data = r.json()
    assert data["status"] == "pending"
    assert "job_id" in data

def test_list_jobs():
    r = client.get("/videos/jobs")
    assert r.status_code == 200
    assert isinstance(r.json(), list)

def test_get_nonexistent_job():
    r = client.get("/videos/jobs/nonexistent-id")
    assert r.status_code == 404

def test_download_not_completed_job():
    with patch("app.routers.videos.run_pipeline", new_callable=AsyncMock):
        r = client.post("/videos/request", json={"concept": "Why do atoms form covalent bonds?"})
    job_id = r.json()["job_id"]
    r2 = client.get(f"/videos/jobs/{job_id}/download")
    assert r2.status_code == 409