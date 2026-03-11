"""add weekly checkin readiness fields

Revision ID: 0015_weekly_checkin_readiness_fields
Revises: 0014_user_coaching_constraints
Create Date: 2026-03-10 00:00:01.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0015_weekly_checkin_readiness_fields"
down_revision: str | None = "0014_user_coaching_constraints"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("weekly_checkins", sa.Column("sleep_quality", sa.Integer(), nullable=True))
    op.add_column("weekly_checkins", sa.Column("stress_level", sa.Integer(), nullable=True))
    op.add_column("weekly_checkins", sa.Column("pain_flags", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("weekly_checkins", "pain_flags")
    op.drop_column("weekly_checkins", "stress_level")
    op.drop_column("weekly_checkins", "sleep_quality")
