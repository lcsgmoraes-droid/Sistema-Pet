"""add tenant discovery coordinates and unique normalized names

Revision ID: zwn20260729a1
Revises: zwm20260724a1
Create Date: 2026-07-29
"""

import re
import unicodedata

from alembic import op
import sqlalchemy as sa


revision = "zwn20260729a1"
down_revision = "zwm20260724a1"
branch_labels = None
depends_on = None


def _normalize_name(value: str | None) -> str:
    normalized = unicodedata.normalize("NFKD", str(value or "").strip().lower())
    without_accents = "".join(
        char for char in normalized if unicodedata.category(char) != "Mn"
    )
    return re.sub(r"\s+", " ", without_accents)


def upgrade() -> None:
    op.add_column("tenants", sa.Column("name_normalized", sa.String(255), nullable=True))
    op.add_column("tenants", sa.Column("latitude", sa.Float(), nullable=True))
    op.add_column("tenants", sa.Column("longitude", sa.Float(), nullable=True))

    connection = op.get_bind()
    rows = list(
        connection.execute(
            sa.text("SELECT id, name FROM tenants ORDER BY id")
        ).mappings()
    )
    normalized_by_id: dict[str, str] = {}
    owners_by_name: dict[str, str] = {}
    duplicate_names: set[str] = set()
    for row in rows:
        tenant_id = str(row["id"])
        normalized_name = _normalize_name(row["name"]) or f"loja-{tenant_id[:8]}"
        if normalized_name in owners_by_name:
            duplicate_names.add(normalized_name)
        owners_by_name[normalized_name] = tenant_id
        normalized_by_id[tenant_id] = normalized_name

    if duplicate_names:
        names = ", ".join(sorted(duplicate_names))
        raise RuntimeError(
            "Existem lojas com nomes duplicados. Corrija antes da migracao: "
            f"{names}"
        )

    for tenant_id, normalized_name in normalized_by_id.items():
        connection.execute(
            sa.text(
                "UPDATE tenants SET name_normalized = :name_normalized WHERE id = :tenant_id"
            ),
            {"name_normalized": normalized_name, "tenant_id": tenant_id},
        )

    op.alter_column("tenants", "name_normalized", nullable=False)
    op.create_index(
        "ux_tenants_name_normalized",
        "tenants",
        ["name_normalized"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ux_tenants_name_normalized", table_name="tenants")
    op.drop_column("tenants", "longitude")
    op.drop_column("tenants", "latitude")
    op.drop_column("tenants", "name_normalized")
