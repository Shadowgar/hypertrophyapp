"""Join additive Authored-load and Customized migrations without changing data."""

revision = "0024_merge_authored_customized"
down_revision = ("0022_authored_load_states", "0023_customized_inventory")
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
