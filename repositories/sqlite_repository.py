import sqlite3
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from models import Offer
from repositories.offers_repository import OffersRepository

SCHEMA = """
CREATE TABLE IF NOT EXISTS notified_offers (
    key TEXT PRIMARY KEY,
    origin TEXT NOT NULL,
    destination TEXT NOT NULL,
    depart_date TEXT NOT NULL,
    return_date TEXT NOT NULL,
    price TEXT NOT NULL,
    currency TEXT NOT NULL,
    source TEXT NOT NULL,
    notified_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS api_usage (
    provider TEXT NOT NULL,
    month TEXT NOT NULL,
    count INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (provider, month)
);
CREATE TABLE IF NOT EXISTS cursors (
    name TEXT PRIMARY KEY,
    value INTEGER NOT NULL
);
"""


class SqliteOffersRepository(OffersRepository):
    def __init__(self, path: str):
        self._conn = sqlite3.connect(path)
        self._conn.executescript(SCHEMA)
        self._conn.commit()

    def last_notified_price(self, key: str) -> Optional[Decimal]:
        row = self._conn.execute("SELECT price FROM notified_offers WHERE key = ?", (key,)).fetchone()
        return Decimal(row[0]) if row else None

    def mark_notified(self, offer: Offer) -> None:
        with self._conn:
            self._conn.execute(
                """INSERT INTO notified_offers
                   (key, origin, destination, depart_date, return_date, price, currency, source, notified_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(key) DO UPDATE SET price = excluded.price, currency = excluded.currency,
                       source = excluded.source, notified_at = excluded.notified_at""",
                (
                    offer.key,
                    offer.origin,
                    offer.destination,
                    offer.depart_date.isoformat(),
                    offer.return_date.isoformat(),
                    str(offer.price),
                    offer.currency,
                    offer.source,
                    datetime.now(timezone.utc).isoformat(),
                ),
            )

    def searches_this_month(self, provider: str, month: str) -> int:
        row = self._conn.execute(
            "SELECT count FROM api_usage WHERE provider = ? AND month = ?", (provider, month)
        ).fetchone()
        return row[0] if row else 0

    def record_search(self, provider: str, month: str) -> None:
        with self._conn:
            self._conn.execute(
                """INSERT INTO api_usage (provider, month, count) VALUES (?, ?, 1)
                   ON CONFLICT(provider, month) DO UPDATE SET count = count + 1""",
                (provider, month),
            )

    def get_cursor(self, name: str) -> int:
        row = self._conn.execute("SELECT value FROM cursors WHERE name = ?", (name,)).fetchone()
        return row[0] if row else 0

    def set_cursor(self, name: str, value: int) -> None:
        with self._conn:
            self._conn.execute(
                "INSERT INTO cursors (name, value) VALUES (?, ?) "
                "ON CONFLICT(name) DO UPDATE SET value = excluded.value",
                (name, value),
            )

    def close(self) -> None:
        self._conn.close()
