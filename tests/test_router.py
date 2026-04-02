from dataclasses import replace
from unittest.mock import patch

import sqlite3

from app.chatbot.router import route
from app.db.init_db import initialize_database
from app.db.repositories import save_reservation

import app.chatbot.router as router_module


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


def test_reservation_suggests_next_slot_when_lot_full(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / "full_lot.db"
    initialize_database(db_path)
    connection = sqlite3.connect(db_path)
    connection.execute("UPDATE parking_availability SET available_spaces = 1")
    connection.commit()
    connection.close()
    save_reservation(
        db_path=db_path,
        first_name="Other",
        last_name="User",
        car_plate="OU1000",
        start_datetime="2099-08-10 10:00",
        end_datetime="2099-08-10 12:00",
    )
    monkeypatch.setattr(
        router_module,
        "config",
        replace(router_module.config, DB_PATH=db_path),
    )

    session: dict = {
        "reservation_active": False,
        "step": None,
        "data": {},
        "cancel_active": False,
        "cancel_step": None,
    }
    route("I need a parking reservation", session)
    route("Jane", session)
    route("Doe", session)
    route("JD2000", session)
    route("2099-08-10 10:00", session)
    response = route("2099-08-10 12:00", session)

    assert "next available slot" in response.lower()
    assert "2099-08-10 12:00" in response
    assert "2099-08-10 14:00" in response
    assert session["step"] == "start_datetime"


@patch("app.chatbot.router.retrieve")
def test_free_places_tomorrow_pm_routes_to_availability_not_rag(
    mock_retrieve, tmp_path, monkeypatch
) -> None:
    db_path = tmp_path / "free_places.db"
    initialize_database(db_path)
    connection = sqlite3.connect(db_path)
    connection.execute("UPDATE parking_availability SET available_spaces = 5")
    connection.commit()
    connection.close()
    monkeypatch.setattr(
        router_module,
        "config",
        replace(router_module.config, DB_PATH=db_path),
    )

    mock_retrieve.side_effect = AssertionError("RAG retrieve should not run for availability")

    session: dict = {"reservation_active": False, "step": None, "data": {}}
    response = route("Do you have free places tommorow at 1.00 PM?", session)

    mock_retrieve.assert_not_called()
    assert "free spaces" in response.lower()


def test_info_availability_for_tomorrow_time_when_space_exists(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / "availability_ok.db"
    initialize_database(db_path)
    connection = sqlite3.connect(db_path)
    connection.execute("UPDATE parking_availability SET available_spaces = 2")
    connection.commit()
    connection.close()
    monkeypatch.setattr(
        router_module,
        "config",
        replace(router_module.config, DB_PATH=db_path),
    )

    session: dict = {"reservation_active": False, "step": None, "data": {}}
    response = route("Are there available spaces tomorrow at 13:00?", session)

    assert "yes, there are free spaces" in response.lower()


def test_info_availability_for_tomorrow_time_suggests_next_slot(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / "availability_full.db"
    initialize_database(db_path)
    connection = sqlite3.connect(db_path)
    connection.execute("UPDATE parking_availability SET available_spaces = 1")
    connection.commit()
    connection.close()
    save_reservation(
        db_path=db_path,
        first_name="Full",
        last_name="Lot",
        car_plate="FULL001",
        start_datetime="2099-08-11 13:00",
        end_datetime="2099-08-11 14:00",
    )
    monkeypatch.setattr(
        router_module,
        "config",
        replace(router_module.config, DB_PATH=db_path),
    )

    session: dict = {"reservation_active": False, "step": None, "data": {}}
    response = route("Check availability at 2099-08-11 13:00", session)

    assert "no free spaces are available at 2099-08-11 13:00" in response.lower()
    assert "first available 1-hour slot is 2099-08-11 14:00 to 2099-08-11 15:00" in response.lower()