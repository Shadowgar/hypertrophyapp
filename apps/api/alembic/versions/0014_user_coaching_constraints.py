"""add user coaching constraint fields

Revision ID: 0014_user_coaching_constraints
Revises: 0013_exercise_state_progression_tracking
Create Date: 2026-03-10 00:00:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0014_user_coaching_constraints"
down_revision: str | None = "0013_exercise_state_progression_tracking"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS session_time_budget_minutes INTEGER")
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS movement_restrictions JSON")
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS near_failure_tolerance VARCHAR")


def downgrade() -> None:
    op.drop_column("users", "near_failure_tolerance")
    op.drop_column("users", "movement_restrictions")
    op.drop_column("users", "session_time_budget_minutes")
