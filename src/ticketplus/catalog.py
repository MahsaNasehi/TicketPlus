"""Event (theatre show) catalog, manageable only by admins.

An event has a title, a venue, a human-readable date/time label, and one or
more seating "rows" -- each row has a label (e.g. "A"), a seat count, and a
price per seat (`priceMinor`, in the minor unit of the venue's currency).

Business rule: every row's price must be strictly greater than 100,000
(the same rule the reference implementation used to apply to a single
event-level price now applies per seating row, since that's the level at
which price actually varies). No other constraint is placed on price or on
the rest of the event fields.
"""

import json
import sqlite3
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

MIN_ROW_PRICE = 100_000

SCHEMA = """
CREATE TABLE IF NOT EXISTS events (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    venue TEXT NOT NULL,
    date_label TEXT NOT NULL,
    rows_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);
"""

# A handful of demo theaters/concerts so the catalog is never empty out of
# the box -- a fresh admin/user shouldn't be staring at an empty event list.
DEFAULT_EVENTS = [
    {
        "title": "Persian Poetry & Traditional Music Night",
        "venue": "Vahdat Hall, Tehran",
        "dateLabel": "Thu, Sep 3 - 8:00 PM",
        "rows": [
            {"label": "A", "seats": 10, "priceMinor": 450_000},
            {"label": "B", "seats": 12, "priceMinor": 300_000},
        ],
    },
    {
        "title": "The Cherry Orchard (Theatre)",
        "venue": "City Theatre, Main Hall",
        "dateLabel": "Fri, Sep 4 - 6:30 PM",
        "rows": [
            {"label": "A", "seats": 8, "priceMinor": 550_000},
            {"label": "B", "seats": 14, "priceMinor": 350_000},
        ],
    },
    {
        "title": "Rastak Ensemble Concert",
        "venue": "Milad Tower Convention Hall",
        "dateLabel": "Sat, Sep 12 - 9:00 PM",
        "rows": [
            {"label": "A", "seats": 20, "priceMinor": 750_000},
            {"label": "B", "seats": 20, "priceMinor": 500_000},
            {"label": "C", "seats": 20, "priceMinor": 350_000},
        ],
    },
]


class InvalidEvent(Exception):
    """Raised when event data fails validation (e.g. a row's price is too low)."""


class EventCatalog:
    def __init__(self, database: str | Path, *, seed_defaults: bool = True) -> None:
        self.database = str(database)
        with self._connect() as connection:
            connection.executescript(SCHEMA)
        if seed_defaults and not self.list():
            for demo in DEFAULT_EVENTS:
                self.create_event(demo["title"], demo["venue"], demo["dateLabel"], demo["rows"])

    @contextmanager
    def _connect(self):
        connection = sqlite3.connect(self.database, timeout=30, isolation_level=None)
        connection.row_factory = sqlite3.Row
        try:
            yield connection
        finally:
            connection.close()

    @staticmethod
    def _validate_rows(rows: object) -> list[dict[str, object]]:
        if not isinstance(rows, list) or not rows:
            raise InvalidEvent("at least one seating row is required")
        cleaned: list[dict[str, object]] = []
        for row in rows:
            if not isinstance(row, dict):
                raise InvalidEvent("each row must be an object")
            label = str(row.get("label", "")).strip()
            seats = row.get("seats")
            price_minor = row.get("priceMinor")
            if not label:
                raise InvalidEvent("each row needs a label")
            if not isinstance(seats, int) or isinstance(seats, bool) or seats <= 0:
                raise InvalidEvent("each row's seat count must be a positive integer")
            if not isinstance(price_minor, int) or isinstance(price_minor, bool):
                raise InvalidEvent("each row's price must be an integer")
            if price_minor <= MIN_ROW_PRICE:
                raise InvalidEvent(f"each row's price must be greater than {MIN_ROW_PRICE}")
            cleaned.append({"label": label, "seats": seats, "priceMinor": price_minor})
        return cleaned

    def create_event(
        self, title: str, venue: str, date_label: str, rows: list[dict[str, object]]
    ) -> dict[str, object]:
        title = (title or "").strip()
        venue = (venue or "").strip()
        date_label = (date_label or "").strip()
        if not title:
            raise InvalidEvent("title is required")
        if not venue:
            raise InvalidEvent("venue is required")
        if not date_label:
            raise InvalidEvent("date label is required")
        cleaned_rows = self._validate_rows(rows)

        event_id = str(uuid4())
        created_at = datetime.now(UTC).isoformat()
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO events (id, title, venue, date_label, rows_json, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (event_id, title, venue, date_label, json.dumps(cleaned_rows), created_at),
            )
        return self.get(event_id)

    def get(self, event_id: str) -> dict[str, object]:
        with self._connect() as connection:
            row = connection.execute("SELECT * FROM events WHERE id = ?", (event_id,)).fetchone()
        if not row:
            raise InvalidEvent(f"event {event_id} not found")
        return {
            "id": row["id"],
            "title": row["title"],
            "venue": row["venue"],
            "dateLabel": row["date_label"],
            "rows": json.loads(row["rows_json"]),
            "createdAt": row["created_at"],
        }

    def list(self) -> list[dict[str, object]]:
        with self._connect() as connection:
            rows = connection.execute("SELECT id FROM events ORDER BY created_at").fetchall()
        return [self.get(row["id"]) for row in rows]
