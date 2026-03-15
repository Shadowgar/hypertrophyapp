"""add user onboarding answers json

Revision ID: 0012_user_onboarding_answers
Revises: 0011_user_active_frequency_adaptation
Create Date: 2026-03-06
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "0012_user_onboarding_answers"
down_revision = "0011_user_active_frequency_adaptation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS onboarding_answers JSON")


def downgrade() -> None:
    op.drop_column("users", "onboarding_answers")
