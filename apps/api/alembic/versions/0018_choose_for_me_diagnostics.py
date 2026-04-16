"""add choose-for-me family and diagnostics fields

Revision ID: 0018_choose_for_me_diagnostics
Revises: 0017_program_selection_mode
Create Date: 2026-03-20
"""

from alembic import op
import sqlalchemy as sa


revision = "0018_choose_for_me_diagnostics"
down_revision = "0017_program_selection_mode"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("users")}

    if "choose_for_me_family" not in columns:
        op.add_column("users", sa.Column("choose_for_me_family", sa.String(), nullable=True))
    if "choose_for_me_diagnostics" not in columns:
        op.add_column("users", sa.Column("choose_for_me_diagnostics", sa.JSON(), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("users")}

    if "choose_for_me_diagnostics" in columns:
        op.drop_column("users", "choose_for_me_diagnostics")
    if "choose_for_me_family" in columns:
        op.drop_column("users", "choose_for_me_family")

