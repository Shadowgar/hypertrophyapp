"""add profile equipment fields

Revision ID: 0003_profile_equipment
Revises: 0002_primary_slot_log
Create Date: 2026-03-02 01:10:00
"""

from alembic import op
import sqlalchemy as sa


revision = "0003_profile_equipment"
down_revision = "0002_primary_slot_log"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("training_location", sa.String(), nullable=True))
    op.add_column("users", sa.Column("equipment_profile", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "equipment_profile")
    op.drop_column("users", "training_location")
