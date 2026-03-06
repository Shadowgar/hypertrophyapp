"""add weak_areas to users

Revision ID: 0010_user_weak_areas
Revises: 0009_coaching_recommendations
Create Date: 2026-03-06 13:05:00
"""

from alembic import op
import sqlalchemy as sa


revision = "0010_user_weak_areas"
down_revision = "0009_coaching_recommendations"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    columns = {column["name"] for column in inspector.get_columns("users")}
    if "weak_areas" not in columns:
        op.add_column("users", sa.Column("weak_areas", sa.JSON(), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    columns = {column["name"] for column in inspector.get_columns("users")}
    if "weak_areas" in columns:
        op.drop_column("users", "weak_areas")
