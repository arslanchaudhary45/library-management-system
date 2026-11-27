#!/usr/bin/env python3
"""Library Management System — books, borrowing, returns,
reservations and overdue records.

Service layer: pure functions owning the data and rules. The CLI and
the Flask app (``app.py``) both call these functions.

Rules: a member may borrow at most 3 books at a time; loans last 14
days; a book with an active reservation by someone else cannot be
borrowed by another member. Data lives in ``library.json`` next to
this file. Standard library only.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date, datetime, timedelta

DATA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         "library.json")

LOAN_DAYS = 14
MAX_LOANS_PER_MEMBER = 3
FINE_PER_DAY = 10  # Rs per overdue day


class LibraryError(ValueError):
    """Raised on invalid input or a missing record."""


def demo_data() -> dict:
    """Small realistic demo dataset (clearly marked demo data)."""
    return {
        "books": [
            {"id": 1, "title": "Clean Code", "author": "Robert C. Martin",
             "isbn": "9780132350884", "category": "Programming",
             "copies": 3},
            {"id": 2, "title": "Introduction to Algorithms",
             "author": "Cormen, Leiserson, Rivest & Stein",
             "isbn": "9780262033848", "category": "Computer Science",
             "copies": 2},
            {"id": 3, "title": "The Alchemist", "author": "Paulo Coelho",
             "isbn": "9780062315007", "category": "Fiction", "copies": 2},
            {"id": 4, "title": "Operating System Concepts",
             "author": "Silberschatz, Galvin & Gagne",
             "isbn": "9781118063330", "category": "Computer Science",
             "copies": 1},
        ],
        "members": [
            {"id": 1, "name": "Arslan Nasir", "email": "arslan@uni.edu",
             "member_type": "student"},
            {"id": 2, "name": "Ayesha Khan", "email": "ayesha@uni.edu",
             "member_type": "student"},
            {"id": 3, "name": "Dr. Sara Ali", "email": "sara@uni.edu",
             "member_type": "teacher"},
        ],
        "loans": [
            {"id": 1, "book_id": 1, "member_id": 1,
             "borrowed_on": "2026-11-20", "due_on": "2026-12-04",
             "returned_on": None},
            {"id": 2, "book_id": 2, "member_id": 2,
             "borrowed_on": "2026-11-05", "due_on": "2026-11-19",
             "returned_on": None},
            {"id": 3, "book_id": 3, "member_id": 1,
             "borrowed_on": "2026-11-10", "due_on": "2026-11-24",
             "returned_on": "2026-11-22"},
        ],
        "reservations": [
            {"id": 1, "book_id": 4, "member_id": 2,
             "reserved_on": "2026-11-26", "status": "active"},
        ],
    }


def empty_data() -> dict:
    """Return an empty store."""
    return {"books": [], "members": [], "loans": [], "reservations": []}


def load_data() -> dict:
    """Load the store, seeding demo data on first run."""
    if not os.path.exists(DATA_FILE):
        data = demo_data()
        save_data(data)
        return data
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError:
            print(f"Warning: {DATA_FILE} is corrupted; starting fresh.",
                  file=sys.stderr)
            return empty_data()
    for key in empty_data():
        data.setdefault(key, [])
    return data


def save_data(data: dict) -> None:
    """Persist the store as indented JSON."""
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def _next_id(items: list[dict]) -> int:
    return max((i["id"] for i in items), default=0) + 1


def _find(items: list[dict], item_id: int) -> dict | None:
    return next((i for i in items if i["id"] == item_id), None)


def _require(items: list[dict], item_id: int, what: str) -> dict:
    item = _find(items, item_id)
    if item is None:
        raise LibraryError(f"No {what} with id {item_id}.")
    return item


def _parse(date_str: str) -> date:
    return datetime.strptime(date_str, "%Y-%m-%d").date()


# ---------------------------------------------------------------------------
# Books & members
# ---------------------------------------------------------------------------

def add_book(title: str, author: str, isbn: str = "",
             category: str = "General", copies: int = 1) -> dict:
    """Add a book and return it."""
    title, author = (title or "").strip(), (author or "").strip()
    if not title or not author:
        raise LibraryError("Book title and author are required.")
    if copies < 1:
        raise LibraryError("Copies must be at least 1.")
    data = load_data()
    if isbn and any(b.get("isbn") == isbn for b in data["books"]):
        raise LibraryError(f"ISBN {isbn!r} already exists.")
    book = {"id": _next_id(data["books"]), "title": title, "author": author,
            "isbn": (isbn or "").strip(),
            "category": (category or "").strip() or "General",
            "copies": copies}
    data["books"].append(book)
    save_data(data)
    return book


def add_member(name: str, email: str, member_type: str = "student") -> dict:
    """Add a member and return them."""
    name, email = (name or "").strip(), (email or "").strip()
    if not name or not email:
        raise LibraryError("Member name and email are required.")
    if "@" not in email:
        raise LibraryError(f"Invalid email {email!r}.")
    if member_type not in ("student", "teacher"):
        raise LibraryError("Member type must be student or teacher.")
    data = load_data()
    member = {"id": _next_id(data["members"]), "name": name,
              "email": email, "member_type": member_type}
    data["members"].append(member)
    save_data(data)
    return member


def list_books(query: str = "") -> list[dict]:
    """Return books, optionally matching a search query."""
    books = load_data()["books"]
    query = (query or "").strip().lower()
    if query:
        books = [b for b in books
                 if query in b["title"].lower()
                 or query in b["author"].lower()
                 or query in b.get("category", "").lower()
                 or query in b.get("isbn", "").lower()]
    return books


def list_members() -> list[dict]:
    """Return all members."""
    return load_data()["members"]


def available_copies(book: dict, data: dict | None = None) -> int:
    """Return how many copies of a book are free to borrow."""
    data = data or load_data()
    on_loan = sum(1 for loan in data["loans"]
                  if loan["book_id"] == book["id"]
                  and loan["returned_on"] is None)
    return book["copies"] - on_loan


def book_with_availability(book: dict) -> dict:
    """Return a book dict with an ``available`` count attached."""
    return {**book, "available": available_copies(book)}


# ---------------------------------------------------------------------------
# Loans
# ---------------------------------------------------------------------------

def borrow_book(book_id: int, member_id: int,
                today: date | None = None) -> dict:
    """Borrow a book for a member (14-day loan) and return the loan."""
    today = today or date.today()
    data = load_data()
    book = _require(data["books"], book_id, "book")
    _require(data["members"], member_id, "member")
    if available_copies(book, data) <= 0:
        raise LibraryError(f"No copies of {book['title']!r} are available.")
    active = [l for l in data["loans"]
              if l["member_id"] == member_id and l["returned_on"] is None]
    if len(active) >= MAX_LOANS_PER_MEMBER:
        raise LibraryError(
            f"Member already has {MAX_LOANS_PER_MEMBER} books on loan.")
    reserved_by_other = any(
        r["book_id"] == book_id and r["status"] == "active"
        and r["member_id"] != member_id for r in data["reservations"])
    if reserved_by_other and available_copies(book, data) <= 1:
        raise LibraryError(
            "This book is reserved by another member.")
    loan = {"id": _next_id(data["loans"]), "book_id": book_id,
            "member_id": member_id, "borrowed_on": today.isoformat(),
            "due_on": (today + timedelta(days=LOAN_DAYS)).isoformat(),
            "returned_on": None}
    data["loans"].append(loan)
    save_data(data)
    return loan


def return_book(loan_id: int, today: date | None = None) -> dict:
    """Return a loaned book and return the loan (with fine info)."""
    today = today or date.today()
    data = load_data()
    loan = _require(data["loans"], loan_id, "loan")
    if loan["returned_on"] is not None:
        raise LibraryError(f"Loan [{loan_id}] was already returned.")
    loan["returned_on"] = today.isoformat()
    save_data(data)
    return loan


def overdue_loans(today: date | None = None) -> list[dict]:
    """Return active loans past their due date, with days/fine."""
    today = today or date.today()
    data = load_data()
    rows = []
    for loan in data["loans"]:
        if loan["returned_on"] is not None:
            continue
        due = _parse(loan["due_on"])
        if due < today:
            days = (today - due).days
            rows.append({**loan, "days_overdue": days,
                         "fine": days * FINE_PER_DAY,
                         "book": _find(data["books"], loan["book_id"]),
                         "member": _find(data["members"],
                                         loan["member_id"])})
    rows.sort(key=lambda r: -r["days_overdue"])
    return rows


def active_loans() -> list[dict]:
    """Return active loans with book/member attached."""
    data = load_data()
    rows = []
    for loan in data["loans"]:
        if loan["returned_on"] is None:
            rows.append({**loan,
                         "book": _find(data["books"], loan["book_id"]),
                         "member": _find(data["members"],
                                         loan["member_id"])})
    return rows


# ---------------------------------------------------------------------------
# Reservations
# ---------------------------------------------------------------------------

def reserve_book(book_id: int, member_id: int,
                 today: date | None = None) -> dict:
    """Reserve a book for a member."""
    today = today or date.today()
    data = load_data()
    _require(data["books"], book_id, "book")
    _require(data["members"], member_id, "member")
    if any(r["book_id"] == book_id and r["member_id"] == member_id
           and r["status"] == "active" for r in data["reservations"]):
        raise LibraryError("This member already has an active "
                           "reservation for this book.")
    reservation = {"id": _next_id(data["reservations"]), "book_id": book_id,
                   "member_id": member_id,
                   "reserved_on": today.isoformat(), "status": "active"}
    data["reservations"].append(reservation)
    save_data(data)
    return reservation


def cancel_reservation(reservation_id: int) -> dict:
    """Cancel a reservation."""
    data = load_data()
    reservation = _require(data["reservations"], reservation_id,
                           "reservation")
    if reservation["status"] != "active":
        raise LibraryError("Reservation is not active.")
    reservation["status"] = "cancelled"
    save_data(data)
    return reservation


def fulfill_reservation(reservation_id: int) -> dict:
    """Mark a reservation fulfilled (book borrowed by the reserver)."""
    data = load_data()
    reservation = _require(data["reservations"], reservation_id,
                           "reservation")
    if reservation["status"] != "active":
        raise LibraryError("Reservation is not active.")
    reservation["status"] = "fulfilled"
    save_data(data)
    return reservation


def stats() -> dict[str, int]:
    """Return headline counts."""
    data = load_data()
    return {"books": len(data["books"]),
            "members": len(data["members"]),
            "on_loan": sum(1 for l in data["loans"]
                           if l["returned_on"] is None),
            "overdue": len(overdue_loans()),
            "reservations": sum(1 for r in data["reservations"]
                                if r["status"] == "active")}


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def cmd_book(args) -> int:
    try:
        if args.action == "add":
            b = add_book(args.title, args.author, args.isbn or "",
                         args.category or "General", args.copies)
            print(f"Added book [{b['id']}] {b['title']} by {b['author']}.")
        else:
            books = list_books(args.query or "")
            if not books:
                print("No books found.")
            for b in books:
                print(f"[{b['id']}] {b['title']} by {b['author']} "
                      f"({b['category']}) — {available_copies(b)}/"
                      f"{b['copies']} available")
    except LibraryError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    return 0


def cmd_member(args) -> int:
    try:
        if args.action == "add":
            m = add_member(args.name, args.email, args.type)
            print(f"Added member [{m['id']}] {m['name']} ({m['member_type']}).")
        else:
            members = list_members()
            if not members:
                print("No members yet.")
            for m in members:
                print(f"[{m['id']}] {m['name']} — {m['email']} "
                      f"({m['member_type']})")
    except LibraryError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    return 0


def cmd_borrow(args) -> int:
    try:
        loan = borrow_book(args.book, args.member)
        print(f"Borrowed book {args.book} for member {args.member} "
              f"(loan {loan['id']}, due {loan['due_on']}).")
    except LibraryError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    return 0


def cmd_return(args) -> int:
    try:
        loan = return_book(args.loan)
        due = _parse(loan["due_on"])
        returned = _parse(loan["returned_on"])
        days = max(0, (returned - due).days)
        if days:
            print(f"Returned loan [{loan['id']}]. Overdue by {days} day(s) "
                  f"— fine Rs {days * FINE_PER_DAY}.")
        else:
            print(f"Returned loan [{loan['id']}] on time.")
    except LibraryError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    return 0


def cmd_loans(args) -> int:
    rows = active_loans()
    if not rows:
        print("No books on loan.")
        return 0
    for loan in rows:
        book = loan["book"] or {}
        member = loan["member"] or {}
        print(f"[{loan['id']}] {book.get('title', '?')} — "
              f"{member.get('name', '?')} (due {loan['due_on']})")
    return 0


def cmd_overdue(args) -> int:
    rows = overdue_loans()
    if not rows:
        print("No overdue books.")
        return 0
    for row in rows:
        book = row["book"] or {}
        member = row["member"] or {}
        print(f"[{row['id']}] {book.get('title', '?')} — "
              f"{member.get('name', '?')}: {row['days_overdue']} day(s) "
              f"overdue, fine Rs {row['fine']}")
    return 0


def cmd_reserve(args) -> int:
    try:
        if args.action == "add":
            r = reserve_book(args.book, args.member)
            print(f"Reserved book {args.book} for member {args.member} "
                  f"(reservation {r['id']}).")
        elif args.action == "cancel":
            cancel_reservation(args.id)
            print(f"Cancelled reservation [{args.id}].")
        else:
            data = load_data()
            active = [r for r in data["reservations"]
                      if r["status"] == "active"]
            if not active:
                print("No active reservations.")
            for r in active:
                print(f"[{r['id']}] book {r['book_id']} — member "
                      f"{r['member_id']} (since {r['reserved_on']})")
    except LibraryError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    return 0


def build_parser() -> argparse.ArgumentParser:
    """Build the command-line argument parser."""
    parser = argparse.ArgumentParser(
        prog="library.py",
        description="Library Management System — books, borrowing, "
                    "returns, reservations and overdue records.")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("book", help="Add or list/search books.")
    p.add_argument("action", choices=("add", "list"))
    p.add_argument("--title"); p.add_argument("--author")
    p.add_argument("--isbn"); p.add_argument("--category")
    p.add_argument("--copies", type=int, default=1)
    p.add_argument("--query", help="Search text.")
    p.set_defaults(func=cmd_book)

    p = sub.add_parser("member", help="Add or list members.")
    p.add_argument("action", choices=("add", "list"))
    p.add_argument("--name"); p.add_argument("--email")
    p.add_argument("--type", choices=("student", "teacher"), default="student")
    p.set_defaults(func=cmd_member)

    p = sub.add_parser("borrow", help="Borrow a book.")
    p.add_argument("--book", type=int, required=True)
    p.add_argument("--member", type=int, required=True)
    p.set_defaults(func=cmd_borrow)

    p = sub.add_parser("return", help="Return a book.")
    p.add_argument("loan", type=int, help="Loan id.")
    p.set_defaults(func=cmd_return)

    p = sub.add_parser("loans", help="List books currently on loan.")
    p.set_defaults(func=cmd_loans)

    p = sub.add_parser("overdue", help="List overdue loans with fines.")
    p.set_defaults(func=cmd_overdue)

    p = sub.add_parser("reserve", help="Manage reservations.")
    p.add_argument("action", choices=("add", "list", "cancel"))
    p.add_argument("--book", type=int); p.add_argument("--member", type=int)
    p.add_argument("--id", type=int)
    p.set_defaults(func=cmd_reserve)
    return parser


def main(argv: list[str] | None = None) -> int:
    """Entry point for the command-line app."""
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
