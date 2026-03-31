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