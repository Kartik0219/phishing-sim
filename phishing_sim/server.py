"""Flask application: serves tracking landing pages and records events.

The server has exactly two user-facing routes:
  GET  /track/<token>   -- renders the simulated login page, records a click
  POST /submit/<token>  -- records credential submission, renders awareness page

Credentials are never stored. The POST handler discards the form data
immediately and only records that a submission occurred (+ timestamp),
so the database never contains real passwords even in a lab context.
"""

from __future__ import annotations

import sqlite3

from flask import Flask, redirect, render_template, request, url_for

from . import db as dbmod
from .models import EVT_CLICK, EVT_SUBMIT

TEMPLATES = {"it_portal"}


def create_app(conn: sqlite3.Connection) -> Flask:
    """Return a configured Flask application bound to the given DB connection."""
    app = Flask(__name__, template_folder="templates")
    app.config["TESTING"] = False

    @app.route("/track/<token>")
    def track(token: str):
        row = dbmod.lookup_token(conn, token)
        if row is None:
            return "Not found", 404

        dbmod.record_event(conn, token, EVT_CLICK)
        template = row["template"] if row["template"] in TEMPLATES else "it_portal"
        return render_template(f"{template}.html", token=token)

    @app.route("/submit/<token>", methods=["POST"])
    def submit(token: str):
        if dbmod.lookup_token(conn, token) is None:
            return "Not found", 404

        # Discard form fields immediately - never log credentials
        _ = request.form.get("username", "")
        _ = request.form.get("password", "")

        dbmod.record_event(conn, token, EVT_SUBMIT)
        return render_template("awareness.html")

    @app.route("/health")
    def health():
        return {"status": "ok"}, 200

    return app
