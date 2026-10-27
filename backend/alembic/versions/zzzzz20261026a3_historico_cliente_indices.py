"""Indices das paginas de historico e suas relacoes de venda."""

from alembic import op

revision = "zzzzz20261026a3"
down_revision = "zzzzz20261026a2"
branch_labels = None
depends_on = None

INDICES = (
    ("ix_vendas_tenant_cliente_data_id", "vendas", ["tenant_id", "cliente_id", "data_venda", "id"]),
    ("ix_venda_itens_tenant_venda", "venda_itens", ["tenant_id", "venda_id"]),
    ("ix_venda_pagamentos_tenant_venda", "venda_pagamentos", ["tenant_id", "venda_id"]),
    ("ix_contas_receber_tenant_cliente_emissao", "contas_receber", ["tenant_id", "cliente_id", "data_emissao", "id"]),
)


def upgrade():
    for nome, tabela, colunas in INDICES:
        op.create_index(nome, tabela, colunas)


def downgrade():
    for nome, tabela, _ in reversed(INDICES):
        op.drop_index(nome, tabela)
