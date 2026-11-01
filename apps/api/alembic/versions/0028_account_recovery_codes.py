"""Add email-free recovery credentials and owner-visible security audit.

Additive only: no account credential, training, schema-state or history backfill.
"""
from alembic import op
import sqlalchemy as sa

revision = '0028_account_recovery_codes'
down_revision = '0027_flexible_training'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('account_recovery_codes',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('user_id', sa.String(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('batch_id', sa.String(36), nullable=False),
        sa.Column('code_hash', sa.String(64), nullable=False, unique=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('used_at', sa.DateTime(), nullable=True),
        sa.Column('revoked_at', sa.DateTime(), nullable=True))
    op.create_index('ix_account_recovery_codes_user_id', 'account_recovery_codes', ['user_id'])
    op.create_table('account_security_events',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('user_id', sa.String(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('kind', sa.String(32), nullable=False),
        sa.Column('command_id', sa.String(36), nullable=True),
        sa.Column('batch_id', sa.String(36), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('acknowledged_at', sa.DateTime(), nullable=True),
        sa.UniqueConstraint('user_id', 'command_id', name='uq_recovery_generation_command'))
    op.create_index('ix_account_security_events_user_id', 'account_security_events', ['user_id'])


def downgrade():
    raise RuntimeError('Preserve recovery audit and credential state; use a separately reviewed forward migration')
