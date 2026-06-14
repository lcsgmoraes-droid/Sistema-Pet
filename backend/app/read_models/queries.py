"""
Queries para Read Models
=========================

Funções simples de consulta otimizadas para leitura.

CARACTERÍSTICAS:
- Queries diretas sem joins complexos
- Retornam dados já agregados
- Otimizadas por índices
- Sem lógica de negócio
"""

import logging
from datetime import date, datetime, timedelta
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import desc, func, inspect, text

from .models import VendasResumoDiario, PerformanceParceiro, ReceitaMensal

logger = logging.getLogger(__name__)


def obter_resumo_diario(db: Session, data: Optional[date] = None) -> Optional[Dict[str, Any]]:
    """
    Obtém o resumo de vendas de um dia específico.
    
    Args:
        db: Sessão do banco de dados
        data: Data desejada (padrão: hoje)
        
    Returns:
        Dicionário com métricas do dia ou None se não houver dados
        
    Exemplo:
        resumo = obter_resumo_diario(db)
        logger.info(f"Vendas finalizadas hoje: {resumo['quantidade_finalizada']}")
    """
    if data is None:
        data = date.today()
    
    logger.debug(f"🔍 Consultando resumo diário: {data}")
    
    resumo = db.query(VendasResumoDiario).filter(
        VendasResumoDiario.data == data
    ).first()
    
    if resumo:
        logger.info(f"✅ Resumo encontrado: {data} - {resumo.quantidade_finalizada} vendas")
        return resumo.to_dict()
    else:
        logger.info(f"ℹ️  Nenhum resumo encontrado para {data}")
        return None


def obter_resumo_periodo(
    db: Session,
    data_inicio: date,
    data_fim: date
) -> List[Dict[str, Any]]:
    """
    Obtém resumo de vendas para um período.
    
    Args:
        db: Sessão do banco de dados
        data_inicio: Data inicial (inclusiva)
        data_fim: Data final (inclusiva)
        
    Returns:
        Lista de resumos diários ordenados por data
        
    Exemplo:
        inicio = date(2026, 1, 1)
        fim = date(2026, 1, 31)
        resumos = obter_resumo_periodo(db, inicio, fim)
    """
    logger.debug(f"🔍 Consultando resumo período: {data_inicio} até {data_fim}")
    
    resumos = db.query(VendasResumoDiario).filter(
        VendasResumoDiario.data >= data_inicio,
        VendasResumoDiario.data <= data_fim
    ).order_by(VendasResumoDiario.data).all()
    
    logger.info(f"✅ {len(resumos)} resumos encontrados no período")
    return [r.to_dict() for r in resumos]


def obter_ultimos_dias(db: Session, quantidade_dias: int = 7) -> List[Dict[str, Any]]:
    """
    Obtém resumo dos últimos N dias.
    
    Args:
        db: Sessão do banco de dados
        quantidade_dias: Número de dias para retornar
        
    Returns:
        Lista de resumos diários ordenados por data (mais recente primeiro)
        
    Exemplo:
        ultimos_7_dias = obter_ultimos_dias(db, 7)
    """
    data_fim = date.today()
    data_inicio = data_fim - timedelta(days=quantidade_dias - 1)
    
    logger.debug(f"🔍 Consultando últimos {quantidade_dias} dias")
    
    resumos = db.query(VendasResumoDiario).filter(
        VendasResumoDiario.data >= data_inicio,
        VendasResumoDiario.data <= data_fim
    ).order_by(desc(VendasResumoDiario.data)).all()
    
    logger.info(f"✅ {len(resumos)} resumos encontrados (últimos {quantidade_dias} dias)")
    return [r.to_dict() for r in resumos]


def obter_ranking_parceiros(
    db: Session,
    mes_referencia: Optional[date] = None,
    limite: int = 10
) -> List[Dict[str, Any]]:
    """
    Obtém ranking de parceiros/funcionários por vendas.
    
    Args:
        db: Sessão do banco de dados
        mes_referencia: Mês desejado (primeiro dia do mês) - padrão: mês atual
        limite: Quantidade máxima de registros
        
    Returns:
        Lista de performances ordenadas por total_vendido (maior primeiro)
        
    Exemplo:
        top_10 = obter_ranking_parceiros(db, limite=10)
        for i, perf in enumerate(top_10, 1):
            logger.info(f"{i}º - Funcionário {perf['funcionario_id']}: R$ {perf['total_vendido']}")
    """
    if mes_referencia is None:
        hoje = date.today()
        mes_referencia = date(hoje.year, hoje.month, 1)
    
    logger.debug(f"🔍 Consultando ranking de parceiros: {mes_referencia}")
    
    performances = db.query(PerformanceParceiro).filter(
        PerformanceParceiro.mes_referencia == mes_referencia
    ).order_by(
        desc(PerformanceParceiro.total_vendido)
    ).limit(limite).all()
    
    # Adiciona posição no ranking
    resultado = []
    for posicao, perf in enumerate(performances, 1):
        data = perf.to_dict()
        data['posicao'] = posicao
        resultado.append(data)
    
    logger.info(f"✅ {len(resultado)} performances encontradas (top {limite})")
    return resultado


def obter_performance_funcionario(
    db: Session,
    funcionario_id: int,
    mes_referencia: Optional[date] = None
) -> Optional[Dict[str, Any]]:
    """
    Obtém performance de um funcionário específico.
    
    Args:
        db: Sessão do banco de dados
        funcionario_id: ID do funcionário
        mes_referencia: Mês desejado (padrão: mês atual)
        
    Returns:
        Dicionário com métricas do funcionário ou None
        
    Exemplo:
        perf = obter_performance_funcionario(db, funcionario_id=5)
        logger.info(f"Total vendido: R$ {perf['total_vendido']}")
    """
    if mes_referencia is None:
        hoje = date.today()
        mes_referencia = date(hoje.year, hoje.month, 1)
    
    logger.debug(f"🔍 Consultando performance: funcionario={funcionario_id}, mes={mes_referencia}")
    
    performance = db.query(PerformanceParceiro).filter(
        PerformanceParceiro.funcionario_id == funcionario_id,
        PerformanceParceiro.mes_referencia == mes_referencia
    ).first()
    
    if performance:
        logger.info(f"✅ Performance encontrada: {funcionario_id} - R$ {performance.total_vendido}")
        return performance.to_dict()
    else:
        logger.info(f"ℹ️  Nenhuma performance encontrada para funcionário {funcionario_id}")
        return None


def obter_receita_mensal(
    db: Session,
    mes_referencia: Optional[date] = None
) -> Optional[Dict[str, Any]]:
    """
    Obtém receita agregada de um mês específico.
    
    Args:
        db: Sessão do banco de dados
        mes_referencia: Mês desejado (primeiro dia do mês) - padrão: mês atual
        
    Returns:
        Dicionário com métricas de receita ou None
        
    Exemplo:
        receita = obter_receita_mensal(db)
        logger.info(f"Receita líquida: R$ {receita['receita_liquida']}")
    """
    if mes_referencia is None:
        hoje = date.today()
        mes_referencia = date(hoje.year, hoje.month, 1)
    
    logger.debug(f"🔍 Consultando receita mensal: {mes_referencia}")
    
    receita = db.query(ReceitaMensal).filter(
        ReceitaMensal.mes_referencia == mes_referencia
    ).first()
    
    if receita:
        logger.info(f"✅ Receita encontrada: {mes_referencia} - R$ {receita.receita_liquida}")
        return receita.to_dict()
    else:
        logger.info(f"ℹ️  Nenhuma receita encontrada para {mes_referencia}")
        return None


def obter_receita_por_periodo(
    db: Session,
    data_inicio: date,
    data_fim: date
) -> List[Dict[str, Any]]:
    """
    Obtém receita de vários meses em um período.
    
    Args:
        db: Sessão do banco de dados
        data_inicio: Data inicial (primeiro dia do mês)
        data_fim: Data final (primeiro dia do mês)
        
    Returns:
        Lista de receitas mensais ordenadas cronologicamente
        
    Exemplo:
        inicio = date(2025, 1, 1)
        fim = date(2026, 1, 1)
        receitas = obter_receita_por_periodo(db, inicio, fim)
    """
    logger.debug(f"🔍 Consultando receita período: {data_inicio} até {data_fim}")
    
    receitas = db.query(ReceitaMensal).filter(
        ReceitaMensal.mes_referencia >= data_inicio,
        ReceitaMensal.mes_referencia <= data_fim
    ).order_by(ReceitaMensal.mes_referencia).all()
    
    logger.info(f"✅ {len(receitas)} receitas encontradas no período")
    return [r.to_dict() for r in receitas]


def obter_comparativo_mensal(
    db: Session,
    meses: int = 6
) -> List[Dict[str, Any]]:
    """
    Obtém comparativo de receita dos últimos N meses.
    
    Args:
        db: Sessão do banco de dados
        meses: Quantidade de meses para comparar
        
    Returns:
        Lista de receitas mensais com variação percentual
        
    Exemplo:
        comparativo = obter_comparativo_mensal(db, meses=6)
        for r in comparativo:
            logger.info(f"{r['mes_referencia']}: R$ {r['receita_liquida']} ({r['variacao_percentual']}%)")
    """
    hoje = date.today()
    mes_atual = date(hoje.year, hoje.month, 1)
    
    # Calcula primeiro dia N meses atrás
    ano = mes_atual.year
    mes = mes_atual.month - meses + 1
    while mes <= 0:
        mes += 12
        ano -= 1
    data_inicio = date(ano, mes, 1)
    
    logger.debug(f"🔍 Consultando comparativo: {meses} meses desde {data_inicio}")
    
    receitas = db.query(ReceitaMensal).filter(
        ReceitaMensal.mes_referencia >= data_inicio,
        ReceitaMensal.mes_referencia <= mes_atual
    ).order_by(ReceitaMensal.mes_referencia).all()
    
    # Calcula variação percentual manual (caso não esteja no modelo)
    resultado = []
    receita_anterior = None
    
    for receita in receitas:
        data = receita.to_dict()
        
        if receita_anterior and receita_anterior > 0:
            variacao = ((float(receita.receita_liquida) - receita_anterior) / receita_anterior) * 100
            data['variacao_calculada'] = round(variacao, 2)
        else:
            data['variacao_calculada'] = None
        
        resultado.append(data)
        receita_anterior = float(receita.receita_liquida)
    
    logger.info(f"✅ Comparativo gerado: {len(resultado)} meses")
    return resultado


def obter_estatisticas_gerais(db: Session) -> Dict[str, Any]:
    """
    Obtém estatísticas gerais consolidadas.
    
    Args:
        db: Sessão do banco de dados
        
    Returns:
        Dicionário com diversas métricas agregadas
        
    Exemplo:
        stats = obter_estatisticas_gerais(db)
        logger.info(f"Total de vendas hoje: {stats['hoje']['quantidade_finalizada']}")
    """
    logger.debug("🔍 Consultando estatísticas gerais")
    
    hoje = date.today()
    mes_atual = date(hoje.year, hoje.month, 1)
    
    # Resumo de hoje
    resumo_hoje = obter_resumo_diario(db, hoje)
    
    # Receita do mês
    receita_mes = obter_receita_mensal(db, mes_atual)
    
    # Top 5 parceiros
    top_parceiros = obter_ranking_parceiros(db, mes_atual, limite=5)
    
    # Últimos 7 dias
    ultimos_dias = obter_ultimos_dias(db, 7)
    
    estatisticas = {
        'hoje': resumo_hoje or {},
        'mes_atual': receita_mes or {},
        'top_5_parceiros': top_parceiros,
        'ultimos_7_dias': ultimos_dias,
        'atualizado_em': datetime.utcnow().isoformat()
    }
    
    logger.info("✅ Estatísticas gerais compiladas")
    return estatisticas


# ===== FUNÇÕES COM FALLBACK PARA API =====

def obter_resumo_diario_ou_vazio(db: Session, data: Optional[date] = None) -> Dict[str, Any]:
    """
    Obtém resumo diário ou retorna estrutura vazia se não houver dados.
    
    Esta função SEMPRE retorna uma estrutura completa, nunca None.
    Ideal para endpoints REST que precisam retornar JSON consistente.
    
    Args:
        db: Sessão do banco de dados
        data: Data desejada (padrão: hoje)
        
    Returns:
        Dicionário com métricas do dia (pode conter zeros se sem dados)
    """
    if data is None:
        data = date.today()
    
    resumo = obter_resumo_diario(db, data)
    
    if resumo:
        return resumo
    
    # Retorna estrutura vazia com aviso
    return {
        "data": data.isoformat(),
        "quantidade_aberta": 0,
        "quantidade_finalizada": 0,
        "quantidade_cancelada": 0,
        "total_vendido": 0.0,
        "total_cancelado": 0.0,
        "ticket_medio": 0.0,
        "atualizado_em": None,
        "aviso": "Nenhuma venda registrada nesta data"
    }


def obter_receita_mensal_ou_vazia(
    db: Session,
    mes_referencia: Optional[date] = None
) -> Dict[str, Any]:
    """
    Obtém receita mensal ou retorna estrutura vazia se não houver dados.
    
    Esta função SEMPRE retorna uma estrutura completa, nunca None.
    
    Args:
        db: Sessão do banco de dados
        mes_referencia: Primeiro dia do mês (padrão: mês atual)
        
    Returns:
        Dicionário com métricas financeiras (pode conter zeros se sem dados)
    """
    if mes_referencia is None:
        hoje = date.today()
        mes_referencia = date(hoje.year, hoje.month, 1)
    
    receita = obter_receita_mensal(db, mes_referencia)
    
    if receita:
        return receita
    
    # Retorna estrutura vazia com aviso
    return {
        "mes_referencia": mes_referencia.isoformat(),
        "receita_bruta": 0.0,
        "receita_cancelada": 0.0,
        "receita_liquida": 0.0,
        "quantidade_vendas": 0,
        "quantidade_cancelamentos": 0,
        "ticket_medio": 0.0,
        "variacao_percentual": None,
        "atualizado_em": None,
        "aviso": "Nenhuma receita registrada neste mês"
    }


def verificar_saude_read_models(db: Session) -> Dict[str, Any]:
    """
    Verifica se os read models estão acessíveis e funcionando.
    
    Usado pelo health check endpoint para garantir que:
    - Banco de dados está conectado
    - Tabelas de read models existem
    - É possível fazer queries básicas
    
    Args:
        db: Sessão do banco de dados
        
    Returns:
        Dicionário com status de saúde
        
    Raises:
        Exception: Se houver problema ao acessar read models
    """
    try:
        db.execute(text("SELECT 1"))

        inspector = inspect(db.get_bind())
        missing_tables = [
            model.__tablename__
            for model in (VendasResumoDiario, ReceitaMensal, PerformanceParceiro)
            if not inspector.has_table(model.__tablename__)
        ]
        if missing_tables:
            raise RuntimeError(
                f"Read models ausentes no schema: {', '.join(missing_tables)}"
            )
        
        logger.info("✅ Health check: Read models acessíveis")
        
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "read_models": ["VendasResumoDiario", "ReceitaMensal", "PerformanceParceiro"]
        }
    except Exception as e:
        logger.error(f"❌ Health check falhou: {e}")
        raise
