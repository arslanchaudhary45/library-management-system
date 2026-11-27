#!/usr/bin/env python3
"""Library Management System — web UI (Flask).

Reuses the logic in library.py; this file only adds HTTP routes and
pages. Run it with:

    pip install -r requirements.txt
    python app.py

Then open http://127.0.0.1:5000 in your browser.
Set the PORT environment variable to use a different port.
The command-line app still works: python3 library.py --help
"""

import os
import sys

from flask import Flask, flash, redirect, render_template, request, url_for

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import library

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-only-key")

APP_NAME = "Library Management System"
APP_TAGLINE = "Books, borrowing, returns, reservations and overdue records"


@app.context_processor
def inject_globals():
    return {"app_name": APP_NAME, "app_tagline": APP_TAGLINE}


@app.route("/")
def index():
    query = request.args.get("q", "")
    books = [library.book_with_availability(b)
             for b in library.list_books(query)]
    return render_template("index.html", stats=library.stats(),
                           books=books, query=query,
                           members=library.list_members(),
                           loans=library.active_loans(),
                           overdue=library.overdue_loans(),
                           reservations=library.load_data()["reservations"])


@app.route("/book/add", methods=["POST"])
def add_book():
    try:
        book = library.add_book(
            request.form.get("title", ""), request.form.get("author", ""),
            request.form.get("isbn", ""),
            request.form.get("category", "General"),
            int(request.form.get("copies", 1) or 1))
        flash(f"Added book [{book['id']}] {book['title']}.", "success")
    except (library.LibraryError, ValueError) as exc:
        flash(str(exc), "error")
    return redirect(url_for("index"))


@app.route("/member/add", methods=["POST"])
def add_member():
    try:
        member = library.add_member(
            request.form.get("name", ""), request.form.get("email", ""),
            request.form.get("member_type", "student"))
        flash(f"Added member [{member['id']}] {member['name']}.",
              "success")
    except library.LibraryError as exc:
        flash(str(exc), "error")
    return redirect(url_for("index"))


@app.route("/borrow", methods=["POST"])
def borrow():
    try:
        loan = library.borrow_book(
            int(request.form.get("book_id", 0) or 0),
            int(request.form.get("member_id", 0) or 0))
        flash(f"Borrowed — due {loan['due_on']} (loan {loan['id']}).",
              "success")
    except (library.LibraryError, ValueError) as exc:
        flash(str(exc), "error")
    return redirect(url_for("index"))


@app.route("/return/<int:loan_id>", methods=["POST"])
def return_loan(loan_id):
    try:
        loan = library.return_book(loan_id)
        flash(f"Returned loan [{loan['id']}].", "success")
    except library.LibraryError as exc:
        flash(str(exc), "error")
    return redirect(url_for("index"))


@app.route("/reserve", methods=["POST"])
def reserve():
    try:
        reservation = library.reserve_book(
            int(request.form.get("book_id", 0) or 0),
            int(request.form.get("member_id", 0) or 0))
        flash(f"Reserved (reservation {reservation['id']}).", "success")
    except (library.LibraryError, ValueError) as exc:
        flash(str(exc), "error")
    return redirect(url_for("index"))


@app.route("/reserve/<int:reservation_id>/cancel", methods=["POST"])
def cancel_reservation(reservation_id):
    try:
        library.cancel_reservation(reservation_id)
        flash(f"Cancelled reservation [{reservation_id}].", "success")
    except library.LibraryError as exc:
        flash(str(exc), "error")
    return redirect(url_for("index"))


@app.route("/reserve/<int:reservation_id>/fulfill", methods=["POST"])
def fulfill_reservation(reservation_id):
    try:
        library.fulfill_reservation(reservation_id)
        flash(f"Reservation [{reservation_id}] fulfilled.", "success")
    except library.LibraryError as exc:
        flash(str(exc), "error")
    return redirect(url_for("index"))


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="127.0.0.1", port=port)
