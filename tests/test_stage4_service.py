from __future__ import annotations

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.stage4.service import app

pytestmark = pytest.mark.stage4


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def test_stage4_service_health(client: TestClient) -> None:
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_stage4_service_run_returns_state(client: TestClient) -> None:
    fake_state = {
        "query": "hi",
        "session": {},
        "reservation_input": None,
        "reservation_id": None,
        "admin_decision": None,
        "chatbot_response": "ok",
        "reservation_status": None,
        "recorded_to_mcp": False,
        "error": None,
    }
    with patch("app.stage4.service.run_stage4_pipeline", return_value=fake_state):
        r = client.post("/stage4/run", json={"query": "hi", "session": {}})
    assert r.status_code == 200
    assert r.json()["chatbot_response"] == "ok"
