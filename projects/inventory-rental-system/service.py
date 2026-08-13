"""
core business logic for the rental system.

everything that touches money, due dates, or item availability lives
here so the rules are defined in exactly one place. the cli and any
future api layer should both call into this module rather than
touching the database directly.
"""

import sqlite3
from datetime import datetime, timedelta
from typing import Optional

from auth import require_role
from models import Item, Member, Rental, CATEGORY_RULES


DATE_FORMAT = "%Y-%m-%d"


class ItemUnavailableError(Exception):
    pass


class RentalNotFoundError(Exception):
    pass


def _today() -> str:
    return datetime.now().strftime(DATE_FORMAT)


def _add_days(date_str: str, days: int) -> str:
    date = datetime.strptime(date_str, DATE_FORMAT)
    return (date + timedelta(days=days)).strftime(DATE_FORMAT)


def add_item(
    conn: sqlite3.Connection,
    actor: Member,
    name: str,
    category: str,
    replacement_cost: float,
    condition_grade: str = "A",
) -> Item:
    require_role(actor, "admin")

    cursor = conn.execute(
        "INSERT INTO items (name, category, condition_grade, replacement_cost, status) "
        "VALUES (?, ?, ?, ?, 'available')",
        (name, category, condition_grade, replacement_cost),
    )
    conn.commit()

    return Item(
        item_id=cursor.lastrowid,
        name=name,
        category=category,
        condition_grade=condition_grade,
        replacement_cost=replacement_cost,
        status="available",
    )


def checkout_item(conn: sqlite3.Connection, actor: Member, item_id: int) -> Rental:
    """
    checks an item out to the acting member.

    this uses an immediate transaction so two concurrent checkouts of the
    same item cannot both succeed. sqlite serializes writers, so the
    second caller will block until the first transaction commits, then
    see the updated status and fail cleanly instead of double booking
    the item.
    """
    conn.execute("BEGIN IMMEDIATE")
    try:
        row = conn.execute(
            "SELECT * FROM items WHERE item_id = ?", (item_id,)
        ).fetchone()

        if row is None:
            raise ItemUnavailableError(f"no item with id {item_id}")
        if row["status"] != "available":
            raise ItemUnavailableError(
                f"item '{row['name']}' is not available (status: {row['status']})"
            )

        rules = CATEGORY_RULES.get(row["category"], CATEGORY_RULES["general"])
        checkout_date = _today()
        due_date = _add_days(checkout_date, rules["max_days"])

        cursor = conn.execute(
            "INSERT INTO rentals (item_id, member_id, checkout_date, due_date) "
            "VALUES (?, ?, ?, ?)",
            (item_id, actor.member_id, checkout_date, due_date),
        )
        conn.execute(
            "UPDATE items SET status = 'checked_out' WHERE item_id = ?", (item_id,)
        )
        conn.commit()

        return Rental(
            rental_id=cursor.lastrowid,
            item_id=item_id,
            member_id=actor.member_id,
            checkout_date=checkout_date,
            due_date=due_date,
        )
    except Exception:
        conn.rollback()
        raise


def _compute_late_fee(due_date: str, return_date: str, daily_rate: float, cap: float) -> float:
    due = datetime.strptime(due_date, DATE_FORMAT)
    returned = datetime.strptime(return_date, DATE_FORMAT)
    days_late = (returned - due).days
    if days_late <= 0:
        return 0.0
    fee = days_late * daily_rate
    return min(fee, cap)


def return_item(
    conn: sqlite3.Connection,
    actor: Member,
    rental_id: int,
    damage_reported: bool = False,
    new_condition_grade: Optional[str] = None,
) -> Rental:
    require_role(actor, "staff", "admin")

    conn.execute("BEGIN IMMEDIATE")
    try:
        rental_row = conn.execute(
            "SELECT * FROM rentals WHERE rental_id = ?", (rental_id,)
        ).fetchone()
        if rental_row is None:
            raise RentalNotFoundError(f"no rental with id {rental_id}")
        if rental_row["return_date"] is not None:
            raise ValueError("this rental has already been returned")

        item_row = conn.execute(
            "SELECT * FROM items WHERE item_id = ?", (rental_row["item_id"],)
        ).fetchone()

        rules = CATEGORY_RULES.get(item_row["category"], CATEGORY_RULES["general"])
        return_date = _today()
        late_fee = _compute_late_fee(
            rental_row["due_date"],
            return_date,
            rules["daily_late_fee"],
            item_row["replacement_cost"],
        )

        conn.execute(
            "UPDATE rentals SET return_date = ?, late_fee = ?, damage_reported = ? "
            "WHERE rental_id = ?",
            (return_date, late_fee, int(damage_reported), rental_id),
        )

        # a damaged item goes to maintenance instead of straight back onto
        # the shelf, condition grade is updated if the staff member logged one
        next_status = "maintenance" if damage_reported else "available"
        grade = new_condition_grade if new_condition_grade else item_row["condition_grade"]
        conn.execute(
            "UPDATE items SET status = ?, condition_grade = ? WHERE item_id = ?",
            (next_status, grade, item_row["item_id"]),
        )

        conn.commit()

        rental_row = conn.execute(
            "SELECT * FROM rentals WHERE rental_id = ?", (rental_id,)
        ).fetchone()
        return Rental(
            rental_id=rental_row["rental_id"],
            item_id=rental_row["item_id"],
            member_id=rental_row["member_id"],
            checkout_date=rental_row["checkout_date"],
            due_date=rental_row["due_date"],
            return_date=rental_row["return_date"],
            late_fee=rental_row["late_fee"],
            damage_reported=bool(rental_row["damage_reported"]),
        )
    except Exception:
        conn.rollback()
        raise


def reserve_item(conn: sqlite3.Connection, actor: Member, item_id: int) -> int:
    # reservations are allowed regardless of current status, an item that
    # looks available the moment you check might be gone by the time you
    # act on it, so queuing is always safe
    cursor = conn.execute(
        "INSERT INTO reservations (item_id, member_id, requested_date, status) "
        "VALUES (?, ?, ?, 'waiting')",
        (item_id, actor.member_id, _today()),
    )
    conn.commit()
    return cursor.lastrowid


def fulfill_next_reservation(conn: sqlite3.Connection, item_id: int) -> Optional[int]:
    """
    call this after an item is returned to promote the oldest waiting
    reservation. returns the member_id that should be notified, or none
    if nobody was waiting.
    """
    row = conn.execute(
        "SELECT * FROM reservations WHERE item_id = ? AND status = 'waiting' "
        "ORDER BY requested_date ASC LIMIT 1",
        (item_id,),
    ).fetchone()

    if row is None:
        return None

    conn.execute(
        "UPDATE reservations SET status = 'fulfilled' WHERE reservation_id = ?",
        (row["reservation_id"],),
    )
    conn.commit()
    return row["member_id"]


def list_available_items(conn: sqlite3.Connection, category: Optional[str] = None):
    if category:
        return conn.execute(
            "SELECT * FROM items WHERE status = 'available' AND category = ? "
            "ORDER BY name",
            (category,),
        ).fetchall()
    return conn.execute(
        "SELECT * FROM items WHERE status = 'available' ORDER BY name"
    ).fetchall()
