"""
Classes de Eventos de Domínio
==============================

Eventos de domínio são objetos imutáveis que representam fatos que
aconteceram no sistema. Eles contêm apenas DADOS, sem lógica de negócio.

Princípios:
- Imutáveis (dataclass frozen)
- Apenas dados (sem métodos de negócio)
- Nomes no passado (VendaRealizadaEvent, não RealizarVendaEvent)
- Timestamp obrigatório
- user_id para multi-tenant

Arquitetura:
- DomainEvent: Classe base abstrata
- Eventos concretos: VendaRealizadaEvent, ProdutoVendidoEvent, etc.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any
from decimal import Decimal
import json


@dataclass(frozen=True, kw_only=True)
class DomainEvent:
    """
    Classe base para todos os eventos de domínio.
    
    Eventos são imutáveis e representam fatos que aconteceram.
    Não devem conter lógica de negócio, apenas dados.
    
    NOTA: timestamp e event_id são opcionais. Se não fornecidos,
    serão gerados automaticamente ao criar o evento.
    
    O uso de kw_only=True permite que classes filhas tenham campos
    obrigatórios mesmo quando a classe base tem campos opcionais.
    """
    
    user_id: int
    timestamp: Optional[datetime] = None
    event_id: Optional[str] = None
    
    def __post_init__(self):
        """Preenche timestamp e event_id se não fornecidos"""
        if self.timestamp is None:
            object.__setattr__(self, 'timestamp', datetime.now())
        if self.event_id is None:
            object.__setattr__(self, 'event_id', datetime.now().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        """Converte evento para dicionário"""
        data = {}
        for key, value in self.__dict__.items():
            if isinstance(value, datetime):
                data[key] = value.isoformat()
            elif isinstance(value, Decimal):
                data[key] = float(value)
            else:
                data[key] = value
        return data
    
    def to_json(self) -> str:
        """Converte evento para JSON"""
        return json.dumps(self.to_dict(), indent=2, ensure_ascii=False)


@dataclass(frozen=True)
class VendaRealizadaEvent(DomainEvent):
    """
    Evento disparado quando uma venda é FINALIZADA com sucesso.
    
    Representa o fato: "Uma venda foi concluída no sistema"
    
    Dados incluídos:
    - venda_id: ID da venda finalizada
    - numero_venda: Número sequencial da venda
    - cliente_id: ID do cliente (opcional)
    - vendedor_id: ID do vendedor (opcional)
    - funcionario_id: ID do funcionário que atendeu (opcional)
    - total: Valor total da venda
    - forma_pagamento: Forma de pagamento principal
    - quantidade_itens: Total de itens vendidos
    - tem_kit: Se a venda contém algum produto KIT
    - timestamp: Momento da finalização
    - user_id: Tenant que realizou a venda
    
    Uso:
    ```python
    evento = VendaRealizadaEvent(
        user_id=1,
        venda_id=123,
        numero_venda="VENDA-2026-00123",
        total=150.50,
        forma_pagamento="Dinheiro",
        quantidade_itens=3
    )
    ```
    """
    
    venda_id: int
    numero_venda: str
    total: float
    forma_pagamento: str
    quantidade_itens: int
    cliente_id: Optional[int] = None
    vendedor_id: Optional[int] = None
    funcionario_id: Optional[int] = None
    tem_kit: bool = False
    metadados: Optional[Dict[str, Any]] = None


@dataclass(frozen=True)
class ProdutoVendidoEvent(DomainEvent):
    """
    Evento disparado quando um produto SIMPLES ou VARIACAO é vendido.
    
    Representa o fato: "Um produto foi vendido em uma venda"
    
    Dados incluídos:
    - venda_id: ID da venda que contém o produto
    - produto_id: ID do produto vendido
    - produto_nome: Nome do produto (para facilitar consultas)
    - tipo_produto: SIMPLES ou VARIACAO
    - quantidade: Quantidade vendida
    - preco_unitario: Preço unitário praticado
    - preco_total: Preço total do item (quantidade × preço unitário)
    - estoque_anterior: Estoque antes da baixa
    - estoque_novo: Estoque após a baixa
    - timestamp: Momento da venda
    - user_id: Tenant
    
    Uso:
    ```python
    evento = ProdutoVendidoEvent(
        user_id=1,
        venda_id=123,
        produto_id=456,
        produto_nome="Shampoo Neutro 500ml",
        tipo_produto="SIMPLES",
        quantidade=2.0,
        preco_unitario=15.50,
        preco_total=31.00,
        estoque_anterior=10.0,
        estoque_novo=8.0
    )
    ```
    """
    
    venda_id: int
    produto_id: int
    produto_nome: str
    tipo_produto: str  # SIMPLES, VARIACAO
    quantidade: float
    preco_unitario: float
    preco_total: float
    estoque_anterior: float
    estoque_novo: float


@dataclass(frozen=True)
class KitVendidoEvent(DomainEvent):
    """
    Evento disparado quando um produto KIT é vendido.
    
    Representa o fato: "Um KIT foi vendido em uma venda"
    
    Dados incluídos:
    - venda_id: ID da venda que contém o KIT
    - kit_id: ID do produto KIT
    - kit_nome: Nome do KIT
    - tipo_kit: FISICO ou VIRTUAL
    - quantidade: Quantidade de KITs vendidos
    - preco_unitario: Preço unitário do KIT
    - preco_total: Preço total (quantidade × preço unitário)
    - componentes_baixados: Lista de componentes que tiveram estoque baixado
    - estoque_kit_anterior: Estoque do KIT antes (apenas FISICO)
    - estoque_kit_novo: Estoque do KIT após (apenas FISICO)
    - timestamp: Momento da venda
    - user_id: Tenant
    
    Uso:
    ```python
    evento = KitVendidoEvent(
        venda_id=123,
        kit_id=789,
        kit_nome="Kit Banho Completo",
        tipo_kit="VIRTUAL",
        quantidade=2.0,
        preco_unitario=85.00,
        preco_total=170.00,
        componentes_baixados=[
            {"produto_id": 10, "nome": "Shampoo", "quantidade": 2.0},
            {"produto_id": 11, "nome": "Condicionador", "quantidade": 2.0}
        ],
        user_id=1
    )
    ```
    """
    
    venda_id: int
    kit_id: int
    kit_nome: str
    tipo_kit: str  # FISICO, VIRTUAL
    quantidade: float
    preco_unitario: float
    preco_total: float
    componentes_baixados: list
    estoque_kit_anterior: Optional[float] = None  # Apenas FISICO
    estoque_kit_novo: Optional[float] = None  # Apenas FISICO
