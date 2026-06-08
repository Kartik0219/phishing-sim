"""Command-line interface for the phishing simulation tool."""

from __future__ import annotations

import argparse
import sys

from . import db as dbmod
from . import report as reportmod
from .campaign import add_recipients, new_campaign, tracking_url

LAB_NOTICE = (
    "This tool simulates phishing for authorized security-awareness training only.\n"
    "Only ever run it against email accounts you own or have explicit written consent\n"
    "to include. Never use it against real targets without authorization.\n"
    "Misuse may violate computer-fraud and anti-spam laws."
)

TEMPLATES = ["it_portal"]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="phishing-sim",
        description="Create phishing simulation campaigns, generate tracking links, "
                    "run the tracking server, and generate awareness-training reports.",
    )
    parser.add_argument("--db", metavar="PATH", default=":memory:",
                        help="SQLite database file (default: in-memory)")
    sub = parser.add_subparsers(dest="command", required=True)

    # --- new-campaign ---
    new_p = sub.add_parser("new-campaign", help="Create a campaign and generate tracking links")
    new_p.add_argument("name", help="Campaign name, e.g. 'Q2 IT Portal Exercise'")
    new_p.add_argument("--template", choices=TEMPLATES, default="it_portal")
    new_p.add_argument("--base-url", default="http://127.0.0.1:5000",
                       help="Base URL where the tracking server is running")
    new_p.add_argument("--recipients", metavar="NAME:EMAIL", nargs="+", required=True,
                       help="Recipient list as 'Full Name:email@example.com' pairs")
    new_p.add_argument("--i-accept-lab-only-terms", action="store_true",
                       help="Required: confirm this exercise is authorized and lab-only")

    # --- report ---
    rep_p = sub.add_parser("report", help="Print or export a campaign results report")
    rep_p.add_argument("campaign_id", type=int)
    rep_p.add_argument("--csv", metavar="PATH")
    rep_p.add_argument("--html", metavar="PATH")
    rep_p.add_argument("-q", "--quiet", action="store_true")

    # --- serve ---
    srv_p = sub.add_parser("serve", help="Run the tracking web server")
    srv_p.add_argument("--host", default="127.0.0.1",
                       help="Bind address (default: 127.0.0.1 - localhost only)")
    srv_p.add_argument("--port", type=int, default=5000)
    srv_p.add_argument("--i-accept-lab-only-terms", action="store_true",
                       help="Required: confirm this exercise is authorized and lab-only")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    conn = dbmod.connect(args.db)

    if args.command == "new-campaign":
        if not args.i_accept_lab_only_terms:
            parser.error(
                "new-campaign requires --i-accept-lab-only-terms\n\n" + LAB_NOTICE
            )
        recipients = []
        for item in args.recipients:
            if ":" not in item:
                parser.error(f"recipient '{item}' must be 'Full Name:email@example.com'")
            name, email = item.split(":", 1)
            recipients.append((name.strip(), email.strip()))

        campaign = new_campaign(conn, name=args.name, template=args.template)
        tokens = add_recipients(conn, campaign.id, recipients)

        print(f"Campaign '{campaign.name}' created (id={campaign.id})\n")
        print("Tracking links (send these to recipients):\n")
        for (name, email), token in zip(recipients, tokens):
            url = tracking_url(args.base_url, token)
            print(f"  {name} <{email}>\n  {url}\n")
        return 0

    if args.command == "report":
        campaign = dbmod.fetch_campaign(conn, args.campaign_id)
        if not campaign:
            print(f"No campaign with id={args.campaign_id}", file=sys.stderr)
            return 1

        if not args.quiet:
            print(reportmod.to_console(campaign))

        if args.csv:
            with open(args.csv, "w", newline="", encoding="utf-8") as fh:
                fh.write(reportmod.to_csv(campaign))
            print(f"\nCSV report written to {args.csv}", file=sys.stderr)

        if args.html:
            with open(args.html, "w", encoding="utf-8") as fh:
                fh.write(reportmod.to_html(campaign))
            print(f"HTML report written to {args.html}", file=sys.stderr)

        return 0

    if args.command == "serve":
        if not args.i_accept_lab_only_terms:
            parser.error(
                "serve requires --i-accept-lab-only-terms\n\n" + LAB_NOTICE
            )
        from .server import create_app
        app = create_app(conn)
        print(f"Tracking server running on http://{args.host}:{args.port}")
        print("Press Ctrl+C to stop.\n")
        app.run(host=args.host, port=args.port)
        return 0

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
