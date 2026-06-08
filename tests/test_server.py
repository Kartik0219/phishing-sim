"""Flask server tests using the test client - no live network required."""

from __future__ import annotations

from phishing_sim import db as dbmod
from phishing_sim.campaign import add_recipients, new_campaign
from phishing_sim.server import create_app


def _setup():
    conn = dbmod.connect()
    campaign = new_campaign(conn, "Server Test")
    [token] = add_recipients(conn, campaign.id, [("Alice", "alice@ex.com")])
    app = create_app(conn)
    app.config["TESTING"] = True
    return app.test_client(), conn, campaign.id, token


def test_track_returns_login_page():
    client, conn, _, token = _setup()
    resp = client.get(f"/track/{token}")
    assert resp.status_code == 200
    assert b"IT Portal" in resp.data or b"form" in resp.data


def test_track_records_click_event():
    client, conn, cid, token = _setup()
    client.get(f"/track/{token}")
    campaign = dbmod.fetch_campaign(conn, cid)
    assert campaign.click_count == 1


def test_track_unknown_token_returns_404():
    client, conn, _, _ = _setup()
    resp = client.get("/track/notarealtoken")
    assert resp.status_code == 404


def test_submit_records_submit_event():
    client, conn, cid, token = _setup()
    resp = client.post(f"/submit/{token}", data={"username": "testuser", "password": "secret"})
    assert resp.status_code == 200
    assert b"phishing" in resp.data.lower() or b"simulation" in resp.data.lower()
    campaign = dbmod.fetch_campaign(conn, cid)
    assert campaign.submit_count == 1


def test_submit_does_not_store_credentials():
    client, conn, cid, token = _setup()
    client.post(f"/submit/{token}", data={"username": "admin", "password": "hunter2"})
    # Verify no events table stores the actual password
    rows = conn.execute("SELECT * FROM events").fetchall()
    raw_events = " ".join(str(dict(r)) for r in rows)
    assert "hunter2" not in raw_events
    assert "admin" not in raw_events


def test_health_endpoint():
    client, _, _, _ = _setup()
    resp = client.get("/health")
    assert resp.status_code == 200


def test_multiple_clicks_do_not_double_count():
    client, conn, cid, token = _setup()
    client.get(f"/track/{token}")
    client.get(f"/track/{token}")
    campaign = dbmod.fetch_campaign(conn, cid)
    assert campaign.click_count == 1
