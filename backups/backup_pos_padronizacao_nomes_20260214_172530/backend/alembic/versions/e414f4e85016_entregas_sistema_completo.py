"""entregas_sistema_completo

Sistema completo de gestão de entregas:
- Campos de entregador em clientes (custo operacional, rateio RH)
- Entregador padrão em configurações
- Tabela rotas_entrega (controle completo de entregas)

Revision ID: e414f4e85016
Revises: 921c0845a97a
Create Date: 2026-01-31 20:09:01.599822

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e414f4e85016'
down_revision: Union[str, Sequence[str], None] = '921c0845a97a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # =====================================================
    # 1️⃣ CLIENTES — CAMPOS DE ENTREGADOR (SÓ OS NOVOS)
    # =====================================================
    # is_entregador JÁ EXISTE - PULAR
    # tipo_vinculo_entrega JÁ EXISTE - PULAR
    
    op.add_column("clientes", sa.Column("entregador_ativo", sa.Boolean(), nullable=False, server_default=sa.true()))
    op.add_column("clientes", sa.Column("controla_rh", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("clientes", sa.Column("media_entregas_configurada", sa.Integer(), nullable=True))
    op.add_column("clientes", sa.Column("media_entregas_real", sa.Integer(), nullable=True))
    op.add_column("clientes", sa.Column("custo_rh_ajustado", sa.Numeric(10, 2), nullable=True))
    op.add_column("clientes", sa.Column("modelo_custo_entrega", sa.String(length=20), nullable=True))
    op.add_column("clientes", sa.Column("taxa_fixa_entrega", sa.Numeric(10, 2), nullable=True))
    op.add_column("clientes", sa.Column("valor_por_km_entrega", sa.Numeric(10, 2), nullable=True))
    op.add_column("clientes", sa.Column("moto_propria", sa.Boolean(), nullable=False, server_default=sa.true()))

    # =====================================================
    # 2️⃣ CONFIGURAÇÕES DE ENTREGA — ENTREGADOR PADRÃO
    # =====================================================
    # entregador_padrao_id JÁ EXISTE - PULAR

    # =====================================================
    # 3️⃣ ROTAS DE ENTREGA — NOVA TABELA
    # =====================================================
    op.create_table(
        "rotas_entrega",
        sa.Column("id", sa.Integer(), sa.Identity(always=True), primary_key=True),
        sa.Column("tenant_id", sa.UUID(), nullable=False),

        sa.Column("numero", sa.String(length=20), nullable=False, unique=True),

        sa.Column("venda_id", sa.Integer(), nullable=True),
        sa.Column("entregador_id", sa.Integer(), nullable=False),

        sa.Column("endereco_destino", sa.Text(), nullable=True),

        sa.Column("distancia_prevista", sa.Numeric(10, 2), nullable=True),
        sa.Column("distancia_real", sa.Numeric(10, 2), nullable=True),

        sa.Column("custo_previsto", sa.Numeric(10, 2), nullable=True),
        sa.Column("custo_real", sa.Numeric(10, 2), nullable=True),

        sa.Column("tentativas", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("moto_da_loja", sa.Boolean(), nullable=False, server_default=sa.false()),

        sa.Column("status", sa.String(length=20), nullable=False, server_default="pendente"),

        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("data_conclusao", sa.DateTime(), nullable=True),
        sa.Column("observacoes", sa.Text(), nullable=True),

        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.ForeignKeyConstraint(["venda_id"], ["vendas.id"]),
        sa.ForeignKeyConstraint(["entregador_id"], ["clientes.id"]),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
    )

    op.create_index("ix_rotas_entrega_tenant", "rotas_entrega", ["tenant_id"])
    op.create_index("ix_rotas_entrega_status", "rotas_entrega", ["status"])


def downgrade() -> None:
    """Downgrade schema."""
    # =====================================================
    # ROTAS DE ENTREGA
    # =====================================================
    op.drop_index("ix_rotas_entrega_status", table_name="rotas_entrega")
    op.drop_index("ix_rotas_entrega_tenant", table_name="rotas_entrega")
    op.drop_table("rotas_entrega")

    # =====================================================
    # CONFIGURAÇÕES DE ENTREGA
    # =====================================================
    # entregador_padrao_id JÁ EXISTIA ANTES - NÃO REMOVE

    # =====================================================
    # CLIENTES (SÓ OS NOVOS)
    # =====================================================
    op.drop_column("clientes", "moto_propria")
    op.drop_column("clientes", "valor_por_km_entrega")
    op.drop_column("clientes", "taxa_fixa_entrega")
    op.drop_column("clientes", "modelo_custo_entrega")
    op.drop_column("clientes", "custo_rh_ajustado")
    op.drop_column("clientes", "media_entregas_real")
    op.drop_column("clientes", "media_entregas_configurada")
    op.drop_column("clientes", "controla_rh")
    op.drop_column("clientes", "entregador_ativo")
    # is_entregador NÃO REMOVE (já existia antes)
    # tipo_vinculo_entrega NÃO REMOVE (já existia antes)
