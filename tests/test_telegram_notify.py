from unittest.mock import MagicMock, patch

import pytest

pytestmark = pytest.mark.stage2

from app.config import get_config
from app.notifications.telegram import (
    notify_admin_new_reservation,
    parse_reservation_callback_data,
    send_telegram_message,
    telegram_is_configured,
)


def test_telegram_not_configured_when_env_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("TELEGRAM_ADMIN_CHAT_ID", raising=False)
    cfg = get_config()
    assert telegram_is_configured(cfg) is False
    assert send_telegram_message("hello", config=cfg) is False


def test_telegram_configured_when_token_and_chat_set(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123:ABC")
    monkeypatch.setenv("TELEGRAM_ADMIN_CHAT_ID", "987654")
    cfg = get_config()
    assert telegram_is_configured(cfg) is True


@patch("urllib.request.urlopen")
def test_send_telegram_message_posts_json_and_returns_true(mock_urlopen, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123:FAKE")
    monkeypatch.setenv("TELEGRAM_ADMIN_CHAT_ID", "111")
    mock_resp = MagicMock()
    mock_resp.read.return_value = b'{"ok":true,"result":{"message_id":1}}'
    mock_urlopen.return_value.__enter__.return_value = mock_resp
    mock_urlopen.return_value.__exit__.return_value = None

    cfg = get_config()
    assert send_telegram_message("New pending reservation #42", config=cfg) is True

    mock_urlopen.assert_called_once()
    req = mock_urlopen.call_args[0][0]
    url = getattr(req, "full_url", None) or req.get_full_url()
    assert url.endswith("/bot123:FAKE/sendMessage")


@patch("urllib.request.urlopen")
def test_send_telegram_message_returns_false_on_api_error(mock_urlopen, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "x")
    monkeypatch.setenv("TELEGRAM_ADMIN_CHAT_ID", "1")
    mock_resp = MagicMock()
    mock_resp.read.return_value = b'{"ok":false,"description":"Bad Request"}'
    mock_urlopen.return_value.__enter__.return_value = mock_resp
    mock_urlopen.return_value.__exit__.return_value = None

    assert send_telegram_message("hi", config=get_config()) is False


def test_parse_reservation_callback_data() -> None:
    assert parse_reservation_callback_data("rv:7:c") == (7, "confirmed")
    assert parse_reservation_callback_data("rv:99:r") == (99, "rejected")
    assert parse_reservation_callback_data("bad") is None


@patch("app.notifications.telegram._telegram_post")
def test_notify_admin_new_reservation_sends_keyboard(mock_post, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "t")
    monkeypatch.setenv("TELEGRAM_ADMIN_CHAT_ID", "1")
    mock_post.return_value = True
    cfg = get_config()
    assert notify_admin_new_reservation(5, "A", "B", "XY", "s", "e", config=cfg) is True
    mock_post.assert_called_once()
    _cfg_arg, method, body = mock_post.call_args[0]
    assert method == "sendMessage"
    assert body["reply_markup"]["inline_keyboard"][0][0]["callback_data"] == "rv:5:c"
    assert body["reply_markup"]["inline_keyboard"][0][1]["callback_data"] == "rv:5:r"
