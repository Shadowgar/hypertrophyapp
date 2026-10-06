"""Add nullable local-date placement fields without assigning dates to legacy work.

No historical occurrence or plan is backfilled. This migration must be rehearsed
on isolated PostgreSQL before a later, separately authorized deployment.
"""
from alembic import op
import sqlalchemy as sa

revision = "0021_selected_workout_dates"
down_revision = "0020_workout_set_amendments"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("scheduling_timezone", sa.String(64), nullable=True))
    op.add_column("workout_plans", sa.Column("placement_revision", sa.Integer(), nullable=True))
    op.add_column("workout_plans", sa.Column("schedule_timezone", sa.String(64), nullable=True))
    op.add_column("workout_occurrences", sa.Column("scheduled_date", sa.Date(), nullable=True))
    op.add_column("workout_occurrences", sa.Column("schedule_timezone", sa.String(64), nullable=True))
    op.add_column("workout_occurrences", sa.Column("placement_revision", sa.Integer(), nullable=True))


def downgrade() -> None:
    raise RuntimeError("Scheduled-date history requires a separately reviewed data-preserving rollback")
