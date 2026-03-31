from app.chatbot.router import route


def test_reservation_flow_starts_correctly() -> None:
    session = {
        "reservation_active": False,
        "step": None,
        "data": {},
    }

    response = route("I want to reserve a parking space", session)

    assert "first name" in response.lower()
    assert session["reservation_active"] is True
    assert session["step"] == "first_name"


def test_reservation_flow_collects_first_name() -> None:
    session = {
        "reservation_active": True,
        "step": "first_name",
        "data": {},
    }

    response = route("John", session)

    assert "last name" in response.lower()
    assert session["data"]["first_name"] == "John"
    assert session["step"] == "last_name"