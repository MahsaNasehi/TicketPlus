import tempfile
import unittest
from pathlib import Path

from ticketplus.catalog import EventCatalog, InvalidEvent


class EventCatalogTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.catalog = EventCatalog(Path(self.temp.name) / "catalog.db")

    def tearDown(self):
        self.temp.cleanup()

    def _rows(self, **overrides):
        rows = [
            {"label": "A", "seats": 10, "priceMinor": 5_000_000},
            {"label": "B", "seats": 8, "priceMinor": 3_000_000},
        ]
        rows[0].update(overrides)
        return rows

    def test_create_event_round_trips_the_real_frontend_shape(self):
        event = self.catalog.create_event("Show", "City Theatre", "1404/05/02", self._rows())
        self.assertEqual(event["title"], "Show")
        self.assertEqual(event["venue"], "City Theatre")
        self.assertEqual(event["dateLabel"], "1404/05/02")
        self.assertEqual(
            event["rows"],
            [
                {"label": "A", "seats": 10, "priceMinor": 5_000_000},
                {"label": "B", "seats": 8, "priceMinor": 3_000_000},
            ],
        )
        self.assertEqual(self.catalog.get(event["id"]), event)
        self.assertEqual(self.catalog.list(), [event])

    def test_row_price_at_or_below_100000_toman_is_rejected(self):
        with self.assertRaises(InvalidEvent):
            self.catalog.create_event(
                "Show", "City Theatre", "1404/05/02",
                [{"label": "A", "seats": 10, "priceMinor": 1_000_000}],  # exactly 100,000 Toman
            )

    def test_a_single_underpriced_row_rejects_the_whole_event_even_if_others_are_valid(self):
        rows = [
            {"label": "A", "seats": 10, "priceMinor": 5_000_000},  # fine
            {"label": "B", "seats": 8, "priceMinor": 300_000},     # 30,000 Toman: too low
        ]
        with self.assertRaises(InvalidEvent):
            self.catalog.create_event("Show", "City Theatre", "1404/05/02", rows)

    def test_missing_title_venue_or_date_label_is_rejected(self):
        for title, venue, date_label in [("", "V", "D"), ("T", "", "D"), ("T", "V", "")]:
            with self.assertRaises(InvalidEvent):
                self.catalog.create_event(title, venue, date_label, self._rows())

    def test_empty_rows_is_rejected(self):
        with self.assertRaises(InvalidEvent):
            self.catalog.create_event("Show", "City Theatre", "1404/05/02", [])

    def test_duplicate_row_labels_are_rejected(self):
        rows = [
            {"label": "A", "seats": 10, "priceMinor": 5_000_000},
            {"label": "A", "seats": 8, "priceMinor": 3_000_000},
        ]
        with self.assertRaises(InvalidEvent):
            self.catalog.create_event("Show", "City Theatre", "1404/05/02", rows)

    def test_non_positive_seats_is_rejected(self):
        with self.assertRaises(InvalidEvent):
            self.catalog.create_event(
                "Show", "City Theatre", "1404/05/02",
                [{"label": "A", "seats": 0, "priceMinor": 5_000_000}],
            )

    def test_list_is_ordered_by_creation(self):
        first = self.catalog.create_event("First", "V", "D", self._rows())
        second = self.catalog.create_event("Second", "V", "D", self._rows())
        self.assertEqual([e["id"] for e in self.catalog.list()], [first["id"], second["id"]])


if __name__ == "__main__":
    unittest.main()
