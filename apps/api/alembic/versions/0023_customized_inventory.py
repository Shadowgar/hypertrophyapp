"""Account-owned real equipment and optional strength information. No backfill."""
from alembic import op
import sqlalchemy as sa
revision='0023_customized_inventory'
down_revision='0022_customized_application'
branch_labels=None
depends_on=None

def upgrade():
    op.create_table('customized_equipment_profiles',
        sa.Column('user_id',sa.String(),sa.ForeignKey('users.id'),primary_key=True),
        sa.Column('revision',sa.Integer(),nullable=False),
        sa.Column('data',sa.JSON(),nullable=False),
        sa.Column('updated_at',sa.DateTime(),nullable=False),
        sa.CheckConstraint('revision > 0',name='ck_customized_inventory_revision'))
    op.create_index('ix_customized_load_cohort_date','workout_occurrences',['user_id','program_id','scheduled_date'])

def downgrade():
    raise RuntimeError('Retain user inventory and load evidence; use a forward migration')
