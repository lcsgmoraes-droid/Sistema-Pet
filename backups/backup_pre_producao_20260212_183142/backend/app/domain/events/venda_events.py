"""
Eventos do Domínio de Vendas
=============================

Define os eventos que podem ocorrer no ciclo de vida de uma venda.
"""

from dataclasses import dataclass
from typing import Optional, List, Dict, Any
from .base import DomainEvent


@dataclass(frozen=True)
class VendaCriada(DomainEvent):
    """
    Evento disparado quando uma nova venda é criada.
    
    Este evento indica que:
    - Uma venda foi registrada no sistema
    - Itens foram associados à venda
    - Contas a receber iniciais foram criadas
    - Status inicial: 'aberta'
    
    Casos de uso:
    - Notificar sistema de análise de vendas
    - Atualizar dashboard em tempo real
    - Disparar fluxo de preparação (separação de estoque)
    - Enviar notificação ao cliente (futuro)
    """
    
    venda_id: int
    numero_venda: str
    user_id: int
    cliente_id: Optional[int]
    funcionario_id: Optional[int]
    total: float
    quantidade_itens: int
    tem_entrega: bool
    
    # Metadados adicionais (opcional)
    metadados: Optional[Dict[str, Any]] = None


@dataclass(frozen=True)
class VendaFinalizada(DomainEvent):
    """
    Evento disparado quando uma venda é finalizada com pagamento.
    
    Este evento indica que:
    - Pagamento foi processado
    - Estoque foi baixado
    - Caixa foi movimentado (se dinheiro)
    - Contas a receber foram baixadas
    - Status: 'finalizada' ou 'baixa_parcial'
    
    Casos de uso:
    - Gerar comissões para vendedores/funcionários
    - Criar lembretes de recorrência
    - Disparar separação de produtos
    - Notificar cliente sobre venda confirmada
    - Atualizar métricas de vendas em tempo real
    - Integrar com sistema de entrega (se aplicável)
    """
    
    venda_id: int
    numero_venda: str
    user_id: int
    user_nome: str
    cliente_id: Optional[int]
    funcionario_id: Optional[int]
    total: float
    total_pago: float
    status: str  # 'finalizada' ou 'baixa_parcial'
    formas_pagamento: List[str]
    
    # Operações realizadas
    estoque_baixado: bool
    caixa_movimentado: bool
    contas_baixadas: int
    
    # Metadados adicionais (opcional)
    metadados: Optional[Dict[str, Any]] = None


@dataclass(frozen=True)
class VendaCancelada(DomainEvent):
    """
    Evento disparado quando uma venda é cancelada.
    
    Este evento indica que:
    - Venda foi cancelada por algum motivo
    - Estoque foi estornado
    - Contas a receber foram canceladas
    - Movimentações de caixa foram removidas
    - Comissões foram estornadas
    - Status: 'cancelada'
    
    Casos de uso:
    - Notificar gestão sobre cancelamento
    - Analisar motivos de cancelamento (BI)
    - Estornar comissões automaticamente
    - Notificar cliente sobre cancelamento
    - Atualizar métricas de vendas
    - Disparar investigação se cancelamento for suspeito
    """
    
    venda_id: int
    numero_venda: str
    user_id: int
    cliente_id: Optional[int]
    funcionario_id: Optional[int]
    motivo: str
    status_anterior: str
    total: float
    
    # Estornos realizados
    itens_estornados: int
    contas_canceladas: int
    comissoes_estornadas: bool
    
    # Metadados adicionais (opcional)
    metadados: Optional[Dict[str, Any]] = None


# Futuras expansões (placeholder):
# - VendaReaberta
# - VendaParcialmentePaga
# - VendaEntregue
# - VendaDevolvida
