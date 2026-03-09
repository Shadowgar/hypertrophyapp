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
    op.add_column(
        "exercise_states",
        sa.Column(
            "consecutive_under_target_exposures",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )
    op.add_column(
        "exercise_states",
        sa.Column(
            "last_progression_action",
            sa.String(),
            nullable=False,
            server_default="hold",
        ),
    )
    op.alter_column("exercise_states", "consecutive_under_target_exposures", server_default=None)
    op.alter_column("exercise_states", "last_progression_action", server_default=None)


def downgrade() -> None:
    op.drop_column("exercise_states", "last_progression_action")
    op.drop_column("exercise_states", "consecutive_under_target_exposures")