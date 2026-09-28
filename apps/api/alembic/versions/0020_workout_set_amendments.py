"""Auditable set amendments and captured progression replay context.

No identity/context/effort backfill; no historical performance rewrite.
"""
from alembic import op
import sqlalchemy as sa

revision = "0020_workout_set_amendments"
down_revision = "0019_workout_occurrence_identity"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("workout_set_logs") as batch:
        batch.add_column(sa.Column("voided_at", sa.DateTime(), nullable=True))
        batch.add_column(sa.Column("void_reason", sa.String(500), nullable=True))
        batch.add_column(sa.Column("void_source", sa.String(), nullable=True))
        batch.add_column(sa.Column("supersedes_id", sa.String(), nullable=True))
        batch.add_column(sa.Column("amended_at", sa.DateTime(), nullable=True))
        batch.add_column(sa.Column("replay_context", sa.JSON(), nullable=True))
        batch.create_foreign_key("fk_set_log_supersedes", "workout_set_logs", ["supersedes_id"], ["id"])
        batch.create_unique_constraint("uq_set_log_supersedes", ["supersedes_id"])


def downgrade():
    raise RuntimeError("Amendment history requires a separately reviewed data-preserving rollback")
