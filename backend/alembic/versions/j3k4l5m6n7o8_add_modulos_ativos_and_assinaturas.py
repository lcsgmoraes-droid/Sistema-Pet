"""add modulos_ativos to tenants and create assinaturas_modulos table

Revision ID: j3k4l5m6n7o8
Revises: i2j3k4l5m6n7
Create Date: 2026-03-07
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision: str = "j3k4l5m6n7o8"
down_revision: Union[str, None] = "i2j3k4l5m6n7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    tenant_columns = {column["name"] for column in inspector.get_columns("tenants")}
    if "modulos_ativos" not in tenant_columns:
        op.add_column(
            "tenants",
            sa.Column(
                "modulos_ativos",
                sa.Text(),
                nullable=True,
                comment='JSON: lista de modulos premium ativos. Ex: ["entregas","campanhas"]',
            ),
        )

    if not inspector.has_table("assinaturas_modulos"):
        op.create_table(
            "assinaturas_modulos",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("tenant_id", sa.String(36), nullable=False, index=True),
            sa.Column("modulo", sa.String(50), nullable=False),
            sa.Column("status", sa.String(20), nullable=False, server_default="ativo"),
            sa.Column("valor_mensal", sa.Numeric(10, 2), nullable=True),
            sa.Column("data_inicio", sa.DateTime(timezone=True), nullable=True),
            sa.Column("data_fim", sa.DateTime(timezone=True), nullable=True),
            sa.Column("payment_id", sa.String(200), nullable=True),
            sa.Column("gateway", sa.String(50), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
                nullable=False,
            ),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
            sa.PrimaryKeyConstraint("id"),
        )
        inspector = inspect(bind)

    index_names = {
        index["name"] for index in inspector.get_indexes("assinaturas_modulos")
    }
    if "ix_assinaturas_modulos_tenant_modulo" not in index_names:
        op.create_index(
            "ix_assinaturas_modulos_tenant_modulo",
            "assinaturas_modulos",
            ["tenant_id", "modulo"],
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    if inspector.has_table("assinaturas_modulos"):
        index_names = {
            index["name"] for index in inspector.get_indexes("assinaturas_modulos")
        }
        if "ix_assinaturas_modulos_tenant_modulo" in index_names:
            op.drop_index(
                "ix_assinaturas_modulos_tenant_modulo",
                table_name="assinaturas_modulos",
            )
        op.drop_table("assinaturas_modulos")

    tenant_columns = {column["name"] for column in inspector.get_columns("tenants")}
    if "modulos_ativos" in tenant_columns:
        op.drop_column("tenants", "modulos_ativos")
