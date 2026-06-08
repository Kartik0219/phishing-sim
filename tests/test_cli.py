"""CLI smoke tests."""

from __future__ import annotations

import pytest

from phishing_sim import db as dbmod
from phishing_sim.campaign import add_recipients, new_campaign
from phishing_sim.cli import main


def _populated_db(tmp_path, click: bool = True, submit: bool = True):
    db_path = str(tmp_path / "sim.sqlite3")
    conn = dbmod.connect(db_path)
    campaign = new_campaign(conn, "CLI Test Campaign")
    tokens = add_recipients(conn, campaign.id, [
        ("Alice", "alice@ex.com"), ("Bob", "bob@ex.com"),
        ("Carol", "carol@ex.com"),
    ])
    if click:
        dbmod.record_event(conn, tokens[0], "click")
        dbmod.record_event(conn, tokens[1], "click")
    if submit:
        dbmod.record_event(conn, tokens[0], "submit")
    conn.close()
    return db_path, campaign.id


def test_new_campaign_prints_links(capsys):
    rc = main([
        "--db", ":memory:", "new-campaign", "Q1 Test",
        "--recipients", "Alice:alice@ex.com", "Bob:bob@ex.com",
        "--i-accept-lab-only-terms",
    ])
    out = capsys.readouterr().out
    assert rc == 0
    assert "alice@ex.com" in out
    assert "/track/" in out


def test_new_campaign_blocked_without_terms(capsys):
    with pytest.raises(SystemExit) as exc_info:
        main([
            "--db", ":memory:", "new-campaign", "Test",
            "--recipients", "Alice:alice@ex.com",
        ])
    assert exc_info.value.code == 2
    assert "i-accept-lab-only-terms" in capsys.readouterr().err


def test_report_console(tmp_path, capsys):
    db_path, cid = _populated_db(tmp_path)
    rc = main(["--db", db_path, "report", str(cid)])
    out = capsys.readouterr().out
    assert rc == 0
    assert "CLI Test Campaign" in out
    assert "Recommendation" in out


def test_report_writes_csv_and_html(tmp_path, capsys):
    db_path, cid = _populated_db(tmp_path)
    csv_out = str(tmp_path / "report.csv")
    html_out = str(tmp_path / "report.html")
    rc = main(["--db", db_path, "report", str(cid), "-q",
               "--csv", csv_out, "--html", html_out])
    capsys.readouterr()
    assert rc == 0
    assert "alice@ex.com" in open(csv_out, encoding="utf-8").read()
    html = open(html_out, encoding="utf-8").read()
    assert "LAB SIMULATION" in html
    assert "CLI Test Campaign" in html


def test_report_unknown_campaign_id(tmp_path, capsys):
    db_path = str(tmp_path / "empty.sqlite3")
    dbmod.connect(db_path).close()
    rc = main(["--db", db_path, "report", "999"])
    assert rc == 1
    assert "No campaign" in capsys.readouterr().err


def test_serve_blocked_without_terms(capsys):
    with pytest.raises(SystemExit) as exc_info:
        main(["--db", ":memory:", "serve"])
    assert exc_info.value.code == 2
    assert "i-accept-lab-only-terms" in capsys.readouterr().err
