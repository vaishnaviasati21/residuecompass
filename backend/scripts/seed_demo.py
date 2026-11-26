"""
Explicit demo-only seeder.
Refuses to run unless DEMO_MODE=true.

Execution order against a fresh database:
  1. Reference data (districts, villages, buyers, machines, trucks) from 002_seed.sql
  2. Demo users (005_seed_officer.py, 005b_seed_demo_users.py)
  3. Sample operational records (load_seed.py: forecasts, decisions, matches, burn_events)
"""
from pathlib import Path

from sqlalchemy import text

from app.core.config import settings
from app.core.db import engine
from scripts.init_db import run_migration_module
from scripts.load_seed import main as load_seed_main

SEED_REF_SQL = Path(__file__).resolve().parents[1] / "migrations" / "002_seed.sql"


def seed_reference_data() -> None:
    """Idempotently load demo reference data (districts, villages, buyers, machines, trucks)."""
    if not settings.DEMO_MODE:
        raise RuntimeError("Refusing to seed demo reference data when DEMO_MODE=false.")
    sql = SEED_REF_SQL.read_text(encoding="utf-8")
    with engine.begin() as conn:
        conn.execute(text(sql))


def main():
    if not settings.DEMO_MODE:
        raise RuntimeError(
            "Refusing to run demo seeder when DEMO_MODE=false. "
            "Demo accounts and sample truncates are forbidden in production."
        )
    seed_reference_data()
    run_migration_module("005_seed_officer.py")
    run_migration_module("005b_seed_demo_users.py")
    load_seed_main()
    print("Demo reference data, users, and sample seed data loaded.")


if __name__ == "__main__":
    main()
