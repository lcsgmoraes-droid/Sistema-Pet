"""
Contratos e interfaces do Motor de IA

Define claramente o que a IA PODE e NÃO PODE fazer.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List
from dataclasses import dataclass
from datetime import datetime


@dataclass
class AIResponse:
    """
    Resposta estruturada do Motor de IA.
    
    Garante que todas as respostas sejam auditáveis e explicáveis.
    """
    resposta: str  # Resposta em linguagem natural
    explicacao: str  # Como a IA chegou a essa conclusão
    fonte_dados: List[str]  # Origem dos dados utilizados (tabelas, insights, etc)
    confianca: float  # Nível de confiança (0.0 a 1.0)
    timestamp: datetime  # Quando a resposta foi gerada
    tenant_id: int  # Multi-tenant obrigatório
    metadata: Dict[str, Any]  # Dados adicionais para auditoria
    
    def __post_init__(self):
        """Validações básicas."""
        if not 0.0 <= self.confianca <= 1.0:
            raise ValueError("Confiança deve estar entre 0.0 e 1.0")
        
        if not self.tenant_id:
            raise ValueError("tenant_id é obrigatório (multi-tenant)")


class IAIPromptBuilder(ABC):
    """
    Interface para construção de prompts.
    
    Garante que prompts sejam controlados e auditáveis.
    """
    
    @abstractmethod
    def build_prompt(self, context: Dict[str, Any], objetivo: str) -> str:
        """
        Constrói um prompt estruturado.
        
        Args:
            context: Dados estruturados (read models, insights, etc)
            objetivo: O que o usuário quer saber/fazer
            
        Returns:
            Prompt formatado para envio ao motor de IA
        """
        pass


class IAIEngine(ABC):
    """
    Interface para o Motor de IA.
    
    Define o contrato de geração de respostas.
    """
    
    @abstractmethod
    async def generate_response(
        self,
        context: Dict[str, Any],
        objetivo: str,
        tenant_id: int
    ) -> AIResponse:
        """
        Gera uma resposta baseada no contexto.
        
        Args:
            context: Dados estruturados (NÃO faz queries no banco)
            objetivo: O que o usuário quer saber
            tenant_id: ID do tenant (multi-tenant)
            
        Returns:
            AIResponse estruturado e auditável
        """
        pass


# CONTRATOS EXPLÍCITOS: O QUE A IA PODE E NÃO PODE FAZER

class AIContracts:
    """
    Documentação clara dos contratos do Motor de IA.
    """
    
    # ❌ O QUE A IA **NÃO PODE** FAZER:
    PROHIBITED = [
        "Acessar banco de dados diretamente",
        "Criar ou modificar regras de negócio",
        "Executar comandos (Commands) no sistema",
        "Modificar estado da aplicação",
        "Acessar APIs externas sem controle",
        "Processar dados não estruturados sem validação",
    ]
    
    # ✅ O QUE A IA **PODE** FAZER:
    ALLOWED = [
        "Interpretar dados já processados (Read Models)",
        "Analisar Insights gerados pelo sistema",
        "Fornecer explicações contextualizadas",
        "Sugerir ações (mas não executá-las)",
        "Responder perguntas sobre o estado do negócio",
        "Gerar relatórios narrativos",
    ]
    
    # 📋 REQUISITOS OBRIGATÓRIOS:
    REQUIREMENTS = [
        "Multi-tenant obrigatório em todas operações",
        "Todas respostas devem ser auditáveis",
        "Fonte dos dados deve ser sempre identificada",
        "Nível de confiança deve ser calculado",
        "Timestamp de geração deve ser registrado",
    ]


@dataclass
class AIContext:
    """
    Contexto estruturado para envio ao Motor de IA.
    
    Padroniza como dados são fornecidos à IA.
    """
    tenant_id: int
    objetivo: str
    dados_estruturados: Dict[str, Any]  # Read Models, Insights, etc
    metadados: Dict[str, Any] = None  # Informações adicionais
    
    def __post_init__(self):
        if not self.tenant_id:
            raise ValueError("tenant_id é obrigatório")
        
        if not self.objetivo:
            raise ValueError("objetivo não pode ser vazio")
        
        if self.metadados is None:
            self.metadados = {}
