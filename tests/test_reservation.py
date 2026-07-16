import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from pathlib import Path

from ticketplus.events import EventBus
from ticketplus.reservation import LockConflict, ReservationService


class ReservationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.service = ReservationService(Path(self.temp.name) / "test.db", EventBus(), ttl_seconds=10)

    def tearDown(self):
        self.temp.cleanup()

    def test_exactly_one_concurrent_lock_winner(self):
        def attempt(number):
            try:
                return self.service.lock_seats("buyer", "event", ["A-1"], f"key-{number}")["id"]
            except LockConflict:
                return None

        with ThreadPoolExecutor(max_workers=32) as pool:
            results = list(pool.map(attempt, range(200)))
        self.assertEqual(1, len([result for result in results if result]))

    def test_idempotent_retry_returns_same_reservation(self):
        first = self.service.lock_seats("buyer", "event", ["A-1"], "same-key")
        second = self.service.lock_seats("buyer", "event", ["A-1"], "same-key")
        self.assertEqual(first["id"], second["id"])

    def test_expiry_releases_seat(self):
        now = datetime.now(UTC)
        original = self.service.lock_seats("buyer", "event", ["A-1"], "old", now=now)
        self.assertEqual(1, self.service.expire_due(now=now + timedelta(seconds=11)))
        self.assertEqual("EXPIRED", self.service.get(original["id"])["status"])
        replacement = self.service.lock_seats(
            "other", "event", ["A-1"], "new", now=now + timedelta(seconds=11)
        )
        self.assertEqual("PENDING", replacement["status"])


if __name__ == "__main__":
    unittest.main()

