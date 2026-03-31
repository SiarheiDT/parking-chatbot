from pathlib import Path
import sqlite3

from app.db.init_db import initialize_database
from app.db.repositories import (
    cancel_upcoming_reservation_by_plate,
    has_overlapping_active_reservation,
    save_reservation,
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

    save_reservation(
        db_path=db_path,
        first_name="John",
        last_name="Smith",
        car_plate="DW12345",
        start_datetime="2026-04-01 09:00",
        end_datetime="2026-04-01 18:00",
    )

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

