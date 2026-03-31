from __future__ import annotations

from pathlib import Path
from typing import Final

from app.db.connection import get_connection

ACTIVE_RESERVATION_STATUSES: Final[tuple[str, ...]] = ("pending", "confirmed")


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


def has_overlapping_active_reservation(
    db_path: Path,
    car_plate: str,
    start_datetime: str,
    end_datetime: str,
) -> bool:
    """
    Check whether an active reservation overlaps with [start_datetime, end_datetime)
    for the same car plate.
    """
    normalized_plate = car_plate.strip().upper()
    if not normalized_plate:
        return False

    connection = get_connection(db_path)
    cursor = connection.cursor()
    placeholders = ", ".join("?" for _ in ACTIVE_RESERVATION_STATUSES)
    cursor.execute(
        f"""
        SELECT 1
        FROM reservations
        WHERE UPPER(car_plate) = ?
          AND status IN ({placeholders})
          AND datetime(start_datetime) < datetime(?)
          AND datetime(end_datetime) > datetime(?)
        LIMIT 1
        """,
        (normalized_plate, *ACTIVE_RESERVATION_STATUSES, end_datetime, start_datetime),
    )
    row = cursor.fetchone()
    connection.close()
    return row is not None


def cancel_upcoming_reservation_by_plate(db_path: Path, car_plate: str) -> tuple[bool, str]:
    """
    Cancel the nearest upcoming reservation for a given car plate.
    Cancellation is only allowed before reservation start time.
    """
    normalized_plate = car_plate.strip().upper()
    if not normalized_plate:
        return False, "Car plate cannot be empty."

    connection = get_connection(db_path)
    cursor = connection.cursor()

    placeholders = ", ".join("?" for _ in ACTIVE_RESERVATION_STATUSES)
    cursor.execute(
        f"""
        SELECT id, start_datetime
        FROM reservations
        WHERE UPPER(car_plate) = ?
          AND status IN ({placeholders})
          AND datetime(start_datetime) > datetime('now')
        ORDER BY datetime(start_datetime) ASC
        LIMIT 1
        """,
        (normalized_plate, *ACTIVE_RESERVATION_STATUSES),
    )
    row = cursor.fetchone()

    if not row:
        connection.close()
        return (
            False,
            "No upcoming active reservation was found for this car plate. "
            "Only future reservations can be cancelled.",
        )

    reservation_id, start_datetime = row
    cursor.execute(
        """
        UPDATE reservations
        SET status = 'cancelled'
        WHERE id = ?
        """,
        (reservation_id,),
    )
    connection.commit()
    connection.close()

    return True, f"Your reservation starting at {start_datetime} has been cancelled."

