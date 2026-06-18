"""create vet partner link and add organization_type to tenants

Revision ID: w2x3y4z5a6b7
Revises: v1a2b3c4d5e6
Create Date: 2026-03-15 00:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.dialects.postgresql import UUID
from alembic import op


revision: str = "w2x3y4z5a6b7"
down_revision: Union[str, Sequence[str], None] = "v1a2b3c4d5e6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    if not inspector.has_table("vet_partner_link"):
        op.create_table(
            "vet_partner_link",
            sa.Column("id", sa.Integer(), sa.Identity(always=True), nullable=False),
            sa.Column("empresa_tenant_id", UUID(as_uuid=True), nullable=False),
            sa.Column("vet_tenant_id", UUID(as_uuid=True), nullable=False),
            sa.Column(
                "tipo_relacao",
                sa.String(20),
                nullable=False,
                server_default="parceiro",
            ),
            sa.Column("comissao_empresa_pct", sa.Numeric(5, 2), nullable=True),
            sa.Column("ativo", sa.Boolean(), nullable=False, server_default="true"),
            sa.Column(
                "criado_em",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("now()"),
            ),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
            sa.PrimaryKeyConstraint("id"),
        )
        inspector = inspect(bind)

    index_names = {index["name"] for index in inspector.get_indexes("vet_partner_link")}
    if "ix_vet_partner_link_empresa_tenant_id" not in index_names:
        op.create_index(
            "ix_vet_partner_link_empresa_tenant_id",
            "vet_partner_link",
            ["empresa_tenant_id"],
        )
    if "ix_vet_partner_link_vet_tenant_id" not in index_names:
        op.create_index(
            "ix_vet_partner_link_vet_tenant_id",
            "vet_partner_link",
            ["vet_tenant_id"],
        )

    tenant_columns = {column["name"] for column in inspector.get_columns("tenants")}
    if "organization_type" not in tenant_columns:
        op.add_column(
            "tenants",
            sa.Column(
                "organization_type",
                sa.String(50),
                nullable=False,
                server_default="petshop",
            ),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    tenant_columns = {column["name"] for column in inspector.get_columns("tenants")}
    if "organization_type" in tenant_columns:
        op.drop_column("tenants", "organization_type")

    if inspector.has_table("vet_partner_link"):
        index_names = {index["name"] for index in inspector.get_indexes("vet_partner_link")}
        if "ix_vet_partner_link_vet_tenant_id" in index_names:
            op.drop_index(
                "ix_vet_partner_link_vet_tenant_id",
                table_name="vet_partner_link",
            )
        if "ix_vet_partner_link_empresa_tenant_id" in index_names:
            op.drop_index(
                "ix_vet_partner_link_empresa_tenant_id",
                table_name="vet_partner_link",
            )
        op.drop_table("vet_partner_link")
