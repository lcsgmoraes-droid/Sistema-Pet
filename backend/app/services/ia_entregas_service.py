"""
🤖 Service de IA para Análise de Entregas

Gera insights automáticos baseados nos dados financeiros do dashboard.
- Alertas: O que está errado
- Sugestões: O que fazer

❌ NÃO escreve no banco
❌ NÃO executa ações  
❌ NÃO muda configurações

✅ Apenas lê e analisa dados
"""


def gerar_insights_entregas(dados: dict) -> dict:
    """
    Gera alertas e sugestões automáticas baseadas nos dados do dashboard.
    
    Args:
        dados: Dict com os KPIs financeiros
            - custo_medio: float
            - taxa_media: float
            - custo_moto_percentual: float
            - total_entregas: int
            
    Returns:
        {
            "alertas": ["⚠️ ..."],
            "sugestoes": ["💡 ..."]
        }
    """
    alertas = []
    sugestoes = []
    
    custo_medio = dados.get("custo_medio", 0)
    taxa_media = dados.get("taxa_media", 0)
    total_entregas = dados.get("total_entregas", 0)
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 1️⃣ ALERTA: Taxa não cobre custo
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    if total_entregas > 0 and custo_medio > taxa_media:
        deficit = custo_medio - taxa_media
        alertas.append(
            f"⚠️ O custo médio da entrega (R$ {custo_medio:.2f}) "
            f"está acima da taxa média cobrada (R$ {taxa_media:.2f}). "
            f"Déficit médio: R$ {deficit:.2f} por entrega."
        )
        
        # Sugestão de ajuste de taxa
        taxa_sugerida_min = custo_medio + 1  # Margem mínima de R$1
        taxa_sugerida_ideal = custo_medio * 1.15  # Margem de 15%
        sugestoes.append(
            f"💡 Sugestão: Considere ajustar a taxa mínima para "
            f"R$ {taxa_sugerida_min:.2f} (margem de R$1) ou "
            f"R$ {taxa_sugerida_ideal:.2f} (margem de 15%)."
        )
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 2️⃣ ALERTA: Moto da loja cara
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    custo_moto_percentual = dados.get("custo_moto_percentual", 0)
    if custo_moto_percentual > 30:
        alertas.append(
            f"⚠️ A moto da loja representa {custo_moto_percentual:.1f}% "
            "do custo total das entregas (acima de 30%)."
        )
        sugestoes.append(
            "💡 Sugestão: Avalie terceirizar entregas em dias de baixa demanda. "
            "Isso pode reduzir custos fixos mantendo a qualidade do serviço."
        )
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 3️⃣ SUCESSO: Tudo OK
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    if not alertas:
        alertas.append("✅ A operação está dentro dos parâmetros esperados.")
    
    if not sugestoes:
        sugestoes.append("✅ Continue monitorando os indicadores para manter a eficiência.")
    
    return {
        "alertas": alertas,
        "sugestoes": sugestoes,
    }


def calcular_custo_moto_percentual(custo_total_moto: float, custo_total_geral: float) -> float:
    """
    Calcula o percentual que a moto da loja representa no custo total.
    
    Args:
        custo_total_moto: Custo total da moto da loja
        custo_total_geral: Custo total de todas as entregas
        
    Returns:
        Percentual (0-100)
    """
    if custo_total_geral == 0:
        return 0.0
    
    return (custo_total_moto / custo_total_geral) * 100
