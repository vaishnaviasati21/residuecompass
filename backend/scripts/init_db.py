"""
Database initializer for startup (safe, idempotent, non-destructive).
Applies all versioned Alembic migrations (`alembic upgrade head`).
NEVER truncates live data or seeds demo users.

To explicitly seed demo data & demo users in a DEMO_MODE=true environment:
    python scripts/seed_demo.py
"""
import importlib.util
from pathlib import Path

from alembic import command
from alembic.config import Config

BACKEND_DIR = Path(__file__).resolve().parents[1]
MIGRATIONS_DIR = BACKEND_DIR / "migrations"


def run_migration_module(filename: str):
    """Run a standalone Python migration/seed script (used by seed_demo.py)."""
    path = MIGRATIONS_DIR / filename
    spec = importlib.util.spec_from_file_location(path.stem, path)
    if spec and spec.loader:
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        mod.upgrade()


def main():
    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(MIGRATIONS_DIR / "alembic"))
    command.upgrade(cfg, "head")
    print("Alembic migrations applied to head (non-destructive).")


if __name__ == "__main__":
    main()
