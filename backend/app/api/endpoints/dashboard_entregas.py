"""
ETAPA 11.1 - Dashboard Financeiro de Entregas
Endpoint que retorna indicadores financeiros consolidados
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import date
from decimal import Decimal
from typing import Optional
import os
from app.db import get_session
from app.auth.dependencies import get_current_user_and_tenant
from app.rotas_entrega_models import RotaEntrega
from app.models import Cliente
from app.services.ia_entregas_service import gerar_insights_entregas, calcular_custo_moto_percentual

router = APIRouter(
    prefix="/dashboard/entregas",
    tags=["Dashboard - Entregas"],
)


@router.get("/financeiro")
def dashboard_financeiro(
    data_inicio: date = Query(..., description="Data inicial (YYYY-MM-DD)"),
    data_fim: date = Query(..., description="Data final (YYYY-MM-DD)"),
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    📊 ETAPA 11.1 - Dashboard Financeiro de Entregas
    
    Retorna KPIs financeiros consolidados de rotas concluídas no período.
    
    **Fonte da verdade:** rotas_entrega (status='concluida')
    
    **KPIs retornados:**
    - total_entregas: Quantidade de entregas realizadas
    - custo_total_entregas: Soma de todos os custos (entregador + moto)
    - custo_total_entregadores: Soma dos custos apenas dos entregadores
    - custo_total_moto: Soma dos custos apenas da moto da loja
    - total_repasse_taxa: Soma das taxas repassadas aos entregadores
    - custo_medio_por_entrega: Custo médio por entrega
    - margem_media: Taxa média - Custo médio
    
    **Filtros obrigatórios:**
    - data_inicio: Data de início do período
    - data_fim: Data de fim do período
    """
    user, tenant_id = user_and_tenant
    
    # Query agregada para buscar todos os KPIs de uma vez
    q = (
        db.query(
            func.count(RotaEntrega.id).label("total_entregas"),
            func.coalesce(func.sum(RotaEntrega.custo_real), 0).label("custo_total"),
            func.coalesce(func.sum(RotaEntrega.custo_moto), 0).label("custo_moto"),
            func.coalesce(
                func.sum(RotaEntrega.custo_real - func.coalesce(RotaEntrega.custo_moto, 0)),
                0,
            ).label("custo_entregadores"),
            func.coalesce(func.sum(RotaEntrega.valor_repasse_entregador), 0).label(
                "total_repasse"
            ),
            func.coalesce(func.avg(RotaEntrega.custo_real), 0).label(
                "custo_medio"
            ),
            func.coalesce(func.avg(RotaEntrega.taxa_entrega_cliente), 0).label(
                "taxa_media"
            ),
        )
        .filter(RotaEntrega.tenant_id == tenant_id)
        .filter(RotaEntrega.status == "concluida")
        .filter(RotaEntrega.data_conclusao.between(data_inicio, data_fim))
    )

    r = q.one()
    
    # Calcular margem média (taxa - custo)
    taxa_media = float(r.taxa_media) if r.taxa_media else 0.0
    custo_medio = float(r.custo_medio) if r.custo_medio else 0.0
    margem_media = taxa_media - custo_medio

    return {
        "total_entregas": r.total_entregas or 0,
        "custo_total_entregas": float(r.custo_total),
        "custo_total_entregadores": float(r.custo_entregadores),
        "custo_total_moto": float(r.custo_moto),
        "total_repasse_taxa": float(r.total_repasse),
        "custo_medio_por_entrega": custo_medio,
        "margem_media": margem_media,
        "periodo": {
            "data_inicio": data_inicio.isoformat(),
            "data_fim": data_fim.isoformat(),
        },
    }


@router.get("/financeiro/graficos")
def dashboard_graficos(
    data_inicio: date = Query(..., description="Data inicial (YYYY-MM-DD)"),
    data_fim: date = Query(..., description="Data final (YYYY-MM-DD)"),
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    📊 ETAPA 11.4 - Dados para Gráficos do Dashboard Financeiro
    
    **Fonte da verdade:** rotas_entrega (status='concluida')
    
    Retorna dados agregados prontos para os gráficos:
    1. **por_dia:** Custo total de entregas por dia
    2. **custo_medio:** Custo médio por entrega por dia
    3. **taxa_vs_custo:** Comparação taxa cobrada × custo real
    
    **Parâmetros obrigatórios:**
    - data_inicio: Data inicial do período (YYYY-MM-DD)
    - data_fim: Data final do período (YYYY-MM-DD)
    
    **Retorno:**
    ```json
    {
      "por_dia": [{ "data": "2026-02-01", "custo": 320.50 }],
      "custo_medio": [{ "data": "2026-02-01", "valor": 16.50 }],
      "taxa_vs_custo": {
        "taxa_media": 15.00,
        "custo_medio": 18.00
      }
    }
    ```
    """
    user, tenant_id = user_and_tenant
    
    # 1. Custo total e médio por dia
    por_dia_query = (
        db.query(
            func.date(RotaEntrega.data_conclusao).label("data"),
            func.coalesce(func.sum(RotaEntrega.custo_real), 0).label("custo_total"),
            func.coalesce(func.avg(RotaEntrega.custo_real), 0).label("custo_medio"),
        )
        .filter(RotaEntrega.tenant_id == tenant_id)
        .filter(RotaEntrega.status == "concluida")
        .filter(RotaEntrega.data_conclusao.between(data_inicio, data_fim))
        .group_by(func.date(RotaEntrega.data_conclusao))
        .order_by(func.date(RotaEntrega.data_conclusao))
    )
    
    resultados_dia = por_dia_query.all()
    
    # Formatar dados por dia
    por_dia = []
    custo_medio_dia = []
    
    for r in resultados_dia:
        data_str = r.data.isoformat() if hasattr(r.data, 'isoformat') else str(r.data)
        por_dia.append({
            "data": data_str,
            "custo": float(r.custo_total),
        })
        custo_medio_dia.append({
            "data": data_str,
            "valor": float(r.custo_medio),
        })
    
    # 2. Taxa vs Custo (médias gerais do período)
    media_geral = (
        db.query(
            func.coalesce(func.avg(RotaEntrega.taxa_entrega_cliente), 0).label("taxa_media"),
            func.coalesce(func.avg(RotaEntrega.custo_real), 0).label("custo_medio"),
        )
        .filter(RotaEntrega.tenant_id == tenant_id)
        .filter(RotaEntrega.status == "concluida")
        .filter(RotaEntrega.data_conclusao.between(data_inicio, data_fim))
    ).one()
    
    taxa_vs_custo = {
        "taxa_media": float(media_geral.taxa_media),
        "custo_medio": float(media_geral.custo_medio),
    }
    
    return {
        "por_dia": por_dia,
        "custo_medio": custo_medio_dia,
        "taxa_vs_custo": taxa_vs_custo,
    }


@router.get("/financeiro/ia")
def dashboard_ia(
    data_inicio: date = Query(..., description="Data inicial (YYYY-MM-DD)"),
    data_fim: date = Query(..., description="Data final (YYYY-MM-DD)"),
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    🤖 BLOCO C - IA de Entregas (Análises + Sugestões)
    
    Gera insights automáticos baseados nos dados financeiros.
    
    **O que a IA faz:**
    - Lê os mesmos dados do dashboard financeiro
    - Gera alertas (o que está errado)
    - Gera sugestões (o que fazer)
    
    **O que a IA NÃO faz:**
    - ❌ Não escreve no banco
    - ❌ Não executa ações
    - ❌ Não muda configurações
    
    **Se a IA cair:** Dashboard continua funcionando normalmente.
    
    **Retorno:**
    ```json
    {
      "alertas": ["⚠️ ..."],
      "sugestoes": ["💡 ..."]
    }
    ```
    """
    user, tenant_id = user_and_tenant
    
    # Buscar dados agregados (reutiliza a mesma query do dashboard)
    q = (
        db.query(
            func.count(RotaEntrega.id).label("total_entregas"),
            func.coalesce(func.sum(RotaEntrega.custo_real), 0).label("custo_total"),
            func.coalesce(func.sum(RotaEntrega.custo_moto), 0).label("custo_moto"),
            func.coalesce(func.avg(RotaEntrega.custo_real), 0).label("custo_medio"),
            func.coalesce(func.avg(RotaEntrega.taxa_entrega_cliente), 0).label("taxa_media"),
        )
        .filter(RotaEntrega.tenant_id == tenant_id)
        .filter(RotaEntrega.status == "concluida")
        .filter(RotaEntrega.data_conclusao.between(data_inicio, data_fim))
    )
    
    r = q.one()
    
    # Preparar dados para a IA
    custo_total = float(r.custo_total)
    custo_moto = float(r.custo_moto)
    
    dados = {
        "total_entregas": r.total_entregas or 0,
        "custo_medio": float(r.custo_medio),
        "taxa_media": float(r.taxa_media),
        "custo_moto_percentual": calcular_custo_moto_percentual(custo_moto, custo_total),
    }
    
    # Gerar insights com o service de IA
    insights = gerar_insights_entregas(dados)
    
    return insights


@router.get("/financeiro/analises-ia")
def analises_ia(
    data_inicio: date = Query(..., description="Data inicial (YYYY-MM-DD)"),
    data_fim: date = Query(..., description="Data final (YYYY-MM-DD)"),
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    🤖 ETAPA 12.1 - Análises Automáticas com IA
    
    Retorna análises e alertas automáticos baseados nos dados do dashboard:
    1. Taxa abaixo do custo
    2. Entregadores fora do padrão
    3. Moto da loja com custo elevado
    
    **Nota:** A IA apenas lê e analisa dados. Não modifica nada.
    """
    user, tenant_id = user_and_tenant
    
    analises = []
    
    # 1. Análise: Taxa vs Custo (últimos 7 dias ou período informado)
    dados_gerais = (
        db.query(
            func.avg(RotaEntrega.taxa_entrega_cliente).label("taxa_media"),
            func.avg(RotaEntrega.custo_real).label("custo_medio"),
            func.count(RotaEntrega.id).label("total"),
        )
        .filter(RotaEntrega.tenant_id == tenant_id)
        .filter(RotaEntrega.status == "concluida")
        .filter(RotaEntrega.data_conclusao.between(data_inicio, data_fim))
    ).one()
    
    if dados_gerais.total > 0:
        taxa_media = float(dados_gerais.taxa_media or 0)
        custo_medio = float(dados_gerais.custo_medio or 0)
        
        if custo_medio > taxa_media:
            deficit = custo_medio - taxa_media
            analises.append({
                "tipo": "alerta",
                "titulo": "Taxa abaixo do custo",
                "mensagem": f"⚠️ Atenção: No período selecionado, o custo médio da entrega (R$ {custo_medio:.2f}) "
                           f"ficou acima da taxa média cobrada (R$ {taxa_media:.2f}). "
                           f"Déficit médio: R$ {deficit:.2f} por entrega.",
                "severidade": "alta"
            })
    
    # 2. Análise: Entregadores fora do padrão
    # Buscar custo médio por entregador
    por_entregador = (
        db.query(
            Cliente.nome.label("entregador_nome"),
            func.avg(RotaEntrega.custo_real).label("custo_medio"),
            func.count(RotaEntrega.id).label("entregas"),
        )
        .join(Cliente, RotaEntrega.entregador_id == Cliente.id)
        .filter(RotaEntrega.tenant_id == tenant_id)
        .filter(RotaEntrega.status == "concluida")
        .filter(RotaEntrega.data_conclusao.between(data_inicio, data_fim))
        .filter(RotaEntrega.moto_da_loja == False)  # Excluir moto da loja
        .group_by(Cliente.nome)
        .having(func.count(RotaEntrega.id) >= 3)  # Mínimo 3 entregas
    ).all()
    
    if por_entregador and dados_gerais.total > 0:
        custo_medio_geral = float(dados_gerais.custo_medio or 0)
        
        for ent in por_entregador:
            custo_ent = float(ent.custo_medio or 0)
            if custo_ent > custo_medio_geral * 1.3:  # 30% acima da média
                diferenca = custo_ent - custo_medio_geral
                analises.append({
                    "tipo": "alerta",
                    "titulo": f"Entregador com custo elevado",
                    "mensagem": f"⚠️ Entregador {ent.entregador_nome}: Custo médio R$ {custo_ent:.2f} "
                               f"(média geral: R$ {custo_medio_geral:.2f}). "
                               f"Diferença: R$ {diferenca:.2f} acima do padrão.",
                    "severidade": "media"
                })
    
    # 3. Análise: Moto da loja
    dados_moto = (
        db.query(
            func.sum(RotaEntrega.custo_moto).label("custo_total_moto"),
            func.sum(RotaEntrega.custo_real).label("custo_total_geral"),
            func.count(RotaEntrega.id).label("entregas_moto"),
        )
        .filter(RotaEntrega.tenant_id == tenant_id)
        .filter(RotaEntrega.status == "concluida")
        .filter(RotaEntrega.data_conclusao.between(data_inicio, data_fim))
        .filter(RotaEntrega.custo_moto > 0)
    ).one()
    
    if dados_moto.entregas_moto and dados_moto.entregas_moto > 0:
        custo_moto = float(dados_moto.custo_total_moto or 0)
        custo_geral = float(dados_moto.custo_total_geral or 0)
        
        if custo_geral > 0:
            percentual = (custo_moto / custo_geral) * 100
            
            if percentual > 30:  # Moto representa mais de 30% do custo
                analises.append({
                    "tipo": "alerta",
                    "titulo": "Custo elevado da moto da loja",
                    "mensagem": f"⚠️ A moto da loja representa {percentual:.1f}% do custo total de entregas. "
                               f"Avalie se vale a pena manter em todos os dias ou terceirizar em períodos de baixa demanda.",
                    "severidade": "media"
                })
    
    # Se não houver alertas, retornar mensagem positiva
    if not analises:
        analises.append({
            "tipo": "info",
            "titulo": "Tudo certo!",
            "mensagem": "✅ Não foram identificados alertas no período. A operação está dentro dos parâmetros esperados.",
            "severidade": "baixa"
        })
    
    return {
        "analises": analises,
        "periodo": {
            "data_inicio": data_inicio.isoformat(),
            "data_fim": data_fim.isoformat(),
        }
    }


@router.get("/financeiro/sugestoes-ia")
def sugestoes_ia(
    data_inicio: date = Query(..., description="Data inicial (YYYY-MM-DD)"),
    data_fim: date = Query(..., description="Data final (YYYY-MM-DD)"),
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    🤖 ETAPA 12.2 - Sugestões Práticas com IA
    
    Retorna sugestões práticas baseadas nos dados do dashboard:
    1. Ajuste de taxa
    2. Otimização do uso da moto
    3. Priorização de entregadores
    
    **Nota:** A IA sugere ações, mas NUNCA executa nada automaticamente.
    """
    user, tenant_id = user_and_tenant
    
    sugestoes = []
    
    # 1. Sugestão: Ajuste de taxa
    dados_gerais = (
        db.query(
            func.avg(RotaEntrega.taxa_entrega_cliente).label("taxa_media"),
            func.avg(RotaEntrega.custo_real).label("custo_medio"),
            func.count(RotaEntrega.id).label("total"),
        )
        .filter(RotaEntrega.tenant_id == tenant_id)
        .filter(RotaEntrega.status == "concluida")
        .filter(RotaEntrega.data_conclusao.between(data_inicio, data_fim))
    ).one()
    
    if dados_gerais.total > 0:
        taxa_media = float(dados_gerais.taxa_media or 0)
        custo_medio = float(dados_gerais.custo_medio or 0)
        
        # Sugerir taxa que cubra custo + margem de 10%
        taxa_sugerida_min = custo_medio * 1.05  # 5% de margem
        taxa_sugerida_ideal = custo_medio * 1.15  # 15% de margem
        
        if custo_medio > taxa_media:
            sugestoes.append({
                "tipo": "ajuste_taxa",
                "titulo": "Ajuste de taxa recomendado",
                "mensagem": f"💡 Sugestão: Para cobrir o custo médio atual (R$ {custo_medio:.2f}), "
                           f"a taxa mínima recomendada seria R$ {taxa_sugerida_min:.2f} "
                           f"(margem de 5%). Para uma operação mais sustentável, "
                           f"considere R$ {taxa_sugerida_ideal:.2f} (margem de 15%).",
                "dados": {
                    "taxa_atual": taxa_media,
                    "custo_medio": custo_medio,
                    "taxa_minima": taxa_sugerida_min,
                    "taxa_ideal": taxa_sugerida_ideal,
                }
            })
    
    # 2. Sugestão: Uso da moto
    dados_moto = (
        db.query(
            func.sum(RotaEntrega.custo_moto).label("custo_total_moto"),
            func.sum(RotaEntrega.custo_real).label("custo_total_geral"),
            func.count(RotaEntrega.id).label("entregas_moto"),
        )
        .filter(RotaEntrega.tenant_id == tenant_id)
        .filter(RotaEntrega.status == "concluida")
        .filter(RotaEntrega.data_conclusao.between(data_inicio, data_fim))
        .filter(RotaEntrega.custo_moto > 0)
    ).one()
    
    if dados_moto.entregas_moto and dados_moto.entregas_moto > 0:
        custo_moto = float(dados_moto.custo_total_moto or 0)
        custo_geral = float(dados_moto.custo_total_geral or 0)
        
        if custo_geral > 0:
            percentual = (custo_moto / custo_geral) * 100
            
            if percentual > 25:
                sugestoes.append({
                    "tipo": "otimizacao_moto",
                    "titulo": "Otimização do uso da moto",
                    "mensagem": f"💡 Sugestão: A moto da loja representa {percentual:.1f}% do custo total. "
                               f"Avalie terceirizar entregas em dias de baixa demanda ou horários específicos. "
                               f"Isso pode reduzir custos fixos mantendo a qualidade do serviço.",
                    "dados": {
                        "percentual_custo": percentual,
                        "custo_moto": custo_moto,
                    }
                })
    
    # 3. Sugestão: Priorizar entregadores eficientes
    por_entregador = (
        db.query(
            Cliente.nome.label("entregador_nome"),
            func.avg(RotaEntrega.custo_real).label("custo_medio"),
            func.count(RotaEntrega.id).label("entregas"),
        )
        .join(Cliente, RotaEntrega.entregador_id == Cliente.id)
        .filter(RotaEntrega.tenant_id == tenant_id)
        .filter(RotaEntrega.status == "concluida")
        .filter(RotaEntrega.data_conclusao.between(data_inicio, data_fim))
        .filter(RotaEntrega.moto_da_loja == False)  # Excluir moto da loja
        .group_by(Cliente.nome)
        .having(func.count(RotaEntrega.id) >= 3)
        .order_by(func.avg(RotaEntrega.custo_real).asc())
    ).all()
    
    if por_entregador and len(por_entregador) >= 2:
        melhor = por_entregador[0]
        custo_melhor = float(melhor.custo_medio)
        
        sugestoes.append({
            "tipo": "priorizacao_entregador",
            "titulo": "Priorização de entregadores eficientes",
            "mensagem": f"💡 Sugestão: O entregador {melhor.entregador_nome} tem o menor custo médio por entrega "
                       f"(R$ {custo_melhor:.2f}). Avalie priorizá-lo em horários de pico ou rotas mais longas "
                       f"para otimizar os custos operacionais.",
            "dados": {
                "entregador": melhor.entregador_nome,
                "custo_medio": custo_melhor,
                "entregas": melhor.entregas,
            }
        })
    
    # Se não houver sugestões, retornar mensagem neutra
    if not sugestoes:
        sugestoes.append({
            "tipo": "info",
            "titulo": "Operação otimizada",
            "mensagem": "✅ A operação atual já está otimizada. Continue monitorando os indicadores para manter a eficiência.",
            "dados": {}
        })
    
    return {
        "sugestoes": sugestoes,
        "periodo": {
            "data_inicio": data_inicio.isoformat(),
            "data_fim": data_fim.isoformat(),
        }
    }
