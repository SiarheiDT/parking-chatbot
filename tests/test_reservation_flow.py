import pytest

pytestmark = pytest.mark.stage1

from app.chatbot.router import route
from unittest.mock import patch
from app.db.init_db import initialize_database
import app.chatbot.router as router_module


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


def test_cancellation_flow_starts_correctly() -> None:
    session = {
        "reservation_active": False,
        "step": None,
        "data": {},
        "cancel_active": False,
        "cancel_step": None,
    }

    response = route("Please cancel my reservation", session)

    assert "car plate" in response.lower()
    assert session["cancel_active"] is True
    assert session["cancel_step"] == "car_plate"


@patch("app.chatbot.router.cancel_upcoming_reservation_by_plate")
def test_cancellation_flow_completes_for_plate(mock_cancel) -> None:
    mock_cancel.return_value = (True, "Your reservation starting at 2099-04-01 09:00 has been cancelled.")
    session = {
        "reservation_active": False,
        "step": None,
        "data": {},
        "cancel_active": True,
        "cancel_step": "car_plate",
    }

    response = route("DW12345", session)

    assert "has been cancelled" in response.lower()
    assert session["cancel_active"] is False
    assert session["cancel_step"] is None


@patch("app.chatbot.router.has_overlapping_active_reservation")
def test_reservation_flow_blocks_overlapping_period(mock_overlap) -> None:
    mock_overlap.return_value = True
    session = {
        "reservation_active": True,
        "step": "end_datetime",
        "data": {
            "first_name": "John",
            "last_name": "Smith",
            "car_plate": "DW12345",
            "start_datetime": "2099-04-01 09:00",
        },
        "cancel_active": False,
        "cancel_step": None,
    }

    response = route("2099-04-01 18:00", session)

    assert "already overlaps" in response.lower()
    assert session["reservation_active"] is True
    assert session["step"] == "start_datetime"


def test_reservation_flow_rejects_invalid_start_datetime_format() -> None:
    session = {
        "reservation_active": True,
        "step": "start_datetime",
        "data": {
            "first_name": "John",
            "last_name": "Smith",
            "car_plate": "DW12345",
        },
        "cancel_active": False,
        "cancel_step": None,
    }

    response = route("tomorrow morning", session)

    assert "invalid date/time format" in response.lower()
    assert session["step"] == "start_datetime"


def test_reservation_flow_rejects_end_before_start() -> None:
    session = {
        "reservation_active": True,
        "step": "end_datetime",
        "data": {
            "first_name": "John",
            "last_name": "Smith",
            "car_plate": "DW12345",
            "start_datetime": "2099-04-01 09:00",
        },
        "cancel_active": False,
        "cancel_step": None,
    }

    response = route("2099-04-01 08:00", session)

    assert "must be later" in response.lower()
    assert session["step"] == "end_datetime"


@patch("app.chatbot.router.has_overlapping_active_reservation")
def test_reservation_flow_normalizes_non_iso_datetime(mock_overlap) -> None:
    mock_overlap.return_value = False
    session = {
        "reservation_active": True,
        "step": "start_datetime",
        "data": {
            "first_name": "John",
            "last_name": "Smith",
            "car_plate": "DW12345",
        },
        "cancel_active": False,
        "cancel_step": None,
    }

    response = route("01/04/2099 2:00PM", session)

    assert "end date and time" in response.lower()
    assert session["data"]["start_datetime"] == "2099-04-01 14:00"


@patch("app.chatbot.router.has_overlapping_active_reservation")
def test_reservation_flow_accepts_dd_mm_yyyy_24h_datetime(mock_overlap) -> None:
    mock_overlap.return_value = False
    session = {
        "reservation_active": True,
        "step": "start_datetime",
        "data": {
            "first_name": "John",
            "last_name": "Smith",
            "car_plate": "DW12345",
        },
        "cancel_active": False,
        "cancel_step": None,
    }

    response = route("01/04/2099 14:30", session)

    assert "end date and time" in response.lower()
    assert session["data"]["start_datetime"] == "2099-04-01 14:30"


def test_reservation_flow_rejects_invalid_end_datetime_format() -> None:
    session = {
        "reservation_active": True,
        "step": "end_datetime",
        "data": {
            "first_name": "John",
            "last_name": "Smith",
            "car_plate": "DW12345",
            "start_datetime": "2099-04-01 09:00",
        },
        "cancel_active": False,
        "cancel_step": None,
    }

    response = route("next friday", session)

    assert "invalid date/time format" in response.lower()
    assert session["step"] == "end_datetime"


def test_cancellation_flow_requires_non_empty_plate() -> None:
    session = {
        "reservation_active": False,
        "step": None,
        "data": {},
        "cancel_active": True,
        "cancel_step": "car_plate",
    }

    response = route("   ", session)

    assert "cannot be empty" in response.lower()
    assert session["cancel_active"] is True
    assert session["cancel_step"] == "car_plate"


def test_abort_command_resets_reservation_flow() -> None:
    session = {
        "reservation_active": True,
        "step": "last_name",
        "data": {"first_name": "John"},
        "cancel_active": False,
        "cancel_step": None,
    }

    response = route("stop", session)

    assert "operation has been cancelled" in response.lower()
    assert session["reservation_active"] is False
    assert session["step"] is None
    assert session["data"] == {}


def test_abort_command_resets_cancellation_flow() -> None:
    session = {
        "reservation_active": False,
        "step": None,
        "data": {},
        "cancel_active": True,
        "cancel_step": "car_plate",
    }

    response = route("refresh", session)

    assert "operation has been cancelled" in response.lower()
    assert session["cancel_active"] is False
    assert session["cancel_step"] is None


def test_abort_alias_quit_resets_reservation_flow() -> None:
    session = {
        "reservation_active": True,
        "step": "car_plate",
        "data": {"first_name": "John", "last_name": "Smith"},
        "cancel_active": False,
        "cancel_step": None,
    }

    response = route("quit", session)

    assert "operation has been cancelled" in response.lower()
    assert session["reservation_active"] is False
    assert session["step"] is None
    assert session["data"] == {}


@patch("app.chatbot.router.notify_admin_new_reservation", return_value=True)
def test_reservation_end_to_end_overlap_then_success(_mock_notify, tmp_path) -> None:
    db_path = tmp_path / "test_parking.db"
    initialize_database(db_path)
    original_db_path = router_module.config.DB_PATH
    router_module.config.DB_PATH = db_path
    try:
        session = {
            "reservation_active": False,
            "step": None,
            "data": {},
            "cancel_active": False,
            "cancel_step": None,
        }

        # Reservation #1 (successful)
        assert "first name" in route("I want to reserve", session).lower()
        assert "last name" in route("Siarhei", session).lower()
        assert "car plate" in route("Kandrashevich", session).lower()
        assert "start date and time" in route("DW11WD1111", session).lower()
        assert "end date and time" in route("01/04/2099 2:00PM", session).lower()
        first_done = route("03/04/2099 1:00PM", session)
        assert "saved with pending status" in first_done.lower()

        # Reservation #2 with overlap (must be blocked)
        assert "first name" in route("next reservation", session).lower()
        assert "last name" in route("Siarhei", session).lower()
        assert "car plate" in route("Kandrashevich", session).lower()
        assert "start date and time" in route("DW11WD1111", session).lower()
        assert "end date and time" in route("01/04/2099 3:00PM", session).lower()
        overlap_response = route("04/04/2099 3:00PM", session)
        assert "already overlaps" in overlap_response.lower()
        assert session["step"] == "start_datetime"
        assert session["reservation_active"] is True

        # Retry with non-overlapping window (must succeed)
        assert "end date and time" in route("05/04/2099 9:00AM", session).lower()
        second_done = route("05/04/2099 11:00AM", session)
        assert "saved with pending status" in second_done.lower()
        assert session["reservation_active"] is False
    finally:
        router_module.config.DB_PATH = original_db_path