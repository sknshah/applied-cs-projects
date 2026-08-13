"""
a small menu driven command line interface for the rental system.

this exists to demo the business logic end to end without needing to
stand up a web server. run seed_data.py first to get sample data,
then run this file and log in as one of the seeded accounts.
"""

import sys

import auth
import database
import reports
import service


def login(conn):
    email = input("email: ").strip()
    password = input("password: ").strip()
    member = auth.authenticate(conn, email, password)
    if member is None:
        print("login failed, check your email and password")
        return None
    print(f"welcome, {member.name} ({member.role})")
    return member


def show_available_items(conn):
    items = service.list_available_items(conn)
    if not items:
        print("no items are currently available")
        return
    for item in items:
        print(
            f"  [{item['item_id']}] {item['name']} "
            f"(category: {item['category']}, condition: {item['condition_grade']})"
        )


def handle_checkout(conn, member):
    show_available_items(conn)
    try:
        item_id = int(input("item id to check out: "))
        rental = service.checkout_item(conn, member, item_id)
        print(f"checked out, due back by {rental.due_date}")
    except (service.ItemUnavailableError, ValueError) as error:
        print(f"could not check out item: {error}")


def handle_return(conn, member):
    try:
        rental_id = int(input("rental id being returned: "))
        damaged = input("was the item damaged? (y/n): ").strip().lower() == "y"
        rental = service.return_item(conn, member, rental_id, damage_reported=damaged)
        fee_note = f", late fee: ${rental.late_fee:.2f}" if rental.late_fee else ""
        print(f"return recorded{fee_note}")

        # if someone was waiting on this item, let them know
        waiting_member_id = service.fulfill_next_reservation(conn, rental.item_id)
        if waiting_member_id:
            print(f"member {waiting_member_id} was next in line and has been notified")
    except (service.RentalNotFoundError, PermissionError, ValueError) as error:
        print(f"could not process return: {error}")


def handle_reports(conn, member):
    try:
        overdue = reports.overdue_report(conn, member)
        print(f"\noverdue rentals: {len(overdue)}")
        for row in overdue:
            print(f"  {row['item_name']} rented by {row['member_name']}, due {row['due_date']}")

        utilization = reports.utilization_report(conn, member)
        print("\nutilization by item:")
        for row in utilization:
            print(f"  {row['item_name']}: {row['times_rented']} rentals")

        if member.role == "admin":
            total = reports.revenue_report(conn, member)
            print(f"\ntotal late fee revenue: ${total:.2f}")
    except PermissionError as error:
        print(f"not permitted: {error}")


def main():
    conn = database.connect("rental_system.db")
    database.init_db(conn)

    member = login(conn)
    if member is None:
        sys.exit(1)

    menu = {
        "1": ("browse available items", lambda: show_available_items(conn)),
        "2": ("check out an item", lambda: handle_checkout(conn, member)),
        "3": ("return an item (staff/admin)", lambda: handle_return(conn, member)),
        "4": ("view reports (staff/admin)", lambda: handle_reports(conn, member)),
        "5": ("exit", None),
    }

    while True:
        print("\nwhat would you like to do?")
        for key, (label, _) in menu.items():
            print(f"  {key}. {label}")

        choice = input("> ").strip()
        if choice == "5":
            break

        action = menu.get(choice)
        if action is None:
            print("not a valid choice")
            continue

        _, handler = action
        handler()


if __name__ == "__main__":
    main()
