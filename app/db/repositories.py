from __future__ import annotations

from pathlib import Path

from app.db.connection import get_connection


def save_reservation(
    db_path: Path,
    first_name: str,
    last_name: str,
    car_plate: str,
    start_datetime: str,
    end_datetime: str,
) -> None:
    """
    Save a reservation request into the SQLite database.
    """
    connection = get_connection(db_path)
    cursor = connection.cursor()

    cursor.execute(
        """
        INSERT INTO reservations (
            first_name,
            last_name,
            car_plate,
            start_datetime,
            end_datetime,
            status
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            first_name,
            last_name,
            car_plate,
            start_datetime,
            end_datetime,
            "pending",
        ),
    )

    connection.commit()
    connection.close()