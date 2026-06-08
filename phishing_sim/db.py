"""SQLite storage for campaigns, recipients, and click/submit events."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone

from .models import Campaign, EVT_CLICK, EVT_SUBMIT, Recipient

SCHEMA = """
CREATE TABLE IF NOT EXISTS campaigns (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    name       TEXT NOT NULL,
    template   TEXT NOT NULL DEFAULT 'it_portal',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS recipients (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    campaign_id INTEGER NOT NULL REFERENCES campaigns(id),
    name        TEXT NOT NULL,
    email       TEXT NOT NULL,
    token       TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS events (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    recipient_id INTEGER NOT NULL REFERENCES recipients(id),
    event_type   TEXT NOT NULL,
    occurred_at  TEXT NOT NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_events_recipient_type
    ON events(recipient_id, event_type);
CREATE INDEX IF NOT EXISTS idx_recipients_campaign ON recipients(campaign_id);
CREATE INDEX IF NOT EXISTS idx_recipients_token ON recipients(token);
"""


def connect(db_path: str = ":memory:") -> sqlite3.Connection:
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    return conn


def create_campaign(conn: sqlite3.Connection, name: str, template: str = "it_portal") -> int:
    cur = conn.execute(
        "INSERT INTO campaigns (name, template, created_at) VALUES (?, ?, ?)",
        (name, template, datetime.now(timezone.utc).isoformat()),
    )
    conn.commit()
    return cur.lastrowid


def add_recipient(conn: sqlite3.Connection, campaign_id: int,
                  name: str, email: str, token: str) -> int:
    cur = conn.execute(
        "INSERT INTO recipients (campaign_id, name, email, token) VALUES (?, ?, ?, ?)",
        (campaign_id, name, email, token),
    )
    conn.commit()
    return cur.lastrowid


def record_event(conn: sqlite3.Connection, token: str, event_type: str) -> bool:
    """Record a click or submit event for the recipient identified by token.

    Returns True if the event was newly recorded, False if it was already
    present (the UNIQUE index on (recipient_id, event_type) prevents double-
    counting without raising an exception — we just swallow the conflict).
    """
    row = conn.execute("SELECT id FROM recipients WHERE token = ?", (token,)).fetchone()
    if not row:
        return False
    try:
        conn.execute(
            "INSERT INTO events (recipient_id, event_type, occurred_at) VALUES (?, ?, ?)",
            (row["id"], event_type, datetime.now(timezone.utc).isoformat()),
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False


def fetch_campaign(conn: sqlite3.Connection, campaign_id: int) -> Campaign | None:
    row = conn.execute("SELECT * FROM campaigns WHERE id = ?", (campaign_id,)).fetchone()
    if not row:
        return None
    return _hydrate_campaign(conn, row)


def fetch_all_campaigns(conn: sqlite3.Connection) -> list[Campaign]:
    rows = conn.execute("SELECT * FROM campaigns ORDER BY id").fetchall()
    return [_hydrate_campaign(conn, r) for r in rows]


def _hydrate_campaign(conn: sqlite3.Connection, row: sqlite3.Row) -> Campaign:
    recipient_rows = conn.execute(
        "SELECT r.*, "
        "  (SELECT occurred_at FROM events WHERE recipient_id=r.id AND event_type=?) AS clicked_at, "
        "  (SELECT occurred_at FROM events WHERE recipient_id=r.id AND event_type=?) AS submitted_at "
        "FROM recipients r WHERE campaign_id = ? ORDER BY r.id",
        (EVT_CLICK, EVT_SUBMIT, row["id"]),
    ).fetchall()

    recipients = [
        Recipient(
            id=r["id"], campaign_id=row["id"], name=r["name"], email=r["email"],
            token=r["token"],
            clicked_at=datetime.fromisoformat(r["clicked_at"]) if r["clicked_at"] else None,
            submitted_at=datetime.fromisoformat(r["submitted_at"]) if r["submitted_at"] else None,
        )
        for r in recipient_rows
    ]
    return Campaign(
        id=row["id"], name=row["name"], template=row["template"],
        created_at=datetime.fromisoformat(row["created_at"]),
        recipients=recipients,
    )


def lookup_token(conn: sqlite3.Connection, token: str) -> sqlite3.Row | None:
    return conn.execute(
        "SELECT r.*, c.template FROM recipients r "
        "JOIN campaigns c ON c.id = r.campaign_id "
        "WHERE r.token = ?", (token,)
    ).fetchone()
