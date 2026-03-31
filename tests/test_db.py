from pathlib import Path
import sqlite3

from app.db.init_db import initialize_database
from app.db.repositories import save_reservation


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