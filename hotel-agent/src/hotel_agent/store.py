from __future__ import annotations

import json
from pathlib import Path
from datetime import date, timedelta
from typing import Dict, List, Optional

from .models import (
    Booking,
    BookingStatus,
    Guest,
    HousekeepingTask,
    Room,
    RoomStatus,
    TaskStatus,
    new_id,
)


class HotelStore:
    """Hotel data store with optional JSON persistence."""

    def __init__(self, data_path: Optional[str] = None) -> None:
        self.data_path = Path(data_path).expanduser().resolve() if data_path else None
        self.rooms: Dict[str, Room] = {}
        self.guests: Dict[str, Guest] = {}
        self.bookings: Dict[str, Booking] = {}
        self.tasks: Dict[str, HousekeepingTask] = {}

    def _save_if_needed(self) -> None:
        if self.data_path:
            self.save()

    def _is_single_file(self) -> bool:
        return bool(self.data_path and self.data_path.suffix.lower() == ".json")

    def _data_file_paths(self) -> Dict[str, Path]:
        if not self.data_path:
            return {}
        if self._is_single_file():
            return {"single": self.data_path}
        return {
            "rooms": self.data_path / "rooms.json",
            "guests": self.data_path / "guests.json",
            "bookings": self.data_path / "bookings.json",
            "tasks": self.data_path / "tasks.json",
        }

    def _serialize_rooms(self) -> List[dict]:
        return [
            {
                "id": r.id,
                "number": r.number,
                "floor": r.floor,
                "room_type": r.room_type,
                "status": r.status.value,
            }
            for r in self.rooms.values()
        ]

    def _serialize_guests(self) -> List[dict]:
        return [
            {
                "id": g.id,
                "name": g.name,
                "email": g.email,
                "phone": g.phone,
            }
            for g in self.guests.values()
        ]

    def _serialize_bookings(self) -> List[dict]:
        return [
            {
                "id": b.id,
                "room_id": b.room_id,
                "guest_id": b.guest_id,
                "check_in": b.check_in.isoformat(),
                "check_out": b.check_out.isoformat(),
                "status": b.status.value,
            }
            for b in self.bookings.values()
        ]

    def _serialize_tasks(self) -> List[dict]:
        return [
            {
                "id": t.id,
                "room_id": t.room_id,
                "note": t.note,
                "status": t.status.value,
            }
            for t in self.tasks.values()
        ]

    def _hydrate_from_payload(self, payload: Dict[str, List[dict]]) -> None:
        self.rooms = {
            r["id"]: Room(
                id=r["id"],
                number=r["number"],
                floor=int(r["floor"]),
                room_type=r["room_type"],
                status=RoomStatus(r["status"]),
            )
            for r in payload.get("rooms", [])
        }
        self.guests = {
            g["id"]: Guest(
                id=g["id"],
                name=g["name"],
                email=g.get("email"),
                phone=g.get("phone"),
            )
            for g in payload.get("guests", [])
        }
        self.bookings = {
            b["id"]: Booking(
                id=b["id"],
                room_id=b["room_id"],
                guest_id=b["guest_id"],
                check_in=date.fromisoformat(b["check_in"]),
                check_out=date.fromisoformat(b["check_out"]),
                status=BookingStatus(b["status"]),
            )
            for b in payload.get("bookings", [])
        }
        self.tasks = {
            t["id"]: HousekeepingTask(
                id=t["id"],
                room_id=t["room_id"],
                note=t["note"],
                status=TaskStatus(t["status"]),
            )
            for t in payload.get("tasks", [])
        }

    def load(self) -> bool:
        if not self.data_path:
            return False
        files = self._data_file_paths()

        if self._is_single_file():
            single = files["single"]
            if not single.exists():
                return False
            payload = json.loads(single.read_text(encoding="utf-8"))
            self._hydrate_from_payload(payload)
            return True

        rooms_f = files["rooms"]
        guests_f = files["guests"]
        bookings_f = files["bookings"]
        tasks_f = files["tasks"]
        if not (rooms_f.exists() and guests_f.exists() and bookings_f.exists() and tasks_f.exists()):
            return False
        payload = {
            "rooms": json.loads(rooms_f.read_text(encoding="utf-8")),
            "guests": json.loads(guests_f.read_text(encoding="utf-8")),
            "bookings": json.loads(bookings_f.read_text(encoding="utf-8")),
            "tasks": json.loads(tasks_f.read_text(encoding="utf-8")),
        }
        self._hydrate_from_payload(payload)
        return True

    def save(self) -> None:
        if not self.data_path:
            return
        files = self._data_file_paths()
        if self._is_single_file():
            single = files["single"]
            single.parent.mkdir(parents=True, exist_ok=True)
            payload = {
                "rooms": self._serialize_rooms(),
                "guests": self._serialize_guests(),
                "bookings": self._serialize_bookings(),
                "tasks": self._serialize_tasks(),
            }
            single.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
            return

        self.data_path.mkdir(parents=True, exist_ok=True)
        files["rooms"].write_text(json.dumps(self._serialize_rooms(), ensure_ascii=False, indent=2), encoding="utf-8")
        files["guests"].write_text(json.dumps(self._serialize_guests(), ensure_ascii=False, indent=2), encoding="utf-8")
        files["bookings"].write_text(
            json.dumps(self._serialize_bookings(), ensure_ascii=False, indent=2), encoding="utf-8"
        )
        files["tasks"].write_text(json.dumps(self._serialize_tasks(), ensure_ascii=False, indent=2), encoding="utf-8")

    def load_or_seed_demo(self) -> None:
        if self.load():
            return
        self.seed_demo()

    def seed_demo(self) -> None:
        if self.rooms:
            return
        for i, (num, floor, rtype) in enumerate(
            [
                ("101", 1, "standard"),
                ("102", 1, "standard"),
                ("201", 2, "deluxe"),
                ("202", 2, "suite"),
            ],
            start=1,
        ):
            rid = f"room_{i}"
            self.rooms[rid] = Room(id=rid, number=num, floor=floor, room_type=rtype)
        gid = new_id("guest")
        self.guests[gid] = Guest(id=gid, name="Demo Guest", email="demo@example.com")
        room_ids = list(self.rooms.keys())
        bid = new_id("book")
        cin = date.today()
        self.bookings[bid] = Booking(
            id=bid,
            room_id=room_ids[0],
            guest_id=gid,
            check_in=cin,
            check_out=cin + timedelta(days=2),
            status=BookingStatus.CONFIRMED,
        )
        self.rooms[room_ids[0]].status = RoomStatus.OCCUPIED
        self._save_if_needed()

    def list_rooms(self, status: Optional[str] = None) -> List[Room]:
        rooms = list(self.rooms.values())
        if status:
            rs = RoomStatus(status)
            rooms = [r for r in rooms if r.status == rs]
        return sorted(rooms, key=lambda r: r.number)

    def get_room(self, room_id: str) -> Optional[Room]:
        return self.rooms.get(room_id)

    def create_room(
        self,
        number: str,
        floor: int,
        room_type: str,
        status: str = "vacant",
    ) -> Room:
        if any(r.number == number for r in self.rooms.values()):
            raise ValueError("room number already exists")
        rid = new_id("room")
        room = Room(
            id=rid,
            number=number,
            floor=floor,
            room_type=room_type,
            status=RoomStatus(status),
        )
        self.rooms[rid] = room
        self._save_if_needed()
        return room

    def set_room_status(self, room_id: str, status: str) -> Room:
        room = self.rooms[room_id]
        room.status = RoomStatus(status)
        self._save_if_needed()
        return room

    def register_guest(self, name: str, email: Optional[str], phone: Optional[str]) -> Guest:
        gid = new_id("guest")
        g = Guest(id=gid, name=name, email=email, phone=phone)
        self.guests[gid] = g
        self._save_if_needed()
        return g

    def create_booking(
        self,
        room_id: str,
        guest_id: str,
        check_in: date,
        check_out: date,
    ) -> Booking:
        if check_out <= check_in:
            raise ValueError("check_out must be after check_in")
        room = self.rooms[room_id]
        if room.status == RoomStatus.MAINTENANCE:
            raise ValueError("room is in maintenance")
        if guest_id not in self.guests:
            raise ValueError("unknown guest_id")
        bid = new_id("book")
        b = Booking(
            id=bid,
            room_id=room_id,
            guest_id=guest_id,
            check_in=check_in,
            check_out=check_out,
            status=BookingStatus.CONFIRMED,
        )
        self.bookings[bid] = b
        self._save_if_needed()
        return b

    def get_booking(self, booking_id: str) -> Optional[Booking]:
        return self.bookings.get(booking_id)

    def list_bookings_for_room(self, room_id: str) -> List[Booking]:
        return [b for b in self.bookings.values() if b.room_id == room_id]

    def check_in(self, booking_id: str) -> Booking:
        b = self.bookings[booking_id]
        if b.status not in (BookingStatus.CONFIRMED, BookingStatus.PENDING):
            raise ValueError("invalid booking status for check-in")
        b.status = BookingStatus.CHECKED_IN
        self.rooms[b.room_id].status = RoomStatus.OCCUPIED
        self._save_if_needed()
        return b

    def check_out(self, booking_id: str) -> Booking:
        b = self.bookings[booking_id]
        if b.status != BookingStatus.CHECKED_IN:
            raise ValueError("guest must be checked in")
        b.status = BookingStatus.CHECKED_OUT
        self.rooms[b.room_id].status = RoomStatus.DIRTY
        self._save_if_needed()
        return b

    def create_housekeeping_task(self, room_id: str, note: str) -> HousekeepingTask:
        if room_id not in self.rooms:
            raise ValueError("unknown room_id")
        tid = new_id("task")
        t = HousekeepingTask(id=tid, room_id=room_id, note=note)
        self.tasks[tid] = t
        self._save_if_needed()
        return t

    def complete_task(self, task_id: str) -> HousekeepingTask:
        t = self.tasks[task_id]
        t.status = TaskStatus.DONE
        room = self.rooms[t.room_id]
        if room.status == RoomStatus.DIRTY:
            room.status = RoomStatus.VACANT
        self._save_if_needed()
        return t

    def list_open_tasks(self) -> List[HousekeepingTask]:
        return [t for t in self.tasks.values() if t.status != TaskStatus.DONE]
