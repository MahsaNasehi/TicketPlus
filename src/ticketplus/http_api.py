"""Dependency-free HTTP adapter for the local TicketPlus reference environment."""

import json
import os
from dataclasses import asdict
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from .auth import AuthService, EmailAlreadyRegistered, InvalidCredentials, NotAuthorized
from .catalog import EventCatalog, InvalidEvent
from .checkout import CheckoutService, NotificationService, PaymentResult, TicketingService
from .events import EventBus
# اضافه کردن ReservationNotFound برای مدیریت خطای عدم وجود رزرویشن
from .reservation import LockConflict, ReservationService, ReservationNotFound


bus = EventBus()
reservations = ReservationService(Path(os.getenv("DATABASE_PATH", "/data/ticketplus.db")), bus)
auth = AuthService(Path(os.getenv("AUTH_DATABASE_PATH", os.getenv("DATABASE_PATH", "/data/ticketplus.db"))))
catalog = EventCatalog(Path(os.getenv("DATABASE_PATH", "/data/ticketplus.db")))


def gateway(idempotency_key: str, amount_minor: int, currency: str):
    outcome = os.getenv("PAYMENT_OUTCOME", "SUCCEEDED")
    return PaymentResult(outcome), f"local-{idempotency_key}"


checkout = CheckoutService(reservations, bus, gateway)
ticketing = TicketingService(bus)
notifications = NotificationService(bus)


class Handler(BaseHTTPRequestHandler):
    def _cors_headers(self) -> None:
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Idempotency-Key, Authorization")

    def _json(self, status: int, payload: object) -> None:
        body = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self._cors_headers()
        self.end_headers()
        self.wfile.write(body)

    def _body(self) -> dict:
        length = int(self.headers.get("Content-Length", "0"))
        return json.loads(self.rfile.read(length) or b"{}")

    def do_OPTIONS(self) -> None:
        self.send_response(HTTPStatus.NO_CONTENT)
        self._cors_headers()
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_GET(self) -> None:
        try:
            path = urlparse(self.path).path
            if path in {"/health/live", "/health/ready"}:
                self._json(HTTPStatus.OK, {"status": "UP"})
                return
            if path == "/auth/me":
                try:
                    user = auth.user_from_auth_header(self.headers.get("Authorization"))
                    self._json(HTTPStatus.OK, {"user": user})
                except InvalidCredentials as error:
                    self._json(HTTPStatus.UNAUTHORIZED, {"error": "unauthorized", "message": str(error)})
                return
            if path == "/events":
                self._json(HTTPStatus.OK, catalog.list())
                return
            if path.startswith("/events/") and path.endswith("/seats"):
                event_id = path.split("/")[2]
                self._json(HTTPStatus.OK, reservations.seat_statuses(event_id))
                return
            if path.startswith("/reservations/"):
                reservation_id = path.rsplit("/", 1)[-1]
                self._json(HTTPStatus.OK, reservations.get(reservation_id))
                return
            if path.startswith("/tickets/by-reservation/"):
                reservation_id = path.rsplit("/", 1)[-1]
                ticket = ticketing.tickets.get(reservation_id)
                self._json(HTTPStatus.OK if ticket else HTTPStatus.NOT_FOUND, ticket or {"error": "not_found"})
                return
            self._json(HTTPStatus.NOT_FOUND, {"error": "not_found"})
        except ReservationNotFound as error:
            # مدیریت خطای عدم وجود رزرویشن با بازگرداندن پاسخ ۴۰۴
            self._json(HTTPStatus.NOT_FOUND, {"error": "reservation_not_found", "message": str(error)})
        except InvalidEvent as error:
            self._json(HTTPStatus.NOT_FOUND, {"error": "event_not_found", "message": str(error)})
        except InvalidCredentials as error:
            self._json(HTTPStatus.UNAUTHORIZED, {"error": "unauthorized", "message": str(error)})
        except Exception as error:
            # مدیریت سایر خطاهای پیش‌بینی نشده برای جلوگیری از کرش کردن ورکر
            self._json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": "internal_error", "message": str(error)})

    def do_POST(self) -> None:
        try:
            path = urlparse(self.path).path
            body = self._body()
            if path == "/auth/register":
                user = auth.register(body.get("email", ""), body.get("password", ""), body.get("name", ""))
                token = auth.issue_token(user["id"])
                self._json(HTTPStatus.CREATED, {"token": token, "user": user})
                return
            if path == "/auth/login":
                user = auth.login(body.get("email", ""), body.get("password", ""))
                token = auth.issue_token(user["id"])
                self._json(HTTPStatus.OK, {"token": token, "user": user})
                return
            if path == "/events":
                auth.require_admin(self.headers.get("Authorization"))
                event = catalog.create_event(body.get("title", ""), body.get("priceToman"))
                self._json(HTTPStatus.CREATED, event)
                return
            if path == "/reservations":
                idempotency_key = self.headers.get("Idempotency-Key", "")
                if len(idempotency_key) < 8:
                    raise ValueError("Idempotency-Key must contain at least 8 characters")
                result = reservations.lock_seats(
                    body["userId"],
                    body["eventId"],
                    body["seatIds"],
                    idempotency_key,
                )
                self._json(HTTPStatus.CREATED, result)
                return
            if path == "/checkouts":
                idempotency_key = self.headers.get("Idempotency-Key", "")
                if len(idempotency_key) < 8:
                    raise ValueError("Idempotency-Key must contain at least 8 characters")
                result = checkout.checkout(
                    body["reservationId"],
                    body["amountMinor"],
                    body["currency"],
                    idempotency_key,
                )
                self._json(HTTPStatus.OK, asdict(result))
                return
            self._json(HTTPStatus.NOT_FOUND, {"error": "not_found"})
        except LockConflict as error:
            self._json(HTTPStatus.CONFLICT, {"error": "seat_unavailable", "message": str(error)})
        except EmailAlreadyRegistered as error:
            self._json(HTTPStatus.CONFLICT, {"error": "email_taken", "message": f"{error} is already registered"})
        except NotAuthorized as error:
            self._json(HTTPStatus.FORBIDDEN, {"error": "forbidden", "message": str(error)})
        except InvalidCredentials as error:
            self._json(HTTPStatus.UNAUTHORIZED, {"error": "invalid_credentials", "message": str(error)})
        except InvalidEvent as error:
            self._json(HTTPStatus.BAD_REQUEST, {"error": "invalid_event", "message": str(error)})
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
