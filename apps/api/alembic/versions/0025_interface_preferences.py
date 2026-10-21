"""Account-owned presentation preferences. No backfill or training-data changes."""
from alembic import op
import sqlalchemy as sa
revision = "0025_interface_preferences"
down_revision = "0024_merge_authored_customized"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("user_interface_preferences",
        sa.Column("user_id", sa.String(), sa.ForeignKey("users.id"), primary_key=True),
        sa.Column("theme_family", sa.String(16), nullable=False),
        sa.Column("appearance", sa.String(16), nullable=False),
        sa.Column("weight_unit", sa.String(2), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.CheckConstraint("revision > 0", name="ck_ui_preference_revision"),
        sa.CheckConstraint("theme_family IN ('graphite','charcoal','classic')", name="ck_ui_preference_theme"),
        sa.CheckConstraint("appearance IN ('light','dark','system')", name="ck_ui_preference_appearance"),
        sa.CheckConstraint("weight_unit IN ('kg','lb')", name="ck_ui_preference_unit"))


def downgrade():
    raise RuntimeError("Retain account preferences; use a forward migration")
