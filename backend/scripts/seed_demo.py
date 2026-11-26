"""
Explicit demo-only seeder.
Refuses to run unless DEMO_MODE=true.
Loads demo users (005, 005b) and sample JSON (load_seed.py).
"""
from app.core.config import settings
from scripts.init_db import run_migration_module
from scripts.load_seed import main as load_seed_main


def main():
    if not settings.DEMO_MODE:
        raise RuntimeError(
            "Refusing to run demo seeder when DEMO_MODE=false. "
            "Demo accounts and sample truncates are forbidden in production."
        )
    run_migration_module("005_seed_officer.py")
    run_migration_module("005b_seed_demo_users.py")
    load_seed_main()
    print("Demo users and sample seed data loaded.")


if __name__ == "__main__":
    main()
