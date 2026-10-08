"""Add isolated authored completed-exposure state without historical backfill."""
from alembic import op
import sqlalchemy as sa

revision = "0022_authored_load_states"
down_revision = "0021_selected_workout_dates"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table("authored_load_states",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("user_id", sa.String(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("comparison_key", sa.String(64), nullable=False),
        sa.Column("primary_exercise_id", sa.String(), nullable=False),
        sa.Column("source_identity", sa.JSON(), nullable=False),
        sa.Column("state", sa.JSON(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("user_id", "comparison_key", name="uq_authored_load_comparison"))
    op.create_index("ix_authored_load_states_user_id", "authored_load_states", ["user_id"])
    op.create_index("ix_authored_load_states_primary_exercise_id", "authored_load_states", ["primary_exercise_id"])


def downgrade() -> None:
    raise RuntimeError("Authored load evidence requires a separately reviewed data-preserving rollback")
