import tempfile
import unittest
from pathlib import Path

from ticketplus.catalog import EventCatalog, EventNotFound, InvalidEvent


VALID_ROWS = [{"label": "A", "seats": 5, "priceMinor": 200_000}]


class EventCatalogTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp.name) / "catalog.db"

    def tearDown(self):
        self.temp.cleanup()

    def test_fresh_catalog_is_seeded_with_default_events(self):
        catalog = EventCatalog(self.db_path)
        events = catalog.list()
        self.assertGreaterEqual(len(events), 1)
        for event in events:
            self.assertTrue(event["title"])
            self.assertTrue(event["venue"])
            self.assertTrue(event["dateLabel"])
            self.assertTrue(event["rows"])

    def test_seeding_is_skipped_when_disabled(self):
        catalog = EventCatalog(self.db_path, seed_defaults=False)
        self.assertEqual(catalog.list(), [])

    def test_seeding_only_happens_once(self):
        EventCatalog(self.db_path)
        seeded_count = len(EventCatalog(self.db_path, seed_defaults=False).list())
        # Re-instantiating with seeding enabled again must not duplicate events.
        again = EventCatalog(self.db_path)
        self.assertEqual(seeded_count, len(again.list()))

    def test_create_event_requires_title_venue_and_date(self):
        catalog = EventCatalog(self.db_path, seed_defaults=False)
        with self.assertRaises(InvalidEvent):
            catalog.create_event("", "Venue", "Sat", VALID_ROWS)
        with self.assertRaises(InvalidEvent):
            catalog.create_event("Title", "", "Sat", VALID_ROWS)
        with self.assertRaises(InvalidEvent):
            catalog.create_event("Title", "Venue", "", VALID_ROWS)

    def test_create_event_rejects_row_price_at_or_below_threshold(self):
        catalog = EventCatalog(self.db_path, seed_defaults=False)
        with self.assertRaises(InvalidEvent):
            catalog.create_event(
                "Title", "Venue", "Sat", [{"label": "A", "seats": 5, "priceMinor": 100_000}]
            )

    def test_create_event_rejects_missing_rows(self):
        catalog = EventCatalog(self.db_path, seed_defaults=False)
        with self.assertRaises(InvalidEvent):
            catalog.create_event("Title", "Venue", "Sat", [])

    def test_create_event_succeeds_with_valid_data(self):
        catalog = EventCatalog(self.db_path, seed_defaults=False)
        event = catalog.create_event("Title", "Venue", "Sat", VALID_ROWS)
        self.assertEqual(event["title"], "Title")
        self.assertEqual(event["venue"], "Venue")
        self.assertEqual(event["rows"], VALID_ROWS)
        self.assertEqual(catalog.list(), [event])

    def test_update_event_overwrites_fields_and_keeps_id(self):
        catalog = EventCatalog(self.db_path, seed_defaults=False)
        original = catalog.create_event("Title", "Venue", "Sat", VALID_ROWS)
        new_rows = [{"label": "A", "seats": 9, "priceMinor": 250_000}]
        updated = catalog.update_event(original["id"], "New Title", "New Venue", "Sun", new_rows)
        self.assertEqual(updated["id"], original["id"])
        self.assertEqual(updated["title"], "New Title")
        self.assertEqual(updated["venue"], "New Venue")
        self.assertEqual(updated["dateLabel"], "Sun")
        self.assertEqual(updated["rows"], new_rows)
        self.assertEqual(catalog.get(original["id"]), updated)

    def test_update_event_raises_when_id_does_not_exist(self):
        catalog = EventCatalog(self.db_path, seed_defaults=False)
        with self.assertRaises(EventNotFound):
            catalog.update_event("missing-id", "Title", "Venue", "Sat", VALID_ROWS)

    def test_update_event_validates_like_create(self):
        catalog = EventCatalog(self.db_path, seed_defaults=False)
        original = catalog.create_event("Title", "Venue", "Sat", VALID_ROWS)
        with self.assertRaises(InvalidEvent):
            catalog.update_event(original["id"], "", "Venue", "Sat", VALID_ROWS)
        with self.assertRaises(InvalidEvent):
            catalog.update_event(
                original["id"], "Title", "Venue", "Sat",
                [{"label": "A", "seats": 5, "priceMinor": 100_000}],
            )
        # a failed update must not have mutated the stored event
        self.assertEqual(catalog.get(original["id"]), original)


if __name__ == "__main__":
    unittest.main()
