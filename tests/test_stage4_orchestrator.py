from __future__ import annotations

from unittest.mock import patch

import pytest

from app.db.init_db import initialize_database
from app.db.repositories import get_reservation_by_id
from app.stage4.orchestrator import run_stage4_pipeline

pytestmark = pytest.mark.stage4


def _reservation_input() -> dict[str, str]:
    return {
        "first_name": "Kate",
        "last_name": "Kate",
        "car_plate": "AS12345",
        "start_datetime": "2099-04-06 01:00",
        "end_datetime": "2099-04-06 12:00",
    }


def test_stage4_pipeline_confirmed_triggers_recording(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    db_path = tmp_path / "s4.db"
    monkeypatch.setenv("DB_PATH", str(db_path))
    initialize_database(db_path)

    with patch("app.stage4.orchestrator.send_confirmed_reservation_to_mcp", return_value=True) as send:
        out = run_stage4_pipeline(reservation_input=_reservation_input(), admin_decision="confirmed")
    assert out["reservation_status"] == "confirmed"
    assert out["recorded_to_mcp"] is True
    assert send.call_count == 1


def test_stage4_pipeline_rejected_does_not_record(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    db_path = tmp_path / "s4_reject.db"
    monkeypatch.setenv("DB_PATH", str(db_path))
    initialize_database(db_path)

    with patch("app.stage4.orchestrator.send_confirmed_reservation_to_mcp", return_value=True) as send:
        out = run_stage4_pipeline(reservation_input=_reservation_input(), admin_decision="rejected")
    assert out["reservation_status"] == "rejected"
    assert out["recorded_to_mcp"] is False
    assert send.call_count == 0


def test_stage4_pipeline_query_only_routes_chat() -> None:
    session = {"reservation_active": False, "step": None, "data": {}}
    out = run_stage4_pipeline(query="What are your working hours?", session=session)
    assert isinstance(out["chatbot_response"], str)
    assert out["reservation_id"] is None


def test_stage4_pipeline_persists_pending_then_updates(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    db_path = tmp_path / "s4_state.db"
    monkeypatch.setenv("DB_PATH", str(db_path))
    initialize_database(db_path)

    with patch("app.stage4.orchestrator.send_confirmed_reservation_to_mcp", return_value=True):
        out = run_stage4_pipeline(reservation_input=_reservation_input(), admin_decision="confirmed")
    rid = out["reservation_id"]
    assert isinstance(rid, int)
    row = get_reservation_by_id(db_path, rid)
    assert row is not None
    assert row["status"] == "confirmed"
