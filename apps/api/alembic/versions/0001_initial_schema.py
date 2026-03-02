"""initial schema

Revision ID: 0001_initial_schema
Revises: None
Create Date: 2026-03-02 00:00:00
"""

from alembic import op
import sqlalchemy as sa

USER_FK = "users.id"


revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("password_hash", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("age", sa.Integer(), nullable=True),
        sa.Column("weight", sa.Float(), nullable=True),
        sa.Column("gender", sa.String(), nullable=True),
        sa.Column("split_preference", sa.String(), nullable=True),
        sa.Column("days_available", sa.Integer(), nullable=True),
        sa.Column("nutrition_phase", sa.String(), nullable=True),
        sa.Column("calories", sa.Integer(), nullable=True),
        sa.Column("protein", sa.Integer(), nullable=True),
        sa.Column("fat", sa.Integer(), nullable=True),
        sa.Column("carbs", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)

    op.create_table(
        "weekly_checkins",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("week_start", sa.Date(), nullable=False),
        sa.Column("body_weight", sa.Float(), nullable=False),
        sa.Column("adherence_score", sa.Integer(), nullable=False),
        sa.Column("notes", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], [USER_FK]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_weekly_checkins_user_id"), "weekly_checkins", ["user_id"], unique=False)

    op.create_table(
        "workout_plans",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("week_start", sa.Date(), nullable=False),
        sa.Column("split", sa.String(), nullable=False),
        sa.Column("phase", sa.String(), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], [USER_FK]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_workout_plans_user_id"), "workout_plans", ["user_id"], unique=False)

    op.create_table(
        "workout_set_logs",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("workout_id", sa.String(), nullable=False),
        sa.Column("exercise_id", sa.String(), nullable=False),
        sa.Column("set_index", sa.Integer(), nullable=False),
        sa.Column("reps", sa.Integer(), nullable=False),
        sa.Column("weight", sa.Float(), nullable=False),
        sa.Column("rpe", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], [USER_FK]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_workout_set_logs_user_id"), "workout_set_logs", ["user_id"], unique=False)
    op.create_index(op.f("ix_workout_set_logs_workout_id"), "workout_set_logs", ["workout_id"], unique=False)
    op.create_index(op.f("ix_workout_set_logs_exercise_id"), "workout_set_logs", ["exercise_id"], unique=False)

    op.create_table(
        "exercise_states",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("exercise_id", sa.String(), nullable=False),
        sa.Column("current_working_weight", sa.Float(), nullable=False),
        sa.Column("exposure_count", sa.Integer(), nullable=False),
        sa.Column("fatigue_score", sa.Float(), nullable=False),
        sa.Column("last_updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], [USER_FK]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_exercise_states_user_id"), "exercise_states", ["user_id"], unique=False)
    op.create_index(op.f("ix_exercise_states_exercise_id"), "exercise_states", ["exercise_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_exercise_states_exercise_id"), table_name="exercise_states")
    op.drop_index(op.f("ix_exercise_states_user_id"), table_name="exercise_states")
    op.drop_table("exercise_states")

    op.drop_index(op.f("ix_workout_set_logs_exercise_id"), table_name="workout_set_logs")
    op.drop_index(op.f("ix_workout_set_logs_workout_id"), table_name="workout_set_logs")
    op.drop_index(op.f("ix_workout_set_logs_user_id"), table_name="workout_set_logs")
    op.drop_table("workout_set_logs")

    op.drop_index(op.f("ix_workout_plans_user_id"), table_name="workout_plans")
    op.drop_table("workout_plans")

    op.drop_index(op.f("ix_weekly_checkins_user_id"), table_name="weekly_checkins")
    op.drop_table("weekly_checkins")

    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_table("users")
