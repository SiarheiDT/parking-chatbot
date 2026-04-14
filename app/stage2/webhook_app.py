"""
FastAPI app for Telegram Bot webhook: Confirm / Reject reservation callbacks.

Run (from repo root, with .env loaded):

    uvicorn app.stage2.webhook_app:app --host 0.0.0.0 --port 9090

Register webhook (HTTPS URL required by Telegram; use ngrok for local dev):

    https://api.telegram.org/bot<TOKEN>/setWebhook?url=https://<host>/telegram/webhook/<TELEGRAM_WEBHOOK_SECRET>

Env: STAGE2_ADMIN_HANDLER=direct (default) or langchain_tools (+ OPENAI_API_KEY). See README Stage 2.
"""

from __future__ import annotations

import logging
import os

from fastapi import FastAPI, HTTPException, Request

from app.config import Config, get_config
from app.db.repositories import get_reservation_by_id, update_reservation_status
from app.notifications.telegram import (
    answer_callback_query,
    clear_inline_keyboard,
    parse_reservation_callback_data,
)
from app.stage2 import admin_agent
from app.stage3.mcp_client import send_confirmed_reservation_to_mcp

logger = logging.getLogger(__name__)

app = FastAPI(title="Parking Chatbot — Admin Telegram Webhook", version="0.1.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/telegram/webhook/{secret}")
async def telegram_webhook(secret: str, request: Request) -> dict[str, bool]:
    cfg = get_config()
    expected = (cfg.TELEGRAM_WEBHOOK_SECRET or "").strip()
    if not expected or secret != expected:
        raise HTTPException(status_code=404, detail="Not found")

    try:
        data = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON") from None

    cb = data.get("callback_query")
    if not cb:
        return {"ok": True}

    cq_id = str(cb.get("id", ""))
    msg = cb.get("message") or {}
    chat = msg.get("chat") or {}
    chat_id = chat.get("id")
    message_id = msg.get("message_id")
    raw_data = cb.get("data") or ""

    parsed = parse_reservation_callback_data(raw_data)
    if not parsed or not cq_id:
        answer_callback_query(cq_id, "Invalid action.", config=cfg)
        return {"ok": True}

    rid, new_status = parsed
    before = get_reservation_by_id(cfg.DB_PATH, rid)
    stage3_sent = False
    use_agent = cfg.STAGE2_ADMIN_HANDLER == "langchain_tools" and bool(
        (os.getenv("OPENAI_API_KEY") or "").strip()
    )
    if use_agent:
        try:
            admin_agent.run_admin_decision_agent(
                cfg,
                reservation_id=rid,
                decision=new_status,
                callback_query_id=cq_id,
                chat_id=chat_id,
                message_id=message_id,
            )
        except Exception:
            logger.exception(
                "Stage2 admin LangChain agent failed; falling back to direct handler (reservation_id=%s)",
                rid,
            )
            updated = _finalize_reservation_callback_direct(cfg, rid, new_status, cq_id, chat_id, message_id)
            _maybe_send_confirmed_to_stage3(cfg, rid, updated, new_status)
            stage3_sent = updated and new_status == "confirmed"
    else:
        if cfg.STAGE2_ADMIN_HANDLER == "langchain_tools" and not (os.getenv("OPENAI_API_KEY") or "").strip():
            logger.warning(
                "STAGE2_ADMIN_HANDLER=langchain_tools but OPENAI_API_KEY is empty; using direct handler."
            )
        updated = _finalize_reservation_callback_direct(cfg, rid, new_status, cq_id, chat_id, message_id)
        _maybe_send_confirmed_to_stage3(cfg, rid, updated, new_status)

    if use_agent:
        after = get_reservation_by_id(cfg.DB_PATH, rid)
        if (not stage3_sent) and before and after and before["status"] == "pending" and after["status"] == "confirmed":
            send_confirmed_reservation_to_mcp(after, config=cfg)

    return {"ok": True}


def _finalize_reservation_callback_direct(
    cfg: Config,
    rid: int,
    new_status: str,
    cq_id: str,
    chat_id: object,
    message_id: object,
) -> bool:
    updated = update_reservation_status(cfg.DB_PATH, rid, new_status)
    if updated:
        label = "confirmed" if new_status == "confirmed" else "rejected"
        answer_callback_query(cq_id, f"Reservation {rid} {label}.", config=cfg)
        if chat_id is not None and message_id is not None:
            clear_inline_keyboard(str(chat_id), int(message_id), config=cfg)
    else:
        answer_callback_query(cq_id, "Not pending or unknown id.", config=cfg)
    return updated


def _maybe_send_confirmed_to_stage3(cfg: Config, rid: int, updated: bool, new_status: str) -> None:
    if not updated or new_status != "confirmed":
        return
    row = get_reservation_by_id(cfg.DB_PATH, rid)
    if row is None or row["status"] != "confirmed":
        return
    send_confirmed_reservation_to_mcp(row, config=cfg)
