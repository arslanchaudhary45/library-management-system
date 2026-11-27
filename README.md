# Library Management System

Manage books, borrowing, returns, reservations, and overdue records. Data is stored in `library.json` next to the code. Use it from the
command line or from the web app below. The project ships with a
small amount of realistic demo data so the interface is not empty
on first run.

## Web app

```bash
cd library-management-system
pip install -r requirements.txt
python app.py
```

Then open http://127.0.0.1:5000 in your browser. Add books and members; search the catalogue; borrow and return books; reserve books; see overdue loans with fines and active reservations. Set the `PORT`
environment variable to run on a different port.

## Requirements

- Python 3.12+
- Flask (for the web app only; see `requirements.txt`)

## Command line

```bash
cd library-management-system
python3 library.py --help
```

## Commands

### Books and members

```bash
python3 library.py book add --title "Clean Code" --author "Robert C. Martin" --isbn 9780132350884 --category Programming --copies 3
python3 library.py book list
python3 library.py book list --query "clean"
python3 library.py member add --name "Arslan Nasir" --email arslan@uni.edu --type student
python3 library.py member list
```

### Borrowing and returns

```bash
python3 library.py borrow --book 1 --member 1
python3 library.py return 1
python3 library.py loans
```

### Overdue and reservations

```bash
python3 library.py overdue
python3 library.py reserve add --book 4 --member 2
python3 library.py reserve list
python3 library.py reserve cancel --id 1
```

## Tests

```bash
pip install pytest
python3 -m pytest tests/ -q
```

## Data

Data is saved in `library.json` in this folder: books, members, loans and reservations. Loans last 14 days; a member may borrow at most 3 books at a time; overdue fines are Rs 10 per day.
