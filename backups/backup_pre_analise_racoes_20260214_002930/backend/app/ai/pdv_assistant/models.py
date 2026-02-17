"""
PDVContext e Modelos de Dados

Define as estruturas de dados para o sistema de IA contextual do PDV.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from datetime import datetime
from decimal import Decimal
from enum import Enum


class TipoPDVSugestao(str, Enum):
    """Tipos de sugestões que a IA pode gerar"""
    CROSS_SELL = "cross_sell"  # Sugestão de produto complementar
    KIT_VANTAJOSO = "kit_vantajoso"  # Kit é mais vantajoso
    CLIENTE_RECORRENTE = "cliente_recorrente"  # Info sobre padrão do cliente
    CLIENTE_INATIVO = "cliente_inativo"  # Cliente há muito tempo sem comprar
    RECOMPRA = "recompra"  # Produto que cliente costuma recomprar
    ESTOQUE_CRITICO = "estoque_critico"  # Produto com estoque baixo
    CLIENTE_VIP = "cliente_vip"  # Cliente de alto valor
    PRODUTO_POPULAR = "produto_popular"  # Produto em alta
    OUTROS = "outros"


class PrioridadeSugestao(str, Enum):
    """Prioridade de exibição da sugestão"""
    ALTA = "alta"  # Exibir com destaque
    MEDIA = "media"  # Exibir normalmente
    BAIXA = "baixa"  # Exibir se houver espaço


@dataclass
class ItemVendaPDV:
    """
    Representa um item já adicionado à venda em andamento.
    """
    produto_id: int
    nome_produto: str
    quantidade: float
    valor_unitario: Decimal
    valor_total: Decimal
    categoria: Optional[str] = None
    fabricante: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "produto_id": self.produto_id,
            "nome_produto": self.nome_produto,
            "quantidade": float(self.quantidade),
            "valor_unitario": float(self.valor_unitario),
            "valor_total": float(self.valor_total),
            "categoria": self.categoria,
            "fabricante": self.fabricante,
        }


@dataclass
class PDVContext:
    """
    Contexto completo de uma venda em andamento no PDV.
    
    Este é o input principal para o PDVAIService.
    
    Attributes:
        tenant_id: ID do tenant (multi-tenant obrigatório)
        timestamp: Momento da análise
        itens: Produtos já adicionados à venda
        total_parcial: Valor total acumulado
        cliente_id: ID do cliente (opcional)
        cliente_nome: Nome do cliente (opcional)
        vendedor_id: ID do vendedor
        vendedor_nome: Nome do vendedor
        loja_id: ID da loja (se aplicável)
        metadata: Dados adicionais
    """
    tenant_id: int
    timestamp: datetime
    itens: List[ItemVendaPDV]
    total_parcial: Decimal
    vendedor_id: int
    vendedor_nome: str
    cliente_id: Optional[int] = None
    cliente_nome: Optional[str] = None
    loja_id: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validações básicas"""
        if not self.itens:
            # Venda vazia é válida (momento inicial)
            pass
        
        if self.total_parcial < 0:
            raise ValueError("Total parcial não pode ser negativo")
    
    @property
    def tem_cliente_identificado(self) -> bool:
        """Verifica se o cliente foi identificado"""
        return self.cliente_id is not None
    
    @property
    def quantidade_itens(self) -> int:
        """Retorna quantidade de itens na venda"""
        return len(self.itens)
    
    @property
    def produto_ids(self) -> List[int]:
        """Retorna lista de IDs de produtos na venda"""
        return [item.produto_id for item in self.itens]
    
    def to_dict(self) -> Dict[str, Any]:
        """Converte para dicionário"""
        return {
            "tenant_id": self.tenant_id,
            "timestamp": self.timestamp.isoformat(),
            "itens": [item.to_dict() for item in self.itens],
            "total_parcial": float(self.total_parcial),
            "vendedor_id": self.vendedor_id,
            "vendedor_nome": self.vendedor_nome,
            "cliente_id": self.cliente_id,
            "cliente_nome": self.cliente_nome,
            "loja_id": self.loja_id,
            "quantidade_itens": self.quantidade_itens,
            "tem_cliente_identificado": self.tem_cliente_identificado,
            "metadata": self.metadata,
        }


@dataclass
class PDVSugestao:
    """
    Representa uma sugestão gerada pela IA para o operador do PDV.
    
    Sugestões são:
    - Curtas e claras
    - Acionáveis
    - Não-intrusivas
    - Explicáveis
    """
    tipo: TipoPDVSugestao
    titulo: str  # Ex: "Kit mais vantajoso"
    mensagem: str  # Ex: "Este kit sai 12% mais barato"
    prioridade: PrioridadeSugestao
    dados_contexto: Dict[str, Any]  # Dados que geraram a sugestão
    confianca: float  # 0.0 a 1.0
    acionavel: bool  # Se tem ação que o operador pode fazer
    acao_sugerida: Optional[str] = None  # Ex: "Oferecer Kit Premium"
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validações"""
        if not 0.0 <= self.confianca <= 1.0:
            raise ValueError("Confiança deve estar entre 0.0 e 1.0")
        
        if len(self.mensagem) > 200:
            raise ValueError("Mensagem deve ter no máximo 200 caracteres")
    
    def to_dict(self) -> Dict[str, Any]:
        """Converte para dicionário"""
        return {
            "tipo": self.tipo.value,
            "titulo": self.titulo,
            "mensagem": self.mensagem,
            "prioridade": self.prioridade.value,
            "dados_contexto": self.dados_contexto,
            "confianca": self.confianca,
            "acionavel": self.acionavel,
            "acao_sugerida": self.acao_sugerida,
            "metadata": self.metadata,
        }
    
    @classmethod
    def criar_sugestao_simples(
        cls,
        tipo: TipoPDVSugestao,
        mensagem: str,
        prioridade: PrioridadeSugestao = PrioridadeSugestao.MEDIA,
        confianca: float = 0.8
    ) -> "PDVSugestao":
        """
        Factory method para criar sugestões simples rapidamente.
        """
        return cls(
            tipo=tipo,
            titulo=tipo.value.replace("_", " ").title(),
            mensagem=mensagem,
            prioridade=prioridade,
            dados_contexto={},
            confianca=confianca,
            acionavel=False,
        )
