"""add active frequency adaptation to users

Revision ID: 0011_user_active_frequency_adaptation
Revises: 0010_user_weak_areas
Create Date: 2026-03-06
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "0011_user_active_frequency_adaptation"
down_revision = "0010_user_weak_areas"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Alembic's default version_num is VARCHAR(32); our revision IDs can be longer.
    op.execute("ALTER TABLE alembic_version ALTER COLUMN version_num TYPE VARCHAR(64)")
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS active_frequency_adaptation JSON")


def downgrade() -> None:
    op.drop_column("users", "active_frequency_adaptation")
