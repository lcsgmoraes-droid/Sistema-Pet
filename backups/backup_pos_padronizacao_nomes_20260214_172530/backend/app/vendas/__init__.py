"""
Módulo de Vendas - Service Orquestrador
========================================

Este módulo contém a lógica de negócio centralizada para vendas,
orquestrando os services especializados (EstoqueService, CaixaService,
ContasReceberService) em transações atômicas.

IMPORTANTE: Este é o ÚNICO lugar onde commits de venda devem acontecer.
"""

from .service import VendaService

__all__ = ['VendaService']
