from __future__ import annotations

from datetime import datetime, time, timedelta
from pathlib import Path
import re
from typing import Any, Literal, TypedDict

from langgraph.graph import END, StateGraph

from app.config import get_config
from app.db.connection import get_connection
from app.db.repositories import (
    cancel_upcoming_reservation_by_plate,
    count_active_reservations_overlapping,
    find_first_available_slot,
    get_concurrent_capacity,
    has_overlapping_active_reservation,
    save_reservation,
)
from app.notifications.telegram import notify_admin_new_reservation
from app.guardrails.filter import contains_sensitive_data, is_blocked_request
from app.rag.retriever import retrieve


config = get_config()


SUPPORTED_DATETIME_FORMATS = (
    "%Y-%m-%d %H:%M",
    "%d/%m/%Y %H:%M",
    "%d/%m/%Y %I:%M%p",
    "%d/%m/%Y %I:%M %p",
)
TIME_ONLY_FORMATS = ("%H:%M", "%H")

FLOW_ABORT_KEYWORDS = {
    "stop",
    "refresh",
    "reset",
    "abort",
    "quit",
    "back",
    "start over",
    "cancel",
    "cancel operation",
    "cancel current operation",
}


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
    q = query.lower().strip()

    cancel_keywords = [
        "cancel reservation",
        "cancel booking",
        "cancel my booking",
        "cancel my reservation",
        "cancel operation",
        "cancel current operation",
    ]
    if q == "cancel" or any(keyword in q for keyword in cancel_keywords):
        return "cancel"

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

    if _looks_like_availability_question(q):
        requested_dt = _extract_availability_datetime(query)
        if requested_dt is not None:
            return _get_availability_for_datetime(config.DB_PATH, requested_dt)
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
        content = _drop_trailing_header_only_line(doc["page_content"])
        if content:
            top_chunks.append(content)

    if not top_chunks:
        return "Sorry, I couldn't find relevant information."

    return "Here is the relevant information I found:\n\n" + "\n\n".join(top_chunks)


def _drop_trailing_header_only_line(content: str) -> str:
    """
    Remove a dangling markdown header at the end of chunk.
    This avoids responses ending with '## Question...' without answer.
    """
    lines = [line for line in content.strip().splitlines()]
    while lines and lines[-1].strip() == "":
        lines.pop()
    if lines and lines[-1].lstrip().startswith("##"):
        lines.pop()
    return "\n".join(lines).strip()


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


def _looks_like_availability_question(q: str) -> bool:
    """
    Detect questions about free capacity / spots (not static FAQ about total capacity only).
    """
    if any(
        phrase in q
        for phrase in (
            "available",
            "availability",
            "free space",
            "free spaces",
            "free place",
            "free places",
            "free spot",
            "free spots",
            "any space",
            "any spaces",
            "any place",
            "any places",
            "spaces left",
            "spots left",
            "place left",
            "places left",
            "room to park",
        )
    ):
        return True
    if re.search(r"\b(do you have|is there|are there)\b.+\b(free|available)\b", q):
        return True
    return False


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


def _normalize_availability_query_text(query: str) -> str:
    text = " ".join(query.lower().strip().split())
    for wrong, fixed in (("tommorow", "tomorrow"), ("tommorrow", "tomorrow")):
        text = text.replace(wrong, fixed)
    return text


def _parse_clock_with_am_pm(text: str) -> tuple[int, int] | None:
    """
    Parse times like 1:00 PM, 1.00 PM, 1 PM into 24h (hour, minute).
    """
    m = re.search(r"\b(\d{1,2})(?:[:.](\d{2}))?\s*(am|pm)\b", text)
    if not m:
        return None
    hour = int(m.group(1))
    minute = int(m.group(2) or 0)
    ampm = m.group(3)
    if ampm == "pm":
        if hour != 12:
            hour += 12
    else:
        if hour == 12:
            hour = 0
    if hour > 23 or minute > 59:
        return None
    return hour, minute


def _extract_availability_datetime(query: str) -> datetime | None:
    normalized = _normalize_availability_query_text(query)
    now = datetime.now()
    base_date = now.date()

    if "tomorrow" in normalized:
        base_date = (now + timedelta(days=1)).date()
    elif "today" in normalized:
        base_date = now.date()

    datetime_match = re.search(r"\b(\d{4}-\d{2}-\d{2}\s+\d{1,2}:\d{2})\b", normalized)
    if datetime_match:
        dt = _normalize_datetime_input(datetime_match.group(1))
        if dt:
            return datetime.strptime(dt, "%Y-%m-%d %H:%M")

    date_time_match = re.search(
        r"\b(\d{1,2}/\d{1,2}/\d{4}\s+\d{1,2}(?::\d{2})?\s*(?:am|pm)?)\b",
        normalized,
    )
    if date_time_match:
        dt = _normalize_datetime_input(date_time_match.group(1))
        if dt:
            return datetime.strptime(dt, "%Y-%m-%d %H:%M")

    am_pm = _parse_clock_with_am_pm(normalized)
    if am_pm is not None:
        hour, minute = am_pm
        return datetime.combine(base_date, time(hour=hour, minute=minute))

    time_match = re.search(
        r"\b(?:at|,)\s*(\d{1,2}(?::\d{2})?)\b(?!\s*(?:am|pm)\b)",
        normalized,
    )
    if not time_match:
        time_match = re.search(r"\b(\d{1,2}(?::\d{2})?)\b", normalized)

    if not time_match:
        return None

    raw_time = time_match.group(1)
    parsed_time = None
    for fmt in TIME_ONLY_FORMATS:
        try:
            parsed_time = datetime.strptime(raw_time, fmt).time()
            break
        except ValueError:
            continue
    if parsed_time is None:
        return None

    return datetime.combine(base_date, parsed_time).replace(second=0, microsecond=0)


def _get_availability_for_datetime(db_path: Path, target_dt: datetime) -> str:
    start = target_dt.replace(second=0, microsecond=0)
    end = start + timedelta(hours=1)
    start_str = start.strftime("%Y-%m-%d %H:%M")
    end_str = end.strftime("%Y-%m-%d %H:%M")

    capacity = get_concurrent_capacity(db_path)
    if capacity <= 0:
        return "Availability check is temporarily unavailable because parking capacity is not configured."

    overlapping = count_active_reservations_overlapping(db_path, start_str, end_str)
    free_spaces = max(0, capacity - overlapping)
    if free_spaces > 0:
        return f"Yes, there are free spaces at {start_str}. Estimated free spaces: {free_spaces}."

    suggestion = find_first_available_slot(
        db_path,
        start_str,
        end_str,
        step_minutes=config.PARKING_SLOT_STEP_MINUTES,
        max_search_days=config.PARKING_SLOT_SEARCH_MAX_DAYS,
    )
    if suggestion:
        suggested_start, suggested_end = suggestion
        return (
            f"No free spaces are available at {start_str}. "
            f"The first available 1-hour slot is {suggested_start} to {suggested_end}."
        )

    return (
        f"No free spaces are available at {start_str}, and no 1-hour alternative slot was found "
        f"within the next {config.PARKING_SLOT_SEARCH_MAX_DAYS} days."
    )


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
        return (
            "Let's start your reservation. Please provide your first name. "
            "You can type 'stop', 'quit', 'back', or 'start over' to cancel current operation."
        )

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

        capacity = get_concurrent_capacity(config.DB_PATH)
        overlapping = count_active_reservations_overlapping(
            config.DB_PATH,
            session["data"]["start_datetime"],
            normalized_end,
        )
        if capacity <= 0:
            session["data"].pop("start_datetime", None)
            session["data"].pop("end_datetime", None)
            session["step"] = "start_datetime"
            return (
                "Parking capacity is not configured. Please contact support. "
                "Enter a new reservation start date and time when resolved "
                "(format: YYYY-MM-DD HH:MM or DD/MM/YYYY HH:MM or DD/MM/YYYY H:MMAM)."
            )

        if overlapping >= capacity:
            suggested = find_first_available_slot(
                config.DB_PATH,
                session["data"]["start_datetime"],
                normalized_end,
                step_minutes=config.PARKING_SLOT_STEP_MINUTES,
                max_search_days=config.PARKING_SLOT_SEARCH_MAX_DAYS,
            )
            session["data"].pop("start_datetime", None)
            session["data"].pop("end_datetime", None)
            session["step"] = "start_datetime"
            if suggested:
                s_start, s_end = suggested
                return (
                    "No parking spaces are available for that time. "
                    f"The next available slot with the same duration is: {s_start} to {s_end}. "
                    "Please enter a new reservation start date and time "
                    "(you can use the suggested start time). "
                    "Formats: YYYY-MM-DD HH:MM or DD/MM/YYYY HH:MM or DD/MM/YYYY H:MMAM."
                )
            return (
                "No parking spaces are available for that time, and no alternative slot was found "
                f"within the next {config.PARKING_SLOT_SEARCH_MAX_DAYS} days. "
                "Please try different dates. "
                "Formats: YYYY-MM-DD HH:MM or DD/MM/YYYY HH:MM or DD/MM/YYYY H:MMAM."
            )

        new_id = save_reservation(
            db_path=config.DB_PATH,
            first_name=session["data"]["first_name"],
            last_name=session["data"]["last_name"],
            car_plate=session["data"]["car_plate"],
            start_datetime=session["data"]["start_datetime"],
            end_datetime=session["data"]["end_datetime"],
        )
        notify_admin_new_reservation(
            new_id,
            session["data"]["first_name"],
            session["data"]["last_name"],
            session["data"]["car_plate"],
            session["data"]["start_datetime"],
            session["data"]["end_datetime"],
            config=config,
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
        return (
            "Please provide your car plate number to cancel your reservation. "
            "You can type 'stop', 'quit', 'back', or 'start over' to cancel current operation."
        )

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


def _is_abort_flow_command(query: str) -> bool:
    normalized = " ".join(query.lower().strip().split())
    return normalized in FLOW_ABORT_KEYWORDS


def _reset_active_flows(session: dict[str, Any]) -> None:
    session["reservation_active"] = False
    session["step"] = None
    session["data"] = {}
    session["cancel_active"] = False
    session["cancel_step"] = None


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

    if (session["reservation_active"] or session["cancel_active"]) and _is_abort_flow_command(query):
        _reset_active_flows(session)
        return "Current operation has been cancelled. You can enter a new request."

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