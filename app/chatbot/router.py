from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Literal, TypedDict

from langgraph.graph import END, StateGraph

from app.config import get_config
from app.db.connection import get_connection
from app.db.repositories import (
    cancel_upcoming_reservation_by_plate,
    has_overlapping_active_reservation,
    save_reservation,
)
from app.guardrails.filter import contains_sensitive_data, is_blocked_request
from app.rag.retriever import retrieve


config = get_config()


SUPPORTED_DATETIME_FORMATS = (
    "%Y-%m-%d %H:%M",
    "%d/%m/%Y %H:%M",
    "%d/%m/%Y %I:%M%p",
    "%d/%m/%Y %I:%M %p",
)


class ChatState(TypedDict):
    query: str
    session: dict[str, Any]
    intent: Literal["reservation", "cancel", "info"] | None
    response: str
    blocked: bool


def classify_intent(query: str) -> Literal["reservation", "cancel", "info"]:
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

    cancel_keywords = [
        "cancel reservation",
        "cancel booking",
        "cancel my booking",
        "cancel my reservation",
        "cancel",
    ]
    if any(keyword in q for keyword in cancel_keywords):
        return "cancel"

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


def _normalize_datetime_input(value: str) -> str | None:
    raw = value.strip()
    for fmt in SUPPORTED_DATETIME_FORMATS:
        try:
            dt = datetime.strptime(raw, fmt)
            return dt.strftime("%Y-%m-%d %H:%M")
        except ValueError:
            continue
    return None


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
        return (
            "Please provide the reservation start date and time "
            "(format: YYYY-MM-DD HH:MM or DD/MM/YYYY HH:MM or DD/MM/YYYY H:MMAM)."
        )

    if step == "start_datetime":
        normalized_start = _normalize_datetime_input(user_input or "")
        if not normalized_start:
            return (
                "Invalid date/time format. Use one of: "
                "YYYY-MM-DD HH:MM or DD/MM/YYYY HH:MM or DD/MM/YYYY H:MMAM."
            )
        session["data"]["start_datetime"] = normalized_start
        session["step"] = "end_datetime"
        return (
            "Please provide the reservation end date and time "
            "(format: YYYY-MM-DD HH:MM or DD/MM/YYYY HH:MM or DD/MM/YYYY H:MMAM)."
        )

    if step == "end_datetime":
        normalized_end = _normalize_datetime_input(user_input or "")
        if not normalized_end:
            return (
                "Invalid date/time format. Use one of: "
                "YYYY-MM-DD HH:MM or DD/MM/YYYY HH:MM or DD/MM/YYYY H:MMAM."
            )

        start_dt = datetime.strptime(session["data"]["start_datetime"], "%Y-%m-%d %H:%M")
        end_dt = datetime.strptime(normalized_end, "%Y-%m-%d %H:%M")
        if end_dt <= start_dt:
            return "Reservation end date/time must be later than start date/time."

        session["data"]["end_datetime"] = normalized_end

        if has_overlapping_active_reservation(
            db_path=config.DB_PATH,
            car_plate=session["data"]["car_plate"],
            start_datetime=session["data"]["start_datetime"],
            end_datetime=session["data"]["end_datetime"],
        ):
            session["data"].pop("start_datetime", None)
            session["data"].pop("end_datetime", None)
            session["step"] = "start_datetime"
            return (
                "An active reservation for this car plate already overlaps with the requested period. "
                "Please provide a different reservation start date and time "
                "(format: YYYY-MM-DD HH:MM or DD/MM/YYYY HH:MM or DD/MM/YYYY H:MMAM)."
            )

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


def handle_cancellation(session: dict[str, Any], user_input: str | None = None) -> str:
    """
    Cancel a reservation by car plate if reservation start is in the future.
    """
    if not session["cancel_active"]:
        session["cancel_active"] = True
        session["cancel_step"] = "car_plate"
        return "Please provide your car plate number to cancel your reservation."

    if session["cancel_step"] == "car_plate":
        plate = (user_input or "").strip()
        if not plate:
            return "Car plate cannot be empty. Please provide your car plate number."

        success, message = cancel_upcoming_reservation_by_plate(config.DB_PATH, plate)
        session["cancel_active"] = False
        session["cancel_step"] = None
        return message if success else message

    session["cancel_active"] = False
    session["cancel_step"] = None
    return "Cancellation flow was reset. Please try again."


def _guardrails_node(state: ChatState) -> ChatState:
    query = state["query"]

    if contains_sensitive_data(query):
        state["blocked"] = True
        state["response"] = "Request blocked due to sensitive data."
        return state

    if is_blocked_request(query):
        state["blocked"] = True
        state["response"] = "I cannot provide private or internal information."
        return state

    state["blocked"] = False
    return state


def _guardrails_route(state: ChatState) -> str:
    return "blocked" if state["blocked"] else "continue"


def _intent_node(state: ChatState) -> ChatState:
    session = state["session"]
    query = state["query"]

    if session["cancel_active"]:
        state["intent"] = "cancel"
        return state

    if session["reservation_active"]:
        state["intent"] = "reservation"
        return state

    state["intent"] = classify_intent(query)
    return state


def _intent_route(state: ChatState) -> str:
    return state["intent"] or "info"


def _reservation_node(state: ChatState) -> ChatState:
    session = state["session"]
    query = state["query"]

    if session["reservation_active"]:
        state["response"] = handle_reservation(session, query)
    else:
        state["response"] = handle_reservation(session)
    return state


def _info_node(state: ChatState) -> ChatState:
    state["response"] = handle_info(state["query"])
    return state


def _cancel_node(state: ChatState) -> ChatState:
    session = state["session"]
    query = state["query"]

    if session["cancel_active"]:
        state["response"] = handle_cancellation(session, query)
    else:
        state["response"] = handle_cancellation(session)
    return state


def _build_graph():
    graph = StateGraph(ChatState)
    graph.add_node("guardrails", _guardrails_node)
    graph.add_node("intent", _intent_node)
    graph.add_node("reservation", _reservation_node)
    graph.add_node("cancel", _cancel_node)
    graph.add_node("info", _info_node)

    graph.set_entry_point("guardrails")
    graph.add_conditional_edges(
        "guardrails",
        _guardrails_route,
        {
            "blocked": END,
            "continue": "intent",
        },
    )
    graph.add_conditional_edges(
        "intent",
        _intent_route,
        {
            "reservation": "reservation",
            "cancel": "cancel",
            "info": "info",
        },
    )
    graph.add_edge("reservation", END)
    graph.add_edge("cancel", END)
    graph.add_edge("info", END)
    return graph.compile()


CHAT_FLOW_GRAPH = _build_graph()


def route(query: str, session: dict[str, Any]) -> str:
    """
    Main orchestration entrypoint powered by LangGraph.
    """
    session.setdefault("reservation_active", False)
    session.setdefault("step", None)
    session.setdefault("data", {})
    session.setdefault("cancel_active", False)
    session.setdefault("cancel_step", None)

    result = CHAT_FLOW_GRAPH.invoke(
        {
            "query": query,
            "session": session,
            "intent": None,
            "response": "",
            "blocked": False,
        }
    )
    return result["response"]