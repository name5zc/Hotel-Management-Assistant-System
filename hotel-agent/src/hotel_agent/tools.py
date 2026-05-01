from __future__ import annotations

import json
from datetime import date
from typing import Any, Callable, Dict, List

from .rag import search_policy
from .store import HotelStore


def _parse_date(s: str) -> date:
    y, m, d = (int(x) for x in s.split("-", 2))
    return date(y, m, d)


def tool_list_rooms(store: HotelStore, arguments: Dict[str, Any]) -> str:
    status = arguments.get("status")
    rooms = store.list_rooms(status=status)
    payload = [
        {
            "id": r.id,
            "number": r.number,
            "floor": r.floor,
            "room_type": r.room_type,
            "status": r.status.value,
        }
        for r in rooms
    ]
    return json.dumps({"rooms": payload}, ensure_ascii=False)


def tool_create_room(store: HotelStore, arguments: Dict[str, Any]) -> str:
    r = store.create_room(
        number=arguments["number"],
        floor=int(arguments["floor"]),
        room_type=arguments["room_type"],
        status=arguments.get("status", "vacant"),
    )
    return json.dumps(
        {
            "room_id": r.id,
            "number": r.number,
            "floor": r.floor,
            "room_type": r.room_type,
            "status": r.status.value,
        },
        ensure_ascii=False,
    )


def tool_register_guest(store: HotelStore, arguments: Dict[str, Any]) -> str:
    g = store.register_guest(
        name=arguments["name"],
        email=arguments.get("email"),
        phone=arguments.get("phone"),
    )
    return json.dumps(
        {"guest_id": g.id, "name": g.name, "email": g.email, "phone": g.phone},
        ensure_ascii=False,
    )


def tool_create_booking(store: HotelStore, arguments: Dict[str, Any]) -> str:
    b = store.create_booking(
        room_id=arguments["room_id"],
        guest_id=arguments["guest_id"],
        check_in=_parse_date(arguments["check_in"]),
        check_out=_parse_date(arguments["check_out"]),
    )
    return json.dumps(
        {
            "booking_id": b.id,
            "room_id": b.room_id,
            "guest_id": b.guest_id,
            "check_in": b.check_in.isoformat(),
            "check_out": b.check_out.isoformat(),
            "status": b.status.value,
        },
        ensure_ascii=False,
    )


def tool_check_in(store: HotelStore, arguments: Dict[str, Any]) -> str:
    b = store.check_in(arguments["booking_id"])
    return json.dumps({"booking_id": b.id, "status": b.status.value}, ensure_ascii=False)


def tool_check_out(store: HotelStore, arguments: Dict[str, Any]) -> str:
    b = store.check_out(arguments["booking_id"])
    return json.dumps({"booking_id": b.id, "status": b.status.value}, ensure_ascii=False)


def tool_set_room_status(store: HotelStore, arguments: Dict[str, Any]) -> str:
    r = store.set_room_status(arguments["room_id"], arguments["status"])
    return json.dumps({"room_id": r.id, "status": r.status.value}, ensure_ascii=False)


def tool_create_housekeeping_task(store: HotelStore, arguments: Dict[str, Any]) -> str:
    t = store.create_housekeeping_task(arguments["room_id"], arguments["note"])
    return json.dumps({"task_id": t.id, "room_id": t.room_id, "note": t.note}, ensure_ascii=False)


def tool_list_open_tasks(store: HotelStore, arguments: Dict[str, Any]) -> str:
    tasks = store.list_open_tasks()
    return json.dumps(
        {
            "tasks": [
                {
                    "task_id": t.id,
                    "room_id": t.room_id,
                    "note": t.note,
                    "status": t.status.value,
                }
                for t in tasks
            ]
        },
        ensure_ascii=False,
    )


def tool_complete_housekeeping_task(store: HotelStore, arguments: Dict[str, Any]) -> str:
    t = store.complete_task(arguments["task_id"])
    return json.dumps({"task_id": t.id, "status": t.status.value}, ensure_ascii=False)


def tool_search_policy(store: HotelStore, arguments: Dict[str, Any]) -> str:
    query = arguments["query"]
    top_k = int(arguments.get("top_k", 3))
    result = search_policy(query=query, top_k=top_k)
    return json.dumps(result, ensure_ascii=False)


TOOL_SPECS: List[Dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "list_rooms",
            "description": "List hotel rooms, optionally filtered by status (vacant, occupied, dirty, maintenance).",
            "parameters": {
                "type": "object",
                "properties": {
                    "status": {
                        "type": "string",
                        "enum": ["vacant", "occupied", "dirty", "maintenance"],
                    }
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_room",
            "description": "Create a new room in the hotel inventory.",
            "parameters": {
                "type": "object",
                "required": ["number", "floor", "room_type"],
                "properties": {
                    "number": {"type": "string", "description": "Room number, e.g. 301"},
                    "floor": {"type": "integer"},
                    "room_type": {"type": "string", "description": "e.g. standard/deluxe/suite"},
                    "status": {
                        "type": "string",
                        "enum": ["vacant", "occupied", "dirty", "maintenance"],
                    },
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_policy",
            "description": "Search hotel SOP/policy knowledge base and return evidence snippets.",
            "parameters": {
                "type": "object",
                "required": ["query"],
                "properties": {
                    "query": {"type": "string", "description": "Question to search in policy docs"},
                    "top_k": {"type": "integer", "minimum": 1, "maximum": 8},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "register_guest",
            "description": "Register a new guest and return guest_id.",
            "parameters": {
                "type": "object",
                "required": ["name"],
                "properties": {
                    "name": {"type": "string"},
                    "email": {"type": "string"},
                    "phone": {"type": "string"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_booking",
            "description": "Create a confirmed booking for a room and guest. Dates YYYY-MM-DD.",
            "parameters": {
                "type": "object",
                "required": ["room_id", "guest_id", "check_in", "check_out"],
                "properties": {
                    "room_id": {"type": "string"},
                    "guest_id": {"type": "string"},
                    "check_in": {"type": "string"},
                    "check_out": {"type": "string"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "check_in",
            "description": "Check in a booking by booking_id.",
            "parameters": {
                "type": "object",
                "required": ["booking_id"],
                "properties": {"booking_id": {"type": "string"}},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "check_out",
            "description": "Check out a booking; room becomes dirty until housekeeping.",
            "parameters": {
                "type": "object",
                "required": ["booking_id"],
                "properties": {"booking_id": {"type": "string"}},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "set_room_status",
            "description": "Set operational room status (e.g. maintenance).",
            "parameters": {
                "type": "object",
                "required": ["room_id", "status"],
                "properties": {
                    "room_id": {"type": "string"},
                    "status": {
                        "type": "string",
                        "enum": ["vacant", "occupied", "dirty", "maintenance"],
                    },
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_housekeeping_task",
            "description": "Create a housekeeping task for a room.",
            "parameters": {
                "type": "object",
                "required": ["room_id", "note"],
                "properties": {
                    "room_id": {"type": "string"},
                    "note": {"type": "string"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_open_tasks",
            "description": "List housekeeping tasks that are not done.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "complete_housekeeping_task",
            "description": "Mark a housekeeping task done; may set room to vacant if it was dirty.",
            "parameters": {
                "type": "object",
                "required": ["task_id"],
                "properties": {"task_id": {"type": "string"}},
            },
        },
    },
]

_TOOL_HANDLERS: Dict[str, Callable[[HotelStore, Dict[str, Any]], str]] = {
    "list_rooms": tool_list_rooms,
    "create_room": tool_create_room,
    "search_policy": tool_search_policy,
    "register_guest": tool_register_guest,
    "create_booking": tool_create_booking,
    "check_in": tool_check_in,
    "check_out": tool_check_out,
    "set_room_status": tool_set_room_status,
    "create_housekeeping_task": tool_create_housekeeping_task,
    "list_open_tasks": tool_list_open_tasks,
    "complete_housekeeping_task": tool_complete_housekeeping_task,
}


def run_tool(store: HotelStore, name: str, arguments_json: str) -> str:
    handler = _TOOL_HANDLERS.get(name)
    if not handler:
        return json.dumps({"error": f"unknown tool: {name}"})
    try:
        args: Dict[str, Any] = json.loads(arguments_json or "{}")
    except json.JSONDecodeError as e:
        return json.dumps({"error": f"invalid json: {e}"})
    try:
        return handler(store, args)
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)
