from __future__ import annotations

from typing import Any, Literal, TypedDict

from langgraph.graph import END, StateGraph

from app.chatbot.router import route
from app.config import get_config
from app.db.repositories import (
    get_reservation_by_id,
    save_reservation,
    update_reservation_status,
)
from app.stage3.mcp_client import send_confirmed_reservation_to_mcp


class Stage4State(TypedDict):
    query: str
    session: dict[str, Any]
    reservation_input: dict[str, str] | None
    reservation_id: int | None
    admin_decision: Literal["confirmed", "rejected"] | None
    chatbot_response: str
    reservation_status: str | None
    recorded_to_mcp: bool
    error: str | None


def _user_interaction_node(state: Stage4State) -> Stage4State:
    state["error"] = None
    query = (state.get("query") or "").strip()
    session = state.get("session") or {}

    if query:
        state["chatbot_response"] = route(query, session)

    reservation_input = state.get("reservation_input")
    if reservation_input:
        rid = save_reservation(
            get_config().DB_PATH,
            reservation_input["first_name"],
            reservation_input["last_name"],
            reservation_input["car_plate"],
            reservation_input["start_datetime"],
            reservation_input["end_datetime"],
        )
        state["reservation_id"] = rid
        state["reservation_status"] = "pending"
    return state


def _admin_approval_node(state: Stage4State) -> Stage4State:
    rid = state.get("reservation_id")
    decision = state.get("admin_decision")
    if rid is None or decision is None:
        state["error"] = "missing reservation_id or admin_decision"
        return state

    ok = update_reservation_status(get_config().DB_PATH, rid, decision)
    if not ok:
        row = get_reservation_by_id(get_config().DB_PATH, rid)
        state["reservation_status"] = row["status"] if row else None
        state["error"] = "reservation not pending or unknown id"
        return state

    row = get_reservation_by_id(get_config().DB_PATH, rid)
    state["reservation_status"] = row["status"] if row else decision
    return state


def _data_recording_node(state: Stage4State) -> Stage4State:
    rid = state.get("reservation_id")
    status = state.get("reservation_status")
    if rid is None or status != "confirmed":
        state["recorded_to_mcp"] = False
        return state

    row = get_reservation_by_id(get_config().DB_PATH, rid)
    if row is None:
        state["recorded_to_mcp"] = False
        state["error"] = "confirmed reservation not found"
        return state
    state["recorded_to_mcp"] = send_confirmed_reservation_to_mcp(row, config=get_config())
    return state


def _route_after_user(state: Stage4State) -> str:
    if state.get("reservation_id") and state.get("admin_decision") in ("confirmed", "rejected"):
        return "admin_approval"
    return "end"


def _route_after_admin(state: Stage4State) -> str:
    if state.get("reservation_status") == "confirmed":
        return "data_recording"
    return "end"


def _build_graph():
    graph = StateGraph(Stage4State)
    graph.add_node("user_interaction", _user_interaction_node)
    graph.add_node("admin_approval", _admin_approval_node)
    graph.add_node("data_recording", _data_recording_node)

    graph.set_entry_point("user_interaction")
    graph.add_conditional_edges(
        "user_interaction",
        _route_after_user,
        {
            "admin_approval": "admin_approval",
            "end": END,
        },
    )
    graph.add_conditional_edges(
        "admin_approval",
        _route_after_admin,
        {
            "data_recording": "data_recording",
            "end": END,
        },
    )
    graph.add_edge("data_recording", END)
    return graph.compile()


STAGE4_GRAPH = _build_graph()


def run_stage4_pipeline(
    *,
    reservation_input: dict[str, str] | None = None,
    admin_decision: Literal["confirmed", "rejected"] | None = None,
    query: str = "",
    session: dict[str, Any] | None = None,
) -> Stage4State:
    return STAGE4_GRAPH.invoke(
        {
            "query": query,
            "session": session or {},
            "reservation_input": reservation_input,
            "reservation_id": None,
            "admin_decision": admin_decision,
            "chatbot_response": "",
            "reservation_status": None,
            "recorded_to_mcp": False,
            "error": None,
        }
    )
