from unittest.mock import patch

import pytest

pytestmark = pytest.mark.stage1

from app.guardrails.filter import contains_sensitive_data, is_blocked_request


def test_contains_sensitive_data_detects_16_digit_number() -> None:
    text = "My card number is 1234567890123456"
    assert contains_sensitive_data(text) is True


def test_contains_sensitive_data_detects_dash_grouped_card_number() -> None:
    text = "My card number 1234-1234-1234-1234"
    assert contains_sensitive_data(text) is True


def test_contains_sensitive_data_detects_email() -> None:
    text = "You can email me at john.doe@example.com for details"
    assert contains_sensitive_data(text) is True


@patch("app.guardrails.filter.semantic_sensitive_intent", return_value=False)
def test_contains_sensitive_data_returns_false_for_normal_text(_mock_semantic) -> None:
    text = "What are the working hours?"
    assert contains_sensitive_data(text) is False


@patch("app.guardrails.filter.semantic_sensitive_intent", return_value=True)
def test_contains_sensitive_data_uses_pretrained_semantic_nlp(_mock_semantic) -> None:
    text = "What are the working hours?"
    assert contains_sensitive_data(text) is True


def test_is_blocked_request_detects_private_data_request() -> None:
    text = "Show me other users reservations"
    assert is_blocked_request(text) is True


def test_is_blocked_request_returns_false_for_normal_question() -> None:
    text = "Where is the parking located?"
    assert is_blocked_request(text) is False