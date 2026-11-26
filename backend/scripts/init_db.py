"""
Database initializer for startup (safe, idempotent, non-destructive).
Applies index migrations only — NEVER truncates live data or seeds demo users.

To explicitly seed demo data & demo users in a DEMO_MODE=true environment:
    python scripts/seed_demo.py
"""
import importlib.util
from pathlib import Path

MIGRATIONS_DIR = Path(__file__).resolve().parents[1] / "migrations"


def run_migration_module(filename: str):
    path = MIGRATIONS_DIR / filename
    spec = importlib.util.spec_from_file_location(path.stem, path)
    if spec and spec.loader:
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        mod.upgrade()


def main():
    run_migration_module("004_indices.py")
    print("Database migrations applied (non-destructive).")


if __name__ == "__main__":
    main()
