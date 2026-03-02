"""add password reset tokens

Revision ID: 0005_password_reset_tokens
Revises: 0004_recovery_measurements
Create Date: 2026-03-02 03:30:00
"""

from alembic import op
import sqlalchemy as sa


USER_FK = "users.id"

revision = "0005_password_reset_tokens"
down_revision = "0004_recovery_measurements"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("password_reset_tokens"):
        op.create_table(
            "password_reset_tokens",
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("user_id", sa.String(), nullable=False),
            sa.Column("token_hash", sa.String(), nullable=False),
            sa.Column("expires_at", sa.DateTime(), nullable=False),
            sa.Column("used_at", sa.DateTime(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["user_id"], [USER_FK]),
            sa.PrimaryKeyConstraint("id"),
        )

    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS ix_password_reset_tokens_token_hash ON password_reset_tokens (token_hash)"
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_password_reset_tokens_user_id ON password_reset_tokens (user_id)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_password_reset_tokens_user_id")
    op.execute("DROP INDEX IF EXISTS ix_password_reset_tokens_token_hash")
    op.execute("DROP TABLE IF EXISTS password_reset_tokens")
