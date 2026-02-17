"""
Models de Insights - Estruturas de Dados
=========================================

Define as estruturas de dados para o sistema de insights automáticos.

Insights são observações/recomendações geradas automaticamente a partir
da análise de eventos de domínio via Read Models.

Características:
- Insights são IMUTÁVEIS (frozen dataclass)
- Gerados por regras determinísticas
- NÃO requerem IA (mas podem ser enriquecidos com IA no futuro)
- Multi-tenant (user_id obrigatório)

Tipos de Insights:
- CLIENTE_RECORRENTE_ATRASADO: Cliente regular não comprou no prazo esperado
- CLIENTE_INATIVO: Cliente sem compras há muito tempo
- PRODUTOS_COMPRADOS_JUNTOS: Oportunidade de cross-sell
- KIT_MAIS_VANTAJOSO: Kit tem melhor custo-benefício que itens separados
- PRODUTO_TOP_VENDAS: Produto está em alta
- KIT_TOP_VENDAS: Kit está em alta
- ESTOQUE_ALERTA: Produto vendendo rápido (futuro)
- SEGMENTO_RFM: Cliente mudou de segmento (futuro)

Severidade:
- INFO: Informação geral, sem ação urgente
- ATENCAO: Requer atenção, possível problema
- OPORTUNIDADE: Chance de aumentar vendas/receita
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any
import json


class TipoInsight(str, Enum):
    """
    Tipos de insights que o sistema pode gerar.
    
    Cada tipo representa uma observação/recomendação específica.
    """
    
    # Insights de clientes
    CLIENTE_RECORRENTE_ATRASADO = "CLIENTE_RECORRENTE_ATRASADO"
    CLIENTE_INATIVO = "CLIENTE_INATIVO"
    CLIENTE_VIP = "CLIENTE_VIP"
    CLIENTE_EM_RISCO_CHURN = "CLIENTE_EM_RISCO_CHURN"
    
    # Insights de produtos
    PRODUTO_TOP_VENDAS = "PRODUTO_TOP_VENDAS"
    PRODUTO_BAIXO_MOVIMENTO = "PRODUTO_BAIXO_MOVIMENTO"
    PRODUTOS_COMPRADOS_JUNTOS = "PRODUTOS_COMPRADOS_JUNTOS"
    
    # Insights de kits
    KIT_TOP_VENDAS = "KIT_TOP_VENDAS"
    KIT_MAIS_VANTAJOSO = "KIT_MAIS_VANTAJOSO"
    
    # Insights gerais
    TENDENCIA_VENDAS = "TENDENCIA_VENDAS"
    OPORTUNIDADE_COMBO = "OPORTUNIDADE_COMBO"


class SeveridadeInsight(str, Enum):
    """
    Nível de severidade/prioridade de um insight.
    
    Define a urgência e importância da ação sugerida.
    """
    
    INFO = "INFO"  # Informação geral, sem urgência
    ATENCAO = "ATENCAO"  # Requer atenção, possível problema
    OPORTUNIDADE = "OPORTUNIDADE"  # Chance de ganho, não urgente
    CRITICO = "CRITICO"  # Requer ação imediata (futuro)


class EntidadeInsight(str, Enum):
    """
    Tipo de entidade sobre a qual o insight trata.
    """
    
    CLIENTE = "CLIENTE"
    PRODUTO = "PRODUTO"
    KIT = "KIT"
    VENDA = "VENDA"
    GERAL = "GERAL"


@dataclass(frozen=True)
class Insight:
    """
    Representa um insight gerado automaticamente pelo sistema.
    
    Insights são observações/recomendações baseadas em análise de dados
    históricos. São imutáveis e servem como base para:
    - Alertas automáticos
    - Recomendações ao usuário
    - Entrada para IA generativa (Sprint 6)
    - Dashboards de insights
    
    Atributos:
        id: Identificador único do insight
        tipo: Tipo do insight (TipoInsight enum)
        titulo: Título curto e descritivo
        descricao: Descrição detalhada do insight
        severidade: Nível de importância/urgência
        entidade: Tipo de entidade sobre a qual trata
        entidade_id: ID da entidade específica (cliente_id, produto_id, etc.)
        dados_contexto: Dados adicionais relevantes (dict)
        user_id: Tenant ao qual o insight pertence
        timestamp: Momento em que o insight foi gerado
        acao_sugerida: Sugestão de ação (opcional)
        metricas: Métricas relevantes (opcional)
    
    Exemplo:
    ```python
    insight = Insight(
        id="INS-20260125-001",
        tipo=TipoInsight.CLIENTE_RECORRENTE_ATRASADO,
        titulo="Cliente João está atrasado",
        descricao="Cliente comprava a cada 15 dias, última compra há 25 dias",
        severidade=SeveridadeInsight.ATENCAO,
        entidade=EntidadeInsight.CLIENTE,
        entidade_id=42,
        dados_contexto={
            "dias_desde_ultima_compra": 25,
            "frequencia_esperada": 15,
            "atraso_dias": 10
        },
        user_id=1,
        timestamp=datetime.now(),
        acao_sugerida="Entre em contato para oferecer promoção personalizada"
    )
    ```
    """
    
    # Identificação
    id: str
    tipo: TipoInsight
    
    # Conteúdo
    titulo: str
    descricao: str
    
    # Classificação
    severidade: SeveridadeInsight
    entidade: EntidadeInsight
    entidade_id: Optional[int] = None
    
    # Dados contextuais
    dados_contexto: Dict[str, Any] = field(default_factory=dict)
    metricas: Dict[str, float] = field(default_factory=dict)
    
    # Ação recomendada
    acao_sugerida: Optional[str] = None
    
    # Multi-tenancy
    user_id: int = None
    
    # Timestamp
    timestamp: datetime = field(default_factory=datetime.now)
    
    def __post_init__(self):
        """Validações básicas"""
        if self.user_id is None:
            raise ValueError("user_id é obrigatório para multi-tenancy")
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Converte insight para dicionário.
        
        Útil para serialização JSON, envio via API, etc.
        
        Returns:
            Dict com todos os campos do insight
        """
        return {
            'id': self.id,
            'tipo': self.tipo.value,
            'titulo': self.titulo,
            'descricao': self.descricao,
            'severidade': self.severidade.value,
            'entidade': self.entidade.value,
            'entidade_id': self.entidade_id,
            'dados_contexto': self.dados_contexto,
            'metricas': self.metricas,
            'acao_sugerida': self.acao_sugerida,
            'user_id': self.user_id,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None
        }
    
    def to_json(self) -> str:
        """
        Converte insight para JSON.
        
        Returns:
            String JSON formatada
        """
        return json.dumps(self.to_dict(), indent=2, ensure_ascii=False)
    
    def __str__(self) -> str:
        """Representação em string para logs"""
        return (
            f"[{self.severidade.value}] {self.titulo} "
            f"(tipo={self.tipo.value}, entidade={self.entidade.value}#{self.entidade_id})"
        )
