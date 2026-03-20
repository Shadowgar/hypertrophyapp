"""add program selection mode to users

Revision ID: 0017_program_selection_mode
Revises: 0016_workout_set_log_technique_fields
Create Date: 2026-03-20
"""

from alembic import op
import sqlalchemy as sa


revision = "0017_program_selection_mode"
down_revision = "0016_workout_set_log_technique_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("users")}

    if "program_selection_mode" not in columns:
        op.add_column(
            "users",
            sa.Column("program_selection_mode", sa.String(), nullable=True),
        )

    # Default existing users to manual (explicit user control) rather than leaving NULL.
    op.execute("UPDATE users SET program_selection_mode = 'manual' WHERE program_selection_mode IS NULL")


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("users")}

    if "program_selection_mode" in columns:
        op.drop_column("users", "program_selection_mode")

