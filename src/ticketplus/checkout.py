"""Idempotent checkout saga and compensation behavior."""

from dataclasses import dataclass
from enum import StrEnum
from threading import RLock
from uuid import uuid4

from .events import DomainEvent, EventBus
from .reservation import ReservationService


class PaymentResult(StrEnum):
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class PaymentAttempt:
    order_id: str
    reservation_id: str
    idempotency_key: str
    amount_minor: int
    currency: str
    status: PaymentResult
    provider_reference: str | None


class CheckoutService:
    def __init__(self, reservations: ReservationService, bus: EventBus, gateway) -> None:
        self.reservations = reservations
        self.bus = bus
        self.gateway = gateway
        self._attempts: dict[str, PaymentAttempt] = {}
        self._lock = RLock()

    def checkout(
        self,
        reservation_id: str,
        amount_minor: int,
        currency: str,
        idempotency_key: str,
    ) -> PaymentAttempt:
        if amount_minor <= 0 or len(currency) != 3:
            raise ValueError("a positive amount and ISO currency are required")
        with self._lock:
            if idempotency_key in self._attempts:
                return self._attempts[idempotency_key]
            result, provider_reference = self.gateway(idempotency_key, amount_minor, currency)
            attempt = PaymentAttempt(
                order_id=str(uuid4()),
                reservation_id=reservation_id,
                idempotency_key=idempotency_key,
                amount_minor=amount_minor,
                currency=currency.upper(),
                status=PaymentResult(result),
                provider_reference=provider_reference,
            )
            self._attempts[idempotency_key] = attempt

            if attempt.status is PaymentResult.SUCCEEDED:
                self.reservations.confirm(reservation_id)
                self.bus.publish(
                    "PaymentSucceeded",
                    attempt.order_id,
                    {"reservationId": reservation_id, "amountMinor": amount_minor, "currency": currency},
                )
            elif attempt.status is PaymentResult.FAILED:
                self.reservations.release(reservation_id, "payment_failed")
                self.bus.publish(
                    "PaymentFailed", attempt.order_id, {"reservationId": reservation_id}
                )
            else:
                self.bus.publish(
                    "PaymentPendingReconciliation",
                    attempt.order_id,
                    {"reservationId": reservation_id},
                )
            return attempt


class TicketingService:
    def __init__(self, bus: EventBus) -> None:
        self.tickets: dict[str, dict[str, str]] = {}
        self.bus = bus
        bus.subscribe("PaymentSucceeded", self._issue)

    def _issue(self, event: DomainEvent) -> None:
        reservation_id = str(event.payload["reservationId"])
        if reservation_id in self.tickets:
            return
        ticket = {"id": str(uuid4()), "reservationId": reservation_id, "qrHash": str(uuid4())}
        self.tickets[reservation_id] = ticket
        self.bus.publish("TicketIssued", ticket["id"], ticket)


class NotificationService:
    def __init__(self, bus: EventBus) -> None:
        self.deliveries: list[dict[str, str]] = []
        bus.subscribe("TicketIssued", self._record)
        bus.subscribe("PaymentFailed", self._record)

    def _record(self, event: DomainEvent) -> None:
        self.deliveries.append({"eventId": event.event_id, "type": event.event_type})
