"""
Módulo Financeiro - Contas a Receber
=====================================

Este módulo isola toda a lógica relacionada a CONTAS A RECEBER:
- Criação de contas a partir de vendas
- Baixa parcial/total de contas
- Controle de parcelamento
- Gestão de recebimentos
- Cálculo de status (pendente/parcial/recebido)

IMPORTANTE: Este módulo NÃO trata de:
- Caixa físico (dinheiro) → CaixaService
- Estoque → EstoqueService
- MovimentacoesBancarias → FinanceiroService (futura expansão)
"""

from .contas_receber_service import ContasReceberService

__all__ = ['ContasReceberService']
