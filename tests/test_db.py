from pathlib import Path
import sqlite3

import pytest

pytestmark = pytest.mark.stage1

from app.db.init_db import initialize_database
from app.db.repositories import (
    cancel_upcoming_reservation_by_plate,
    count_active_reservations_overlapping,
    find_first_available_slot,
    get_concurrent_capacity,
    get_reservation_by_id,
    has_overlapping_active_reservation,
    list_pending_reservations,
    save_reservation,
    update_reservation_status,
)


def test_initialize_database_creates_reservations_table(tmp_path: Path) -> None:
    db_path = tmp_path / "test_parking.db"

    initialize_database(db_path)

    connection = sqlite3.connect(db_path)
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type='table' AND name='reservations'
        """
    )
    row = cursor.fetchone()
    connection.close()

    assert row is not None
    assert row[0] == "reservations"


def test_initialize_database_seeds_dynamic_tables(tmp_path: Path) -> None:
    db_path = tmp_path / "test_parking.db"
    initialize_database(db_path)

    connection = sqlite3.connect(db_path)
    cursor = connection.cursor()
    cursor.execute("SELECT COUNT(*) FROM parking_hours")
    hours_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM parking_prices")
    prices_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM parking_availability")
    availability_count = cursor.fetchone()[0]
    connection.close()

    assert hours_count >= 1
    assert prices_count >= 1
    assert availability_count >= 1


def test_save_reservation_inserts_row(tmp_path: Path) -> None:
    db_path = tmp_path / "test_parking.db"

    initialize_database(db_path)

    new_id = save_reservation(
        db_path=db_path,
        first_name="John",
        last_name="Smith",
        car_plate="DW12345",
        start_datetime="2026-04-01 09:00",
        end_datetime="2026-04-01 18:00",
    )
    assert new_id == 1

    connection = sqlite3.connect(db_path)
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT first_name, last_name, car_plate, start_datetime, end_datetime, status
        FROM reservations
        """
    )
    row = cursor.fetchone()
    connection.close()

    assert row == (
        "John",
        "Smith",
        "DW12345",
        "2026-04-01 09:00",
        "2026-04-01 18:00",
        "pending",
    )


def test_cancel_upcoming_reservation_by_plate_updates_status(tmp_path: Path) -> None:
    db_path = tmp_path / "test_parking.db"
    initialize_database(db_path)

    save_reservation(
        db_path=db_path,
        first_name="John",
        last_name="Smith",
        car_plate="DW12345",
        start_datetime="2099-04-01 09:00",
        end_datetime="2099-04-01 18:00",
    )

    success, _ = cancel_upcoming_reservation_by_plate(db_path, "DW12345")
    assert success is True

    connection = sqlite3.connect(db_path)
    cursor = connection.cursor()
    cursor.execute("SELECT status FROM reservations ORDER BY id DESC LIMIT 1")
    row = cursor.fetchone()
    connection.close()

    assert row == ("cancelled",)


def test_cancel_upcoming_reservation_by_plate_rejects_past_reservation(tmp_path: Path) -> None:
    db_path = tmp_path / "test_parking.db"
    initialize_database(db_path)

    save_reservation(
        db_path=db_path,
        first_name="Jane",
        last_name="Doe",
        car_plate="AB123CD",
        start_datetime="2000-01-01 09:00",
        end_datetime="2000-01-01 18:00",
    )

    success, message = cancel_upcoming_reservation_by_plate(db_path, "AB123CD")
    assert success is False
    assert "future reservations can be cancelled" in message.lower()


def test_has_overlapping_active_reservation_detects_overlap(tmp_path: Path) -> None:
    db_path = tmp_path / "test_parking.db"
    initialize_database(db_path)

    save_reservation(
        db_path=db_path,
        first_name="John",
        last_name="Smith",
        car_plate="DW12345",
        start_datetime="2099-04-01 09:00",
        end_datetime="2099-04-01 18:00",
    )

    assert has_overlapping_active_reservation(
        db_path=db_path,
        car_plate="DW12345",
        start_datetime="2099-04-01 10:00",
        end_datetime="2099-04-01 12:00",
    ) is True


def test_has_overlapping_active_reservation_returns_false_for_non_overlap(tmp_path: Path) -> None:
    db_path = tmp_path / "test_parking.db"
    initialize_database(db_path)

    save_reservation(
        db_path=db_path,
        first_name="John",
        last_name="Smith",
        car_plate="DW12345",
        start_datetime="2099-04-01 09:00",
        end_datetime="2099-04-01 18:00",
    )

    assert has_overlapping_active_reservation(
        db_path=db_path,
        car_plate="DW12345",
        start_datetime="2099-04-01 18:00",
        end_datetime="2099-04-01 20:00",
    ) is False


def test_has_overlapping_active_reservation_is_case_insensitive_for_plate(tmp_path: Path) -> None:
    db_path = tmp_path / "test_parking.db"
    initialize_database(db_path)

    save_reservation(
        db_path=db_path,
        first_name="John",
        last_name="Smith",
        car_plate="dw12345",
        start_datetime="2099-04-01 09:00",
        end_datetime="2099-04-01 18:00",
    )

    assert has_overlapping_active_reservation(
        db_path=db_path,
        car_plate="DW12345",
        start_datetime="2099-04-01 10:00",
        end_datetime="2099-04-01 12:00",
    ) is True


def test_has_overlapping_active_reservation_ignores_cancelled_status(tmp_path: Path) -> None:
    db_path = tmp_path / "test_parking.db"
    initialize_database(db_path)

    save_reservation(
        db_path=db_path,
        first_name="John",
        last_name="Smith",
        car_plate="DW12345",
        start_datetime="2099-04-01 09:00",
        end_datetime="2099-04-01 18:00",
    )

    connection = sqlite3.connect(db_path)
    cursor = connection.cursor()
    cursor.execute("UPDATE reservations SET status = 'cancelled' WHERE car_plate = 'DW12345'")
    connection.commit()
    connection.close()

    assert has_overlapping_active_reservation(
        db_path=db_path,
        car_plate="DW12345",
        start_datetime="2099-04-01 10:00",
        end_datetime="2099-04-01 12:00",
    ) is False


def test_cancel_upcoming_reservation_by_plate_rejects_empty_plate(tmp_path: Path) -> None:
    db_path = tmp_path / "test_parking.db"
    initialize_database(db_path)
    success, message = cancel_upcoming_reservation_by_plate(db_path, "   ")
    assert success is False
    assert "cannot be empty" in message.lower()


def test_get_concurrent_capacity_reads_latest_row(tmp_path: Path) -> None:
    db_path = tmp_path / "test_parking.db"
    initialize_database(db_path)
    assert get_concurrent_capacity(db_path) == 37


def test_count_active_reservations_overlapping(tmp_path: Path) -> None:
    db_path = tmp_path / "test_parking.db"
    initialize_database(db_path)
    save_reservation(
        db_path=db_path,
        first_name="A",
        last_name="B",
        car_plate="AA111",
        start_datetime="2099-05-01 10:00",
        end_datetime="2099-05-01 12:00",
    )
    save_reservation(
        db_path=db_path,
        first_name="C",
        last_name="D",
        car_plate="BB222",
        start_datetime="2099-05-01 11:00",
        end_datetime="2099-05-01 13:00",
    )
    assert count_active_reservations_overlapping(db_path, "2099-05-01 10:30", "2099-05-01 11:30") == 2
    assert count_active_reservations_overlapping(db_path, "2099-05-01 12:00", "2099-05-01 14:00") == 1


def test_find_first_available_slot_returns_same_window_when_free(tmp_path: Path) -> None:
    db_path = tmp_path / "test_parking.db"
    initialize_database(db_path)
    connection = sqlite3.connect(db_path)
    connection.execute("UPDATE parking_availability SET available_spaces = 2")
    connection.commit()
    connection.close()
    slot = find_first_available_slot(
        db_path,
        "2099-06-01 09:00",
        "2099-06-01 11:00",
        step_minutes=30,
        max_search_days=1,
    )
    assert slot == ("2099-06-01 09:00", "2099-06-01 11:00")


def test_get_reservation_by_id_returns_row(tmp_path: Path) -> None:
    db_path = tmp_path / "test_parking.db"
    initialize_database(db_path)
    rid = save_reservation(
        db_path=db_path,
        first_name="A",
        last_name="B",
        car_plate="XX1",
        start_datetime="2099-01-01 10:00",
        end_datetime="2099-01-01 12:00",
    )
    row = get_reservation_by_id(db_path, rid)
    assert row is not None
    assert row["id"] == rid
    assert row["first_name"] == "A"
    assert row["status"] == "pending"
    assert get_reservation_by_id(db_path, 99999) is None


def test_list_pending_reservations_and_admin_status_update(tmp_path: Path) -> None:
    db_path = tmp_path / "test_parking.db"
    initialize_database(db_path)
    r1 = save_reservation(
        db_path=db_path,
        first_name="U",
        last_name="One",
        car_plate="P1",
        start_datetime="2099-02-01 09:00",
        end_datetime="2099-02-01 10:00",
    )
    save_reservation(
        db_path=db_path,
        first_name="U",
        last_name="Two",
        car_plate="P2",
        start_datetime="2099-02-02 09:00",
        end_datetime="2099-02-02 10:00",
    )
    pending = list_pending_reservations(db_path, limit=10)
    assert len(pending) == 2
    assert {p["id"] for p in pending} == {r1, r1 + 1}

    assert update_reservation_status(db_path, r1, "confirmed") is True
    assert get_reservation_by_id(db_path, r1)["status"] == "confirmed"
    assert update_reservation_status(db_path, r1, "rejected") is False

    assert update_reservation_status(db_path, r1 + 1, "rejected") is True
    assert list_pending_reservations(db_path) == []

    assert update_reservation_status(db_path, 1, "invalid") is False


def test_find_first_available_slot_skips_full_window(tmp_path: Path) -> None:
    db_path = tmp_path / "test_parking.db"
    initialize_database(db_path)
    connection = sqlite3.connect(db_path)
    connection.execute("UPDATE parking_availability SET available_spaces = 1")
    connection.commit()
    connection.close()
    save_reservation(
        db_path=db_path,
        first_name="A",
        last_name="B",
        car_plate="XX1",
        start_datetime="2099-07-01 10:00",
        end_datetime="2099-07-01 12:00",
    )
    slot = find_first_available_slot(
        db_path,
        "2099-07-01 10:00",
        "2099-07-01 12:00",
        step_minutes=30,
        max_search_days=1,
    )
    assert slot == ("2099-07-01 12:00", "2099-07-01 14:00")

