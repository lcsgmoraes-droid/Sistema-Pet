"""
AIPromptBuilder - Construtor de Prompts Controlados

Responsável por montar prompts estruturados e explicáveis para o Motor de IA.
Garante que todos os contextos sejam formatados de forma padronizada.
"""

from typing import Dict, Any, List
import json
from datetime import datetime

from app.ai.contracts import IAIPromptBuilder


class AIPromptBuilder(IAIPromptBuilder):
    """
    Construtor de prompts para o Motor de IA.
    
    Recebe contexto estruturado e objetivo, retorna prompt formatado.
    """
    
    def __init__(self):
        """Inicializa o construtor de prompts."""
        self.template_base = self._load_template_base()
    
    def _load_template_base(self) -> str:
        """
        Template base para construção de prompts.
        
        Pode ser customizado conforme necessidade.
        """
        return """
Você é um assistente especializado em análise de dados de Pet Shop.

**SEU PAPEL:**
- Interpretar dados estruturados fornecidos
- Fornecer insights acionáveis
- Explicar suas conclusões de forma clara
- Sugerir ações (mas não executá-las)

**RESTRIÇÕES:**
- Você NÃO tem acesso direto ao banco de dados
- Você NÃO pode executar comandos no sistema
- Você NÃO pode criar ou modificar regras de negócio
- Você apenas interpreta os dados que lhe são fornecidos

**FORMATO DE RESPOSTA:**
Sua resposta deve ser clara, objetiva e baseada nos dados fornecidos.

---

**CONTEXTO:**
{contexto}

---

**OBJETIVO:**
{objetivo}

---

**INSTRUÇÕES:**
Analise o contexto fornecido e responda ao objetivo de forma:
1. Clara e objetiva
2. Baseada nos dados fornecidos
3. Com explicação de raciocínio
4. Com sugestões acionáveis (quando aplicável)
"""
    
    def build_prompt(self, context: Dict[str, Any], objetivo: str) -> str:
        """
        Constrói um prompt estruturado.
        
        Args:
            context: Dados estruturados (read models, insights, etc)
            objetivo: O que o usuário quer saber/fazer
            
        Returns:
            Prompt formatado para envio ao motor de IA
        """
        # Formata o contexto de forma legível
        contexto_formatado = self._format_context(context)
        
        # Substitui no template
        prompt = self.template_base.format(
            contexto=contexto_formatado,
            objetivo=objetivo
        )
        
        return prompt
    
    def _format_context(self, context: Dict[str, Any]) -> str:
        """
        Formata o contexto de forma legível para o prompt.
        
        Args:
            context: Dicionário com dados estruturados
            
        Returns:
            String formatada com o contexto
        """
        sections = []
        
        # Processa cada seção do contexto
        for key, value in context.items():
            section = self._format_section(key, value)
            sections.append(section)
        
        return "\n\n".join(sections)
    
    def _format_section(self, key: str, value: Any) -> str:
        """
        Formata uma seção específica do contexto.
        
        Args:
            key: Nome da seção
            value: Dados da seção
            
        Returns:
            String formatada
        """
        # Título da seção
        title = key.replace("_", " ").title()
        section = f"### {title}\n"
        
        # Formata o valor conforme tipo
        if isinstance(value, dict):
            section += self._format_dict(value)
        elif isinstance(value, list):
            section += self._format_list(value)
        else:
            section += str(value)
        
        return section
    
    def _format_dict(self, data: Dict[str, Any], indent: int = 0) -> str:
        """
        Formata um dicionário de forma legível.
        
        Args:
            data: Dicionário a ser formatado
            indent: Nível de indentação
            
        Returns:
            String formatada
        """
        lines = []
        prefix = "  " * indent
        
        for key, value in data.items():
            key_formatted = key.replace("_", " ").title()
            
            if isinstance(value, dict):
                lines.append(f"{prefix}- **{key_formatted}:**")
                lines.append(self._format_dict(value, indent + 1))
            elif isinstance(value, list):
                lines.append(f"{prefix}- **{key_formatted}:**")
                lines.append(self._format_list(value, indent + 1))
            else:
                lines.append(f"{prefix}- **{key_formatted}:** {value}")
        
        return "\n".join(lines)
    
    def _format_list(self, data: List[Any], indent: int = 0) -> str:
        """
        Formata uma lista de forma legível.
        
        Args:
            data: Lista a ser formatada
            indent: Nível de indentação
            
        Returns:
            String formatada
        """
        lines = []
        prefix = "  " * indent
        
        for i, item in enumerate(data, 1):
            if isinstance(item, dict):
                lines.append(f"{prefix}{i}. Item:")
                lines.append(self._format_dict(item, indent + 1))
            else:
                lines.append(f"{prefix}{i}. {item}")
        
        return "\n".join(lines)
    
    def build_insight_prompt(
        self,
        insight_type: str,
        insight_data: Dict[str, Any],
        objetivo: str
    ) -> str:
        """
        Constrói um prompt específico para análise de Insights.
        
        Args:
            insight_type: Tipo do insight (ex: ClienteRecorrenteAtrasado)
            insight_data: Dados do insight
            objetivo: O que o usuário quer saber
            
        Returns:
            Prompt formatado
        """
        context = {
            "tipo_insight": insight_type,
            "dados_insight": insight_data,
            "timestamp": datetime.now().isoformat()
        }
        
        return self.build_prompt(context, objetivo)
    
    def build_multi_insight_prompt(
        self,
        insights: List[Dict[str, Any]],
        objetivo: str
    ) -> str:
        """
        Constrói um prompt para análise de múltiplos insights.
        
        Args:
            insights: Lista de insights
            objetivo: O que o usuário quer saber
            
        Returns:
            Prompt formatado
        """
        context = {
            "total_insights": len(insights),
            "insights": insights,
            "timestamp": datetime.now().isoformat()
        }
        
        return self.build_prompt(context, objetivo)
