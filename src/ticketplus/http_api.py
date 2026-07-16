"""Dependency-free HTTP adapter for the local TicketPlus reference environment."""

import json
import os
from dataclasses import asdict
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from .checkout import CheckoutService, NotificationService, PaymentResult, TicketingService
from .events import EventBus
from .reservation import LockConflict, ReservationService


bus = EventBus()
reservations = ReservationService(Path(os.getenv("DATABASE_PATH", "/data/ticketplus.db")), bus)


def gateway(idempotency_key: str, amount_minor: int, currency: str):
    outcome = os.getenv("PAYMENT_OUTCOME", "SUCCEEDED")
    return PaymentResult(outcome), f"local-{idempotency_key}"


checkout = CheckoutService(reservations, bus, gateway)
ticketing = TicketingService(bus)
notifications = NotificationService(bus)


class Handler(BaseHTTPRequestHandler):
    def _json(self, status: int, payload: object) -> None:
        body = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _body(self) -> dict:
        length = int(self.headers.get("Content-Length", "0"))
        return json.loads(self.rfile.read(length) or b"{}")

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path in {"/health/live", "/health/ready"}:
            self._json(HTTPStatus.OK, {"status": "UP"})
            return
        if path.startswith("/reservations/"):
            self._json(HTTPStatus.OK, reservations.get(path.rsplit("/", 1)[-1]))
            return
        if path.startswith("/tickets/by-reservation/"):
            reservation_id = path.rsplit("/", 1)[-1]
            ticket = ticketing.tickets.get(reservation_id)
            self._json(HTTPStatus.OK if ticket else HTTPStatus.NOT_FOUND, ticket or {"error": "not_found"})
            return
        self._json(HTTPStatus.NOT_FOUND, {"error": "not_found"})

    def do_POST(self) -> None:
        try:
            path = urlparse(self.path).path
            body = self._body()
            if path == "/reservations":
                result = reservations.lock_seats(
                    body["userId"],
                    body["eventId"],
                    body["seatIds"],
                    self.headers.get("Idempotency-Key", ""),
                )
                self._json(HTTPStatus.CREATED, result)
                return
            if path == "/checkouts":
                result = checkout.checkout(
                    body["reservationId"],
                    body["amountMinor"],
                    body["currency"],
                    self.headers.get("Idempotency-Key", ""),
                )
                self._json(HTTPStatus.OK, asdict(result))
                return
            self._json(HTTPStatus.NOT_FOUND, {"error": "not_found"})
        except LockConflict as error:
            self._json(HTTPStatus.CONFLICT, {"error": "seat_unavailable", "message": str(error)})
        except (KeyError, ValueError) as error:
            self._json(HTTPStatus.BAD_REQUEST, {"error": "invalid_request", "message": str(error)})
        except Exception as error:
            self._json(HTTPStatus.CONFLICT, {"error": type(error).__name__, "message": str(error)})

    def log_message(self, format: str, *args) -> None:
        print(json.dumps({"message": format % args}))


def main() -> None:
    server = ThreadingHTTPServer(("0.0.0.0", int(os.getenv("PORT", "8080"))), Handler)
    server.serve_forever()


if __name__ == "__main__":
    main()

