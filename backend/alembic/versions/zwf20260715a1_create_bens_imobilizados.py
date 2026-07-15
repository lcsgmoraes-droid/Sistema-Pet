"""create fixed assets registry

Revision ID: zwf20260715a1
Revises: zwe20260709a1
Create Date: 2026-07-15 07:35:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from app.tenant_rls_migration import TENANT_RLS_GUARD, apply_tenant_rls


revision: str = "zwf20260715a1"
down_revision: Union[str, None] = "zwe20260709a1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TABELAS_RLS = ("bens_imobilizados",)
TENANT_GUARD = TENANT_RLS_GUARD


def upgrade() -> None:
    op.create_table(
        "bens_imobilizados",
        sa.Column("nome", sa.String(length=180), nullable=False),
        sa.Column("codigo_patrimonial", sa.String(length=60), nullable=True),
        sa.Column("categoria", sa.String(length=40), nullable=False),
        sa.Column("descricao", sa.Text(), nullable=True),
        sa.Column("localizacao", sa.String(length=150), nullable=True),
        sa.Column("fornecedor", sa.String(length=180), nullable=True),
        sa.Column("documento", sa.String(length=100), nullable=True),
        sa.Column("documento_url", sa.String(length=500), nullable=True),
        sa.Column("quantidade", sa.Integer(), nullable=False),
        sa.Column("data_aquisicao", sa.Date(), nullable=False),
        sa.Column("valor_aquisicao", sa.Numeric(14, 2), nullable=False),
        sa.Column("valor_residual", sa.Numeric(14, 2), nullable=False),
        sa.Column("valor_mercado", sa.Numeric(14, 2), nullable=True),
        sa.Column("depreciar", sa.Boolean(), nullable=False),
        sa.Column("vida_util_meses", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("data_baixa", sa.Date(), nullable=True),
        sa.Column("motivo_baixa", sa.Text(), nullable=True),
        sa.Column("observacoes", sa.Text(), nullable=True),
        sa.Column("id", sa.Integer(), sa.Identity(always=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint("quantidade > 0", name="ck_bens_imobilizados_quantidade"),
        sa.CheckConstraint(
            "valor_aquisicao >= 0 AND valor_residual >= 0",
            name="ck_bens_imobilizados_valores",
        ),
        sa.CheckConstraint(
            "valor_residual <= valor_aquisicao",
            name="ck_bens_imobilizados_residual",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id",
            "codigo_patrimonial",
            name="uq_bens_imobilizados_tenant_codigo",
        ),
    )
    op.create_index(
        "ix_bens_imobilizados_tenant_id",
        "bens_imobilizados",
        ["tenant_id"],
        unique=False,
    )
    op.create_index(
        "ix_bens_imobilizados_tenant_status",
        "bens_imobilizados",
        ["tenant_id", "status"],
        unique=False,
    )
    op.create_index(
        "ix_bens_imobilizados_tenant_categoria",
        "bens_imobilizados",
        ["tenant_id", "categoria"],
        unique=False,
    )
    apply_tenant_rls(
        op_module=op,
        sa_module=sa,
        table_names=TABELAS_RLS,
        enable=True,
    )


def downgrade() -> None:
    apply_tenant_rls(
        op_module=op,
        sa_module=sa,
        table_names=TABELAS_RLS,
        enable=False,
    )
    op.drop_index(
        "ix_bens_imobilizados_tenant_categoria",
        table_name="bens_imobilizados",
    )
    op.drop_index(
        "ix_bens_imobilizados_tenant_status",
        table_name="bens_imobilizados",
    )
    op.drop_index("ix_bens_imobilizados_tenant_id", table_name="bens_imobilizados")
    op.drop_table("bens_imobilizados")
