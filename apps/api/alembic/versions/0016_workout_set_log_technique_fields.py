"""add workout set log technique fields

Revision ID: 0016_workout_set_log_technique_fields
Revises: 0015_weekly_checkin_readiness_fields
Create Date: 2026-03-18 00:00:00.000000
"""

from collections.abc import Sequence

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "0016_workout_set_log_technique_fields"
down_revision: str | None = "0015_weekly_checkin_readiness_fields"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("ALTER TABLE workout_set_logs ADD COLUMN IF NOT EXISTS set_kind VARCHAR")
    op.execute("ALTER TABLE workout_set_logs ADD COLUMN IF NOT EXISTS parent_set_index INTEGER")
    op.execute("ALTER TABLE workout_set_logs ADD COLUMN IF NOT EXISTS technique JSON")


def downgrade() -> None:
    op.drop_column("workout_set_logs", "technique")
    op.drop_column("workout_set_logs", "parent_set_index")
    op.drop_column("workout_set_logs", "set_kind")

