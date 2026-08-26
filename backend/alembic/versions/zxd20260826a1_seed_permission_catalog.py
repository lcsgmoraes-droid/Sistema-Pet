"""seed the canonical RBAC permission catalog

Revision ID: zxd20260826a1
Revises: zxc20260826a1
Create Date: 2026-08-26

The permissions table is structural data: a new database cannot create usable
tenant roles while it is empty. Keep this snapshot inside the migration so its
historical result remains reproducible even if the application evolves.
"""

from alembic import op
import sqlalchemy as sa


revision = "zxd20260826a1"
down_revision = "zxc20260826a1"
branch_labels = None
depends_on = None

PERMISSION_CATALOG = (
    ("cadastros.bancos", "Gerenciar bancos"),
    ("cadastros.cargos", "Gerenciar cargos"),
    ("cadastros.categorias_financeiras", "Gerenciar categorias financeiras"),
    ("cadastros.categorias_produtos", "Gerenciar categorias de produtos"),
    ("cadastros.especies_racas", "Gerenciar especies e racas"),
    ("cadastros.formas_pagamento", "Gerenciar formas de pagamento"),
    ("cadastros.operadoras", "Gerenciar operadoras de cartao"),
    ("clientes.criar", "Criar clientes"),
    ("clientes.editar", "Editar clientes"),
    ("clientes.excluir", "Excluir clientes"),
    ("clientes.visualizar", "Visualizar clientes"),
    ("comissoes.abertas", "Visualizar comissoes em aberto"),
    ("comissoes.configurar", "Configurar comissoes"),
    ("comissoes.demonstrativo", "Visualizar demonstrativo de comissoes"),
    ("comissoes.fechamentos", "Gerenciar fechamentos de comissoes"),
    ("comissoes.relatorios", "Visualizar relatorios de comissoes"),
    ("compras.entrada_xml", "Importar entradas de compra por XML"),
    ("compras.gerenciar", "Gerenciar compras"),
    ("compras.pedidos", "Gerenciar pedidos de compra"),
    ("compras.sincronizacao_bling", "Sincronizar compras com o Bling"),
    ("configuracoes.custos_moto", "Configurar custos de entrega por moto"),
    ("configuracoes.editar", "Editar configuracoes do tenant"),
    ("configuracoes.empresa", "Editar dados da empresa"),
    ("configuracoes.entregas", "Configurar entregas"),
    ("configuracoes.fechamento_mensal", "Configurar fechamento mensal"),
    ("entregas.abertas", "Visualizar entregas em aberto"),
    ("entregas.dashboard", "Visualizar painel de entregas"),
    ("entregas.historico", "Visualizar historico de entregas"),
    ("entregas.rotas", "Gerenciar rotas de entrega"),
    ("financeiro.conciliacao_bancaria", "Gerenciar conciliacao bancaria"),
    ("financeiro.conciliacao_cartao", "Gerenciar conciliacao de cartao"),
    ("financeiro.contas_bancarias", "Gerenciar contas bancarias"),
    ("financeiro.contas_pagar", "Gerenciar contas a pagar"),
    ("financeiro.contas_receber", "Gerenciar contas a receber"),
    ("financeiro.dashboard", "Visualizar painel financeiro"),
    ("financeiro.dre", "Visualizar demonstrativo de resultados"),
    ("financeiro.fluxo_caixa", "Visualizar fluxo de caixa"),
    ("financeiro.formas_pagamento", "Gerenciar formas de pagamento financeiras"),
    ("financeiro.relatorio_taxas", "Visualizar relatorio de taxas"),
    ("financeiro.vendas", "Visualizar vendas no financeiro"),
    ("ia.fluxo_caixa", "Usar analise de fluxo de caixa por IA"),
    ("ia.whatsapp", "Usar recursos de IA no WhatsApp"),
    ("produtos.criar", "Criar produtos"),
    ("produtos.editar", "Editar produtos"),
    ("produtos.excluir", "Excluir produtos"),
    ("produtos.visualizar", "Visualizar produtos"),
    ("relatorios.financeiro", "Visualizar relatorios financeiros"),
    ("relatorios.gerencial", "Visualizar relatorios gerenciais"),
    ("rh.funcionarios", "Gerenciar funcionarios"),
    ("usuarios.manage", "Gerenciar usuarios, perfis e permissoes"),
    ("vendas.criar", "Criar vendas"),
    ("vendas.editar", "Editar vendas"),
    ("vendas.excluir", "Excluir vendas"),
    ("vendas.visualizar", "Visualizar vendas"),
)


def upgrade() -> None:
    bind = op.get_bind()
    bind.execute(
        sa.text(
            """
            INSERT INTO permissions (code, description)
            VALUES (:code, :description)
            ON CONFLICT (code) DO UPDATE
            SET description = EXCLUDED.description
            """
        ),
        [
            {"code": code, "description": description}
            for code, description in PERMISSION_CATALOG
        ],
    )


def downgrade() -> None:
    """Preserve permission rows because tenant roles may already reference them."""
