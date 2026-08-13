"""
unit tests for the business rules in service.py and auth.py.

each test gets a fresh in memory database so tests cannot leak state
into each other, run with: python3 -m unittest tests.py
"""

import unittest

import auth
import database
import service
from models import Member


def make_test_db():
    conn = database.connect(":memory:")
    database.init_db(conn)
    return conn


# incrementing counter so repeated calls in the same test never collide
# on the unique email constraint
_member_counter = 0


def make_member(conn, role="member"):
    global _member_counter
    _member_counter += 1
    email = f"{role}{_member_counter}@test.com"
    created = auth.create_member(conn, f"test {role}", email, "password", role=role)
    return Member(created.member_id, created.name, created.email, role, "", "")


class AuthTests(unittest.TestCase):
    def test_authenticate_succeeds_with_correct_password(self):
        conn = make_test_db()
        auth.create_member(conn, "Ada", "ada@test.com", "correcthorse", role="member")
        member = auth.authenticate(conn, "ada@test.com", "correcthorse")
        self.assertIsNotNone(member)
        self.assertEqual(member.email, "ada@test.com")

    def test_authenticate_fails_with_wrong_password(self):
        conn = make_test_db()
        auth.create_member(conn, "Ada", "ada@test.com", "correcthorse", role="member")
        member = auth.authenticate(conn, "ada@test.com", "wrongpassword")
        self.assertIsNone(member)


class CheckoutTests(unittest.TestCase):
    def test_checkout_marks_item_unavailable(self):
        conn = make_test_db()
        admin = make_member(conn, "admin")
        member = make_member(conn, "member")

        item = service.add_item(conn, admin, "drill", "power_tool", 100.0)
        service.checkout_item(conn, member, item.item_id)

        available = service.list_available_items(conn)
        self.assertEqual(len(available), 0)

    def test_double_checkout_is_rejected(self):
        conn = make_test_db()
        admin = make_member(conn, "admin")
        member_one = make_member(conn, "member")

        item = service.add_item(conn, admin, "camera", "camera", 500.0)
        service.checkout_item(conn, member_one, item.item_id)

        with self.assertRaises(service.ItemUnavailableError):
            service.checkout_item(conn, member_one, item.item_id)

    def test_non_admin_cannot_add_items(self):
        conn = make_test_db()
        member = make_member(conn, "member")

        with self.assertRaises(PermissionError):
            service.add_item(conn, member, "drill", "power_tool", 100.0)


class ReturnTests(unittest.TestCase):
    def test_on_time_return_has_no_late_fee(self):
        conn = make_test_db()
        admin = make_member(conn, "admin")
        staff = make_member(conn, "staff")
        member = make_member(conn, "member")

        item = service.add_item(conn, admin, "saw", "power_tool", 200.0)
        rental = service.checkout_item(conn, member, item.item_id)
        returned = service.return_item(conn, staff, rental.rental_id)

        self.assertEqual(returned.late_fee, 0.0)

    def test_damaged_return_sends_item_to_maintenance(self):
        conn = make_test_db()
        admin = make_member(conn, "admin")
        staff = make_member(conn, "staff")
        member = make_member(conn, "member")

        item = service.add_item(conn, admin, "projector", "av_equipment", 600.0)
        rental = service.checkout_item(conn, member, item.item_id)
        service.return_item(conn, staff, rental.rental_id, damage_reported=True)

        row = conn.execute(
            "SELECT status FROM items WHERE item_id = ?", (item.item_id,)
        ).fetchone()
        self.assertEqual(row["status"], "maintenance")

    def test_member_cannot_process_returns(self):
        conn = make_test_db()
        admin = make_member(conn, "admin")
        member = make_member(conn, "member")

        item = service.add_item(conn, admin, "tripod", "camera", 90.0)
        rental = service.checkout_item(conn, member, item.item_id)

        with self.assertRaises(PermissionError):
            service.return_item(conn, member, rental.rental_id)


class ReservationTests(unittest.TestCase):
    def test_reservation_is_fulfilled_in_order(self):
        conn = make_test_db()
        admin = make_member(conn, "admin")
        staff = make_member(conn, "staff")
        first_member = make_member(conn, "member")
        second_member = make_member(conn, "member")

        item = service.add_item(conn, admin, "drone", "camera", 1500.0)
        rental = service.checkout_item(conn, first_member, item.item_id)

        service.reserve_item(conn, second_member, item.item_id)

        service.return_item(conn, staff, rental.rental_id)
        notified_member_id = service.fulfill_next_reservation(conn, item.item_id)

        self.assertEqual(notified_member_id, second_member.member_id)


if __name__ == "__main__":
    unittest.main()
