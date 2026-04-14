"""
Stage 3 MCP-like server for confirmed reservation persistence.

Run:
    uvicorn app.stage3.mcp_server:app --host 0.0.0.0 --port 9191
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import threading

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

from app.config import get_config

app = FastAPI(title="Parking Chatbot — Stage 3 MCP Server", version="0.1.0")
_WRITE_LOCK = threading.Lock()


class ConfirmedReservationPayload(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    car_number: str = Field(min_length=1, max_length=64)
    reservation_period: str = Field(min_length=1, max_length=128)
    approval_time: str = Field(min_length=1, max_length=64)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _format_line(payload: ConfirmedReservationPayload) -> str:
    return f"{payload.name} | {payload.car_number} | {payload.reservation_period} | {payload.approval_time}"


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/mcp/v1/confirmed-reservations")
def write_confirmed_reservation(
    payload: ConfirmedReservationPayload,
    x_api_key: str = Header(default="", alias="X-API-Key"),
) -> dict[str, str]:
    cfg = get_config()
    expected = (cfg.STAGE3_MCP_API_KEY or "").strip()
    if not expected:
        raise HTTPException(status_code=503, detail="MCP API key is not configured")
    if x_api_key.strip() != expected:
        raise HTTPException(status_code=401, detail="Unauthorized")

    safe_payload = payload
    if not safe_payload.approval_time.strip():
        safe_payload = ConfirmedReservationPayload(
            name=payload.name,
            car_number=payload.car_number,
            reservation_period=payload.reservation_period,
            approval_time=_utc_now_iso(),
        )

    line = _format_line(safe_payload)
    target = cfg.STAGE3_MCP_OUTPUT_FILE
    target.parent.mkdir(parents=True, exist_ok=True)
    with _WRITE_LOCK:
        with target.open("a", encoding="utf-8") as f:
            f.write(line + "\n")
    return {"status": "stored"}
