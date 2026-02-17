"""
Módulo de Caixa (Cash Register)
================================

Este módulo isola toda a lógica relacionada ao CAIXA físico do PDV:
- Validação de caixa aberto
- Registro de movimentações de entrada/saída
- Vinculação de vendas ao caixa
- Registro de devoluções em dinheiro

IMPORTANTE: Este módulo NÃO trata de movimentações bancárias (PIX, cartão).
Isso pertence ao módulo financeiro.
"""

from .service import CaixaService

__all__ = ['CaixaService']
