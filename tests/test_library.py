"""Tests for library.py core logic."""

from datetime import date

import pytest

import library
from library import (
    LibraryError, add_book, add_member, borrow_book, overdue_loans,
    reserve_book, return_book,
)


@pytest.fixture(autouse=True)
def _tmp_data(tmp_path, monkeypatch):
    monkeypatch.setattr(library, "DATA_FILE", str(tmp_path / "library.json"))
    monkeypatch.setattr(library, "demo_data", library.empty_data)


def _setup(copies=2):
    book = add_book("Clean Code", "Robert C. Martin", copies=copies)
    m1 = add_member("Arslan", "arslan@uni.edu")
    m2 = add_member("Ayesha", "ayesha@uni.edu")
    return book, m1, m2


def test_borrow_and_return():
    book, m1, _ = _setup()
    loan = borrow_book(book["id"], m1["id"], date(2026, 11, 20))
    assert loan["due_on"] == "2026-12-04"  # 14 days later
    assert library.available_copies(book) == 1
    return_book(loan["id"], date(2026, 11, 25))
    assert library.available_copies(book) == 2
    with pytest.raises(LibraryError):
        return_book(loan["id"])  # already returned


def test_no_copies_available():
    book, m1, m2 = _setup(copies=1)
    borrow_book(book["id"], m1["id"], date(2026, 11, 20))
    with pytest.raises(LibraryError):
        borrow_book(book["id"], m2["id"], date(2026, 11, 20))


def test_max_three_loans_per_member():
    book, m1, _ = _setup()
    b2 = add_book("Book 2", "Author")
    b3 = add_book("Book 3", "Author")
    b4 = add_book("Book 4", "Author")
    for b in (book, b2, b3):
        borrow_book(b["id"], m1["id"], date(2026, 11, 20))
    with pytest.raises(LibraryError):
        borrow_book(b4["id"], m1["id"], date(2026, 11, 20))


def test_overdue_and_fine():
    book, m1, _ = _setup()
    borrow_book(book["id"], m1["id"], date(2026, 11, 1))
    overdue = overdue_loans(date(2026, 11, 20))
    assert len(overdue) == 1
    assert overdue[0]["days_overdue"] == 5  # due 2026-11-15
    assert overdue[0]["fine"] == 50


def test_reservation_blocks_last_copy():
    book, m1, m2 = _setup(copies=1)
    reserve_book(book["id"], m2["id"], date(2026, 11, 20))
    with pytest.raises(LibraryError):
        borrow_book(book["id"], m1["id"], date(2026, 11, 20))
    # The reserver themselves can still borrow it.
    loan = borrow_book(book["id"], m2["id"], date(2026, 11, 20))
    assert loan["book_id"] == book["id"]


def test_search_books():
    _setup()
    assert len(library.list_books("clean")) == 1
    assert len(library.list_books("nope")) == 0
