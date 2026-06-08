# Phishing Simulation & Security Awareness Tool

A lab-only command-line tool for running authorized phishing simulations:
generates per-recipient tracking links, serves a realistic-but-clearly-
simulated login page, records click and credential-submission events in
SQLite, and produces awareness training reports with funnel charts and
remediation recommendations.

> **Lab use only.** Never run this against real targets without explicit
> written authorization. See the [Ethical Use](#ethical-use) section.

```
$ python -m phishing_sim.cli --db campaign.sqlite3 report 1

Campaign : Q2 IT Portal Awareness Exercise
Recipients: 6   Clicked: 4 (67%)   Submitted: 3 (50%)

Name         | Email                  | Clicked             | Submitted
-------------+------------------------+---------------------+--------------------
Alice Chen   | alice.chen@lab.local   | 2026-06-08 22:36:21 | 2026-06-08 22:36:21
Bob Martinez | bob.martinez@lab.local | 2026-06-08 22:36:21 | 2026-06-08 22:36:21
Carol Kim    | carol.kim@lab.local    | 2026-06-08 22:36:21 | 2026-06-08 22:36:21
Dave Singh   | dave.singh@lab.local   | 2026-06-08 22:36:21 | -
...

Recommendation (CRITICAL): More than half of recipients submitted
credentials. Immediate, mandatory security-awareness training is warranted.
```

## How it works

1. **Create a campaign** — the tool generates a unique tracking URL for each
   recipient (no emails sent; you paste the links into your test email client).
2. **Run the tracking server** — a Flask server serves the simulated login page
   on localhost. When a recipient visits their link, a click event is recorded.
3. **Credential submission** — if they submit the fake form, a submit event
   is recorded. **Credentials are never stored** — the POST handler discards
   form data immediately.
4. **Awareness page** — after submitting, the recipient sees a clearly-branded
   explanation that it was a simulation and tips for spotting phishing.
5. **Report** — print a console table or export CSV/HTML with click/submit rates,
   per-recipient status, and a tiered training recommendation.

## Installation

```bash
git clone <this-repo>
cd phishing-sim
python -m venv venv
# Windows: venv\Scripts\activate   |   macOS/Linux: source venv/bin/activate
pip install -r requirements.txt
```

Requires Python 3.10+, [Flask](https://flask.palletsprojects.com/) and
[matplotlib](https://matplotlib.org/) (installed via `requirements.txt`).

## Usage

```bash
# 1. Create a campaign and get tracking links
python -m phishing_sim.cli --db campaign.sqlite3 new-campaign "Q2 IT Portal Test" \
    --recipients "Alice Chen:alice@lab.local" "Bob Jones:bob@lab.local" \
    --i-accept-lab-only-terms

# 2. Start the tracking server (localhost only by default)
python -m phishing_sim.cli --db campaign.sqlite3 serve \
    --i-accept-lab-only-terms

# 3. Report results (console + CSV + HTML)
python -m phishing_sim.cli --db campaign.sqlite3 report 1 \
    --csv results.csv --html report.html
```

The tracking links are printed to the console when you create a campaign —
paste them into a test email client or browser to simulate recipients clicking.

## How it's built

```
phishing_sim/
├── models.py    # Campaign, Recipient dataclasses + event-type constants
├── db.py        # SQLite schema, campaign/recipient/event storage
├── campaign.py  # Campaign creation + recipient management + token generation
├── server.py    # Flask app: /track/<token> and /submit/<token> routes
├── report.py    # Console table, CSV, HTML+chart rendering + training recommendations
└── cli.py       # argparse front-end with authorization gate

phishing_sim/templates/
├── it_portal.html   # Simulated IT Portal login page (lab-only comment in source)
└── awareness.html   # Post-submission awareness training page
```

## Testing

The test suite covers DB/campaign logic, the Flask server via the test client
(no live port required), the report layer, and the CLI — 27 tests total.

```bash
pip install -r requirements-dev.txt
pytest
```

## Ethical use

This tool is designed for **closed-lab, authorized security-awareness training only**:

- The `new-campaign` and `serve` commands require `--i-accept-lab-only-terms` to run — a deliberate friction point that confirms you understand the scope.
- The tracking server binds to `127.0.0.1` (localhost) by default; use `--host 0.0.0.0` only within an isolated lab network.
- Credentials entered on the landing page are **never stored** — the POST handler discards them immediately and only logs that a submission occurred.
- The landing page HTML contains a `<!-- LAB SIMULATION ONLY -->` comment, and every recipient who submits sees the awareness page immediately.
- Only run this against accounts you own or that belong to people who have explicitly consented to be included in the exercise.

Using phishing tools against real targets without authorization is illegal in most jurisdictions (e.g. the US Computer Fraud and Abuse Act, UK Computer Misuse Act).

`samples/README.md` explains how to set up a realistic closed-lab scenario (isolated VM network + test email accounts) for a safe, demonstrable exercise.
