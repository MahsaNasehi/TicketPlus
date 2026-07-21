"""Event (theatre show) catalog, manageable only by admins.

An event has a title, a venue, a human-readable date label, and one or
more seating rows. Each row has a label (e.g. "A"), a seat count, and a
per-seat price in Rial (``priceMinor`` — the frontend sells and prices
seats row by row, there is no single event-level price).

Business rule: every row's per-seat price must be strictly greater than
100,000 Toman (1 Toman == 10 Rial). This is enforced per row rather than
against some derived "event price" because customers are charged the
row's price when they buy a seat in it; checking only a derived minimum
across rows would be mathematically equivalent (the minimum exceeds the
threshold iff every row does), but validating each row directly lets us
report exactly which row is invalid. No other constraint is placed on
price or on the rest of the event fields.
"""

import sqlite3
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

RIAL_PER_TOMAN = 10
MIN_PRICE_TOMAN = 100_000
MIN_PRICE_RIAL = MIN_PRICE_TOMAN * RIAL_PER_TOMAN  # 1,000,000 Rial

SCHEMA = f"""
CREATE TABLE IF NOT EXISTS events (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    venue TEXT NOT NULL,
    date_label TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS event_rows (
    event_id TEXT NOT NULL REFERENCES events(id),
    position INTEGER NOT NULL,
    label TEXT NOT NULL,
    seats INTEGER NOT NULL CHECK(seats > 0),
    price_minor INTEGER NOT NULL CHECK(price_minor > {MIN_PRICE_RIAL}),
    PRIMARY KEY (event_id, position)
);
"""


class InvalidEvent(Exception):
    """Raised when event data fails validation (e.g. a row's price is too low)."""


class EventCatalog:
    def __init__(self, database: str | Path) -> None:
        self.database = str(database)
        with self._connect() as connection:
            connection.executescript(SCHEMA)

    @contextmanager
    def _connect(self):
        connection = sqlite3.connect(self.database, timeout=30, isolation_level=None)
        connection.row_factory = sqlite3.Row
        try:
            yield connection
        finally:
            connection.close()

    @staticmethod
    def _normalize_rows(rows: object) -> list[dict[str, object]]:
        if not isinstance(rows, list) or not rows:
            raise InvalidEvent("at least one seating row is required")

        normalized: list[dict[str, object]] = []
        seen_labels: set[str] = set()
        for raw_row in rows:
            if not isinstance(raw_row, dict):
                raise InvalidEvent("each row must be an object with label, seats and priceMinor")

            label = str(raw_row.get("label", "")).strip()
            if not label:
                raise InvalidEvent("each row requires a non-empty label")
            if label in seen_labels:
                raise InvalidEvent(f"duplicate row label: {label!r}")
            seen_labels.add(label)

            seats = raw_row.get("seats")
            if not isinstance(seats, int) or isinstance(seats, bool) or seats <= 0:
                raise InvalidEvent(f"row {label!r}: seats must be a positive integer")

            price_minor = raw_row.get("priceMinor")
            if not isinstance(price_minor, int) or isinstance(price_minor, bool):
                raise InvalidEvent(f"row {label!r}: priceMinor must be an integer number of Rial")
            if price_minor <= MIN_PRICE_RIAL:
                raise InvalidEvent(
                    f"row {label!r}: price must be greater than {MIN_PRICE_TOMAN} Toman "
                    f"({MIN_PRICE_RIAL} Rial) per seat"
                )

            normalized.append({"label": label, "seats": seats, "priceMinor": price_minor})
        return normalized

    def create_event(
        self,
        title: str,
        venue: str,
        date_label: str,
        rows: object,
    ) -> dict[str, object]:
        title = (title or "").strip()
        venue = (venue or "").strip()
        date_label = (date_label or "").strip()
        if not title:
            raise InvalidEvent("title is required")
        if not venue:
            raise InvalidEvent("venue is required")
        if not date_label:
            raise InvalidEvent("dateLabel is required")

        normalized_rows = self._normalize_rows(rows)

        event_id = str(uuid4())
        created_at = datetime.now(UTC).isoformat()
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            try:
                connection.execute(
                    "INSERT INTO events (id, title, venue, date_label, created_at) VALUES (?, ?, ?, ?, ?)",
                    (event_id, title, venue, date_label, created_at),
                )
                connection.executemany(
                    "INSERT INTO event_rows (event_id, position, label, seats, price_minor) "
                    "VALUES (?, ?, ?, ?, ?)",
                    [
                        (event_id, position, row["label"], row["seats"], row["priceMinor"])
                        for position, row in enumerate(normalized_rows)
                    ],
                )
            except sqlite3.IntegrityError as error:
                connection.rollback()
                raise InvalidEvent(f"could not save event rows: {error}") from error
            connection.commit()
        return self.get(event_id)

    def get(self, event_id: str) -> dict[str, object]:
        with self._connect() as connection:
            event_row = connection.execute(
                "SELECT * FROM events WHERE id = ?", (event_id,)
            ).fetchone()
            if not event_row:
                raise InvalidEvent(f"event {event_id} not found")
            row_records = connection.execute(
                "SELECT label, seats, price_minor FROM event_rows "
                "WHERE event_id = ? ORDER BY position",
                (event_id,),
            ).fetchall()
        return {
            "id": event_row["id"],
            "title": event_row["title"],
            "venue": event_row["venue"],
            "dateLabel": event_row["date_label"],
            "rows": [
                {"label": r["label"], "seats": r["seats"], "priceMinor": r["price_minor"]}
                for r in row_records
            ],
            "createdAt": event_row["created_at"],
        }

    def list(self) -> list[dict[str, object]]:
        with self._connect() as connection:
            rows = connection.execute("SELECT id FROM events ORDER BY created_at").fetchall()
        return [self.get(row["id"]) for row in rows]
