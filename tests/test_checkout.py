import tempfile
import unittest
from pathlib import Path

from ticketplus.checkout import CheckoutService, NotificationService, PaymentResult, TicketingService
from ticketplus.events import EventBus
from ticketplus.reservation import ReservationService


class CheckoutTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.bus = EventBus()
        self.reservations = ReservationService(Path(self.temp.name) / "test.db", self.bus)
        self.ticketing = TicketingService(self.bus)
        self.notifications = NotificationService(self.bus)

    def tearDown(self):
        self.temp.cleanup()

    def reservation(self):
        return self.reservations.lock_seats("buyer", "event", ["A-1"], "reservation-key")

    def test_success_confirms_and_issues_one_ticket(self):
        reservation = self.reservation()
        service = CheckoutService(
            self.reservations, self.bus, lambda key, amount, currency: (PaymentResult.SUCCEEDED, "ref")
        )
        first = service.checkout(reservation["id"], 10000, "IRR", "payment-key")
        second = service.checkout(reservation["id"], 10000, "IRR", "payment-key")
        self.assertEqual(first, second)
        self.assertEqual("CONFIRMED", self.reservations.get(reservation["id"])["status"])
        self.assertEqual(1, len(self.ticketing.tickets))
        self.assertEqual(1, len(self.notifications.deliveries))

    def test_definitive_failure_releases_seat(self):
        reservation = self.reservation()
        service = CheckoutService(
            self.reservations, self.bus, lambda key, amount, currency: (PaymentResult.FAILED, None)
        )
        service.checkout(reservation["id"], 10000, "IRR", "payment-key")
        self.assertEqual("CANCELLED", self.reservations.get(reservation["id"])["status"])

    def test_unknown_payment_keeps_reservation_for_reconciliation(self):
        reservation = self.reservation()
        service = CheckoutService(
            self.reservations, self.bus, lambda key, amount, currency: (PaymentResult.UNKNOWN, None)
        )
        service.checkout(reservation["id"], 10000, "IRR", "payment-key")
        self.assertEqual("PENDING", self.reservations.get(reservation["id"])["status"])


if __name__ == "__main__":
    unittest.main()

