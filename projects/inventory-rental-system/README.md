# Inventory & Equipment Rental System

A role-based rental/checkout system for tracking business equipment (cameras, power tools, AV gear), built to demonstrate business-logic rule enforcement, relational data persistence, and reliability under concurrent access: the kind of system a company runs its daily operations on.

## Why this exists

Skill goals: prove that I can build secure, reliable systems that companies use to run daily operations, with real business rules, real data persistence, and real concurrency handling, not just a script.

## Stack

Python 3 + SQLite (standard library only: `sqlite3`, `hashlib`, `dataclasses`). No external dependencies, no build tool, runs anywhere `python3` runs. That constraint was deliberate: it keeps the project fully self-contained and trivially runnable while still forcing real schema design (foreign keys, indices, transactions).

## Business rules implemented

- **Category-based checkout limits and late fees**: each item category (camera, power tool, AV equipment) has its own max checkout duration and daily late-fee rate.
- **Late fee calculation**: accrues daily past the due date, capped at the item's replacement cost.
- **Damage tracking**: a damaged return sends the item to `maintenance` status instead of back into circulation, and updates its condition grade.
- **Reservation queue**: members can reserve an item that's currently checked out; the oldest reservation is auto-fulfilled when the item comes back.
- **Concurrency-safe checkout**: checkout uses an immediate SQLite transaction, so two simultaneous checkout attempts on the same item can't both succeed; the second caller fails cleanly with `ItemUnavailableError` instead of corrupting state.
- **Role-based access control**: `member` (browse/checkout/reserve), `staff` (process returns, view reports), `admin` (manage inventory, view revenue). Enforced in `service.py`, not just hidden in the UI.

## Structure

```
inventory-rental-system/
├── models.py       <- data classes and business rule constants
├── database.py     <- schema and connection handling
├── auth.py         <- password hashing and role checks
├── service.py       <- all business logic (checkout, return, reserve)
├── reports.py       <- read-only reporting queries
├── seed_data.py      <- sample data for demoing
├── cli.py          <- menu-driven demo interface
└── tests.py        <- unit tests (unittest, in-memory db)
```

## Run it

```bash
python3 seed_data.py     # creates rental_system.db with sample data
python3 cli.py            # log in as one of the seeded accounts and try it
python3 -m unittest tests.py -v
```

Seeded logins: `ada@example.com` / `adminpass` (admin), `sam@example.com` / `staffpass` (staff), `mia@example.com` / `memberpass` (member).

## Known limitations

This is a portfolio demo, not a production system: the auth is hand-rolled sha256 hashing rather than a vetted library like bcrypt, there's no web layer (CLI only), and `check_same_thread=False` is a shortcut appropriate for a single demo process, not a real multi-user deployment.
