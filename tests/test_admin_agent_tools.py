"""Unit tests for LangChain admin tools (no OpenAI calls)."""

import pytest

pytestmark = pytest.mark.stage2

from app.config import get_config
from app.db.init_db import initialize_database
from app.db.repositories import get_reservation_by_id, save_reservation
from app.stage2.admin_agent import build_admin_tools


def test_build_admin_tools_apply_decision_updates_db(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    db = tmp_path / "agent_tools.db"
    monkeypatch.setenv("DB_PATH", str(db))
    initialize_database(db)
    rid = save_reservation(
        db,
        "A",
        "B",
        "C1",
        "2099-05-01 10:00",
        "2099-05-01 11:00",
    )
    cfg = get_config()
    tools = build_admin_tools(cfg, callback_query_id="cq1", chat_id=None, message_id=None)
    by_name = {t.name: t for t in tools}
    raw = by_name["get_reservation_details"].invoke({"reservation_id": rid})
    assert "pending" in raw
    out = by_name["apply_admin_decision"].invoke({"reservation_id": rid, "decision": "confirmed"})
    assert "success" in out
    assert get_reservation_by_id(db, rid)["status"] == "confirmed"


def test_apply_admin_decision_invalid_decision_string(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    db = tmp_path / "agent_tools2.db"
    monkeypatch.setenv("DB_PATH", str(db))
    initialize_database(db)
    rid = save_reservation(
        db,
        "A",
        "B",
        "C2",
        "2099-05-02 10:00",
        "2099-05-02 11:00",
    )
    cfg = get_config()
    tools = build_admin_tools(cfg, callback_query_id="cq1", chat_id=None, message_id=None)
    by_name = {t.name: t for t in tools}
    out = by_name["apply_admin_decision"].invoke({"reservation_id": rid, "decision": "maybe"})
    assert "error" in out
