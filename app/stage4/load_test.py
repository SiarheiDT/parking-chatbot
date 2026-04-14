from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
import statistics
import time
from typing import Literal, TypedDict

from app.stage4.orchestrator import run_stage4_pipeline


class LoadTestSummary(TypedDict):
    total: int
    successes: int
    failures: int
    avg_ms: float
    p50_ms: float
    p95_ms: float
    max_ms: float


def _percentile(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    idx = int(round((p / 100) * (len(ordered) - 1)))
    return ordered[max(0, min(idx, len(ordered) - 1))]


def run_stage4_load_test(
    *,
    total_requests: int = 20,
    workers: int = 4,
    mode: Literal["chat_only", "confirm_flow"] = "chat_only",
) -> LoadTestSummary:
    total = max(1, total_requests)
    pool = max(1, workers)
    latencies: list[float] = []
    successes = 0
    failures = 0

    def one_call(i: int) -> bool:
        t0 = time.perf_counter()
        try:
            if mode == "chat_only":
                out = run_stage4_pipeline(
                    query="What are your working hours?",
                    session={"reservation_active": False, "step": None, "data": {}},
                )
                ok = isinstance(out.get("chatbot_response"), str)
            else:
                out = run_stage4_pipeline(
                    reservation_input={
                        "first_name": "Load",
                        "last_name": f"User{i}",
                        "car_plate": f"LD{i:04d}",
                        "start_datetime": "2099-06-01 08:00",
                        "end_datetime": "2099-06-01 09:00",
                    },
                    admin_decision="confirmed",
                )
                ok = out.get("reservation_status") == "confirmed"
            return bool(ok)
        finally:
            latencies.append((time.perf_counter() - t0) * 1000.0)

    with ThreadPoolExecutor(max_workers=pool) as ex:
        futures = [ex.submit(one_call, i) for i in range(total)]
        for f in as_completed(futures):
            if f.result():
                successes += 1
            else:
                failures += 1

    return LoadTestSummary(
        total=total,
        successes=successes,
        failures=failures,
        avg_ms=round(statistics.mean(latencies), 2) if latencies else 0.0,
        p50_ms=round(_percentile(latencies, 50), 2),
        p95_ms=round(_percentile(latencies, 95), 2),
        max_ms=round(max(latencies), 2) if latencies else 0.0,
    )
