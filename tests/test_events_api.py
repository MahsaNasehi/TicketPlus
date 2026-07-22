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


class EventsApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        os.environ["DATABASE_PATH"] = str(Path(cls.temp.name) / "api.db")
        cls.api = importlib.import_module("ticketplus.http_api")
        # http_api builds its service singletons (reservations/auth/catalog) at
        # *import* time from the DATABASE_PATH above. Since Python caches
        # modules by name, a plain import_module() would silently hand back
        # whatever instance another test class already created against a
        # different (possibly already-cleaned-up) temp directory. Reload so
        # this class gets its own isolated instances every time.
        cls.api = importlib.reload(cls.api)
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

    def request(self, method, path, body=None, token=None):
        data = json.dumps(body).encode() if body is not None else None
        request = urllib.request.Request(self.base + path, data=data, method=method)
        if data:
            request.add_header("Content-Type", "application/json")
        if token:
            request.add_header("Authorization", f"Bearer {token}")
        try:
            with urllib.request.urlopen(request) as response:
                return response.status, json.load(response)
        except urllib.error.HTTPError as error:
            return error.code, json.load(error)

    def register(self, email, role=None):
        body = {"email": email, "password": "change-me-please", "name": "Someone"}
        if role is not None:
            body["role"] = role
        status, result = self.request("POST", "/auth/register", body)
        self.assertEqual(201, status, result)
        return result["token"], result["user"]

    def test_get_events_returns_seeded_default_events_wrapped_in_events_key(self):
        status, body = self.request("GET", "/events")
        self.assertEqual(200, status)
        self.assertIn("events", body)
        self.assertGreaterEqual(len(body["events"]), 1)
        first = body["events"][0]
        for field in ("id", "title", "venue", "dateLabel", "rows"):
            self.assertIn(field, first)

    def test_register_with_role_admin_actually_grants_admin_role(self):
        _, user = self.register("admin-role-test@example.com", role="admin")
        self.assertEqual("admin", user["role"])

    def test_register_without_role_defaults_to_user(self):
        _, user = self.register("plain-user-test@example.com")
        self.assertEqual("user", user["role"])

    def test_admin_can_create_event_with_venue_date_and_rows_payload(self):
        token, _ = self.register("admin-create-test@example.com", role="admin")
        status, event = self.request(
            "POST",
            "/events",
            {
                "title": "New Show",
                "venue": "New Hall",
                "dateLabel": "Sun",
                "rows": [{"label": "A", "seats": 3, "priceMinor": 150_000}],
            },
            token=token,
        )
        self.assertEqual(201, status, event)
        self.assertEqual(event["venue"], "New Hall")
        self.assertEqual(event["rows"][0]["priceMinor"], 150_000)

    def test_non_admin_cannot_create_event(self):
        token, _ = self.register("regular-user-test@example.com")
        status, body = self.request(
            "POST",
            "/events",
            {"title": "Nope", "venue": "Hall", "dateLabel": "Sun", "rows": [{"label": "A", "seats": 1, "priceMinor": 200_000}]},
            token=token,
        )
        self.assertEqual(403, status)

    def test_event_with_row_price_at_threshold_is_rejected(self):
        token, _ = self.register("admin-price-test@example.com", role="admin")
        status, body = self.request(
            "POST",
            "/events",
            {
                "title": "Too Cheap",
                "venue": "Hall",
                "dateLabel": "Sun",
                "rows": [{"label": "A", "seats": 1, "priceMinor": 100_000}],
            },
            token=token,
        )
        self.assertEqual(400, status)

    def test_admin_can_edit_an_existing_event(self):
        token, _ = self.register("admin-edit-test@example.com", role="admin")
        _, created = self.request(
            "POST",
            "/events",
            {
                "title": "Original",
                "venue": "Original Hall",
                "dateLabel": "Mon",
                "rows": [{"label": "A", "seats": 5, "priceMinor": 150_000}],
            },
            token=token,
        )
        status, updated = self.request(
            "PUT",
            f"/events/{created['id']}",
            {
                "title": "Updated",
                "venue": "Updated Hall",
                "dateLabel": "Tue",
                "rows": [{"label": "A", "seats": 7, "priceMinor": 175_000}],
            },
            token=token,
        )
        self.assertEqual(200, status, updated)
        self.assertEqual(updated["id"], created["id"])
        self.assertEqual(updated["title"], "Updated")
        self.assertEqual(updated["venue"], "Updated Hall")

        status, listed = self.request("GET", "/events")
        edited = next(e for e in listed["events"] if e["id"] == created["id"])
        self.assertEqual(edited["title"], "Updated")

    def test_non_admin_cannot_edit_an_event(self):
        admin_token, _ = self.register("admin-edit-guard-test@example.com", role="admin")
        _, created = self.request(
            "POST",
            "/events",
            {"title": "T", "venue": "V", "dateLabel": "D", "rows": [{"label": "A", "seats": 1, "priceMinor": 200_000}]},
            token=admin_token,
        )
        user_token, _ = self.register("user-edit-guard-test@example.com")
        status, _ = self.request(
            "PUT",
            f"/events/{created['id']}",
            {"title": "Hacked", "venue": "V", "dateLabel": "D", "rows": [{"label": "A", "seats": 1, "priceMinor": 200_000}]},
            token=user_token,
        )
        self.assertEqual(403, status)

    def test_editing_a_missing_event_returns_404(self):
        token, _ = self.register("admin-edit-missing-test@example.com", role="admin")
        status, _ = self.request(
            "PUT",
            "/events/does-not-exist",
            {"title": "T", "venue": "V", "dateLabel": "D", "rows": [{"label": "A", "seats": 1, "priceMinor": 200_000}]},
            token=token,
        )
        self.assertEqual(404, status)


if __name__ == "__main__":
    unittest.main()
