"""WSGI entry point for production deployment."""
import os
from phishing_sim import db as dbmod
from phishing_sim.server import create_app

_db_path = os.environ.get("PHISHING_SIM_DB", "phishing_sim.db")
_conn = dbmod.connect(_db_path)
app = create_app(_conn)
