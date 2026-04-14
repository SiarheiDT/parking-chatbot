"""Client for Stage 3 MCP-like service."""
from __future__ import annotations

from datetime import datetime, timezone
import time
import logging

import httpx

from app.config import Config
from app.db.repositories import ReservationRecord

logger = logging.getLogger(__name__)


def _approval_time_utc_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def send_confirmed_reservation_to_mcp(
    reservation: ReservationRecord,
    *,
    config: Config,
    max_attempts: int = 3,
) -> bool:
    if not config.STAGE3_MCP_ENABLED:
        return False

    api_key = config.STAGE3_MCP_API_KEY.strip()
    endpoint = config.STAGE3_MCP_ENDPOINT.rstrip("/")
    if not api_key or not endpoint:
        logger.warning("Stage3 MCP disabled at runtime: endpoint or API key is empty.")
        return False

    period = f"{reservation['start_datetime']} -> {reservation['end_datetime']}"
    payload = {
        "name": f"{reservation['first_name']} {reservation['last_name']}".strip(),
        "car_number": reservation["car_plate"],
        "reservation_period": period,
        "approval_time": _approval_time_utc_iso(),
    }
    headers = {"X-API-Key": api_key}
    timeout = max(1.0, float(config.STAGE3_MCP_TIMEOUT_SECONDS))

    delay = 0.2
    for attempt in range(1, max(1, max_attempts) + 1):
        try:
            response = httpx.post(endpoint, json=payload, headers=headers, timeout=timeout)
            if response.status_code < 500:
                return response.status_code == 200
        except httpx.HTTPError:
            if attempt >= max_attempts:
                break
        if attempt < max_attempts:
            time.sleep(delay)
            delay *= 2

    logger.warning(
        "Failed to persist confirmed reservation to Stage3 MCP endpoint (reservation_id=%s).",
        reservation["id"],
    )
    return False
