"""Tests for the report rendering layer."""

from __future__ import annotations

from datetime import datetime

from phishing_sim.models import Campaign, Recipient
from phishing_sim import report as reportmod


def _make_campaign(click_count: int = 0, submit_count: int = 0, total: int = 4) -> Campaign:
    now = datetime(2024, 1, 15, 9, 0)
    recipients = []
    for i in range(total):
        r = Recipient(
            id=i + 1, campaign_id=1, name=f"User{i}", email=f"user{i}@ex.com",
            token=f"tok{i}",
            clicked_at=now if i < click_count else None,
            submitted_at=now if i < submit_count else None,
        )
        recipients.append(r)
    return Campaign(id=1, name="Test Campaign", template="it_portal",
                    created_at=now, recipients=recipients)


def test_console_report_shows_key_fields():
    c = _make_campaign(click_count=2, submit_count=1)
    text = reportmod.to_console(c)
    assert "Test Campaign" in text
    assert "2 (50%)" in text
    assert "1 (25%)" in text
    assert "Recommendation" in text


def test_console_report_empty_recipients():
    c = _make_campaign(total=0)
    assert "No recipients" in reportmod.to_console(c)


def test_csv_round_trips_all_recipients():
    c = _make_campaign(click_count=1, submit_count=1)
    text = reportmod.to_csv(c)
    lines = text.strip().splitlines()
    assert lines[0].startswith("campaign,name,email")
    assert len(lines) == 5  # header + 4 recipients


def test_html_includes_kpis_and_lab_banner():
    c = _make_campaign(click_count=3, submit_count=2)
    html = reportmod.to_html(c)
    assert "LAB SIMULATION" in html
    assert "75%" in html   # click rate
    assert "50%" in html   # submit rate
    assert "data:image/png;base64," in html


def test_html_empty_campaign_has_no_events_message():
    c = _make_campaign(total=0)
    html = reportmod.to_html(c)
    assert "No events recorded yet." in html


def test_recommendation_levels():
    assert reportmod._recommendation(0.60)[0] == "critical"
    assert reportmod._recommendation(0.35)[0] == "high"
    assert reportmod._recommendation(0.15)[0] == "medium"
    assert reportmod._recommendation(0.05)[0] == "low"
