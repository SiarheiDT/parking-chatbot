from unittest.mock import patch

import pytest

pytestmark = pytest.mark.stage2
from fastapi.testclient import TestClient

from app.db.init_db import initialize_database
from app.db.repositories import get_reservation_by_id, save_reservation
from app.stage2.webhook_app import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def test_webhook_wrong_secret_returns_404(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TELEGRAM_WEBHOOK_SECRET", "real")
    r = client.post("/telegram/webhook/fake", json={})
    assert r.status_code == 404


def test_webhook_empty_secret_returns_404(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("TELEGRAM_WEBHOOK_SECRET", raising=False)
    r = client.post("/telegram/webhook/anything", json={})
    assert r.status_code == 404


def test_webhook_confirm_updates_reservation(
    client: TestClient, tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    db_path = tmp_path / "wh.db"
    monkeypatch.setenv("DB_PATH", str(db_path))
    monkeypatch.setenv("TELEGRAM_WEBHOOK_SECRET", "sec")
    initialize_database(db_path)
    rid = save_reservation(
        db_path,
        "X",
        "Y",
        "Z1",
        "2099-03-01 08:00",
        "2099-03-01 09:00",
    )

    body = {
        "callback_query": {
            "id": "999",
            "data": f"rv:{rid}:c",
            "message": {"chat": {"id": 111}, "message_id": 222},
        }
    }
    with (
        patch("app.stage2.webhook_app.answer_callback_query", return_value=True),
        patch("app.stage2.webhook_app.clear_inline_keyboard", return_value=True),
    ):
        r = client.post("/telegram/webhook/sec", json=body)
    assert r.status_code == 200
    assert get_reservation_by_id(db_path, rid)["status"] == "confirmed"


def test_health(client: TestClient) -> None:
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_webhook_confirm_langchain_mode_delegates_to_agent(
    client: TestClient, tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    db_path = tmp_path / "wh_lc.db"
    monkeypatch.setenv("DB_PATH", str(db_path))
    monkeypatch.setenv("TELEGRAM_WEBHOOK_SECRET", "sec")
    monkeypatch.setenv("STAGE2_ADMIN_HANDLER", "langchain_tools")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-not-used")
    initialize_database(db_path)
    rid = save_reservation(
        db_path,
        "X",
        "Y",
        "Z2",
        "2099-04-01 08:00",
        "2099-04-01 09:00",
    )

    body = {
        "callback_query": {
            "id": "999",
            "data": f"rv:{rid}:c",
            "message": {"chat": {"id": 111}, "message_id": 222},
        }
    }

    def _fake_agent(cfg, *, reservation_id, decision, callback_query_id, chat_id, message_id):
        from app.db.repositories import update_reservation_status
        from app.notifications.telegram import answer_callback_query

        update_reservation_status(cfg.DB_PATH, reservation_id, decision)
        answer_callback_query(callback_query_id, f"stub {decision}", config=cfg)

    with (
        patch("app.stage2.admin_agent.run_admin_decision_agent", side_effect=_fake_agent),
        patch("app.stage2.webhook_app.clear_inline_keyboard", return_value=True),
    ):
        r = client.post("/telegram/webhook/sec", json=body)
    assert r.status_code == 200
    assert get_reservation_by_id(db_path, rid)["status"] == "confirmed"


def test_webhook_confirm_langchain_without_openai_key_falls_back_direct(
    client: TestClient, tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    db_path = tmp_path / "wh_fallback.db"
    monkeypatch.setenv("DB_PATH", str(db_path))
    monkeypatch.setenv("TELEGRAM_WEBHOOK_SECRET", "sec")
    monkeypatch.setenv("STAGE2_ADMIN_HANDLER", "langchain_tools")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    initialize_database(db_path)
    rid = save_reservation(
        db_path,
        "X",
        "Y",
        "Z3",
        "2099-04-02 08:00",
        "2099-04-02 09:00",
    )
    body = {
        "callback_query": {
            "id": "999",
            "data": f"rv:{rid}:c",
            "message": {"chat": {"id": 111}, "message_id": 222},
        }
    }
    with (
        patch("app.stage2.webhook_app.answer_callback_query", return_value=True),
        patch("app.stage2.webhook_app.clear_inline_keyboard", return_value=True),
    ):
        r = client.post("/telegram/webhook/sec", json=body)
    assert r.status_code == 200
    assert get_reservation_by_id(db_path, rid)["status"] == "confirmed"
