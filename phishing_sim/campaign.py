"""Campaign management: create campaigns, add recipients, generate tracking links."""

from __future__ import annotations

import secrets
import sqlite3

from . import db
from .models import Campaign


def new_campaign(conn: sqlite3.Connection, name: str,
                 template: str = "it_portal") -> Campaign:
    cid = db.create_campaign(conn, name=name, template=template)
    return db.fetch_campaign(conn, cid)


def add_recipients(conn: sqlite3.Connection, campaign_id: int,
                   recipients: list[tuple[str, str]]) -> list[str]:
    """Add (name, email) pairs to a campaign.  Returns the generated tokens."""
    tokens = []
    for name, email in recipients:
        token = secrets.token_hex(16)
        db.add_recipient(conn, campaign_id, name=name, email=email, token=token)
        tokens.append(token)
    return tokens


def tracking_url(base_url: str, token: str) -> str:
    return f"{base_url.rstrip('/')}/track/{token}"
