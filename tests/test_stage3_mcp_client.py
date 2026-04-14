from __future__ import annotations

from unittest.mock import Mock, patch

import httpx
import pytest

from app.config import get_config
from app.stage3.mcp_client import send_confirmed_reservation_to_mcp

pytestmark = pytest.mark.stage3


def _reservation() -> dict[str, object]:
    return {
        "id": 11,
        "first_name": "Kate",
        "last_name": "Kate",
        "car_plate": "AS12345",
        "start_datetime": "2026-04-06 01:00",
        "end_datetime": "2026-04-06 12:00",
        "status": "confirmed",
    }


def test_mcp_client_posts_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("STAGE3_MCP_ENABLED", "true")
    monkeypatch.setenv("STAGE3_MCP_API_KEY", "k1")
    monkeypatch.setenv("STAGE3_MCP_ENDPOINT", "http://localhost:9191/mcp/v1/confirmed-reservations")
    cfg = get_config()

    ok_response = Mock()
    ok_response.status_code = 200
    with patch("app.stage3.mcp_client.httpx.post", return_value=ok_response) as post:
        ok = send_confirmed_reservation_to_mcp(_reservation(), config=cfg)
    assert ok is True
    assert post.call_count == 1
    kwargs = post.call_args.kwargs
    assert kwargs["headers"]["X-API-Key"] == "k1"
    assert kwargs["json"]["name"] == "Kate Kate"
    assert kwargs["json"]["car_number"] == "AS12345"


def test_mcp_client_retries_then_succeeds(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("STAGE3_MCP_ENABLED", "true")
    monkeypatch.setenv("STAGE3_MCP_API_KEY", "k1")
    monkeypatch.setenv("STAGE3_MCP_ENDPOINT", "http://localhost:9191/mcp/v1/confirmed-reservations")
    cfg = get_config()

    ok_response = Mock()
    ok_response.status_code = 200
    with (
        patch("app.stage3.mcp_client.time.sleep", return_value=None),
        patch(
            "app.stage3.mcp_client.httpx.post",
            side_effect=[httpx.ConnectError("fail"), ok_response],
        ) as post,
    ):
        ok = send_confirmed_reservation_to_mcp(_reservation(), config=cfg, max_attempts=3)

    assert ok is True
    assert post.call_count == 2
