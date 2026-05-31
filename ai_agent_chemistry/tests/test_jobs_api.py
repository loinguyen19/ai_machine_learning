import time

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_create_job_returns_202() -> None:
    response = client.post(
        "/v1/videos",
        json={"query": "How does the pH scale work?", "topic": "chemistry"},
    )
    assert response.status_code == 202
    body = response.json()
    assert body["status"] == "queued"
    assert body["job_id"]


def test_get_unknown_job_404() -> None:
    response = client.get("/v1/videos/not-a-real-id")
    assert response.status_code == 404


def test_invalid_query_eventually_fails() -> None:
    response = client.post(
        "/v1/videos",
        json={"query": "Explain photosynthesis", "topic": "chemistry"},
    )
    assert response.status_code == 202
    job_id = response.json()["job_id"]

    for _ in range(15):
        detail = client.get(f"/v1/videos/{job_id}")
        if detail.json()["status"] == "failed":
            assert detail.json()["error_message"]
            return
        time.sleep(0.1)
    raise AssertionError("Expected failed status for unsupported query")
