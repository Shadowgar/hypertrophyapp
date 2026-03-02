"""add soreness and body measurement tables

Revision ID: 0004_recovery_measurements
Revises: 0003_profile_equipment
Create Date: 2026-03-02 02:20:00
"""

from alembic import op
import sqlalchemy as sa


USER_FK = "users.id"

revision = "0004_recovery_measurements"
down_revision = "0003_profile_equipment"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("soreness_entries"):
        op.create_table(
            "soreness_entries",
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("user_id", sa.String(), nullable=False),
            sa.Column("entry_date", sa.Date(), nullable=False),
            sa.Column("severity_by_muscle", sa.JSON(), nullable=False),
            sa.Column("notes", sa.String(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["user_id"], [USER_FK]),
            sa.PrimaryKeyConstraint("id"),
        )

    if not inspector.has_table("body_measurement_entries"):
        op.create_table(
            "body_measurement_entries",
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("user_id", sa.String(), nullable=False),
            sa.Column("measured_on", sa.Date(), nullable=False),
            sa.Column("name", sa.String(), nullable=False),
            sa.Column("value", sa.Float(), nullable=False),
            sa.Column("unit", sa.String(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["user_id"], [USER_FK]),
            sa.PrimaryKeyConstraint("id"),
        )

    op.execute("CREATE INDEX IF NOT EXISTS ix_soreness_entries_user_id ON soreness_entries (user_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_soreness_entries_entry_date ON soreness_entries (entry_date)")
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_body_measurement_entries_user_id ON body_measurement_entries (user_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_body_measurement_entries_measured_on ON body_measurement_entries (measured_on)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_body_measurement_entries_measured_on")
    op.execute("DROP INDEX IF EXISTS ix_body_measurement_entries_user_id")
    op.execute("DROP TABLE IF EXISTS body_measurement_entries")

    op.execute("DROP INDEX IF EXISTS ix_soreness_entries_entry_date")
    op.execute("DROP INDEX IF EXISTS ix_soreness_entries_user_id")
    op.execute("DROP TABLE IF EXISTS soreness_entries")
