"""exercise state progression tracking

Revision ID: 0013_exercise_state_progression_tracking
Revises: 0012_user_onboarding_answers
Create Date: 2026-03-08 00:00:00
"""

from alembic import op
import sqlalchemy as sa


revision = "0013_exercise_state_progression_tracking"
down_revision = "0012_user_onboarding_answers"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE exercise_states ADD COLUMN IF NOT EXISTS consecutive_under_target_exposures INTEGER NOT NULL DEFAULT 0"
    )
    op.execute(
        "ALTER TABLE exercise_states ADD COLUMN IF NOT EXISTS last_progression_action VARCHAR NOT NULL DEFAULT 'hold'"
    )


def downgrade() -> None:
    op.drop_column("exercise_states", "last_progression_action")
    op.drop_column("exercise_states", "consecutive_under_target_exposures")