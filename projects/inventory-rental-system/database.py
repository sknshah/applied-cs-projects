"""
schema creation and connection handling.

uses plain sqlite3 from the standard library on purpose, no orm and no
external driver, so the project runs anywhere with just python installed.
"""

import sqlite3


SCHEMA = """
CREATE TABLE IF NOT EXISTS items (
    item_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    category TEXT NOT NULL,
    condition_grade TEXT NOT NULL DEFAULT 'A',
    replacement_cost REAL NOT NULL,
    status TEXT NOT NULL DEFAULT 'available'
);

CREATE TABLE IF NOT EXISTS members (
    member_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    role TEXT NOT NULL DEFAULT 'member',
    password_hash TEXT NOT NULL,
    password_salt TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS rentals (
    rental_id INTEGER PRIMARY KEY AUTOINCREMENT,
    item_id INTEGER NOT NULL REFERENCES items(item_id),
    member_id INTEGER NOT NULL REFERENCES members(member_id),
    checkout_date TEXT NOT NULL,
    due_date TEXT NOT NULL,
    return_date TEXT,
    late_fee REAL,
    damage_reported INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS reservations (
    reservation_id INTEGER PRIMARY KEY AUTOINCREMENT,
    item_id INTEGER NOT NULL REFERENCES items(item_id),
    member_id INTEGER NOT NULL REFERENCES members(member_id),
    requested_date TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'waiting'
);

CREATE INDEX IF NOT EXISTS idx_rentals_item ON rentals(item_id);
CREATE INDEX IF NOT EXISTS idx_rentals_open ON rentals(item_id, return_date);
CREATE INDEX IF NOT EXISTS idx_reservations_item ON reservations(item_id, status);
"""


def connect(db_path: str = "rental_system.db") -> sqlite3.Connection:
    # check_same_thread=False keeps this simple for the demo cli, a real
    # multi-user deployment would use a connection pool instead
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    # foreign keys are off by default in sqlite, turn them on explicitly
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA)
    conn.commit()
