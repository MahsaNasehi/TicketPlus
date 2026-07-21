#!/usr/bin/env python3
"""Seed the TicketPlus catalog with 3 fictitious demo theaters.

Each demo event has a different number of seating rows, seat counts, and
per-seat prices, so the "add theater" admin panel and the seat map have
something realistic to show right after setup.

Usage:
    cd TicketPlus
    PYTHONPATH=src DATABASE_PATH=./ticketplus.db python3 scripts/seed_demo_events.py

`DATABASE_PATH` should point at the same SQLite file the backend
(`ticketplus.http_api`) is configured with, so the seeded events show up
in the running app. Safe to re-run: any event whose title already exists
in the catalog is skipped instead of being duplicated.
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from ticketplus.catalog import EventCatalog, InvalidEvent  # noqa: E402

RIAL_PER_TOMAN = 10


def toman(amount: int) -> int:
    """Convert a price given in Toman to Rial — the unit `priceMinor` is stored in."""
    return amount * RIAL_PER_TOMAN


DEMO_EVENTS = [
    {
        "title": "شب‌های کمدی",
        "venue": "تئاتر شهر",
        "dateLabel": "۱۴۰۴/۰۶/۱۵",
        "rows": [
            {"label": "A", "seats": 12, "priceMinor": toman(750_000)},
            {"label": "B", "seats": 20, "priceMinor": toman(450_000)},
            {"label": "C", "seats": 30, "priceMinor": toman(250_000)},
        ],
    },
    {
        "title": "کنسرت ارکستر سمفونیک تهران",
        "venue": "سالن رودکی",
        "dateLabel": "۱۴۰۴/۰۷/۰۲",
        "rows": [
            {"label": "VIP", "seats": 10, "priceMinor": toman(2_000_000)},
            {"label": "A", "seats": 40, "priceMinor": toman(900_000)},
            {"label": "B", "seats": 60, "priceMinor": toman(500_000)},
        ],
    },
    {
        "title": "نمایش موزیکال شب‌های روشن",
        "venue": "تئاتر ایرانشهر",
        "dateLabel": "۱۴۰۴/۰۵/۲۸",
        "rows": [
            {"label": "A", "seats": 15, "priceMinor": toman(600_000)},
            {"label": "B", "seats": 25, "priceMinor": toman(350_000)},
            {"label": "C", "seats": 35, "priceMinor": toman(150_000)},
        ],
    },
]


def main() -> int:
    database_path = os.getenv("DATABASE_PATH", "/data/ticketplus.db")
    catalog = EventCatalog(Path(database_path))
    existing_titles = {event["title"] for event in catalog.list()}

    exit_code = 0
    for demo in DEMO_EVENTS:
        if demo["title"] in existing_titles:
            print(f"skip (already exists): {demo['title']}")
            continue
        try:
            created = catalog.create_event(
                demo["title"], demo["venue"], demo["dateLabel"], demo["rows"]
            )
        except InvalidEvent as error:
            print(f"failed: {demo['title']} -> {error}", file=sys.stderr)
            exit_code = 1
            continue
        seat_total = sum(row["seats"] for row in created["rows"])
        row_summary = ", ".join(
            f"{row['label']}: {row['seats']} seats @ {row['priceMinor'] // RIAL_PER_TOMAN:,} Toman"
            for row in created["rows"]
        )
        print(f"created: {created['title']} ({created['venue']}, {seat_total} seats total)")
        print(f"    {row_summary}")
        print(f"    id={created['id']}")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
