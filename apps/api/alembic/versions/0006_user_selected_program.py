"""add selected program id to users

Revision ID: 0006_user_selected_program
Revises: 0005_password_reset_tokens
Create Date: 2026-03-02 15:20:00
"""

from alembic import op
import sqlalchemy as sa


revision = "0006_user_selected_program"
down_revision = "0005_password_reset_tokens"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("users")}

    if "selected_program_id" not in columns:
        op.add_column("users", sa.Column("selected_program_id", sa.String(), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("users")}

    if "selected_program_id" in columns:
        op.drop_column("users", "selected_program_id")
