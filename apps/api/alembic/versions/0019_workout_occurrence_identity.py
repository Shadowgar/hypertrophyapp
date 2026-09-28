"""Nullable legacy identity; persisted execution snapshots and retry results.

No historical backfill. Downgrade is deliberately blocked: old uniqueness cannot
represent qualified occurrences and dropping the ledger would lose retry safety.
"""
from alembic import op
import sqlalchemy as sa

revision = "0019_workout_occurrence_identity"
down_revision = "0018_choose_for_me_diagnostics"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table("workout_occurrences",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("user_id", sa.String(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("plan_id", sa.String(), nullable=False),
        sa.Column("week_start", sa.Date(), nullable=False),
        sa.Column("session_slot", sa.Integer(), nullable=False),
        sa.Column("workout_id", sa.String(), nullable=False),
        sa.Column("program_id", sa.String(), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("user_id", "plan_id", "session_slot", name="uq_workout_occurrence_slot"))
    op.create_index("ix_workout_occurrences_user_id", "workout_occurrences", ["user_id"])
    op.create_table("workout_log_commands",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("user_id", sa.String(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("command_id", sa.String(128), nullable=False),
        sa.Column("request_digest", sa.String(64), nullable=False),
        sa.Column("workout_occurrence_id", sa.String(), sa.ForeignKey("workout_occurrences.id"), nullable=False),
        sa.Column("exercise_occurrence_id", sa.String(), nullable=False),
        sa.Column("response", sa.JSON(), nullable=False),
        sa.Column("undone_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("user_id", "command_id", name="uq_workout_log_command_user"))
    op.create_index("ix_workout_log_commands_user_id", "workout_log_commands", ["user_id"])
    for table, check in [("workout_set_logs", "ck_set_log_occurrence_pair"),
                         ("workout_session_states", "ck_session_occurrence_pair")]:
        with op.batch_alter_table(table) as batch:
            batch.add_column(sa.Column("workout_occurrence_id", sa.String(), nullable=True))
            batch.add_column(sa.Column("exercise_occurrence_id", sa.String(), nullable=True))
            batch.create_foreign_key(f"fk_{table}_occurrence", "workout_occurrences", ["workout_occurrence_id"], ["id"])
            batch.create_check_constraint(check, "(workout_occurrence_id IS NULL) = (exercise_occurrence_id IS NULL)")
            batch.create_index(f"ix_{table}_workout_occurrence_id", ["workout_occurrence_id"])
            if table == "workout_set_logs":
                batch.add_column(sa.Column("command_id", sa.String(128), nullable=True))
                batch.add_column(sa.Column("request_digest", sa.String(64), nullable=True))
                batch.create_unique_constraint("uq_workout_set_log_command_user", ["user_id", "command_id"])
            else:
                batch.drop_constraint("uq_workout_session_states_user_workout_exercise", type_="unique")
                batch.create_unique_constraint("uq_workout_session_occurrence", ["user_id", "workout_occurrence_id", "exercise_occurrence_id"])
                batch.create_index("uq_workout_session_legacy", ["user_id", "workout_id", "exercise_id"], unique=True,
                    postgresql_where=sa.text("workout_occurrence_id IS NULL"), sqlite_where=sa.text("workout_occurrence_id IS NULL"))


def downgrade() -> None:
    raise RuntimeError("Occurrence history requires a separately reviewed data-preserving rollback")
