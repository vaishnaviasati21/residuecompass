"""
One-shot database initializer for local dev and Docker startup.
Runs idempotent indices, demo users, and seed data loading.
"""
import importlib.util
from pathlib import Path

from scripts.load_seed import main as load_seed_main

MIGRATIONS_DIR = Path(__file__).resolve().parents[1] / "migrations"


def _run_migration_module(filename: str):
    path = MIGRATIONS_DIR / filename
    spec = importlib.util.spec_from_file_location(path.stem, path)
    if spec and spec.loader:
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        mod.upgrade()


def main():
    _run_migration_module("004_indices.py")
    _run_migration_module("005_seed_officer.py")
    _run_migration_module("005b_seed_demo_users.py")
    load_seed_main()
    print("Database initialized (indices + demo users + seed data).")


if __name__ == "__main__":
    main()
