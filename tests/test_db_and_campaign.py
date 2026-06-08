"""Tests for DB storage, campaign management, and token generation."""

from __future__ import annotations

from phishing_sim import db as dbmod
from phishing_sim.campaign import add_recipients, new_campaign, tracking_url


def test_create_and_fetch_campaign():
    conn = dbmod.connect()
    campaign = new_campaign(conn, "Test Exercise", template="it_portal")
    assert campaign.id is not None
    assert campaign.name == "Test Exercise"
    assert campaign.template == "it_portal"
    assert campaign.recipients == []
    conn.close()


def test_add_recipients_generates_unique_tokens():
    conn = dbmod.connect()
    campaign = new_campaign(conn, "Q1 Test")
    tokens = add_recipients(conn, campaign.id, [
        ("Alice Smith", "alice@example.com"),
        ("Bob Jones", "bob@example.com"),
    ])
    assert len(tokens) == 2
    assert tokens[0] != tokens[1]
    assert all(len(t) == 32 for t in tokens)  # hex(16) = 32 chars

    fetched = dbmod.fetch_campaign(conn, campaign.id)
    assert len(fetched.recipients) == 2
    assert {r.email for r in fetched.recipients} == {"alice@example.com", "bob@example.com"}
    conn.close()


def test_record_click_event():
    conn = dbmod.connect()
    campaign = new_campaign(conn, "Click Test")
    [token] = add_recipients(conn, campaign.id, [("Alice", "alice@ex.com")])

    result = dbmod.record_event(conn, token, "click")
    assert result is True

    fetched = dbmod.fetch_campaign(conn, campaign.id)
    assert fetched.recipients[0].clicked_at is not None
    assert fetched.recipients[0].submitted_at is None
    conn.close()


def test_record_submit_event():
    conn = dbmod.connect()
    campaign = new_campaign(conn, "Submit Test")
    [token] = add_recipients(conn, campaign.id, [("Bob", "bob@ex.com")])

    dbmod.record_event(conn, token, "click")
    dbmod.record_event(conn, token, "submit")

    fetched = dbmod.fetch_campaign(conn, campaign.id)
    r = fetched.recipients[0]
    assert r.clicked_at is not None
    assert r.submitted_at is not None
    conn.close()


def test_duplicate_events_are_not_double_counted():
    conn = dbmod.connect()
    campaign = new_campaign(conn, "Dedup Test")
    [token] = add_recipients(conn, campaign.id, [("Carol", "carol@ex.com")])

    first = dbmod.record_event(conn, token, "click")
    second = dbmod.record_event(conn, token, "click")
    assert first is True
    assert second is False  # already recorded

    fetched = dbmod.fetch_campaign(conn, campaign.id)
    assert fetched.click_count == 1
    conn.close()


def test_unknown_token_is_ignored():
    conn = dbmod.connect()
    result = dbmod.record_event(conn, "deadbeef" * 4, "click")
    assert result is False
    conn.close()


def test_campaign_metrics():
    conn = dbmod.connect()
    campaign = new_campaign(conn, "Metrics Test")
    tokens = add_recipients(conn, campaign.id, [
        ("Alice", "a@ex.com"), ("Bob", "b@ex.com"),
        ("Carol", "c@ex.com"), ("Dave", "d@ex.com"),
    ])
    dbmod.record_event(conn, tokens[0], "click")
    dbmod.record_event(conn, tokens[0], "submit")
    dbmod.record_event(conn, tokens[1], "click")

    fetched = dbmod.fetch_campaign(conn, campaign.id)
    assert fetched.click_count == 2
    assert fetched.submit_count == 1
    assert fetched.click_rate == 0.5
    assert fetched.submit_rate == 0.25
    conn.close()


def test_tracking_url_format():
    url = tracking_url("http://127.0.0.1:5000", "abc123")
    assert url == "http://127.0.0.1:5000/track/abc123"
