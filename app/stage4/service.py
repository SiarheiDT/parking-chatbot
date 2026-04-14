from __future__ import annotations

from typing import Any, Literal

from fastapi import FastAPI
from pydantic import BaseModel

from app.stage4.orchestrator import run_stage4_pipeline

app = FastAPI(title="Parking Chatbot — Stage 4 Orchestration", version="0.1.0")


class Stage4RunRequest(BaseModel):
    query: str = ""
    session: dict[str, Any] = {}
    reservation_input: dict[str, str] | None = None
    admin_decision: Literal["confirmed", "rejected"] | None = None


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/stage4/run")
def run_pipeline(body: Stage4RunRequest) -> dict[str, Any]:
    state = run_stage4_pipeline(
        reservation_input=body.reservation_input,
        admin_decision=body.admin_decision,
        query=body.query,
        session=body.session,
    )
    return state
