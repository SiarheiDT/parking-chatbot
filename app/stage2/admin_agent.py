"""
LangChain tool-calling agent for Stage 2 admin decisions (second agent in the system).

Triggered from the Telegram webhook when STAGE2_ADMIN_HANDLER=langchain_tools.
Uses the same DB and Telegram helpers as the direct path; the agent must call tools
to persist status and finalize the Telegram callback UI.
"""
from __future__ import annotations

import json
import logging
import os
from typing import TYPE_CHECKING, Any, Literal

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import StructuredTool
from langchain_openai import ChatOpenAI

from app.db.repositories import get_reservation_by_id, update_reservation_status
from app.notifications.telegram import answer_callback_query, clear_inline_keyboard

if TYPE_CHECKING:
    from app.config import Config

logger = logging.getLogger(__name__)

Decision = Literal["confirmed", "rejected"]


def build_admin_tools(
    cfg: Config,
    *,
    callback_query_id: str,
    chat_id: str | None,
    message_id: int | None,
) -> list[StructuredTool]:
    def get_reservation_details(reservation_id: int) -> str:
        """Load reservation row from SQLite by id. Use before applying a decision."""
        row = get_reservation_by_id(cfg.DB_PATH, reservation_id)
        if row is None:
            return json.dumps({"error": "not_found", "reservation_id": reservation_id})
        return json.dumps(
            {
                "id": row["id"],
                "first_name": row["first_name"],
                "last_name": row["last_name"],
                "car_plate": row["car_plate"],
                "start_datetime": row["start_datetime"],
                "end_datetime": row["end_datetime"],
                "status": row["status"],
            },
            ensure_ascii=False,
        )

    def apply_admin_decision(reservation_id: int, decision: str) -> str:
        """
        Set reservation status from pending to confirmed or rejected.
        decision must be exactly 'confirmed' or 'rejected'.
        """
        d = (decision or "").strip().lower()
        if d not in ("confirmed", "rejected"):
            return "error: decision must be 'confirmed' or 'rejected'"
        ok = update_reservation_status(cfg.DB_PATH, reservation_id, d)
        if ok:
            return f"success: reservation {reservation_id} is now {d}"
        return f"no_op: reservation {reservation_id} was not pending or does not exist"

    def finalize_telegram_callback(user_facing_message: str) -> str:
        """
        Answer the Telegram callback query and remove inline buttons from the admin message.
        Call once after apply_admin_decision. Keep user_facing_message short (Telegram limit).
        """
        text = (user_facing_message or "").strip() or "Done."
        answer_callback_query(callback_query_id, text[:200], config=cfg)
        if chat_id is not None and message_id is not None:
            clear_inline_keyboard(str(chat_id), int(message_id), config=cfg)
        return "success: telegram callback finalized"

    return [
        StructuredTool.from_function(
            get_reservation_details,
            name="get_reservation_details",
            description="Fetch reservation by id from the database (JSON). Call first to verify pending state.",
        ),
        StructuredTool.from_function(
            apply_admin_decision,
            name="apply_admin_decision",
            description="Transition pending reservation to confirmed or rejected in SQLite.",
        ),
        StructuredTool.from_function(
            finalize_telegram_callback,
            name="finalize_telegram_callback",
            description="Notify Telegram: answer callback and clear Confirm/Reject keyboard.",
        ),
    ]


_SYSTEM = (
    "You are the parking admin backend agent. "
    "You receive structured events from Telegram when an admin taps Confirm or Reject.\n"
    "You MUST use tools — do not invent reservation ids.\n"
    "Workflow:\n"
    "1) get_reservation_details(reservation_id) to confirm the row exists and is pending.\n"
    "2) apply_admin_decision(reservation_id, decision) with the exact decision from the event.\n"
    "3) finalize_telegram_callback(user_facing_message) with a short confirmation, "
    "e.g. 'Reservation 7 confirmed.' or 'Reservation 7 rejected.'\n"
    "If step 2 returns no_op, still finalize Telegram with an honest message (e.g. not pending)."
)


def _tool_call_parts(call: Any) -> tuple[str, dict[str, Any], str]:
    if isinstance(call, dict):
        name = str(call.get("name", ""))
        args = call.get("args") if isinstance(call.get("args"), dict) else {}
        tid = str(call.get("id", "") or "call")
        return name, args, tid
    name = str(getattr(call, "name", "") or "")
    args = getattr(call, "args", None)
    if not isinstance(args, dict):
        args = {}
    tid = str(getattr(call, "id", "") or "call")
    return name, args, tid


def _run_tool_loop(llm: ChatOpenAI, tools: list[StructuredTool], user_text: str, *, max_steps: int = 12) -> None:
    by_name = {t.name: t for t in tools}
    messages: list[Any] = [
        SystemMessage(content=_SYSTEM),
        HumanMessage(content=user_text),
    ]
    bound = llm.bind_tools(tools)
    for _ in range(max_steps):
        ai = bound.invoke(messages)
        messages.append(ai)
        if not isinstance(ai, AIMessage):
            break
        calls = ai.tool_calls or []
        if not calls:
            break
        for call in calls:
            name, args, tid = _tool_call_parts(call)
            tool_fn = by_name.get(name)
            if tool_fn is None:
                out = f"error: unknown tool {name}"
            else:
                try:
                    out = tool_fn.invoke(args)
                except Exception as exc:  # noqa: BLE001
                    out = f"error: {exc}"
            messages.append(ToolMessage(content=str(out), tool_call_id=tid))


def run_admin_decision_agent(
    cfg: Config,
    *,
    reservation_id: int,
    decision: Decision,
    callback_query_id: str,
    chat_id: Any,
    message_id: Any,
) -> None:
    """
    Run OpenAI tool-calling agent to execute DB update + Telegram finalization.
    Raises on unexpected failures (webhook caller may fall back to direct path).
    """
    api_key = (os.getenv("OPENAI_API_KEY") or "").strip()
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set")

    model = (cfg.ADMIN_AGENT_MODEL or cfg.MODEL_NAME or "gpt-4o-mini").strip()
    llm = ChatOpenAI(model=model, temperature=0, api_key=api_key)

    tools = build_admin_tools(
        cfg,
        callback_query_id=callback_query_id,
        chat_id=str(chat_id) if chat_id is not None else None,
        message_id=int(message_id) if message_id is not None else None,
    )

    payload = (
        f"Telegram callback event:\n"
        f"- reservation_id: {reservation_id}\n"
        f"- decision: {decision}\n"
        f"Execute the workflow with these exact values."
    )
    verbose = os.getenv("ADMIN_AGENT_VERBOSE", "").lower() in ("1", "true", "yes")
    logger.info("Stage2 admin LangChain agent running for reservation_id=%s decision=%s", reservation_id, decision)
    if verbose:
        logger.debug("Admin agent payload:\n%s", payload)
    _run_tool_loop(llm, tools, payload, max_steps=12)
