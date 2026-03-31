from __future__ import annotations

import json
import time
from pathlib import Path
from statistics import mean
from typing import Any

from app.chatbot.router import handle_info


BASE_DIR = Path(__file__).resolve().parents[2]
DATASET_PATH = BASE_DIR / "data" / "eval" / "evaluation_dataset.json"
REPORT_PATH = BASE_DIR / "data" / "eval" / "latency_eval_report.json"


def _percentile(sorted_values: list[float], percentile: float) -> float:
    if not sorted_values:
        return 0.0
    if len(sorted_values) == 1:
        return sorted_values[0]

    index = int((len(sorted_values) - 1) * percentile)
    return sorted_values[index]


def load_dataset(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def main() -> None:
    dataset = load_dataset(DATASET_PATH)
    questions = [item["question"] for item in dataset if item.get("expected_sources")]

    latencies_ms: list[float] = []
    failed_questions: list[dict[str, str]] = []

    for question in questions:
        started = time.perf_counter()
        try:
            _ = handle_info(question)
            elapsed_ms = (time.perf_counter() - started) * 1000
            latencies_ms.append(round(elapsed_ms, 2))
        except Exception as exc:  # noqa: BLE001
            failed_questions.append(
                {
                    "question": question,
                    "error": str(exc),
                }
            )

    sorted_latencies = sorted(latencies_ms)
    summary = {
        "total_questions": len(questions),
        "successful_requests": len(latencies_ms),
        "failed_requests": len(failed_questions),
        "avg_latency_ms": round(mean(latencies_ms), 2) if latencies_ms else 0.0,
        "p50_latency_ms": round(_percentile(sorted_latencies, 0.50), 2),
        "p95_latency_ms": round(_percentile(sorted_latencies, 0.95), 2),
        "max_latency_ms": round(sorted_latencies[-1], 2) if sorted_latencies else 0.0,
    }

    payload = {
        "summary": summary,
        "latencies_ms": latencies_ms,
        "failed_questions": failed_questions,
    }

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with REPORT_PATH.open("w", encoding="utf-8") as file:
        json.dump(payload, file, indent=2, ensure_ascii=False)

    print("=== Latency Evaluation Summary ===")
    for key, value in summary.items():
        print(f"{key}: {value}")
    print(f"\nReport saved to: {REPORT_PATH}")


if __name__ == "__main__":
    main()
