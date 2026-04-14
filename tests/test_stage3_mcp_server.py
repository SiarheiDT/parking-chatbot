from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.stage3.mcp_server import app

pytestmark = pytest.mark.stage3


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def test_mcp_server_rejects_unauthorized(client: TestClient, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    out = tmp_path / "confirmed.txt"
    monkeypatch.setenv("STAGE3_MCP_API_KEY", "secret")
    monkeypatch.setenv("STAGE3_MCP_OUTPUT_FILE", str(out))
    body = {
        "name": "John Smith",
        "car_number": "DW12345",
        "reservation_period": "2026-04-06 10:00 -> 2026-04-06 12:00",
        "approval_time": "2026-04-06T10:01:00+00:00",
    }
    r = client.post("/mcp/v1/confirmed-reservations", json=body, headers={"X-API-Key": "wrong"})
    assert r.status_code == 401
    assert not out.exists()


def test_mcp_server_writes_expected_line(client: TestClient, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    out = tmp_path / "confirmed.txt"
    monkeypatch.setenv("STAGE3_MCP_API_KEY", "secret")
    monkeypatch.setenv("STAGE3_MCP_OUTPUT_FILE", str(out))
    body = {
        "name": "Kate Kate",
        "car_number": "AS12345",
        "reservation_period": "2026-04-06 01:00 -> 2026-04-06 12:00",
        "approval_time": "2026-04-06T11:30:00+00:00",
    }
    r = client.post("/mcp/v1/confirmed-reservations", json=body, headers={"X-API-Key": "secret"})
    assert r.status_code == 200
    lines = out.read_text(encoding="utf-8").splitlines()
    assert lines == ["Kate Kate | AS12345 | 2026-04-06 01:00 -> 2026-04-06 12:00 | 2026-04-06T11:30:00+00:00"]
