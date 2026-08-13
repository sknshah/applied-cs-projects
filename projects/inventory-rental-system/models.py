"""
data model definitions and business rule constants for the rental system.

these are plain dataclasses, not orm models. the database module is
responsible for turning rows into these objects and back.
"""

from dataclasses import dataclass
from typing import Optional


# business rules per item category: how long an item can be checked out
# before it is late, and the daily late fee once it is.
CATEGORY_RULES = {
    "camera": {"max_days": 3, "daily_late_fee": 5.00},
    "power_tool": {"max_days": 7, "daily_late_fee": 3.00},
    "av_equipment": {"max_days": 2, "daily_late_fee": 8.00},
    "general": {"max_days": 5, "daily_late_fee": 2.00},
}

ITEM_STATUSES = ("available", "checked_out", "maintenance")
CONDITION_GRADES = ("A", "B", "C", "D")
MEMBER_ROLES = ("member", "staff", "admin")
RESERVATION_STATUSES = ("waiting", "fulfilled", "cancelled")


@dataclass
class Item:
    item_id: Optional[int]
    name: str
    category: str
    condition_grade: str
    replacement_cost: float
    status: str = "available"

    def category_rules(self) -> dict:
        # fall back to the general rule set if the category is unrecognized
        return CATEGORY_RULES.get(self.category, CATEGORY_RULES["general"])


@dataclass
class Member:
    member_id: Optional[int]
    name: str
    email: str
    role: str
    password_hash: str
    password_salt: str


@dataclass
class Rental:
    rental_id: Optional[int]
    item_id: int
    member_id: int
    checkout_date: str
    due_date: str
    return_date: Optional[str] = None
    late_fee: Optional[float] = None
    damage_reported: bool = False


@dataclass
class Reservation:
    reservation_id: Optional[int]
    item_id: int
    member_id: int
    requested_date: str
    status: str = "waiting"
