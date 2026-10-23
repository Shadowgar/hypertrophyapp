"""Separate, versioned reported calibration; no training-data backfill."""
from alembic import op
import sqlalchemy as sa

revision = "0026_initial_calibration"
down_revision = "0025_interface_preferences"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("authored_initial_calibrations",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("user_id", sa.String(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("command_id", sa.String(128), nullable=False),
        sa.Column("command_digest", sa.String(64), nullable=False),
        sa.Column("source_scope", sa.String(64), nullable=False),
        sa.Column("setup_scope", sa.String(64), nullable=False),
        sa.Column("workout_occurrence_id", sa.String(), nullable=False),
        sa.Column("exercise_occurrence_id", sa.String(), nullable=False),
        sa.Column("data", sa.JSON(), nullable=False),
        sa.Column("load_context", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("user_id", "command_id", name="uq_initial_calibration_command"),
        sa.UniqueConstraint("user_id", "revision", name="uq_initial_calibration_revision"),
        sa.CheckConstraint("revision > 0", name="ck_initial_calibration_revision"))
    op.create_index("ix_authored_initial_calibrations_user_id", "authored_initial_calibrations", ["user_id"])
    op.create_index("ix_initial_calibration_scope", "authored_initial_calibrations", ["user_id", "source_scope", "setup_scope"])


def downgrade():
    raise RuntimeError("Retain calibration provenance; use a forward migration")
