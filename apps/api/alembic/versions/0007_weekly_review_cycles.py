"""add weekly review cycles table

Revision ID: 0007_weekly_review_cycles
Revises: 0006_user_selected_program
Create Date: 2026-03-04 20:30:00
"""

from alembic import op
import sqlalchemy as sa


revision = "0007_weekly_review_cycles"
down_revision = "0006_user_selected_program"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    if "weekly_review_cycles" not in tables:
        op.create_table(
            "weekly_review_cycles",
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("user_id", sa.String(), nullable=False),
            sa.Column("reviewed_on", sa.Date(), nullable=False),
            sa.Column("week_start", sa.Date(), nullable=False),
            sa.Column("previous_week_start", sa.Date(), nullable=False),
            sa.Column("body_weight", sa.Float(), nullable=False),
            sa.Column("calories", sa.Integer(), nullable=False),
            sa.Column("protein", sa.Integer(), nullable=False),
            sa.Column("fat", sa.Integer(), nullable=False),
            sa.Column("carbs", sa.Integer(), nullable=False),
            sa.Column("adherence_score", sa.Integer(), nullable=False),
            sa.Column("notes", sa.String(), nullable=True),
            sa.Column("faults", sa.JSON(), nullable=False),
            sa.Column("adjustments", sa.JSON(), nullable=False),
            sa.Column("summary", sa.JSON(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_weekly_review_cycles_user_id"), "weekly_review_cycles", ["user_id"], unique=False)
        op.create_index(op.f("ix_weekly_review_cycles_reviewed_on"), "weekly_review_cycles", ["reviewed_on"], unique=False)
        op.create_index(op.f("ix_weekly_review_cycles_week_start"), "weekly_review_cycles", ["week_start"], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    if "weekly_review_cycles" in tables:
        indexes = {index["name"] for index in inspector.get_indexes("weekly_review_cycles")}
        for index_name in (
            op.f("ix_weekly_review_cycles_week_start"),
            op.f("ix_weekly_review_cycles_reviewed_on"),
            op.f("ix_weekly_review_cycles_user_id"),
        ):
            if index_name in indexes:
                op.drop_index(index_name, table_name="weekly_review_cycles")
        op.drop_table("weekly_review_cycles")
