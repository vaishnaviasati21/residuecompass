"""Initial PostGIS schema (001_init.sql).

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-11-26
"""
from pathlib import Path
from alembic import op

revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None

_SQL_PATH = Path(__file__).resolve().parents[2] / "001_init.sql"


def upgrade() -> None:
    op.execute(_SQL_PATH.read_text(encoding="utf-8"))


def downgrade() -> None:
    # Destructive schema teardown intentionally omitted in production migrations.
    pass
