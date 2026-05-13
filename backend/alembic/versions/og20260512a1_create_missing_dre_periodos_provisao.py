"""legacy DRE reconciliation intentionally disabled

Revision ID: og20260512a1
Revises: of20260512a1
Create Date: 2026-05-13 10:00:00.000000

This revision is kept only to preserve the Alembic chain between
of20260512a1 and oh20260513a1. The previous draft inserted reconciled
dre_periodos for historical test DRE details. We no longer recover legacy DRE
test data; new tenants must receive clean tenant-owned template copies instead.
"""

from __future__ import annotations


revision = "og20260512a1"
down_revision = "of20260512a1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """No-op by design: do not create or reconcile legacy DRE records."""


def downgrade() -> None:
    """No-op by design: this revision does not change data or schema."""
