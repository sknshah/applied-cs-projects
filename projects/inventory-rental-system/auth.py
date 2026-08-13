"""
minimal password hashing and authentication helpers.

this is good enough for a portfolio demo, it is not a production auth
system. a real deployment would use a vetted library like bcrypt or
argon2 instead of hand rolled sha256 hashing.
"""

import hashlib
import os
import sqlite3
from typing import Optional

from models import Member, MEMBER_ROLES


def _hash_password(password: str, salt: str) -> str:
    # combine password and salt before hashing so identical passwords do
    # not produce identical hashes across accounts
    combined = (salt + password).encode("utf-8")
    return hashlib.sha256(combined).hexdigest()


def create_member(
    conn: sqlite3.Connection,
    name: str,
    email: str,
    password: str,
    role: str = "member",
) -> Member:
    if role not in MEMBER_ROLES:
        raise ValueError(f"unknown role: {role}")

    salt = os.urandom(16).hex()
    password_hash = _hash_password(password, salt)

    cursor = conn.execute(
        "INSERT INTO members (name, email, role, password_hash, password_salt) "
        "VALUES (?, ?, ?, ?, ?)",
        (name, email, role, password_hash, salt),
    )
    conn.commit()

    return Member(
        member_id=cursor.lastrowid,
        name=name,
        email=email,
        role=role,
        password_hash=password_hash,
        password_salt=salt,
    )


def authenticate(conn: sqlite3.Connection, email: str, password: str) -> Optional[Member]:
    row = conn.execute(
        "SELECT * FROM members WHERE email = ?", (email,)
    ).fetchone()

    if row is None:
        return None

    expected_hash = _hash_password(password, row["password_salt"])
    if expected_hash != row["password_hash"]:
        return None

    return Member(
        member_id=row["member_id"],
        name=row["name"],
        email=row["email"],
        role=row["role"],
        password_hash=row["password_hash"],
        password_salt=row["password_salt"],
    )


def require_role(member: Member, *allowed_roles: str) -> None:
    # small guard used throughout service.py to enforce role based access
    if member.role not in allowed_roles:
        raise PermissionError(
            f"role '{member.role}' is not permitted to perform this action, "
            f"requires one of {allowed_roles}"
        )
