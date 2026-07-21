"""Event (theatre show) catalog, manageable only by admins.

Business rule: an event's price must be strictly greater than 100,000 Toman.
No other constraint is placed on price or on the rest of the event fields.
"""

import sqlite3
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

MIN_PRICE_TOMAN = 100_000

SCHEMA = """
CREATE TABLE IF NOT EXISTS events (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    price_toman INTEGER NOT NULL CHECK(price_toman > 100000),
    created_at TEXT NOT NULL
);
"""


class InvalidEvent(Exception):
    """Raised when event data fails validation (e.g. price too low)."""


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

    def create_event(self, title: str, price_toman: int) -> dict[str, object]:
        title = (title or "").strip()
        if not title:
            raise InvalidEvent("title is required")
        if not isinstance(price_toman, int) or isinstance(price_toman, bool):
            raise InvalidEvent("price_toman must be an integer number of Toman")
        if price_toman <= MIN_PRICE_TOMAN:
            raise InvalidEvent(f"price must be greater than {MIN_PRICE_TOMAN} Toman")

        event_id = str(uuid4())
        created_at = datetime.now(UTC).isoformat()
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO events (id, title, price_toman, created_at) VALUES (?, ?, ?, ?)",
                (event_id, title, price_toman, created_at),
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
            "priceToman": row["price_toman"],
            "createdAt": row["created_at"],
        }

    def list(self) -> list[dict[str, object]]:
        with self._connect() as connection:
            rows = connection.execute("SELECT id FROM events ORDER BY created_at").fetchall()
        return [self.get(row["id"]) for row in rows]
