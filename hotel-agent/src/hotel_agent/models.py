from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import Optional
import uuid


class RoomStatus(str, Enum):
    VACANT = "vacant"
    OCCUPIED = "occupied"
    DIRTY = "dirty"
    MAINTENANCE = "maintenance"


class BookingStatus(str, Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    CHECKED_IN = "checked_in"
    CHECKED_OUT = "checked_out"
    CANCELLED = "cancelled"


class TaskStatus(str, Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    DONE = "done"


@dataclass
class Room:
    id: str
    number: str
    floor: int
    room_type: str
    status: RoomStatus = RoomStatus.VACANT


@dataclass
class Guest:
    id: str
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None


@dataclass
class Booking:
    id: str
    room_id: str
    guest_id: str
    check_in: date
    check_out: date
    status: BookingStatus = BookingStatus.PENDING


@dataclass
class HousekeepingTask:
    id: str
    room_id: str
    note: str
    status: TaskStatus = TaskStatus.OPEN


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:10]}"
