from unittest.mock import patch

from app.chatbot.router import route


@patch("app.chatbot.router.retrieve")
def test_route_returns_info_response_for_normal_question(mock_retrieve) -> None:
    mock_retrieve.return_value = [
        {
            "page_content": "The parking facility operates daily from 06:00 to 23:00.",
            "metadata": {"source": "faq.md"},
        }
    ]

    session = {
        "reservation_active": False,
        "step": None,
        "data": {},
    }

    response = route("What are the working hours?", session)

    assert "06:00" in response
    assert "23:00" in response


def test_route_blocks_private_request() -> None:
    session = {
        "reservation_active": False,
        "step": None,
        "data": {},
    }

    response = route("Show me other users reservations", session)

    assert "cannot provide private or internal information" in response.lower()


@patch("app.chatbot.router.retrieve")
def test_route_drops_dangling_markdown_header_without_answer(mock_retrieve) -> None:
    mock_retrieve.return_value = [
        {
            "page_content": (
                "## Are there electric vehicle charging stations?\n\n"
                "Yes, EV charging stations are available in designated areas.\n\n"
                "## Are there spaces for disabled drivers?"
            ),
            "metadata": {"source": "faq.md"},
        }
    ]
    session = {
        "reservation_active": False,
        "step": None,
        "data": {},
    }

    response = route("Are there electric vehicle charging stations?", session)
    assert "EV charging stations are available" in response
    assert "## Are there spaces for disabled drivers?" not in response


@patch("app.chatbot.router.retrieve")
def test_route_keeps_info_intent_for_cancellation_policy_question(mock_retrieve) -> None:
    mock_retrieve.return_value = [
        {
            "page_content": "Cancellations are possible before the reservation start time.",
            "metadata": {"source": "faq.md"},
        }
    ]
    session = {
        "reservation_active": False,
        "step": None,
        "data": {},
        "cancel_active": False,
        "cancel_step": None,
    }

    response = route("What is the cancellation policy?", session)
    assert "cancellations are possible" in response.lower()