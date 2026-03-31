from __future__ import annotations

from pathlib import Path

from app.db.connection import get_connection


def initialize_database(db_path: Path) -> None:
    """
    Create required tables and seed basic dynamic data.
    """
    connection = get_connection(db_path)
    cursor = connection.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS parking_hours (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            open_time TEXT NOT NULL,
            close_time TEXT NOT NULL
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS parking_prices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            hourly_rate REAL NOT NULL,
            daily_rate REAL,
            monthly_rate REAL
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS parking_availability (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            available_spaces INTEGER NOT NULL,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS reservations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            first_name TEXT NOT NULL,
            last_name TEXT NOT NULL,
            car_plate TEXT NOT NULL,
            start_datetime TEXT NOT NULL,
            end_datetime TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending'
        )
        """
    )

    cursor.execute("SELECT COUNT(*) FROM parking_hours")
    if cursor.fetchone()[0] == 0:
        cursor.execute(
            """
            INSERT INTO parking_hours (open_time, close_time)
            VALUES (?, ?)
            """,
            ("06:00", "23:00"),
        )

    cursor.execute("SELECT COUNT(*) FROM parking_prices")
    if cursor.fetchone()[0] == 0:
        cursor.execute(
            """
            INSERT INTO parking_prices (hourly_rate, daily_rate, monthly_rate)
            VALUES (?, ?, ?)
            """,
            (5.50, 35.00, 420.00),
        )

    cursor.execute("SELECT COUNT(*) FROM parking_availability")
    if cursor.fetchone()[0] == 0:
        cursor.execute(
            """
            INSERT INTO parking_availability (available_spaces)
            VALUES (?)
            """,
            (37,),
        )

    connection.commit()
    connection.close()