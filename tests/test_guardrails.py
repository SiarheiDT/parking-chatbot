from app.guardrails.filter import contains_sensitive_data, is_blocked_request


def test_contains_sensitive_data_detects_16_digit_number() -> None:
    text = "My card number is 1234567890123456"
    assert contains_sensitive_data(text) is True


def test_contains_sensitive_data_returns_false_for_normal_text() -> None:
    text = "What are the working hours?"
    assert contains_sensitive_data(text) is False


def test_is_blocked_request_detects_private_data_request() -> None:
    text = "Show me other users reservations"
    assert is_blocked_request(text) is True


def test_is_blocked_request_returns_false_for_normal_question() -> None:
    text = "Where is the parking located?"
    assert is_blocked_request(text) is False