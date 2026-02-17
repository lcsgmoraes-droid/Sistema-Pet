"""add_missing_permissions

Revision ID: 20260215_add_missing_permissions
Revises: ed82d13a98a0
Create Date: 2026-02-15 16:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20260215_add_missing_permissions'
down_revision: Union[str, Sequence[str], None] = '20260215_add_data_fechamento_comissao'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Adiciona todas as 51 permissões do sistema (35 novas + 16 existentes)"""
    
    # Usar INSERT com ON CONFLICT para não duplicar as 16 já existentes
    op.execute("""
        INSERT INTO permissions (code, description) VALUES
        -- Vendas (4 - já existem)
        ('vendas.criar', 'Criar vendas'),
        ('vendas.editar', 'Editar vendas'),
        ('vendas.excluir', 'Excluir vendas'),
        ('vendas.visualizar', 'Visualizar vendas'),
        
        -- Produtos (4 - já existem)
        ('produtos.criar', 'Criar produtos'),
        ('produtos.editar', 'Editar produtos'),
        ('produtos.excluir', 'Excluir produtos'),
        ('produtos.visualizar', 'Visualizar produtos'),
        
        -- Clientes (4 - já existem)
        ('clientes.criar', 'Criar clientes'),
        ('clientes.editar', 'Editar clientes'),
        ('clientes.excluir', 'Excluir clientes'),
        ('clientes.visualizar', 'Visualizar clientes'),
        
        -- Relatórios (2 - já existem)
        ('relatorios.financeiro', 'Acessar relatórios financeiros'),
        ('relatorios.gerencial', 'Acessar relatórios gerenciais'),
        
        -- Configurações (1 - já existe)
        ('configuracoes.editar', 'Editar configurações do sistema'),
        
        -- Usuários (1 - já existe)
        ('usuarios.gerenciar', 'Gerenciar usuários e permissões'),
        
        -- ====== NOVAS PERMISSÕES (35) ======
        
        -- Financeiro (10 novas)
        ('financeiro.dashboard', 'Visualizar Dashboard Financeiro'),
        ('financeiro.vendas', 'Visualizar Relatório de Vendas'),
        ('financeiro.fluxo_caixa', 'Visualizar Fluxo de Caixa'),
        ('financeiro.dre', 'Visualizar DRE (Demonstrativo de Resultados)'),
        ('financeiro.contas_pagar', 'Gerenciar Contas a Pagar'),
        ('financeiro.contas_receber', 'Gerenciar Contas a Receber'),
        ('financeiro.contas_bancarias', 'Gerenciar Contas Bancárias'),
        ('financeiro.formas_pagamento', 'Gerenciar Formas de Pagamento'),
        ('financeiro.relatorio_taxas', 'Visualizar Relatório de Taxas'),
        ('financeiro.conciliacao_cartao', 'Realizar Conciliação de Cartão'),
        
        -- Comissões (5)
        ('comissoes.configurar', 'Configurar Sistema de Comissões'),
        ('comissoes.demonstrativo', 'Visualizar Demonstrativo de Comissões'),
        ('comissoes.abertas', 'Visualizar Comissões em Aberto'),
        ('comissoes.fechamentos', 'Gerenciar Fechamentos de Comissões'),
        ('comissoes.relatorios', 'Visualizar Relatórios Analíticos de Comissões'),
        
        -- Entregas (4)
        ('entregas.abertas', 'Visualizar Entregas em Aberto'),
        ('entregas.rotas', 'Gerenciar Rotas de Entrega'),
        ('entregas.historico', 'Visualizar Histórico de Entregas'),
        ('entregas.dashboard', 'Visualizar Dashboard Financeiro de Entregas'),
        
        -- RH (1)
        ('rh.funcionarios', 'Gerenciar Funcionários'),
        
        -- Compras (4)
        ('compras.gerenciar', 'Gerenciar compras e pedidos'),
        ('compras.pedidos', 'Gerenciar Pedidos de Compra'),
        ('compras.entrada_xml', 'Processar Entrada de Notas por XML'),
        ('compras.sincronizacao_bling', 'Sincronizar com Bling'),
        
        -- Cadastros (4)
        ('cadastros.cargos', 'Gerenciar Cargos'),
        ('cadastros.categorias_produtos', 'Gerenciar Categorias de Produtos'),
        ('cadastros.categorias_financeiras', 'Gerenciar Categorias Financeiras'),
        ('cadastros.especies_racas', 'Gerenciar Espécies e Raças'),
        
        -- Configurações extras (4)
        ('configuracoes.empresa', 'Configurar Dados da Empresa'),
        ('configuracoes.entregas', 'Configurar Parâmetros de Entregas'),
        ('configuracoes.custos_moto', 'Configurar Custos da Moto'),
        ('configuracoes.fechamento_mensal', 'Realizar Fechamento Mensal'),
        
        -- IA (2)
        ('ia.whatsapp', 'Acessar Bot WhatsApp'),
        ('ia.fluxo_caixa', 'Acessar IA de Fluxo de Caixa'),
        
        -- Usuários frontend (1)
        ('usuarios.manage', 'Gerenciar usuários e permissões (frontend)')
        
        ON CONFLICT (code) DO NOTHING
    """)
    
    print("✅ 51 permissões garantidas no sistema (35 novas adicionadas)")


def downgrade() -> None:
    """Remove as 35 permissões adicionadas"""
    op.execute("""
        DELETE FROM permissions WHERE code IN (
            'financeiro.dashboard', 'financeiro.vendas', 'financeiro.fluxo_caixa',
            'financeiro.dre', 'financeiro.contas_pagar', 'financeiro.contas_receber',
            'financeiro.contas_bancarias', 'financeiro.formas_pagamento',
            'financeiro.relatorio_taxas', 'financeiro.conciliacao_cartao',
            'comissoes.configurar', 'comissoes.demonstrativo', 'comissoes.abertas',
            'comissoes.fechamentos', 'comissoes.relatorios',
            'entregas.abertas', 'entregas.rotas', 'entregas.historico', 'entregas.dashboard',
            'rh.funcionarios',
            'compras.gerenciar', 'compras.pedidos', 'compras.entrada_xml', 'compras.sincronizacao_bling',
            'cadastros.cargos', 'cadastros.categorias_produtos',
            'cadastros.categorias_financeiras', 'cadastros.especies_racas',
            'configuracoes.empresa', 'configuracoes.entregas',
            'configuracoes.custos_moto', 'configuracoes.fechamento_mensal',
            'ia.whatsapp', 'ia.fluxo_caixa',
            'usuarios.manage'
        )
    """)
    print("✅ 35 permissões removidas")
