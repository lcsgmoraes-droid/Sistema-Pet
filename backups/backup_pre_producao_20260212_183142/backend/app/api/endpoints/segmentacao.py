"""
Endpoints para Segmentação Automática de Clientes
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Optional

from app.db import get_session
from app.models import User
from app.auth import get_current_user_and_tenant
from app.services.segmentacao_service import SegmentacaoService
from app.schemas.segmentacao import (
    SegmentoResponse,
    RecalcularSegmentoResponse,
    RecalcularTodosRequest,
    RecalcularTodosResponse,
    ListarSegmentosResponse,
    EstatisticasSegmentosResponse,
    MetricasCliente,
    DetalheProcessamento
)


router = APIRouter(prefix="/segmentacao", tags=["Segmentação de Clientes"])


@router.post(
    "/clientes/{cliente_id}/recalcular",
    response_model=RecalcularSegmentoResponse,
    status_code=status.HTTP_200_OK,
    summary="Recalcular segmento de um cliente",
    description="""
    Recalcula o segmento de um cliente específico baseado em suas métricas atuais.
    
    **Regras aplicadas:**
    - VIP: total_compras_90d >= 2000 OU ticket_medio >= 300
    - Recorrente: compras_90d >= 3
    - Novo: primeira_compra <= 30 dias
    - Inativo: ultima_compra >= 90 dias
    - Endividado: total_em_aberto >= 500
    - Risco de churn: compras_90d < compras_90d_anteriores
    """
)
def recalcular_segmento_cliente(
    cliente_id: int,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant)
):
    """Recalcula segmento de um cliente específico"""
    current_user, tenant_id = user_and_tenant
    try:
        resultado = SegmentacaoService.recalcular_segmento_cliente(
            cliente_id=cliente_id,
            tenant_id=tenant_id,
            db=db
        )
        
        resultado['mensagem'] = f"Segmento do cliente {resultado['cliente_nome']} recalculado com sucesso"
        
        return resultado
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao recalcular segmento: {str(e)}"
        )


@router.post(
    "/recalcular-todos",
    response_model=RecalcularTodosResponse,
    status_code=status.HTTP_200_OK,
    summary="Recalcular segmentos de todos os clientes",
    description="""
    Recalcula os segmentos de todos os clientes ativos do usuário.
    
    **Parâmetros:**
    - limit: Limitar quantidade de clientes processados (útil para testes)
    
    **Retorna:**
    - Total processados, sucessos, erros
    - Detalhes de cada cliente processado
    - Distribuição de clientes por segmento
    """
)
def recalcular_todos_segmentos(
    request: RecalcularTodosRequest,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant)
):
    """Recalcula segmentos de todos os clientes ativos"""
    current_user, tenant_id = user_and_tenant
    try:
        resultado = SegmentacaoService.recalcular_todos_segmentos(
            tenant_id=tenant_id,
            db=db,
            limit=request.limit
        )
        
        resultado['mensagem'] = (
            f"Processamento concluído: {resultado['sucessos']} sucessos, "
            f"{resultado['erros']} erros de {resultado['total_processados']} clientes"
        )
        
        return resultado
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao recalcular segmentos em lote: {str(e)}"
        )


@router.get(
    "/clientes/{cliente_id}",
    response_model=SegmentoResponse,
    status_code=status.HTTP_200_OK,
    summary="Obter segmento de um cliente",
    description="Retorna o segmento atual de um cliente com todas as métricas calculadas"
)
def obter_segmento_cliente(
    cliente_id: int,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant)
):
    """Obtém segmento atual de um cliente"""
    current_user, tenant_id = user_and_tenant
    try:
        segmento = SegmentacaoService.obter_segmento_cliente(
            cliente_id=cliente_id,
            tenant_id=tenant_id,
            db=db
        )
        
        if not segmento:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Segmento não encontrado. Execute o recálculo primeiro."
            )
        
        return segmento
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao obter segmento: {str(e)}"
        )


@router.get(
    "/listar",
    response_model=ListarSegmentosResponse,
    status_code=status.HTTP_200_OK,
    summary="Listar todos os segmentos",
    description="Lista segmentos de todos os clientes, com filtro opcional por segmento"
)
def listar_segmentos(
    segmento: Optional[str] = Query(
        None,
        description="Filtrar por segmento específico (VIP, Recorrente, Novo, Inativo, Endividado, Risco, Regular)"
    ),
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant)
):
    """Lista segmentos de todos os clientes"""
    current_user, tenant_id = user_and_tenant
    try:
        segmentos = SegmentacaoService.listar_segmentos(
            tenant_id=tenant_id,
            db=db,
            segmento_filtro=segmento
        )
        
        return {
            'total': len(segmentos),
            'segmentos': segmentos
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao listar segmentos: {str(e)}"
        )


@router.get(
    "/estatisticas",
    response_model=EstatisticasSegmentosResponse,
    status_code=status.HTTP_200_OK,
    summary="Estatísticas de segmentação",
    description="Retorna estatísticas consolidadas: distribuição de clientes por segmento"
)
def obter_estatisticas_segmentos(
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant)
):
    """Obtém estatísticas consolidadas dos segmentos"""
    current_user, tenant_id = user_and_tenant
    try:
        from sqlalchemy import text
        from datetime import datetime
        
        # Buscar distribuição
        query = text("""
            SELECT 
                segmento,
                COUNT(*) as quantidade
            FROM cliente_segmentos
            WHERE tenant_id = :tenant_id
            GROUP BY segmento
            ORDER BY quantidade DESC
        """)
        
        results = db.execute(query, {'tenant_id': tenant_id}).fetchall()
        
        distribuicao = {}
        total_clientes = 0
        
        for row in results:
            distribuicao[row[0]] = row[1]
            total_clientes += row[1]
        
        # Buscar última atualização
        ultima_atualizacao_query = text("""
            SELECT MAX(updated_at) as ultima
            FROM cliente_segmentos
            WHERE tenant_id = :tenant_id
        """)
        
        ultima_result = db.execute(
            ultima_atualizacao_query,
            {'tenant_id': tenant_id}
        ).fetchone()
        
        ultima_atualizacao = ultima_result[0] if ultima_result else None
        
        return {
            'distribuicao': distribuicao,
            'total_clientes': total_clientes,
            'ultima_atualizacao': ultima_atualizacao
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao obter estatísticas: {str(e)}"
        )


@router.get(
    "/metricas/{cliente_id}",
    response_model=MetricasCliente,
    status_code=status.HTTP_200_OK,
    summary="Obter métricas brutas de um cliente",
    description="Retorna apenas as métricas calculadas sem aplicar regras de segmentação"
)
def obter_metricas_cliente(
    cliente_id: int,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant)
):
    """Obtém métricas calculadas de um cliente sem aplicar regras"""
    current_user, tenant_id = user_and_tenant
    try:
        metricas = SegmentacaoService.calcular_metricas_cliente(
            cliente_id=cliente_id,
            tenant_id=tenant_id,
            db=db
        )
        
        return metricas
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao calcular métricas: {str(e)}"
        )
