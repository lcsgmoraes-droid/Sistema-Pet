"""
Models para IA Conversacional Interna (Chat do Operador)

Este módulo define os contratos de dados para o chat interno que permite
ao operador fazer perguntas em linguagem natural sobre o sistema.

PRINCÍPIOS:
- Dataclasses imutáveis (frozen=True)
- Multi-tenant obrigatório
- Apenas consulta (não executa ações)
- Sempre auditável
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, List, Any


@dataclass(frozen=True)
class OperatorMessage:
    """
    Representa uma mensagem/pergunta do operador.
    
    Atributos:
        pergunta: Texto livre em linguagem natural
        operador_id: ID do operador que fez a pergunta
        operador_nome: Nome do operador (para contexto)
        timestamp: Momento da pergunta
    """
    pergunta: str
    operador_id: int
    operador_nome: str
    timestamp: datetime = field(default_factory=datetime.now)
    
    def __post_init__(self):
        """Validações básicas"""
        if not self.pergunta or not self.pergunta.strip():
            raise ValueError("Pergunta não pode ser vazia")
        if self.operador_id <= 0:
            raise ValueError("operador_id deve ser maior que 0")
        if not self.operador_nome or not self.operador_nome.strip():
            raise ValueError("operador_nome não pode ser vazio")


@dataclass(frozen=True)
class OperatorChatContext:
    """
    Contexto completo para processar uma pergunta do operador.
    
    Este contexto reúne TODOS os dados necessários para a IA responder,
    incluindo informações do PDV, insights e dados de clientes/produtos.
    
    Atributos:
        tenant_id: ID do tenant (multi-tenant obrigatório)
        message: Mensagem/pergunta do operador
        contexto_pdv: Dados da venda em andamento (opcional)
        contexto_insights: Insights relevantes disponíveis (opcional)
        contexto_cliente: Dados do cliente sendo atendido (opcional)
        contexto_produto: Dados de produtos da venda (opcional)
        metadados: Informações adicionais para auditoria
    """
    tenant_id: int
    message: OperatorMessage
    contexto_pdv: Optional[Dict[str, Any]] = None
    contexto_insights: Optional[List[Dict[str, Any]]] = None
    contexto_cliente: Optional[Dict[str, Any]] = None
    contexto_produto: Optional[List[Dict[str, Any]]] = None
    metadados: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validações críticas"""
        if self.tenant_id <= 0:
            raise ValueError("tenant_id deve ser maior que 0")
        if not isinstance(self.message, OperatorMessage):
            raise ValueError("message deve ser do tipo OperatorMessage")


@dataclass(frozen=True)
class OperatorChatResponse:
    """
    Resposta da IA para uma pergunta do operador.
    
    IMPORTANTE:
    - A resposta é SEMPRE consultiva
    - NUNCA executa ações
    - SEMPRE indica fontes utilizadas
    - SEMPRE indica nível de confiança
    
    Atributos:
        resposta: Texto da resposta em linguagem natural
        confianca: Nível de confiança (0.0 a 1.0)
        fontes_utilizadas: Quais fontes foram consultadas
        sugestoes_acao: Sugestões (opcional) - NUNCA automáticas
        contexto_usado: Resumo do contexto que foi processado
        timestamp: Momento da resposta
        tempo_processamento_ms: Tempo para gerar resposta
        origem: Origem da resposta (mock, openai, claude, etc)
        intencao_detectada: Tipo de pergunta identificada
    """
    resposta: str
    confianca: float
    fontes_utilizadas: List[str]
    contexto_usado: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.now)
    tempo_processamento_ms: Optional[int] = None
    origem: str = "mock"
    intencao_detectada: Optional[str] = None
    sugestoes_acao: Optional[List[str]] = None
    
    def __post_init__(self):
        """Validações da resposta"""
        if not self.resposta or not self.resposta.strip():
            raise ValueError("Resposta não pode ser vazia")
        if not (0.0 <= self.confianca <= 1.0):
            raise ValueError("Confiança deve estar entre 0.0 e 1.0")
        if not self.fontes_utilizadas:
            raise ValueError("Deve ter pelo menos uma fonte utilizada")


@dataclass(frozen=True)
class IntentionDetectionResult:
    """
    Resultado da detecção de intenção (heurística simples).
    
    Usado pelo adapter para determinar qual prompt usar.
    
    Atributos:
        intencao: Tipo de intenção detectada
        confianca: Confiança da detecção (0.0 a 1.0)
        palavras_chave: Palavras-chave que levaram à detecção
        prompt_sugerido: Nome do prompt recomendado
    """
    intencao: str
    confianca: float
    palavras_chave: List[str]
    prompt_sugerido: str
    
    def __post_init__(self):
        """Validações"""
        if not self.intencao:
            raise ValueError("Intenção não pode ser vazia")
        if not (0.0 <= self.confianca <= 1.0):
            raise ValueError("Confiança deve estar entre 0.0 e 1.0")


# Tipos de intenção suportados (usado pelo adapter)
INTENCAO_CLIENTE = "cliente"
INTENCAO_PRODUTO = "produto"
INTENCAO_KIT = "kit"
INTENCAO_ESTOQUE = "estoque"
INTENCAO_INSIGHT = "insight"
INTENCAO_VENDA = "venda"
INTENCAO_GENERICA = "generica"

# Fontes de dados possíveis (para rastreabilidade)
FONTE_PDV_CONTEXT = "pdv_context"
FONTE_READ_MODEL = "read_model"
FONTE_INSIGHT = "insight"
FONTE_REGRA_NEGOCIO = "regra_negocio"
FONTE_HEURISTICA = "heuristica"
