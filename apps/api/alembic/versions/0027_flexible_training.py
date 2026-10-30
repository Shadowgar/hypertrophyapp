"""Add native-source Flexible lifecycle and explicit receipt dates.

Existing prescriptions, occurrence anchors and receipts retain their values.
No enrollment, performed-date or source-position backfill is inferred.
"""
from alembic import op
import sqlalchemy as sa

revision = "0027_flexible_training"
down_revision = "0026_initial_calibration"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("users", sa.Column("schedule_mode", sa.String(16), nullable=False, server_default="calendar"))
    op.add_column("users", sa.Column("expected_sessions_per_week", sa.Integer(), nullable=True))
    op.create_table("training_sequences",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("user_id", sa.String(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("program_id", sa.String(), nullable=False),
        sa.Column("source_digest", sa.String(64), nullable=False),
        sa.Column("source_catalog", sa.JSON(), nullable=False),
        sa.Column("timezone", sa.String(64), nullable=False),
        sa.Column("expected_sessions_per_week", sa.Integer(), nullable=True),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("cursor", sa.Integer(), nullable=False),
        sa.Column("state", sa.String(24), nullable=False),
        sa.Column("consent", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("id", "user_id", name="uq_training_sequence_owner"),
        sa.CheckConstraint("revision > 0 AND cursor >= 0", name="ck_training_sequence_revision"),
        sa.CheckConstraint("expected_sessions_per_week IS NULL OR expected_sessions_per_week BETWEEN 1 AND 7", name="ck_training_sequence_frequency"),
        sa.CheckConstraint("state IN ('active','attention_required','finished','retired')", name="ck_training_sequence_state"))
    op.create_index("ix_training_sequences_user_id", "training_sequences", ["user_id"])
    op.create_index("uq_training_sequence_current", "training_sequences", ["user_id"], unique=True,
        postgresql_where=sa.text("state IN ('active','attention_required')"),
        sqlite_where=sa.text("state IN ('active','attention_required')"))
    op.create_table("training_sequence_commands",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("user_id", sa.String(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("command_id", sa.String(128), nullable=False),
        sa.Column("request_digest", sa.String(64), nullable=False),
        sa.Column("sequence_id", sa.String(), sa.ForeignKey("training_sequences.id"), nullable=False),
        sa.Column("operation", sa.String(24), nullable=False),
        sa.Column("response", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("user_id", "command_id", name="uq_training_sequence_command_user"),
        sa.ForeignKeyConstraint(["sequence_id", "user_id"], ["training_sequences.id", "training_sequences.user_id"],
            name="fk_sequence_command_owner"))
    op.create_index("ix_training_sequence_commands_user_id", "training_sequence_commands", ["user_id"])
    with op.batch_alter_table("workout_occurrences") as batch:
        batch.add_column(sa.Column("sequence_id", sa.String(), nullable=True))
        batch.add_column(sa.Column("source_position", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("source_week", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("source_session", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("prescription_digest", sa.String(64), nullable=True))
        batch.add_column(sa.Column("execution_state", sa.String(24), nullable=True))
        batch.add_column(sa.Column("execution_context", sa.JSON(), nullable=True))
        batch.add_column(sa.Column("advancement", sa.JSON(), nullable=True))
        batch.alter_column("plan_id", existing_type=sa.String(), nullable=True)
        batch.alter_column("week_start", existing_type=sa.Date(), nullable=True)
        batch.create_index("ix_workout_occurrences_sequence_id", ["sequence_id"])
        batch.create_unique_constraint("uq_sequence_source_position", ["sequence_id", "source_position"])
        batch.create_foreign_key("fk_occurrence_sequence_owner", "training_sequences", ["sequence_id", "user_id"], ["id", "user_id"])
        batch.create_check_constraint("ck_occurrence_anchor",
            "(sequence_id IS NULL AND plan_id IS NOT NULL AND week_start IS NOT NULL) OR "
            "(sequence_id IS NOT NULL AND plan_id IS NULL AND week_start IS NULL AND source_position IS NOT NULL AND execution_state IS NOT NULL)")
    op.add_column("workout_set_logs", sa.Column("performed_local_date", sa.Date(), nullable=True))
    op.add_column("workout_set_logs", sa.Column("performed_timezone", sa.String(64), nullable=True))
    op.add_column("workout_set_logs", sa.Column("execution_context_id", sa.String(128), nullable=True))


def downgrade():
    raise RuntimeError("Retain Flexible ownership, source identities and actual-date history; use a reviewed forward migration")
