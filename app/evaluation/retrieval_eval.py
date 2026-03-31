from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from app.rag.retriever import retrieve


BASE_DIR = Path(__file__).resolve().parents[2]
DATASET_PATH = BASE_DIR / "data" / "eval" / "evaluation_dataset.json"
REPORT_PATH = BASE_DIR / "data" / "eval" / "retrieval_eval_report.json"


@dataclass
class EvalResult:
    case_id: int
    question: str
    expected_sources: list[str]
    retrieved_sources: list[str]
    matched_sources: list[str]
    recall_at_k: float
    precision_at_k: float
    hit: bool
    category: str


def load_dataset(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def normalize_source(source: str) -> str:
    return Path(source).name.strip().lower()


def safe_divide(numerator: float, denominator: float) -> float:
    return numerator / denominator if denominator else 0.0


def evaluate_case(case: dict[str, Any], top_k: int) -> EvalResult:
    question = case["question"]
    expected_sources = [normalize_source(s) for s in case.get("expected_sources", [])]

    docs = retrieve(question, top_k=top_k)

    retrieved_sources = [
        normalize_source(doc["metadata"]["source"])
        for doc in docs
        if "metadata" in doc and "source" in doc["metadata"]
    ]

    matched_sources = list(set(expected_sources) & set(retrieved_sources))

    recall_at_k = safe_divide(len(matched_sources), len(expected_sources))
    precision_at_k = safe_divide(len(matched_sources), top_k)
    hit = len(matched_sources) > 0

    return EvalResult(
        case_id=case["id"],
        question=question,
        expected_sources=expected_sources,
        retrieved_sources=retrieved_sources,
        matched_sources=matched_sources,
        recall_at_k=round(recall_at_k, 4),
        precision_at_k=round(precision_at_k, 4),
        hit=hit,
        category=case.get("category", "unknown"),
    )


def main() -> None:
    print("Running retrieval evaluation...")

    dataset = load_dataset(DATASET_PATH)

    cases = [c for c in dataset if c.get("expected_sources")]
    top_k = 3

    results = [evaluate_case(c, top_k) for c in cases]

    avg_recall = safe_divide(sum(r.recall_at_k for r in results), len(results))
    avg_precision = safe_divide(sum(r.precision_at_k for r in results), len(results))
    hit_rate = safe_divide(sum(1 for r in results if r.hit), len(results))

    summary = {
        "total_cases": len(dataset),
        "evaluated_cases": len(results),
        "top_k": top_k,
        "avg_recall_at_k": round(avg_recall, 4),
        "avg_precision_at_k": round(avg_precision, 4),
        "hit_rate": round(hit_rate, 4),
    }

    payload = {
        "summary": summary,
        "results": [asdict(r) for r in results],
    }

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with REPORT_PATH.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)

    print("\n=== Evaluation Summary ===")
    for k, v in summary.items():
        print(f"{k}: {v}")

    print(f"\nReport saved to: {REPORT_PATH}")


if __name__ == "__main__":
    main()