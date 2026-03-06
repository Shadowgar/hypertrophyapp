"""add coaching recommendations table

Revision ID: 0009_coaching_recommendations
Revises: 0008_workout_session_states
Create Date: 2026-03-06 06:35:00
"""

from alembic import op
import sqlalchemy as sa


revision = "0009_coaching_recommendations"
down_revision = "0008_workout_session_states"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    if "coaching_recommendations" not in tables:
        op.create_table(
            "coaching_recommendations",
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("user_id", sa.String(), nullable=False),
            sa.Column("template_id", sa.String(), nullable=False),
            sa.Column("recommendation_type", sa.String(), nullable=False),
            sa.Column("current_phase", sa.String(), nullable=False),
            sa.Column("recommended_phase", sa.String(), nullable=False),
            sa.Column("progression_action", sa.String(), nullable=False),
            sa.Column("request_payload", sa.JSON(), nullable=False),
            sa.Column("recommendation_payload", sa.JSON(), nullable=False),
            sa.Column("status", sa.String(), nullable=False),
            sa.Column("applied_at", sa.DateTime(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            op.f("ix_coaching_recommendations_user_id"),
            "coaching_recommendations",
            ["user_id"],
            unique=False,
        )
        op.create_index(
            op.f("ix_coaching_recommendations_template_id"),
            "coaching_recommendations",
            ["template_id"],
            unique=False,
        )
        op.create_index(
            op.f("ix_coaching_recommendations_recommendation_type"),
            "coaching_recommendations",
            ["recommendation_type"],
            unique=False,
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    if "coaching_recommendations" in tables:
        indexes = {index["name"] for index in inspector.get_indexes("coaching_recommendations")}
        for index_name in (
            op.f("ix_coaching_recommendations_recommendation_type"),
            op.f("ix_coaching_recommendations_template_id"),
            op.f("ix_coaching_recommendations_user_id"),
        ):
            if index_name in indexes:
                op.drop_index(index_name, table_name="coaching_recommendations")
        op.drop_table("coaching_recommendations")
