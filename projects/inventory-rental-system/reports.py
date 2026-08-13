"""
read only reporting queries for staff and admin users.

kept separate from service.py because reports are queries, not
state changing business operations, and it is worth being able to
reason about the two categories independently.
"""

import sqlite3
from datetime import datetime

from auth import require_role
from models import Member


def overdue_report(conn: sqlite3.Connection, actor: Member):
    require_role(actor, "staff", "admin")

    today = datetime.now().strftime("%Y-%m-%d")
    return conn.execute(
        """
        SELECT rentals.rental_id, items.name AS item_name, members.name AS member_name,
               rentals.due_date
        FROM rentals
        JOIN items ON items.item_id = rentals.item_id
        JOIN members ON members.member_id = rentals.member_id
        WHERE rentals.return_date IS NULL AND rentals.due_date < ?
        ORDER BY rentals.due_date ASC
        """,
        (today,),
    ).fetchall()


def utilization_report(conn: sqlite3.Connection, actor: Member):
    require_role(actor, "staff", "admin")

    return conn.execute(
        """
        SELECT items.name AS item_name, COUNT(rentals.rental_id) AS times_rented
        FROM items
        LEFT JOIN rentals ON rentals.item_id = items.item_id
        GROUP BY items.item_id
        ORDER BY times_rented DESC
        """
    ).fetchall()


def revenue_report(conn: sqlite3.Connection, actor: Member):
    require_role(actor, "admin")

    row = conn.execute(
        "SELECT COALESCE(SUM(late_fee), 0) AS total_late_fees FROM rentals"
    ).fetchone()
    return row["total_late_fees"]
