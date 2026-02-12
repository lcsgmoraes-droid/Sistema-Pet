"""
Analytics API Routes - CQRS Read Side
======================================

API REST de consulta (read-only) usando exclusivamente read models.

ARQUITETURA:
- Router "burro": Apenas delega para queries
- Zero lógica de negócio
- Zero construção de fallbacks
- Zero acesso a domínio ou UoW

CARACTERÍSTICAS:
- Consultas otimizadas (dados pré-agregados)
- Respostas rápidas (< 50ms)
- Segurança com validação JWT
- Logs de auditoria

ENDPOINTS:
- GET /analytics/resumo-diario         - Resumo de vendas do dia
- GET /analytics/receita-mensal        - Receita agregada do mês
- GET /analytics/ranking-parceiros     - Ranking de vendedores
- GET /analytics/estatisticas-gerais   - Dashboard completo
- GET /analytics/ultimos-dias          - Histórico de dias
- GET /analytics/periodo               - Resumo customizado
- GET /analytics/comparativo-receita   - Comparativo mensal
- GET /analytics/performance-funcionario/{id} - Métricas individuais
- GET /analytics/health                - Health check
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import Optional, List, Dict, Any
from datetime import date, datetime
import logging

from app.db import SessionLocal
from app.auth import get_current_user
from app.auth.dependencies import get_current_user_and_tenant
from app.models import User
from app.read_models import queries

logger = logging.getLogger(__name__)


# Dependency para obter sessão do banco
def get_db():
    """Dependency para injeção de sessão do banco"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Router de analytics (read-only)
router = APIRouter(
    prefix="/analytics",
    tags=["Analytics"],
    responses={
        404: {"description": "Dados não encontrados"},
        401: {"description": "Não autorizado"}
    }
)


# ===== FUNÇÕES AUXILIARES =====

def validate_date_range(data_inicio: date, data_fim: date) -> None:
    """
    Valida intervalo de datas.
    
    Raises:
        HTTPException: Se intervalo for inválido
    """
    if data_inicio > data_fim:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="data_inicio deve ser anterior a data_fim"
        )
    
    delta = (data_fim - data_inicio).days
    if delta > 365:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Intervalo máximo permitido: 365 dias"
        )


def log_analytics_request(
    endpoint: str,
    user_id: int,
    params: Dict[str, Any]
) -> None:
    """Registra acesso a endpoint de analytics para auditoria"""
    logger.info(
        f"📊 Analytics - Endpoint: {endpoint} | "
        f"User: {user_id} | "
        f"Params: {params}"
    )


# ===== ENDPOINTS DE ANALYTICS =====

@router.get("/resumo-diario")
def get_resumo_diario(
    data: Optional[date] = Query(
        None,
        description="Data desejada (YYYY-MM-DD). Padrão: hoje"
    ),
    db: Session = Depends(get_db),
    user_and_tenant = Depends(get_current_user_and_tenant)
) -> Dict[str, Any]:
    """
    📊 Resumo de vendas de um dia específico.
    
    Retorna métricas agregadas:
    - Quantidade de vendas (aberta, finalizada, cancelada)
    - Total vendido e cancelado
    - Ticket médio
    
    **Fonte de dados:** VendasResumoDiario (read model)
    
    **Performance:** ~5ms (dados pré-agregados)
    
    Exemplo de resposta:
    ```json
    {
        "data": "2026-01-23",
        "quantidade_aberta": 2,
        "quantidade_finalizada": 15,
        "quantidade_cancelada": 1,
        "total_vendido": 7500.00,
        "total_cancelado": 300.00,
        "ticket_medio": 500.00,
        "atualizado_em": "2026-01-23T14:30:00"
    }
    ```
    """
    current_user, tenant_id = user_and_tenant
    log_analytics_request("resumo-diario", current_user.id, {"data": data or date.today()})
    return queries.obter_resumo_diario_ou_vazio(db, data)


@router.get("/receita-mensal")
def get_receita_mensal(
    mes_referencia: Optional[date] = Query(
        None,
        description="Primeiro dia do mês desejado (YYYY-MM-01). Padrão: mês atual"
    ),
    db: Session = Depends(get_db),
    user_and_tenant = Depends(get_current_user_and_tenant)
) -> Dict[str, Any]:
    """
    💰 Receita agregada de um mês específico.
    
    Retorna métricas financeiras:
    - Receita bruta, cancelada e líquida
    - Quantidade de vendas e cancelamentos
    - Ticket médio
    - Variação percentual em relação ao mês anterior
    
    **Fonte de dados:** ReceitaMensal (read model)
    
    **Performance:** ~8ms
    
    Exemplo de resposta:
    ```json
    {
        "mes_referencia": "2026-01-01",
        "receita_bruta": 85000.00,
        "receita_cancelada": 2500.00,
        "receita_liquida": 82500.00,
        "quantidade_vendas": 150,
        "quantidade_cancelamentos": 5,
        "ticket_medio": 566.67,
        "variacao_percentual": 12.5
    }
    ```
    """
    current_user, tenant_id = user_and_tenant
    log_analytics_request("receita-mensal", current_user.id, {"mes_referencia": mes_referencia or date.today()})
    return queries.obter_receita_mensal_ou_vazia(db, mes_referencia)


@router.get("/ranking-parceiros")
def get_ranking_parceiros(
    mes_referencia: Optional[date] = Query(
        None,
        description="Primeiro dia do mês (YYYY-MM-01). Padrão: mês atual"
    ),
    limite: int = Query(
        10,
        ge=1,
        le=100,
        description="Quantidade de resultados (1-100)"
    ),
    db: Session = Depends(get_db),
    user_and_tenant = Depends(get_current_user_and_tenant)
) -> List[Dict[str, Any]]:
    """
    🏆 Ranking de parceiros/vendedores por performance.
    
    Retorna lista ordenada por total vendido (maior primeiro):
    - Posição no ranking
    - ID do funcionário
    - Quantidade de vendas
    - Total vendido
    - Ticket médio
    - Taxa de cancelamento
    
    **Fonte de dados:** PerformanceParceiro (read model)
    
    **Performance:** ~10ms
    
    **Filtros:**
    - `mes_referencia`: Mês desejado (padrão: atual)
    - `limite`: Top N vendedores (padrão: 10, max: 100)
    
    Exemplo de resposta:
    ```json
    [
        {
            "posicao": 1,
            "funcionario_id": 7,
            "quantidade_vendas": 25,
            "total_vendido": 15000.00,
            "ticket_medio": 600.00,
            "taxa_cancelamento": 5.5
        }
    ]
    ```
    """
    current_user, tenant_id = user_and_tenant
    log_analytics_request("ranking-parceiros", current_user.id, {"mes_referencia": mes_referencia, "limite": limite})
    return queries.obter_ranking_parceiros(db, mes_referencia=mes_referencia, limite=limite)


@router.get("/estatisticas-gerais")
def get_estatisticas_gerais(
    db: Session = Depends(get_db),
    user_and_tenant = Depends(get_current_user_and_tenant)
) -> Dict[str, Any]:
    """
    📈 Dashboard completo com estatísticas gerais.
    
    Retorna agregação de múltiplos read models:
    - Resumo do dia atual
    - Receita do mês atual
    - Top 5 vendedores
    - Últimos 7 dias
    
    **Fontes de dados:** Múltiplos read models
    
    **Performance:** ~30ms (consulta integrada)
    
    **Ideal para:** Dashboards gerenciais, home screens
    """
    current_user, tenant_id = user_and_tenant
    log_analytics_request("estatisticas-gerais", current_user.id, {})
    return queries.obter_estatisticas_gerais(db)


@router.get("/ultimos-dias")
def get_ultimos_dias(
    quantidade: int = Query(
        7,
        ge=1,
        le=90,
        description="Quantidade de dias (1-90)"
    ),
    db: Session = Depends(get_db),
    user_and_tenant = Depends(get_current_user_and_tenant)
) -> List[Dict[str, Any]]:
    """
    📅 Histórico de vendas dos últimos N dias.
    
    Retorna lista de resumos diários ordenados por data (mais recente primeiro).
    
    **Fonte de dados:** VendasResumoDiario (read model)
    
    **Performance:** ~15ms para 30 dias
    
    **Filtros:**
    - `quantidade`: Número de dias (1-90, padrão: 7)
    
    **Uso comum:** Gráficos de tendência, análise temporal
    """
    current_user, tenant_id = user_and_tenant
    log_analytics_request("ultimos-dias", current_user.id, {"quantidade": quantidade})
    return queries.obter_ultimos_dias(db, quantidade_dias=quantidade)


@router.get("/periodo")
def get_resumo_periodo(
    data_inicio: date = Query(..., description="Data inicial (YYYY-MM-DD)"),
    data_fim: date = Query(..., description="Data final (YYYY-MM-DD)"),
    db: Session = Depends(get_db),
    user_and_tenant = Depends(get_current_user_and_tenant)
) -> List[Dict[str, Any]]:
    """
    📆 Resumo de vendas para um período customizado.
    
    Retorna lista de resumos diários no intervalo especificado.
    
    **Fonte de dados:** VendasResumoDiario (read model)
    
    **Performance:** ~20ms para 30 dias
    
    **Validações:**
    - data_inicio <= data_fim
    - Intervalo máximo: 365 dias
    
    **Parâmetros obrigatórios:**
    - `data_inicio`: Data inicial (inclusiva)
    - `data_fim`: Data final (inclusiva)
    """
    validate_date_range(data_inicio, data_fim)
    current_user, tenant_id = user_and_tenant
    log_analytics_request("periodo", current_user.id, {"data_inicio": data_inicio, "data_fim": data_fim})
    return queries.obter_resumo_periodo(db, data_inicio, data_fim)


@router.get("/comparativo-receita")
def get_comparativo_receita(
    meses: int = Query(
        6,
        ge=2,
        le=24,
        description="Quantidade de meses para comparar (2-24)"
    ),
    db: Session = Depends(get_db),
    user_and_tenant = Depends(get_current_user_and_tenant)
) -> List[Dict[str, Any]]:
    """
    📊 Comparativo de receita dos últimos N meses.
    
    Retorna lista de receitas mensais com variação percentual.
    
    **Fonte de dados:** ReceitaMensal (read model)
    
    **Performance:** ~15ms para 12 meses
    
    **Filtros:**
    - `meses`: Quantidade de meses (2-24, padrão: 6)
    
    **Uso comum:** Gráficos de evolução, projeções, análise de tendência
    """
    current_user, tenant_id = user_and_tenant
    log_analytics_request("comparativo-receita", current_user.id, {"meses": meses})
    return queries.obter_comparativo_mensal(db, meses=meses)


@router.get("/performance-funcionario/{funcionario_id}")
def get_performance_funcionario(
    funcionario_id: int,
    mes_referencia: Optional[date] = Query(
        None,
        description="Primeiro dia do mês (YYYY-MM-01). Padrão: mês atual"
    ),
    db: Session = Depends(get_db),
    user_and_tenant = Depends(get_current_user_and_tenant)
) -> Dict[str, Any]:
    """
    👤 Performance individual de um funcionário.
    
    Retorna métricas detalhadas de um funcionário específico:
    - Quantidade de vendas
    - Total vendido
    - Ticket médio
    - Taxa de cancelamento
    - Vendas canceladas
    
    **Fonte de dados:** PerformanceParceiro (read model)
    
    **Performance:** ~8ms
    
    **Parâmetros:**
    - `funcionario_id`: ID do funcionário (path parameter)
    - `mes_referencia`: Mês desejado (query parameter, padrão: atual)
    """
    current_user, tenant_id = user_and_tenant
    log_analytics_request("performance-funcionario", current_user.id, {"funcionario_id": funcionario_id, "mes_referencia": mes_referencia})
    
    performance = queries.obter_performance_funcionario(
        db,
        funcionario_id=funcionario_id,
        mes_referencia=mes_referencia
    )
    
    if not performance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Nenhuma performance encontrada para funcionário {funcionario_id}"
        )
    
    return performance


# ===== ENDPOINT DE SAÚDE =====

@router.get("/health")
def health_check(db: Session = Depends(get_db)) -> Dict[str, str]:
    """
    🏥 Health check da API de analytics.
    
    Verifica se:
    - Banco de dados está acessível
    - Read models estão disponíveis
    
    **Não requer autenticação**
    
    Retorna:
    ```json
    {
        "status": "healthy",
        "timestamp": "2026-01-23T14:30:00Z"
    }
    ```
    """
    try:
        return queries.verificar_saude_read_models(db)
    except Exception as e:
        logger.error(f"❌ Health check falhou: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Analytics API indisponível"
        )
