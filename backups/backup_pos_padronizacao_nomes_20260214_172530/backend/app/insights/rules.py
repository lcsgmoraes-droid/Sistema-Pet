"""
Regras de Geração de Insights
==============================

Define as regras determinísticas que geram insights automaticamente.

Cada regra:
- Consome dados dos Read Models
- Aplica lógica determinística (sem IA)
- Retorna lista de Insights
- É independente e testável

Regras implementadas:
1. ClienteRecorrenteAtrasado: Cliente regular atrasou compra
2. ClienteInativo: Cliente sem compras há muito tempo
3. ProdutosCompradosJuntos: Oportunidade de cross-sell
4. KitMaisVantajoso: Kit tem melhor preço que itens separados

Arquitetura:
- Cada regra é uma função pura
- Recebe Read Models como dependências
- Retorna lista de Insights
- Multi-tenant (user_id obrigatório)
"""

from typing import List, Optional
from datetime import datetime

from .models import (
    Insight,
    TipoInsight,
    SeveridadeInsight,
    EntidadeInsight
)


def gerar_id_insight(tipo: TipoInsight, entidade_id: Optional[int] = None) -> str:
    """
    Gera ID único para um insight.
    
    Formato: INS-{tipo}-{timestamp}-{entidade_id}
    
    Args:
        tipo: Tipo do insight
        entidade_id: ID da entidade (opcional)
        
    Returns:
        String com ID único
    """
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    tipo_code = tipo.value[:10].replace("_", "")
    
    if entidade_id:
        return f"INS-{tipo_code}-{timestamp}-{entidade_id}"
    else:
        return f"INS-{tipo_code}-{timestamp}"


# ============================================================================
# REGRA 1: Cliente Recorrente Atrasado
# ============================================================================

def regra_cliente_recorrente_atrasado(
    clientes_rm,
    user_id: int,
    dias_analise: int = 90,
    margem_atraso: float = 1.5
) -> List[Insight]:
    """
    Identifica clientes recorrentes que estão atrasados em sua próxima compra.
    
    Lógica:
    1. Busca clientes recorrentes (2+ compras)
    2. Calcula frequência média de compras (dias entre compras)
    3. Verifica se está atrasado: recencia > frequencia * margem_atraso
    4. Gera insight para cada cliente atrasado
    
    Args:
        clientes_rm: ClientesRecorrentesReadModel
        user_id: Tenant
        dias_analise: Período de análise
        margem_atraso: Multiplicador para considerar atraso (1.5 = 50% de atraso)
        
    Returns:
        Lista de insights de clientes atrasados
    """
    insights = []
    
    # Buscar clientes recorrentes
    clientes = clientes_rm.clientes_recorrentes(
        dias=dias_analise,
        user_id=user_id,
        min_compras=2
    )
    
    for cliente in clientes:
        # Dados do cliente
        cliente_id = cliente['cliente_id']
        frequencia = cliente['dias_entre_compras']
        recencia = cliente['recencia']
        numero_compras = cliente['numero_compras']
        
        # Pular se não tem frequência estabelecida
        if frequencia <= 0:
            continue
        
        # Calcular atraso esperado
        dias_esperado = frequencia * margem_atraso
        
        # Cliente está atrasado?
        if recencia > dias_esperado:
            atraso_dias = int(recencia - frequencia)
            
            # Determinar severidade baseado no atraso
            if atraso_dias > frequencia * 2:
                severidade = SeveridadeInsight.ATENCAO
            else:
                severidade = SeveridadeInsight.OPORTUNIDADE
            
            # Criar insight
            insight = Insight(
                id=gerar_id_insight(TipoInsight.CLIENTE_RECORRENTE_ATRASADO, cliente_id),
                tipo=TipoInsight.CLIENTE_RECORRENTE_ATRASADO,
                titulo=f"Cliente #{cliente_id} está atrasado para próxima compra",
                descricao=(
                    f"Cliente compra a cada {frequencia:.0f} dias em média, "
                    f"mas não compra há {recencia} dias ({atraso_dias} dias de atraso). "
                    f"Histórico: {numero_compras} compras, ticket médio R$ {cliente['ticket_medio']:.2f}."
                ),
                severidade=severidade,
                entidade=EntidadeInsight.CLIENTE,
                entidade_id=cliente_id,
                dados_contexto={
                    'frequencia_media': frequencia,
                    'recencia': recencia,
                    'atraso_dias': atraso_dias,
                    'numero_compras': numero_compras,
                    'valor_total': cliente['valor_total']
                },
                metricas={
                    'ticket_medio': cliente['ticket_medio'],
                    'frequencia_dias': frequencia,
                    'atraso_percentual': (atraso_dias / frequencia) * 100
                },
                acao_sugerida=(
                    f"Contatar cliente com oferta personalizada. "
                    f"Última compra foi em {cliente['ultima_compra'][:10]}."
                ),
                user_id=user_id
            )
            
            insights.append(insight)
    
    return insights


# ============================================================================
# REGRA 2: Cliente Inativo
# ============================================================================

def regra_cliente_inativo(
    clientes_rm,
    user_id: int,
    dias_inatividade: int = 60,
    min_compras_historico: int = 2
) -> List[Insight]:
    """
    Identifica clientes que não compram há muito tempo (risco de churn).
    
    Lógica:
    1. Busca clientes em risco de churn
    2. Filtra por nível de risco
    3. Gera insights com recomendações
    
    Args:
        clientes_rm: ClientesRecorrentesReadModel
        user_id: Tenant
        dias_inatividade: Dias sem comprar para considerar inativo
        min_compras_historico: Mínimo de compras históricas
        
    Returns:
        Lista de insights de clientes inativos
    """
    insights = []
    
    # Buscar clientes em risco
    clientes_risco = clientes_rm.clientes_em_risco_churn(
        dias_inatividade=dias_inatividade,
        user_id=user_id,
        min_compras_historico=min_compras_historico
    )
    
    for cliente in clientes_risco:
        cliente_id = cliente['cliente_id']
        dias_sem_comprar = cliente['dias_sem_comprar']
        risco_nivel = cliente['risco_nivel']
        
        # Determinar severidade
        if risco_nivel == "ALTO":
            severidade = SeveridadeInsight.ATENCAO
        elif risco_nivel == "MEDIO":
            severidade = SeveridadeInsight.OPORTUNIDADE
        else:
            severidade = SeveridadeInsight.INFO
        
        # Criar insight
        insight = Insight(
            id=gerar_id_insight(TipoInsight.CLIENTE_INATIVO, cliente_id),
            tipo=TipoInsight.CLIENTE_INATIVO,
            titulo=f"Cliente #{cliente_id} inativo há {dias_sem_comprar} dias (Risco: {risco_nivel})",
            descricao=(
                f"Cliente com {cliente['numero_compras_historico']} compras no histórico "
                f"(R$ {cliente['valor_total_historico']:.2f} total) não compra há {dias_sem_comprar} dias. "
                f"Nível de risco: {risco_nivel}."
            ),
            severidade=severidade,
            entidade=EntidadeInsight.CLIENTE,
            entidade_id=cliente_id,
            dados_contexto={
                'dias_sem_comprar': dias_sem_comprar,
                'risco_nivel': risco_nivel,
                'numero_compras': cliente['numero_compras_historico'],
                'valor_total': cliente['valor_total_historico']
            },
            metricas={
                'ticket_medio': cliente['ticket_medio'],
                'dias_inativo': dias_sem_comprar
            },
            acao_sugerida=(
                f"Campanha de reativação urgente. "
                f"Última compra: {cliente['ultima_compra'][:10]}. "
                f"Ofereça desconto ou vantagem especial."
            ),
            user_id=user_id
        )
        
        insights.append(insight)
    
    return insights


# ============================================================================
# REGRA 3: Produtos Comprados Juntos (Cross-Sell)
# ============================================================================

def regra_produtos_comprados_juntos(
    comprados_rm,
    user_id: int,
    produto_id: int,
    min_confianca: float = 50.0,
    limit: int = 3
) -> List[Insight]:
    """
    Identifica oportunidades de cross-sell para um produto específico.
    
    Lógica:
    1. Busca produtos frequentemente comprados junto
    2. Filtra por confiança mínima
    3. Gera insight de oportunidade
    
    Args:
        comprados_rm: ProdutosCompradosJuntosReadModel
        user_id: Tenant
        produto_id: Produto de referência
        min_confianca: Confiança mínima (%) para sugestão
        limit: Máximo de sugestões
        
    Returns:
        Lista de insights de cross-sell
    """
    insights = []
    
    # Buscar produtos comprados juntos
    sugestoes = comprados_rm.produtos_comprados_juntos(
        produto_id=produto_id,
        limit=limit,
        user_id=user_id,
        min_ocorrencias=2
    )
    
    # Filtrar por confiança
    sugestoes_filtradas = [
        s for s in sugestoes 
        if s['confianca'] >= min_confianca
    ]
    
    if sugestoes_filtradas:
        # Criar um único insight com múltiplas sugestões
        produtos_sugeridos = [s['produto_nome'] for s in sugestoes_filtradas]
        confianca_media = sum(s['confianca'] for s in sugestoes_filtradas) / len(sugestoes_filtradas)
        
        insight = Insight(
            id=gerar_id_insight(TipoInsight.PRODUTOS_COMPRADOS_JUNTOS, produto_id),
            tipo=TipoInsight.PRODUTOS_COMPRADOS_JUNTOS,
            titulo=f"Oportunidade de cross-sell para produto #{produto_id}",
            descricao=(
                f"Clientes que compram este produto também compram: "
                f"{', '.join(produtos_sugeridos[:3])}. "
                f"Confiança média: {confianca_media:.1f}%."
            ),
            severidade=SeveridadeInsight.OPORTUNIDADE,
            entidade=EntidadeInsight.PRODUTO,
            entidade_id=produto_id,
            dados_contexto={
                'produtos_sugeridos': [
                    {
                        'id': s['produto_id'],
                        'nome': s['produto_nome'],
                        'confianca': s['confianca'],
                        'frequencia': s['frequencia']
                    }
                    for s in sugestoes_filtradas
                ]
            },
            metricas={
                'confianca_media': confianca_media,
                'numero_sugestoes': len(sugestoes_filtradas)
            },
            acao_sugerida=(
                f"Ofereça combo ou desconto ao comprar estes produtos juntos. "
                f"Exiba sugestões no carrinho/checkout."
            ),
            user_id=user_id
        )
        
        insights.append(insight)
    
    return insights


# ============================================================================
# REGRA 4: Kit Mais Vantajoso que Itens Separados
# ============================================================================

def regra_kit_mais_vantajoso(
    kits_rm,
    produtos_rm,
    user_id: int,
    desconto_minimo: float = 10.0
) -> List[Insight]:
    """
    Identifica kits que têm melhor custo-benefício que comprar itens separados.
    
    Lógica:
    1. Busca top kits vendidos
    2. Calcula preço médio do kit vs componentes (estimativa)
    3. Se economia >= desconto_minimo%, gera insight
    
    NOTA: Esta é uma implementação simplificada pois não temos
    acesso aos componentes individuais dos kits. Em produção,
    seria necessário buscar esses dados do banco.
    
    Args:
        kits_rm: KitsMaisVendidosReadModel
        produtos_rm: ProdutosMaisVendidosReadModel
        user_id: Tenant
        desconto_minimo: Desconto mínimo (%) para gerar insight
        
    Returns:
        Lista de insights de kits vantajosos
    """
    insights = []
    
    # Buscar top kits
    top_kits = kits_rm.top_kits(limit=5, user_id=user_id)
    
    for kit in top_kits:
        kit_id = kit['kit_id']
        kit_nome = kit['kit_nome']
        preco_medio_kit = kit['preco_medio']
        
        # SIMPLIFICAÇÃO: Assumir que o kit tem economia de ~15%
        # Em produção, calcularia baseado nos componentes reais
        economia_estimada = 15.0  # percentual
        
        if economia_estimada >= desconto_minimo:
            insight = Insight(
                id=gerar_id_insight(TipoInsight.KIT_MAIS_VANTAJOSO, kit_id),
                tipo=TipoInsight.KIT_MAIS_VANTAJOSO,
                titulo=f"Kit '{kit_nome}' oferece economia estimada de {economia_estimada:.0f}%",
                descricao=(
                    f"O kit '{kit_nome}' (R$ {preco_medio_kit:.2f}) "
                    f"oferece economia em relação aos itens separados. "
                    f"Vendido {kit['quantidade_vendida']:.0f} vezes."
                ),
                severidade=SeveridadeInsight.OPORTUNIDADE,
                entidade=EntidadeInsight.KIT,
                entidade_id=kit_id,
                dados_contexto={
                    'kit_nome': kit_nome,
                    'preco_medio': preco_medio_kit,
                    'quantidade_vendida': kit['quantidade_vendida'],
                    'tipo_kit': kit['tipo_kit']
                },
                metricas={
                    'economia_percentual': economia_estimada,
                    'preco_kit': preco_medio_kit,
                    'vendas': kit['numero_vendas']
                },
                acao_sugerida=(
                    f"Destaque a economia do kit em banners e emails. "
                    f"Sugira o kit quando cliente adicionar componentes individuais."
                ),
                user_id=user_id
            )
            
            insights.append(insight)
    
    return insights
