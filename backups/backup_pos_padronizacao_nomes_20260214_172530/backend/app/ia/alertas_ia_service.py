"""
Serviço de Alertas Proativos com IA.

A IA observa o sistema e gera alertas automáticos sobre:
- Riscos financeiros
- Tendências de faturamento
- Custos crescentes
- Provisões insuficientes

📌 Características:
- IA não executa nada, apenas alerta
- Apenas recomendações explicativas
- Sem impacto contábil
- Pode ser exibido no dashboard ou chat
"""

from typing import Dict, List, Any


def gerar_alertas_ia(dados: Dict[str, Any]) -> List[str]:
    """
    Gera alertas proativos baseados na análise dos dados fornecidos.
    
    Args:
        dados: Dicionário com informações do sistema:
            - caixa_negativo_previsto: bool
            - simples_subindo: bool
            - folha_crescimento_maior_receita: bool
            - provisoes_insuficientes: bool
            - margem_baixa: bool
            - inadimplencia_alta: bool
            
    Returns:
        Lista de mensagens de alerta
        
    Exemplo:
        dados = {
            "caixa_negativo_previsto": True,
            "simples_subindo": False,
            "folha_crescimento_maior_receita": True
        }
        alertas = gerar_alertas_ia(dados)
        # ["⚠️ O caixa projetado ficará negativo...", "⚠️ O custo com pessoal..."]
    """
    alertas = []
    
    # Alerta de caixa negativo
    if dados.get("caixa_negativo_previsto"):
        alertas.append(
            "⚠️ O caixa projetado ficará negativo nas próximas semanas. "
            "Recomendo revisar despesas ou postergar compromissos."
        )
    
    # Alerta de mudança de faixa do Simples Nacional
    if dados.get("simples_subindo"):
        alertas.append(
            "⚠️ Sua alíquota do Simples tende a subir no próximo período "
            "devido ao aumento do faturamento."
        )
    
    # Alerta de folha crescendo mais que receita
    if dados.get("folha_crescimento_maior_receita"):
        alertas.append(
            "⚠️ O custo com pessoal está crescendo mais rápido que a receita. "
            "Isso pressiona sua margem operacional."
        )
    
    # Alerta de provisões insuficientes
    if dados.get("provisoes_insuficientes"):
        alertas.append(
            "⚠️ As provisões de férias ou 13º salário podem estar abaixo do necessário. "
            "Recomendo revisar os cálculos para evitar surpresas."
        )
    
    # Alerta de margem baixa
    if dados.get("margem_baixa"):
        alertas.append(
            "⚠️ Sua margem de lucro está abaixo do ideal para o setor. "
            "Considere revisar preços ou otimizar custos operacionais."
        )
    
    # Alerta de inadimplência alta
    if dados.get("inadimplencia_alta"):
        alertas.append(
            "⚠️ A taxa de inadimplência está acima da média. "
            "Isso pode comprometer o fluxo de caixa. Revise sua política de crédito."
        )
    
    return alertas


def analisar_tendencias_ia(dados_historicos: Dict[str, Any]) -> Dict[str, Any]:
    """
    Analisa tendências históricas e identifica padrões.
    
    Args:
        dados_historicos: Dados de múltiplos períodos
        
    Returns:
        Dicionário com análise de tendências e flags de alerta
    """
    analise = {
        "caixa_negativo_previsto": False,
        "simples_subindo": False,
        "folha_crescimento_maior_receita": False,
        "provisoes_insuficientes": False,
        "margem_baixa": False,
        "inadimplencia_alta": False,
    }
    
    # Análise de caixa
    if dados_historicos.get("projecao_caixa"):
        projecao = dados_historicos["projecao_caixa"]
        if any(p.get("saldo", 0) < 0 for p in projecao):
            analise["caixa_negativo_previsto"] = True
    
    # Análise de Simples Nacional
    if dados_historicos.get("faturamento_acumulado_12m"):
        faturamento = dados_historicos["faturamento_acumulado_12m"]
        # Exemplo: se está próximo de 180k, 360k, 720k, etc.
        limites = [180000, 360000, 720000, 1440000, 2880000, 3600000, 4800000]
        for limite in limites:
            if limite * 0.9 <= faturamento < limite:
                analise["simples_subindo"] = True
                break
    
    # Análise de folha vs receita
    if dados_historicos.get("crescimento_folha") and dados_historicos.get("crescimento_receita"):
        cresc_folha = dados_historicos["crescimento_folha"]
        cresc_receita = dados_historicos["crescimento_receita"]
        if cresc_folha > cresc_receita:
            analise["folha_crescimento_maior_receita"] = True
    
    # Análise de provisões
    if dados_historicos.get("provisao_ferias") and dados_historicos.get("provisao_13"):
        prov_ferias = dados_historicos["provisao_ferias"]
        prov_13 = dados_historicos["provisao_13"]
        folha_total = dados_historicos.get("folha_total", 0)
        
        if folha_total > 0:
            # Provisões devem ser ~18% da folha (férias ~11%, 13º ~8%)
            provisao_esperada = folha_total * 0.18
            provisao_atual = prov_ferias + prov_13
            
            if provisao_atual < provisao_esperada * 0.8:  # 80% do esperado
                analise["provisoes_insuficientes"] = True
    
    # Análise de margem
    if dados_historicos.get("margem_liquida"):
        margem = dados_historicos["margem_liquida"]
        if margem < 0.05:  # Menos de 5%
            analise["margem_baixa"] = True
    
    # Análise de inadimplência
    if dados_historicos.get("taxa_inadimplencia"):
        taxa = dados_historicos["taxa_inadimplencia"]
        if taxa > 0.10:  # Mais de 10%
            analise["inadimplencia_alta"] = True
    
    return analise


def gerar_recomendacoes_ia(alertas: List[str], contexto: Dict[str, Any]) -> List[str]:
    """
    Gera recomendações acionáveis baseadas nos alertas.
    
    Args:
        alertas: Lista de alertas gerados
        contexto: Contexto adicional do negócio
        
    Returns:
        Lista de recomendações práticas
    """
    recomendacoes = []
    
    if any("caixa" in alerta.lower() for alerta in alertas):
        recomendacoes.append(
            "💡 Negocie prazos maiores com fornecedores ou antecipe recebíveis."
        )
    
    if any("simples" in alerta.lower() for alerta in alertas):
        recomendacoes.append(
            "💡 Considere planejar despesas dedutíveis ou antecipar investimentos "
            "para evitar mudança de faixa."
        )
    
    if any("pessoal" in alerta.lower() or "folha" in alerta.lower() for alerta in alertas):
        recomendacoes.append(
            "💡 Avalie a produtividade da equipe e considere automações "
            "antes de novas contratações."
        )
    
    if any("provisão" in alerta.lower() or "provisões" in alerta.lower() for alerta in alertas):
        recomendacoes.append(
            "💡 Aumente as provisões mensais gradualmente para evitar impacto "
            "concentrado no pagamento de férias e 13º."
        )
    
    if any("margem" in alerta.lower() for alerta in alertas):
        recomendacoes.append(
            "💡 Revise sua estrutura de custos e precificação. "
            "Pequenos ajustes podem ter grande impacto."
        )
    
    if any("inadimplência" in alerta.lower() for alerta in alertas):
        recomendacoes.append(
            "💡 Implemente análise de crédito mais rigorosa e considere "
            "descontos para pagamento antecipado."
        )
    
    return recomendacoes
