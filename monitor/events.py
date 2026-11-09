"""Event log (SQLite) and optional Telegram alerts. Only events and counts are stored, never video."""
from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime

import httpx


class EventLog:
    def __init__(self, path: str = "events.db"):
        self._db = sqlite3.connect(path)
        self._db.execute(
            "CREATE TABLE IF NOT EXISTS events (ts TEXT, camera TEXT, type TEXT, zone TEXT, data TEXT)"
        )
        self._db.commit()

    def add(self, camera: str, event: dict, ts: datetime) -> None:
        self._db.execute(
            "INSERT INTO events VALUES (?, ?, ?, ?, ?)",
            (ts.isoformat(timespec="seconds"), camera, event["type"], event.get("zone"), json.dumps(event)),
        )
        self._db.commit()

    def count(self, type_: str, day: str) -> int:
        cur = self._db.execute("SELECT COUNT(*) FROM events WHERE type = ? AND ts LIKE ?", (type_, day + "%"))
        return cur.fetchone()[0]


def send_alert(text: str, snapshot_jpeg: bytes | None = None) -> None:
    token, chat = os.environ.get("TELEGRAM_BOT_TOKEN"), os.environ.get("ALERT_CHAT_ID")
    if not token or not chat:
        return
    base = f"https://api.telegram.org/bot{token}"
    try:
        if snapshot_jpeg:
            httpx.post(f"{base}/sendPhoto", data={"chat_id": chat, "caption": text},
                       files={"photo": ("frame.jpg", snapshot_jpeg, "image/jpeg")}, timeout=15)
        else:
            httpx.post(f"{base}/sendMessage", data={"chat_id": chat, "text": text}, timeout=15)
    except httpx.HTTPError:
        pass
