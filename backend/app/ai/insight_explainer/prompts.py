"""
InsightPromptLibrary - Biblioteca de Prompts por Tipo de Insight

Contém prompts especializados para cada tipo de insight do Sprint 5.

Cada tipo de insight tem um template de prompt otimizado que:
- Contextualiza o tipo de insight
- Orienta a IA sobre o tom e abordagem
- Define formato de resposta esperado
- Garante explicações acionáveis
"""

from typing import Dict, Any
from app.insights.models import TipoInsight


class InsightPromptLibrary:
    """
    Biblioteca de prompts especializados por tipo de insight.
    
    Cada método retorna um prompt customizado para um tipo específico
    de insight, garantindo que a IA gere explicações contextualizadas.
    """
    
    @staticmethod
    def get_prompt_for_tipo(
        tipo: TipoInsight,
        dados_insight: Dict[str, Any]
    ) -> str:
        """
        Retorna prompt especializado para o tipo de insight.
        
        Args:
            tipo: Tipo do insight
            dados_insight: Dados estruturados do insight
            
        Returns:
            Prompt customizado
        """
        prompts_map = {
            TipoInsight.CLIENTE_RECORRENTE_ATRASADO: 
                InsightPromptLibrary._prompt_cliente_atrasado,
            TipoInsight.CLIENTE_INATIVO:
                InsightPromptLibrary._prompt_cliente_inativo,
            TipoInsight.PRODUTOS_COMPRADOS_JUNTOS:
                InsightPromptLibrary._prompt_produtos_juntos,
            TipoInsight.KIT_MAIS_VANTAJOSO:
                InsightPromptLibrary._prompt_kit_vantajoso,
            TipoInsight.CLIENTE_VIP:
                InsightPromptLibrary._prompt_cliente_vip,
            TipoInsight.CLIENTE_EM_RISCO_CHURN:
                InsightPromptLibrary._prompt_risco_churn,
            TipoInsight.PRODUTO_TOP_VENDAS:
                InsightPromptLibrary._prompt_produto_top,
        }
        
        prompt_fn = prompts_map.get(
            tipo,
            InsightPromptLibrary._prompt_generico
        )
        
        return prompt_fn(dados_insight)
    
    @staticmethod
    def _prompt_cliente_atrasado(dados: Dict[str, Any]) -> str:
        """
        Prompt para CLIENTE_RECORRENTE_ATRASADO.
        
        Foca em reengajamento sem ser invasivo.
        """
        titulo = dados.get('titulo', 'N/A')
        descricao = dados.get('descricao', 'N/A')
        severidade = dados.get('severidade', 'N/A')
        contexto = dados.get('dados_contexto', {})
        metricas = dados.get('metricas', {})
        
        return f"""
**CONTEXTO:**
Você está analisando um insight sobre um cliente recorrente que está atrasado em sua frequência de compra habitual.

**DADOS DO INSIGHT:**
- Título: {titulo}
- Descrição: {descricao}
- Severidade: {severidade}
- Dados contextuais: {contexto}
- Métricas: {metricas}

**SUA TAREFA:**
1. **Explique de forma clara e empática:**
   - Por que este cliente está sendo classificado como "atrasado"
   - O padrão de compra histórico dele
   - Quanto tempo de atraso existe
   - Por que isso é relevante para o negócio

2. **Sugira uma abordagem de reengajamento:**
   - Tom amigável e não invasivo
   - Personalizada baseada no histórico
   - Momento ideal para contato
   - Canal recomendado (WhatsApp, telefone, etc.)
   - Possível oferta ou incentivo

3. **Seja específico e acionável:**
   - Use dados concretos do insight
   - Evite generalidades
   - Foque no cliente específico

**TOM:**
- Profissional mas empático
- Orientado a ação
- Respeitoso com o cliente

{{contexto}}
{{objetivo}}
"""
    
    @staticmethod
    def _prompt_cliente_inativo(dados: Dict[str, Any]) -> str:
        """
        Prompt para CLIENTE_INATIVO.
        
        Foca em reconquista estratégica.
        """
        titulo = dados.get('titulo', 'N/A')
        descricao = dados.get('descricao', 'N/A')
        severidade = dados.get('severidade', 'N/A')
        contexto = dados.get('dados_contexto', {})
        metricas = dados.get('metricas', {})
        
        return f"""
**CONTEXTO:**
Você está analisando um insight sobre um cliente que está inativo há um tempo significativo.

**DADOS DO INSIGHT:**
- Título: {titulo}
- Descrição: {descricao}
- Severidade: {severidade}
- Dados contextuais: {contexto}
- Métricas: {metricas}

**SUA TAREFA:**
1. **Explique a situação de inatividade:**
   - Há quanto tempo o cliente não compra
   - Qual era o padrão de compra anterior
   - Possíveis razões para inatividade
   - Valor perdido (LTV potencial)

2. **Sugira estratégia de reconquista:**
   - Campanha de reativação personalizada
   - Oferta exclusiva "volta cliente"
   - Pesquisa de satisfação (entender o porquê)
   - Momento e canal ideais

3. **Avalie prioridade:**
   - Este cliente vale a pena reconquistar?
   - Qual o esforço vs. retorno esperado?
   - Segmentação (VIP, regular, ocasional)

**TOM:**
- Estratégico e analítico
- Focado em retorno
- Realista sobre chances de sucesso

{{contexto}}
{{objetivo}}
"""
    
    @staticmethod
    def _prompt_produtos_juntos(dados: Dict[str, Any]) -> str:
        """
        Prompt para PRODUTOS_COMPRADOS_JUNTOS.
        
        Foca em cross-sell natural.
        """
        titulo = dados.get('titulo', 'N/A')
        descricao = dados.get('descricao', 'N/A')
        contexto = dados.get('dados_contexto', {})
        metricas = dados.get('metricas', {})
        
        return f"""
**CONTEXTO:**
Você está analisando um insight sobre produtos que são frequentemente comprados juntos, representando uma oportunidade de cross-sell.

**DADOS DO INSIGHT:**
- Título: {titulo}
- Descrição: {descricao}
- Dados contextuais: {contexto}
- Métricas: {metricas}

**SUA TAREFA:**
1. **Explique a correlação:**
   - Por que esses produtos são comprados juntos
   - Frequência da combinação
   - Lógica do comportamento (complementaridade)
   - Valor da oportunidade

2. **Sugira como oferecer o cross-sell:**
   - No PDV: momento ideal durante a venda
   - No WhatsApp: script de oferta natural
   - Online: posicionamento no site/app
   - Argumento de valor (por que faz sentido)

3. **Recomende abordagem:**
   - Tom: sugestão, não empurrar
   - Benefício claro para o cliente
   - Possível desconto combo
   - Exemplos de uso conjunto

**TOM:**
- Consultivo e útil
- Focado no benefício do cliente
- Natural, não forçado

{{contexto}}
{{objetivo}}
"""
    
    @staticmethod
    def _prompt_kit_vantajoso(dados: Dict[str, Any]) -> str:
        """
        Prompt para KIT_MAIS_VANTAJOSO.
        
        Foca em comunicação de valor financeiro.
        """
        titulo = dados.get('titulo', 'N/A')
        descricao = dados.get('descricao', 'N/A')
        contexto = dados.get('dados_contexto', {})
        metricas = dados.get('metricas', {})
        
        return f"""
**CONTEXTO:**
Você está analisando um insight sobre um kit que oferece melhor custo-benefício do que comprar os itens separadamente.

**DADOS DO INSIGHT:**
- Título: {titulo}
- Descrição: {descricao}
- Dados contextuais: {contexto}
- Métricas: {metricas}

**SUA TAREFA:**
1. **Explique a vantagem financeira:**
   - Preço do kit vs. itens separados
   - Economia em reais e percentual
   - Por que o kit é mais vantajoso
   - Benefício adicional além do preço

2. **Sugira como comunicar ao cliente:**
   - Destaque a economia de forma clara
   - Use comparativo visual (antes/depois)
   - Enfatize conveniência (tudo em um)
   - Momento ideal para oferecer

3. **Recomende estratégia de venda:**
   - Positioning: economia inteligente
   - Upsell: quando cliente compra item avulso
   - Promoção: tempo limitado
   - Social proof: "clientes escolhem"

**TOM:**
- Transparente sobre economia
- Focado em valor
- Educativo

{{contexto}}
{{objetivo}}
"""
    
    @staticmethod
    def _prompt_cliente_vip(dados: Dict[str, Any]) -> str:
        """
        Prompt para CLIENTE_VIP.
        
        Foca em tratamento diferenciado.
        """
        titulo = dados.get('titulo', 'N/A')
        descricao = dados.get('descricao', 'N/A')
        contexto = dados.get('dados_contexto', {})
        metricas = dados.get('metricas', {})
        
        return f"""
**CONTEXTO:**
Você está analisando um insight sobre um cliente VIP que merece tratamento especial.

**DADOS DO INSIGHT:**
- Título: {titulo}
- Descrição: {descricao}
- Dados contextuais: {contexto}
- Métricas: {metricas}

**SUA TAREFA:**
1. **Explique por que é VIP:**
   - Critérios que o qualificaram (ticket, frequência, etc.)
   - Valor gerado para o negócio
   - Histórico de relacionamento
   - Potencial futuro

2. **Sugira tratamento diferenciado:**
   - Benefícios exclusivos a oferecer
   - Comunicação personalizada
   - Prioridade no atendimento
   - Programa de fidelidade VIP

3. **Recomende estratégia de retenção:**
   - Como mantê-lo satisfeito
   - Antecipar necessidades
   - Surpreender positivamente
   - Evitar perda para concorrência

**TOM:**
- Respeitoso e valorizado
- Exclusivo
- Proativo

{{contexto}}
{{objetivo}}
"""
    
    @staticmethod
    def _prompt_risco_churn(dados: Dict[str, Any]) -> str:
        """
        Prompt para CLIENTE_EM_RISCO_CHURN.
        
        Foca em ação preventiva urgente.
        """
        titulo = dados.get('titulo', 'N/A')
        descricao = dados.get('descricao', 'N/A')
        severidade = dados.get('severidade', 'N/A')
        contexto = dados.get('dados_contexto', {})
        metricas = dados.get('metricas', {})
        
        return f"""
**CONTEXTO:**
Você está analisando um insight sobre um cliente em risco de churn (abandono).

**DADOS DO INSIGHT:**
- Título: {titulo}
- Descrição: {descricao}
- Severidade: {severidade}
- Dados contextuais: {contexto}
- Métricas: {metricas}

**SUA TAREFA:**
1. **Explique o risco:**
   - Sinais de abandono identificados
   - Mudança no padrão de compra
   - Gravidade da situação
   - Janela de oportunidade

2. **Sugira ação preventiva urgente:**
   - Contato imediato recomendado
   - Abordagem empática (ouvir primeiro)
   - Oferta de retenção (se necessário)
   - Resolver possível insatisfação

3. **Priorize ações:**
   - O que fazer HOJE
   - O que fazer esta SEMANA
   - Plano de acompanhamento
   - Métricas de sucesso

**TOM:**
- Urgente mas não desesperado
- Empático e solucionador
- Focado em retenção

{{contexto}}
{{objetivo}}
"""
    
    @staticmethod
    def _prompt_produto_top(dados: Dict[str, Any]) -> str:
        """
        Prompt para PRODUTO_TOP_VENDAS.
        
        Foca em maximização de oportunidade.
        """
        titulo = dados.get('titulo', 'N/A')
        descricao = dados.get('descricao', 'N/A')
        contexto = dados.get('dados_contexto', {})
        metricas = dados.get('metricas', {})
        
        return f"""
**CONTEXTO:**
Você está analisando um insight sobre um produto que está em alta nas vendas.

**DADOS DO INSIGHT:**
- Título: {titulo}
- Descrição: {descricao}
- Dados contextuais: {contexto}
- Métricas: {metricas}

**SUA TAREFA:**
1. **Explique por que está em alta:**
   - Tendência identificada
   - Comparativo com período anterior
   - Possíveis fatores (sazonalidade, promoção, etc.)
   - Oportunidade de mercado

2. **Sugira estratégias de maximização:**
   - Garantir estoque adequado
   - Destaque no PDV/vitrine
   - Cross-sell com produtos relacionados
   - Comunicação nas redes sociais

3. **Recomende ações táticas:**
   - Aproveitar momentum
   - Criar bundle/combo
   - Upsell para versão premium
   - Capturar demanda latente

**TOM:**
- Oportunista (sentido positivo)
- Estratégico
- Orientado a crescimento

{{contexto}}
{{objetivo}}
"""
    
    @staticmethod
    def _prompt_generico(dados: Dict[str, Any]) -> str:
        """
        Prompt genérico para tipos não especializados.
        """
        tipo = dados.get('tipo_insight', 'N/A')
        titulo = dados.get('titulo', 'N/A')
        descricao = dados.get('descricao', 'N/A')
        severidade = dados.get('severidade', 'N/A')
        contexto = dados.get('dados_contexto', {})
        metricas = dados.get('metricas', {})
        
        return f"""
**CONTEXTO:**
Você está analisando um insight gerado automaticamente pelo sistema.

**DADOS DO INSIGHT:**
- Tipo: {tipo}
- Título: {titulo}
- Descrição: {descricao}
- Severidade: {severidade}
- Dados contextuais: {contexto}
- Métricas: {metricas}

**SUA TAREFA:**
1. **Explique o insight de forma clara:**
   - O que foi identificado
   - Por que é relevante
   - Impacto no negócio

2. **Sugira ações práticas:**
   - O que fazer com essa informação
   - Prioridade de ação
   - Resultados esperados

3. **Seja específico:**
   - Use os dados fornecidos
   - Evite generalidades
   - Foque em ações concretas

**TOM:**
- Profissional
- Acionável
- Objetivo

{{contexto}}
{{objetivo}}
"""
