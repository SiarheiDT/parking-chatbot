from __future__ import annotations

from pathlib import Path
from typing import Any

from app.config import get_config
from app.db.connection import get_connection
from app.db.repositories import save_reservation
from app.guardrails.filter import contains_sensitive_data, is_blocked_request
from app.rag.retriever import retrieve


config = get_config()


def classify_intent(query: str) -> str:
    """
    Very simple intent classification for Stage 1.
    """
    q = query.lower()

    reservation_keywords = [
        "book",
        "booking",
        "reserve",
        "reservation",
        "park my car",
        "parking space",
        "parking spot",
        "i want to park",
        "i need parking",
    ]

    if any(keyword in q for keyword in reservation_keywords):
        return "reservation"

    return "info"


def handle_info(query: str) -> str:
    """
    Handle informational queries using a hybrid approach:
    - direct SQL lookup for dynamic data
    - RAG retrieval for static information
    """
    q = query.lower()

    if "hour" in q or "working" in q:
        return _get_working_hours(config.DB_PATH)

    if "price" in q or "cost" in q or "tariff" in q:
        return _get_prices(config.DB_PATH)

    if "available" in q or "availability" in q or "free spaces" in q:
        return _get_availability(config.DB_PATH)

    docs = retrieve(query, top_k=config.TOP_K)

    if not docs:
        return "Sorry, I couldn't find relevant information."

    return _build_concise_answer(docs)


def _build_concise_answer(docs: list[dict[str, Any]]) -> str:
    """
    Return a short answer from the best retrieved chunks.
    """
    top_chunks = []
    for doc in docs[:2]:
        content = doc["page_content"].strip()
        if content:
            top_chunks.append(content)

    if not top_chunks:
        return "Sorry, I couldn't find relevant information."

    return "Here is the relevant information I found:\n\n" + "\n\n".join(top_chunks)


def _get_working_hours(db_path: Path) -> str:
    connection = get_connection(db_path)
    cursor = connection.cursor()
    cursor.execute("SELECT open_time, close_time FROM parking_hours ORDER BY id DESC LIMIT 1")
    row = cursor.fetchone()
    connection.close()

    if not row:
        return "Working hours information is unavailable."

    return f"The parking facility operates daily from {row[0]} to {row[1]}."


def _get_prices(db_path: Path) -> str:
    connection = get_connection(db_path)
    cursor = connection.cursor()
    cursor.execute(
        """
        SELECT hourly_rate, daily_rate, monthly_rate
        FROM parking_prices
        ORDER BY id DESC
        LIMIT 1
        """
    )
    row = cursor.fetchone()
    connection.close()

    if not row:
        return "Pricing information is unavailable."

    hourly_rate, daily_rate, monthly_rate = row
    return (
        f"The current parking prices are: hourly rate {hourly_rate:.2f}, "
        f"daily rate {daily_rate:.2f}, monthly rate {monthly_rate:.2f}."
    )


def _get_availability(db_path: Path) -> str:
    connection = get_connection(db_path)
    cursor = connection.cursor()
    cursor.execute(
        """
        SELECT available_spaces, updated_at
        FROM parking_availability
        ORDER BY id DESC
        LIMIT 1
        """
    )
    row = cursor.fetchone()
    connection.close()

    if not row:
        return "Availability information is unavailable."

    available_spaces, updated_at = row
    return f"Currently, {available_spaces} parking spaces are available. Last updated at: {updated_at}."


def handle_reservation(session: dict[str, Any], user_input: str | None = None) -> str:
    """
    Collect reservation data step by step and persist it to SQLite.
    """
    if not session["reservation_active"]:
        session["reservation_active"] = True
        session["step"] = "first_name"
        session["data"] = {}
        return "Let's start your reservation. Please provide your first name."

    step = session["step"]

    if step == "first_name":
        session["data"]["first_name"] = user_input
        session["step"] = "last_name"
        return "Please provide your last name."

    if step == "last_name":
        session["data"]["last_name"] = user_input
        session["step"] = "car_plate"
        return "Please provide your car plate number."

    if step == "car_plate":
        session["data"]["car_plate"] = user_input
        session["step"] = "start_datetime"
        return "Please provide the reservation start date and time."

    if step == "start_datetime":
        session["data"]["start_datetime"] = user_input
        session["step"] = "end_datetime"
        return "Please provide the reservation end date and time."

    if step == "end_datetime":
        session["data"]["end_datetime"] = user_input

        save_reservation(
            db_path=config.DB_PATH,
            first_name=session["data"]["first_name"],
            last_name=session["data"]["last_name"],
            car_plate=session["data"]["car_plate"],
            start_datetime=session["data"]["start_datetime"],
            end_datetime=session["data"]["end_datetime"],
        )

        session["reservation_active"] = False
        session["step"] = None
        session["data"] = {}

        return (
            "Your reservation request has been collected successfully and saved with pending status. "
            "It will require administrator confirmation."
        )

    session["reservation_active"] = False
    session["step"] = None
    session["data"] = {}
    return "Reservation flow was reset. Please try again."


def route(query: str, session: dict[str, Any]) -> str:
    """
    Main orchestration entrypoint.
    """
    if contains_sensitive_data(query):
        return "Request blocked due to sensitive data."

    if is_blocked_request(query):
        return "I cannot provide private or internal information."

    if session["reservation_active"]:
        return handle_reservation(session, query)

    intent = classify_intent(query)

    if intent == "reservation":
        return handle_reservation(session)

    return handle_info(query)