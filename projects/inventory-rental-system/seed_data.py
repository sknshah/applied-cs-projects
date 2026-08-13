"""
populates a fresh database with sample members and items so the cli
has something to demo against right away.
"""

import database
import auth
import service
from models import Member


def seed(conn) -> None:
    admin = auth.create_member(conn, "Ada Admin", "ada@example.com", "adminpass", role="admin")
    staff = auth.create_member(conn, "Sam Staff", "sam@example.com", "staffpass", role="staff")
    auth.create_member(conn, "Mia Member", "mia@example.com", "memberpass", role="member")
    auth.create_member(conn, "Leo Member", "leo@example.com", "memberpass", role="member")

    admin_member = Member(admin.member_id, admin.name, admin.email, "admin", "", "")

    service.add_item(conn, admin_member, "Canon R6 camera", "camera", 2200.00)
    service.add_item(conn, admin_member, "Cordless drill", "power_tool", 150.00)
    service.add_item(conn, admin_member, "Portable projector", "av_equipment", 600.00)
    service.add_item(conn, admin_member, "Tripod", "camera", 90.00)
    service.add_item(conn, admin_member, "Circular saw", "power_tool", 220.00)


if __name__ == "__main__":
    conn = database.connect("rental_system.db")
    database.init_db(conn)
    seed(conn)
    print("seeded rental_system.db with sample members and items")
    print("admin login: ada@example.com / adminpass")
    print("staff login: sam@example.com / staffpass")
    print("member login: mia@example.com / memberpass")
