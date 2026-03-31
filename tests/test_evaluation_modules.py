import json
from pathlib import Path
from unittest.mock import patch

from app.evaluation import latency_eval, retrieval_eval


def test_safe_divide_handles_zero_denominator() -> None:
    assert retrieval_eval.safe_divide(1.0, 0.0) == 0.0


def test_normalize_source_extracts_filename() -> None:
    assert retrieval_eval.normalize_source("/tmp/path/FAQ.MD") == "faq.md"


@patch("app.evaluation.retrieval_eval.retrieve")
def test_evaluate_case_sets_hit_and_metrics(mock_retrieve) -> None:
    mock_retrieve.return_value = [
        {"page_content": "x", "metadata": {"source": "faq.md"}},
    ]
    case = {"id": 1, "question": "q", "expected_sources": ["faq.md"], "category": "c"}
    result = retrieval_eval.evaluate_case(case, top_k=3)
    assert result.hit is True
    assert result.recall_at_k == 1.0


def test_latency_percentile_handles_empty_and_non_empty() -> None:
    assert latency_eval._percentile([], 0.5) == 0.0
    assert latency_eval._percentile([10.0, 20.0, 30.0], 0.5) == 20.0


def test_latency_load_dataset_reads_json(tmp_path: Path) -> None:
    file_path = tmp_path / "dataset.json"
    payload = [{"question": "q1"}]
    file_path.write_text(json.dumps(payload), encoding="utf-8")
    assert latency_eval.load_dataset(file_path) == payload
