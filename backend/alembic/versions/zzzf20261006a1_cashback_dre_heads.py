"""Merge cashback insert-clock and DRE benefit migration branches.

Revision ID: zzzf20261006a1
Revises: zzze20261005a1, drebenef20261005a1
"""

revision = "zzzf20261006a1"
down_revision = ("zzze20261005a1", "drebenef20261005a1")
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
