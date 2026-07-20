"""Concurrency-safe seat reservation aggregate backed by SQLite."""

import sqlite3
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path
from threading import RLock
from uuid import uuid4

from .events import EventBus


class LockConflict(Exception):
    """Raised when an event seat is already locked or booked."""


class ReservationNotFound(Exception):
    """Raised when a reservation identifier does not exist."""


class InvalidReservationState(Exception):
    """Raised when a reservation cannot perform the requested transition."""


SCHEMA = """
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS reservations (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    event_id TEXT NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('PENDING','CONFIRMED','EXPIRED','CANCELLED')),
    expires_at TEXT NOT NULL,
    idempotency_key TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS reservation_seats (
    reservation_id TEXT NOT NULL REFERENCES reservations(id),
    event_id TEXT NOT NULL,
    seat_id TEXT NOT NULL,
    PRIMARY KEY (reservation_id, seat_id)
);
CREATE UNIQUE INDEX IF NOT EXISTS one_active_owner_per_event_seat
ON reservation_seats(event_id, seat_id);
"""


class ReservationService:
    def __init__(self, database: str | Path, bus: EventBus, ttl_seconds: int = 600) -> None:
        self.database = str(database)
        self.bus = bus
        self.ttl_seconds = ttl_seconds
        self._write_lock = RLock()
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

    def lock_seats(
        self,
        user_id: str,
        event_id: str,
        seat_ids: list[str],
        idempotency_key: str,
        *,
        now: datetime | None = None,
    ) -> dict[str, object]:
        if not seat_ids or len(set(seat_ids)) != len(seat_ids):
            raise ValueError("seat_ids must contain unique seats")
        current = now or datetime.now(UTC)
        expires = current + timedelta(seconds=self.ttl_seconds)

        with self._write_lock, self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            self._expire_locked(connection, current)
            existing = connection.execute(
                "SELECT * FROM reservations WHERE idempotency_key = ?",
                (idempotency_key,),
            ).fetchone()
            if existing:
                connection.commit()
                return self.get(existing["id"])

            reservation_id = str(uuid4())
            try:
                connection.execute(
                    "INSERT INTO reservations VALUES (?, ?, ?, 'PENDING', ?, ?, ?)",
                    (
                        reservation_id,
                        user_id,
                        event_id,
                        expires.isoformat(),
                        idempotency_key,
                        current.isoformat(),
                    ),
                )
                connection.executemany(
                    "INSERT INTO reservation_seats VALUES (?, ?, ?)",
                    [(reservation_id, event_id, seat_id) for seat_id in seat_ids],
                )
            except sqlite3.IntegrityError as error:
                connection.rollback()
                raise LockConflict("one or more seats are unavailable") from error
            connection.commit()

        self.bus.publish(
            "ReservationCreated",
            reservation_id,
            {"eventId": event_id, "seatIds": seat_ids, "expiresAt": expires.isoformat()},
        )
        return self.get(reservation_id)

    def confirm(self, reservation_id: str, *, now: datetime | None = None) -> dict[str, object]:
        current = now or datetime.now(UTC)
        with self._write_lock, self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT * FROM reservations WHERE id = ?", (reservation_id,)
            ).fetchone()
            if not row:
                connection.rollback()
                raise ReservationNotFound(reservation_id)
            if row["status"] == "CONFIRMED":
                connection.commit()
                return self.get(reservation_id)
            if row["status"] != "PENDING" or datetime.fromisoformat(row["expires_at"]) <= current:
                if row["status"] == "PENDING":
                    self._expire_one(connection, reservation_id)
                    connection.commit()
                else:
                    connection.rollback()
                raise InvalidReservationState("reservation is not confirmable")
            connection.execute(
                "UPDATE reservations SET status = 'CONFIRMED' WHERE id = ?", (reservation_id,)
            )
            connection.commit()
        self.bus.publish("ReservationConfirmed", reservation_id, {})
        return self.get(reservation_id)

    def release(self, reservation_id: str, reason: str = "cancelled") -> dict[str, object]:
        with self._write_lock, self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT status FROM reservations WHERE id = ?", (reservation_id,)
            ).fetchone()
            if not row:
                connection.rollback()
                raise ReservationNotFound(reservation_id)
            if row["status"] == "CONFIRMED":
                connection.rollback()
                raise InvalidReservationState("confirmed reservations cannot be released")
            if row["status"] == "PENDING":
                connection.execute(
                    "UPDATE reservations SET status = 'CANCELLED' WHERE id = ?", (reservation_id,)
                )
                connection.execute(
                    "DELETE FROM reservation_seats WHERE reservation_id = ?", (reservation_id,)
                )
            connection.commit()
        self.bus.publish("ReservationReleased", reservation_id, {"reason": reason})
        return self.get(reservation_id)

    def expire_due(self, *, now: datetime | None = None) -> int:
        current = now or datetime.now(UTC)
        with self._write_lock, self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            expired = self._expire_locked(connection, current)
            connection.commit()
        for reservation_id in expired:
            self.bus.publish("ReservationExpired", reservation_id, {})
        return len(expired)

    def _expire_locked(self, connection: sqlite3.Connection, now: datetime) -> list[str]:
        rows = connection.execute(
            "SELECT id FROM reservations WHERE status = 'PENDING' AND expires_at <= ?",
            (now.isoformat(),),
        ).fetchall()
        ids = [row["id"] for row in rows]
        for reservation_id in ids:
            self._expire_one(connection, reservation_id)
        return ids

    @staticmethod
    def _expire_one(connection: sqlite3.Connection, reservation_id: str) -> None:
        connection.execute(
            "UPDATE reservations SET status = 'EXPIRED' WHERE id = ?", (reservation_id,)
        )
        connection.execute(
            "DELETE FROM reservation_seats WHERE reservation_id = ?", (reservation_id,)
        )

    def get(self, reservation_id: str) -> dict[str, object]:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM reservations WHERE id = ?", (reservation_id,)
            ).fetchone()
            if not row:
                raise ReservationNotFound(reservation_id)
            seats = connection.execute(
                "SELECT seat_id FROM reservation_seats WHERE reservation_id = ? ORDER BY seat_id",
                (reservation_id,),
            ).fetchall()
        return {
            "id": row["id"],
            "userId": row["user_id"],
            "eventId": row["event_id"],
            "status": row["status"],
            "expiresAt": row["expires_at"],
            "seatIds": [seat["seat_id"] for seat in seats],
        }
