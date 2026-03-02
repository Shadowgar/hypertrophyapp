"""add primary_exercise_id to workout set logs

Revision ID: 0002_primary_slot_log
Revises: 0001_initial_schema
Create Date: 2026-03-02 00:30:00
"""

from alembic import op
import sqlalchemy as sa


revision = "0002_primary_slot_log"
down_revision = "0001_initial_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "workout_set_logs",
        sa.Column("primary_exercise_id", sa.String(), nullable=True),
    )
    op.execute("UPDATE workout_set_logs SET primary_exercise_id = exercise_id WHERE primary_exercise_id IS NULL")
    op.alter_column("workout_set_logs", "primary_exercise_id", nullable=False)
    op.create_index(
        op.f("ix_workout_set_logs_primary_exercise_id"),
        "workout_set_logs",
        ["primary_exercise_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_workout_set_logs_primary_exercise_id"), table_name="workout_set_logs")
    op.drop_column("workout_set_logs", "primary_exercise_id")
