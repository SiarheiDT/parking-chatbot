from __future__ import annotations

import json
import logging
import re
import urllib.error
import urllib.request
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.config import Config

from app.config import get_config

logger = logging.getLogger(__name__)

_TELEGRAM_MAX_MESSAGE_LEN = 4096

# callback_data max 64 bytes; format: rv:<id>:c|r
CALLBACK_RESERVATION_RE = re.compile(r"^rv:(\d+):([cr])$")


def telegram_is_configured(config: Config | None = None) -> bool:
    cfg = config or get_config()
    return bool(cfg.TELEGRAM_BOT_TOKEN.strip() and cfg.TELEGRAM_ADMIN_CHAT_ID.strip())


def _telegram_post(cfg: Config, method: str, body: dict[str, Any]) -> bool:
    token = cfg.TELEGRAM_BOT_TOKEN.strip()
    base = cfg.TELEGRAM_API_BASE.rstrip("/")
    url = f"{base}/bot{token}/{method}"
    payload = json.dumps(body).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            raw = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        logger.warning("Telegram HTTP error %s: %s", exc.code, exc.read().decode("utf-8", errors="replace"))
        return False
    except urllib.error.URLError as exc:
        logger.warning("Telegram network error: %s", exc)
        return False
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        logger.warning("Telegram invalid JSON response: %s", raw[:200])
        return False
    if not data.get("ok"):
        logger.warning("Telegram API error: %s", data)
        return False
    return True


def send_telegram_message(text: str, *, config: Config | None = None) -> bool:
    """
    POST sendMessage to Telegram Bot API. Returns True if HTTP 200 and response ok=true.
    No-op (returns False) when token or admin chat id are missing.
    """
    cfg = config or get_config()
    if not telegram_is_configured(cfg):
        logger.debug("Telegram escalation skipped: TELEGRAM_BOT_TOKEN or TELEGRAM_ADMIN_CHAT_ID not set.")
        return False

    body = text if len(text) <= _TELEGRAM_MAX_MESSAGE_LEN else text[: _TELEGRAM_MAX_MESSAGE_LEN - 20] + "\n…(truncated)"
    return _telegram_post(
        cfg,
        "sendMessage",
        {
            "chat_id": cfg.TELEGRAM_ADMIN_CHAT_ID.strip(),
            "text": body,
            "disable_web_page_preview": True,
        },
    )


def notify_admin_new_reservation(
    reservation_id: int,
    first_name: str,
    last_name: str,
    car_plate: str,
    start_datetime: str,
    end_datetime: str,
    *,
    config: Config | None = None,
) -> bool:
    """
    Send admin a reservation summary with Confirm / Reject inline buttons.
    """
    cfg = config or get_config()
    if not telegram_is_configured(cfg):
        return False

    text = (
        f"🔔 New reservation request\n\n"
        f"ID: {reservation_id}\n"
        f"Status: pending\n\n"
        f"Name: {first_name} {last_name}\n"
        f"Car plate: {car_plate}\n"
        f"From: {start_datetime}\n"
        f"To: {end_datetime}\n\n"
        "Please tap Confirm or Reject below."
    )
    rid = int(reservation_id)
    keyboard = {
        "inline_keyboard": [
            [
                {"text": "✅ Confirm", "callback_data": f"rv:{rid}:c"},
                {"text": "❌ Reject", "callback_data": f"rv:{rid}:r"},
            ]
        ]
    }
    return _telegram_post(
        cfg,
        "sendMessage",
        {
            "chat_id": cfg.TELEGRAM_ADMIN_CHAT_ID.strip(),
            "text": text,
            "disable_web_page_preview": True,
            "reply_markup": keyboard,
        },
    )


def parse_reservation_callback_data(data: str) -> tuple[int, str] | None:
    """
    Parse callback_data from inline buttons. Returns (reservation_id, 'confirmed'|'rejected') or None.
    """
    m = CALLBACK_RESERVATION_RE.match((data or "").strip())
    if not m:
        return None
    rid = int(m.group(1))
    action = m.group(2)
    if action == "c":
        return (rid, "confirmed")
    if action == "r":
        return (rid, "rejected")
    return None


def answer_callback_query(callback_query_id: str, text: str, *, config: Config | None = None) -> bool:
    cfg = config or get_config()
    if not telegram_is_configured(cfg):
        return False
    body: dict[str, Any] = {"callback_query_id": callback_query_id}
    if text:
        body["text"] = text[:200]
        body["show_alert"] = False
    return _telegram_post(cfg, "answerCallbackQuery", body)


def clear_inline_keyboard(chat_id: str, message_id: int, *, config: Config | None = None) -> bool:
    cfg = config or get_config()
    if not telegram_is_configured(cfg):
        return False
    return _telegram_post(
        cfg,
        "editMessageReplyMarkup",
        {
            "chat_id": chat_id,
            "message_id": message_id,
            "reply_markup": {"inline_keyboard": []},
        },
    )
