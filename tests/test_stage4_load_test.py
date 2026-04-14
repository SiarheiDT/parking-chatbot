from __future__ import annotations

from unittest.mock import patch

import pytest

from app.stage4.load_test import run_stage4_load_test

pytestmark = pytest.mark.stage4


def test_stage4_load_test_chat_only_summary_shape() -> None:
    with patch(
        "app.stage4.load_test.run_stage4_pipeline",
        return_value={
            "chatbot_response": "ok",
            "reservation_status": None,
            "recorded_to_mcp": False,
        },
    ):
        summary = run_stage4_load_test(total_requests=5, workers=2, mode="chat_only")
    assert summary["total"] == 5
    assert summary["successes"] == 5
    assert summary["failures"] == 0
    assert summary["p95_ms"] >= 0


def test_stage4_load_test_confirm_flow_successes() -> None:
    with patch(
        "app.stage4.load_test.run_stage4_pipeline",
        return_value={
            "chatbot_response": "",
            "reservation_status": "confirmed",
            "recorded_to_mcp": True,
        },
    ):
        summary = run_stage4_load_test(total_requests=6, workers=3, mode="confirm_flow")
    assert summary["total"] == 6
    assert summary["successes"] == 6
    assert summary["failures"] == 0
