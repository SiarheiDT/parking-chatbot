from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from typing import Final

from app.db.connection import get_connection

ACTIVE_RESERVATION_STATUSES: Final[tuple[str, ...]] = ("pending", "confirmed")

_DATETIME_FMT: Final[str] = "%Y-%m-%d %H:%M"


def get_concurrent_capacity(db_path: Path) -> int:
    """
    Maximum concurrent active reservations from the latest parking_availability row.
    """
    connection = get_connection(db_path)
    cursor = connection.cursor()
    cursor.execute(
        """
        SELECT available_spaces
        FROM parking_availability
        ORDER BY id DESC
        LIMIT 1
        """
    )
    row = cursor.fetchone()
    connection.close()
    if row is None or row[0] is None:
        return 0
    return max(0, int(row[0]))


def count_active_reservations_overlapping(
    db_path: Path,
    start_datetime: str,
    end_datetime: str,
) -> int:
    """
    Count pending/confirmed reservations whose interval overlaps [start_datetime, end_datetime).
    """
    connection = get_connection(db_path)
    cursor = connection.cursor()
    placeholders = ", ".join("?" for _ in ACTIVE_RESERVATION_STATUSES)
    cursor.execute(
        f"""
        SELECT COUNT(*)
        FROM reservations
        WHERE status IN ({placeholders})
          AND datetime(start_datetime) < datetime(?)
          AND datetime(end_datetime) > datetime(?)
        """,
        (*ACTIVE_RESERVATION_STATUSES, end_datetime, start_datetime),
    )
    count = int(cursor.fetchone()[0])
    connection.close()
    return count


def find_first_available_slot(
    db_path: Path,
    desired_start: str,
    desired_end: str,
    *,
    step_minutes: int = 30,
    max_search_days: int = 14,
) -> tuple[str, str] | None:
    """
    Starting from desired_start, advance in step_minutes increments and return the first
    window with the same duration as [desired_start, desired_end) where occupancy is below capacity.
    """
    capacity = get_concurrent_capacity(db_path)
    if capacity <= 0:
        return None

    start_dt = datetime.strptime(desired_start, _DATETIME_FMT)
    end_dt = datetime.strptime(desired_end, _DATETIME_FMT)
    if end_dt <= start_dt:
        return None

    duration = end_dt - start_dt
    step = timedelta(minutes=max(1, step_minutes))
    horizon = start_dt + timedelta(days=max(1, max_search_days))

    current_start = start_dt
    while current_start + duration <= horizon:
        current_end = current_start + duration
        cs = current_start.strftime(_DATETIME_FMT)
        ce = current_end.strftime(_DATETIME_FMT)
        if count_active_reservations_overlapping(db_path, cs, ce) < capacity:
            return (cs, ce)
        current_start += step

    return None


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

