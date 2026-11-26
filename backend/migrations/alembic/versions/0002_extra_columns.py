"""Add harvest_status to forecasts and net_to_farmers_inr to matches.

Revision ID: 0002_extra_columns
Revises: 0001_initial_schema
Create Date: 2026-11-26
"""
from alembic import op

revision = "0002_extra_columns"
down_revision = "0001_initial_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE forecasts
          ADD COLUMN IF NOT EXISTS harvest_status TEXT NOT NULL DEFAULT 'GROWING';
        DO $$
        BEGIN
          IF NOT EXISTS (
            SELECT 1 FROM pg_constraint WHERE conname = 'forecasts_harvest_status_check'
          ) THEN
            ALTER TABLE forecasts
              ADD CONSTRAINT forecasts_harvest_status_check
              CHECK (harvest_status IN ('GROWING','READY_SOON','HARVESTED'));
          END IF;
        END $$;
        ALTER TABLE matches
          ADD COLUMN IF NOT EXISTS net_to_farmers_inr NUMERIC;
    """)


def downgrade() -> None:
    op.execute("""
        ALTER TABLE matches DROP COLUMN IF EXISTS net_to_farmers_inr;
        ALTER TABLE forecasts DROP COLUMN IF EXISTS harvest_status;
    """)
