import importlib
import json
import os
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path


class HttpApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        os.environ["DATABASE_PATH"] = str(Path(cls.temp.name) / "api.db")
        cls.api = importlib.import_module("ticketplus.http_api")
        try:
            cls.server = ThreadingHTTPServer(("127.0.0.1", 0), cls.api.Handler)
        except PermissionError as error:
            cls.temp.cleanup()
            raise unittest.SkipTest("environment forbids loopback sockets") from error
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base = f"http://127.0.0.1:{cls.server.server_port}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=2)
        cls.temp.cleanup()

    def request(self, method, path, body=None, key=None):
        data = json.dumps(body).encode() if body is not None else None
        request = urllib.request.Request(self.base + path, data=data, method=method)
        if data:
            request.add_header("Content-Type", "application/json")
        if key:
            request.add_header("Idempotency-Key", key)
        try:
            with urllib.request.urlopen(request) as response:
                return response.status, json.load(response)
        except urllib.error.HTTPError as error:
            return error.code, json.load(error)

    def test_health_reservation_checkout_and_ticket_journey(self):
        status, health = self.request("GET", "/health/ready")
        self.assertEqual((200, "UP"), (status, health["status"]))

        payload = {"userId": "buyer", "eventId": "event", "seatIds": ["A-1"]}
        status, reservation = self.request("POST", "/reservations", payload, "reserve-0001")
        self.assertEqual(201, status)
        status, duplicate = self.request("POST", "/reservations", payload, "reserve-0002")
        self.assertEqual((409, "seat_unavailable"), (status, duplicate["error"]))

        status, fetched = self.request("GET", f"/reservations/{reservation['id']}")
        self.assertEqual((200, reservation["id"]), (status, fetched["id"]))
        checkout = {"reservationId": reservation["id"], "amountMinor": 10000, "currency": "IRR"}
        status, _ = self.request("POST", "/checkouts", checkout, "payment-0001")
        self.assertEqual(200, status)
        status, ticket = self.request("GET", f"/tickets/by-reservation/{reservation['id']}")
        self.assertEqual((200, reservation["id"]), (status, ticket["reservationId"]))

    def test_validation_and_not_found(self):
        status, body = self.request(
            "POST", "/reservations", {"userId": "u", "eventId": "e", "seatIds": ["S"]}, "short"
        )
        self.assertEqual((400, "invalid_request"), (status, body["error"]))
        status, body = self.request("GET", "/missing")
        self.assertEqual((404, "not_found"), (status, body["error"]))


if __name__ == "__main__":
    unittest.main()
