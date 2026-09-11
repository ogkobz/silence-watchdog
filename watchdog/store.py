"""Хранилище последних событий и отправленных алертов.

SQLite выбран сознательно: сторож должен переживать перезапуск, но не должен
тащить за собой отдельную базу — иначе он сам становится тем, за чем надо следить.
"""
from __future__ import annotations

import sqlite3
from contextlib import closing
from typing import Optional

SCHEMA = """
CREATE TABLE IF NOT EXISTS heartbeats (
    source     TEXT PRIMARY KEY,
    last_seen  INTEGER NOT NULL,
    payload    TEXT
);
CREATE TABLE IF NOT EXISTS alerts (
    source     TEXT PRIMARY KEY,
    sent_at    INTEGER NOT NULL,
    silent_for INTEGER NOT NULL
);
"""


class Store:
    def __init__(self, path: str = "data/watchdog.db") -> None:
        self.path = path
        with closing(self._connect()) as conn:
            conn.executescript(SCHEMA)
            conn.commit()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        return conn

    def heartbeat(self, source: str, now: int, payload: Optional[str] = None) -> None:
        with closing(self._connect()) as conn:
            conn.execute(
                "INSERT INTO heartbeats(source, last_seen, payload) VALUES(?,?,?) "
                "ON CONFLICT(source) DO UPDATE SET last_seen=excluded.last_seen, "
                "payload=excluded.payload",
                (source, now, payload),
            )
            conn.commit()

    def last_seen(self, source: str) -> Optional[int]:
        with closing(self._connect()) as conn:
            row = conn.execute(
                "SELECT last_seen FROM heartbeats WHERE source = ?", (source,)
            ).fetchone()
        return int(row["last_seen"]) if row else None

    def all_last_seen(self) -> dict[str, int]:
        with closing(self._connect()) as conn:
            rows = conn.execute("SELECT source, last_seen FROM heartbeats").fetchall()
        return {row["source"]: int(row["last_seen"]) for row in rows}

    def alert_sent_at(self, source: str) -> Optional[int]:
        with closing(self._connect()) as conn:
            row = conn.execute(
                "SELECT sent_at FROM alerts WHERE source = ?", (source,)
            ).fetchone()
        return int(row["sent_at"]) if row else None

    def record_alert(self, source: str, now: int, silent_for: int) -> None:
        with closing(self._connect()) as conn:
            conn.execute(
                "INSERT INTO alerts(source, sent_at, silent_for) VALUES(?,?,?) "
                "ON CONFLICT(source) DO UPDATE SET sent_at=excluded.sent_at, "
                "silent_for=excluded.silent_for",
                (source, now, silent_for),
            )
            conn.commit()

    def clear_alert(self, source: str) -> None:
        with closing(self._connect()) as conn:
            conn.execute("DELETE FROM alerts WHERE source = ?", (source,))
            conn.commit()
