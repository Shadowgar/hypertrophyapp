"""add workout session states table

Revision ID: 0008_workout_session_states
Revises: 0007_weekly_review_cycles
Create Date: 2026-03-05 10:45:00
"""

from alembic import op
import sqlalchemy as sa


revision = "0008_workout_session_states"
down_revision = "0007_weekly_review_cycles"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    if "workout_session_states" not in tables:
        op.create_table(
            "workout_session_states",
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("user_id", sa.String(), nullable=False),
            sa.Column("workout_id", sa.String(), nullable=False),
            sa.Column("primary_exercise_id", sa.String(), nullable=False),
            sa.Column("exercise_id", sa.String(), nullable=False),
            sa.Column("planned_sets", sa.Integer(), nullable=False),
            sa.Column("planned_reps_min", sa.Integer(), nullable=False),
            sa.Column("planned_reps_max", sa.Integer(), nullable=False),
            sa.Column("planned_weight", sa.Float(), nullable=False),
            sa.Column("completed_sets", sa.Integer(), nullable=False),
            sa.Column("total_logged_reps", sa.Integer(), nullable=False),
            sa.Column("total_logged_weight", sa.Float(), nullable=False),
            sa.Column("set_history", sa.JSON(), nullable=False),
            sa.Column("remaining_sets", sa.Integer(), nullable=False),
            sa.Column("recommended_reps_min", sa.Integer(), nullable=False),
            sa.Column("recommended_reps_max", sa.Integer(), nullable=False),
            sa.Column("recommended_weight", sa.Float(), nullable=False),
            sa.Column("last_guidance", sa.String(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "user_id",
                "workout_id",
                "exercise_id",
                name="uq_workout_session_states_user_workout_exercise",
            ),
        )
        op.create_index(op.f("ix_workout_session_states_user_id"), "workout_session_states", ["user_id"], unique=False)
        op.create_index(op.f("ix_workout_session_states_workout_id"), "workout_session_states", ["workout_id"], unique=False)
        op.create_index(
            op.f("ix_workout_session_states_primary_exercise_id"),
            "workout_session_states",
            ["primary_exercise_id"],
            unique=False,
        )
        op.create_index(
            op.f("ix_workout_session_states_exercise_id"),
            "workout_session_states",
            ["exercise_id"],
            unique=False,
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    if "workout_session_states" in tables:
        indexes = {index["name"] for index in inspector.get_indexes("workout_session_states")}
        for index_name in (
            op.f("ix_workout_session_states_exercise_id"),
            op.f("ix_workout_session_states_primary_exercise_id"),
            op.f("ix_workout_session_states_workout_id"),
            op.f("ix_workout_session_states_user_id"),
        ):
            if index_name in indexes:
                op.drop_index(index_name, table_name="workout_session_states")
        op.drop_table("workout_session_states")
