"""Cria tabela vet_partner_link e adiciona organization_type ao tenant

Revision ID: w2x3y4z5a6b7
Revises: v1a2b3c4d5e6
Create Date: 2026-03-15 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID
from alembic import op

revision: str = "w2x3y4z5a6b7"
down_revision: Union[str, Sequence[str], None] = "v1a2b3c4d5e6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # vet_partner_link — vínculo entre tenant da loja e tenant do veterinário parceiro
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
        ),  # 'parceiro' | 'funcionario'
        sa.Column("comissao_empresa_pct", sa.Numeric(5, 2), nullable=True),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column(
            "criado_em",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["empresa_tenant_id"],
            ["tenants.id"],
            name="fk_vet_partner_link_empresa_tenant",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["vet_tenant_id"],
            ["tenants.id"],
            name="fk_vet_partner_link_vet_tenant",
            ondelete="CASCADE",
        ),
    )
    op.create_index(
        "ix_vet_partner_link_empresa_tenant_id",
        "vet_partner_link",
        ["empresa_tenant_id"],
    )
    op.create_index(
        "ix_vet_partner_link_vet_tenant_id",
        "vet_partner_link",
        ["vet_tenant_id"],
    )

    # organization_type no tenant — identifica o tipo de organização
    # petshop | veterinary_clinic | grooming | hospital
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
    op.drop_column("tenants", "organization_type")
    op.drop_index("ix_vet_partner_link_vet_tenant_id", table_name="vet_partner_link")
    op.drop_index(
        "ix_vet_partner_link_empresa_tenant_id", table_name="vet_partner_link"
    )
    op.drop_table("vet_partner_link")
