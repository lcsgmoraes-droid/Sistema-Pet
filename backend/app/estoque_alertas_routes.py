"""
Rotas de Alertas de Estoque Negativo - MODELO CONTROLADO
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc
from datetime import datetime

from app.auth import get_current_user
from app.models import User
from app.db import get_session
from app.estoque_models import AlertaEstoqueNegativo
from app.utils.logger import logger


router = APIRouter(prefix="/estoque/alertas", tags=["Estoque - Alertas"])


# ============================================================================
# SCHEMAS
# ============================================================================

class AlertaEstoqueResponse(BaseModel):
    id: int
    produto_id: int
    produto_nome: str
    estoque_anterior: float
    quantidade_vendida: float
    estoque_resultante: float
    venda_id: Optional[int] = None
    venda_codigo: Optional[str] = None
    data_alerta: datetime
    status: str
    data_resolucao: Optional[datetime] = None
    observacao: Optional[str] = None
    notificado: bool
    critico: bool
    
    class Config:
        from_attributes = True


class ResolverAlertaRequest(BaseModel):
    status: str  # 'resolvido' ou 'ignorado'
    observacao: Optional[str] = None


class DashboardAlertasResponse(BaseModel):
    total_alertas_pendentes: int
    total_produtos_afetados: int
    total_criticos: int
    alertas_recentes: List[AlertaEstoqueResponse]


# ============================================================================
# ENDPOINTS
# ============================================================================

@router.get("/pendentes", response_model=List[AlertaEstoqueResponse])
def listar_alertas_pendentes(
    apenas_criticos: bool = Query(False, description="Filtrar apenas alertas críticos"),
    limit: int = Query(50, le=200, description="Limite de resultados"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session)
):
    """
    Lista todos os alertas de estoque negativo pendentes.
    
    🟢 MODELO CONTROLADO - Visibilidade total de produtos com estoque negativo
    """
    tenant_id = current_user.tenant_id
    
    query = db.query(AlertaEstoqueNegativo).filter(
        and_(
            AlertaEstoqueNegativo.tenant_id == tenant_id,
            AlertaEstoqueNegativo.status == 'pendente'
        )
    )
    
    if apenas_criticos:
        query = query.filter(AlertaEstoqueNegativo.critico == True)
    
    alertas = query.order_by(
        desc(AlertaEstoqueNegativo.critico),
        desc(AlertaEstoqueNegativo.data_alerta)
    ).limit(limit).all()
    
    return alertas


@router.get("/todos", response_model=List[AlertaEstoqueResponse])
def listar_todos_alertas(
    status: Optional[str] = Query(None, description="Filtrar por status"),
    limit: int = Query(100, le=500, description="Limite de resultados"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session)
):
    """
    Lista todos os alertas de estoque negativo (histórico completo).
    """
    tenant_id = current_user.tenant_id
    
    query = db.query(AlertaEstoqueNegativo).filter(
        AlertaEstoqueNegativo.tenant_id == tenant_id
    )
    
    if status:
        query = query.filter(AlertaEstoqueNegativo.status == status)
    
    alertas = query.order_by(
        desc(AlertaEstoqueNegativo.data_alerta)
    ).limit(limit).all()
    
    return alertas


@router.get("/dashboard", response_model=DashboardAlertasResponse)
def dashboard_alertas(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session)
):
    """
    Retorna resumo de alertas para dashboard.
    
    🟢 MODELO CONTROLADO - Métricas visíveis para tomada de decisão
    """
    tenant_id = current_user.tenant_id
    
    # Total de alertas pendentes
    total_pendentes = db.query(AlertaEstoqueNegativo).filter(
        and_(
            AlertaEstoqueNegativo.tenant_id == tenant_id,
            AlertaEstoqueNegativo.status == 'pendente'
        )
    ).count()
    
    # Total de produtos afetados (distintos)
    from sqlalchemy import func
    produtos_afetados = db.query(
        func.count(func.distinct(AlertaEstoqueNegativo.produto_id))
    ).filter(
        and_(
            AlertaEstoqueNegativo.tenant_id == tenant_id,
            AlertaEstoqueNegativo.status == 'pendente'
        )
    ).scalar() or 0
    
    # Total de alertas críticos
    total_criticos = db.query(AlertaEstoqueNegativo).filter(
        and_(
            AlertaEstoqueNegativo.tenant_id == tenant_id,
            AlertaEstoqueNegativo.status == 'pendente',
            AlertaEstoqueNegativo.critico == True
        )
    ).count()
    
    # Alertas recentes (últimos 10)
    alertas_recentes = db.query(AlertaEstoqueNegativo).filter(
        and_(
            AlertaEstoqueNegativo.tenant_id == tenant_id,
            AlertaEstoqueNegativo.status == 'pendente'
        )
    ).order_by(
        desc(AlertaEstoqueNegativo.critico),
        desc(AlertaEstoqueNegativo.data_alerta)
    ).limit(10).all()
    
    return DashboardAlertasResponse(
        total_alertas_pendentes=total_pendentes,
        total_produtos_afetados=produtos_afetados,
        total_criticos=total_criticos,
        alertas_recentes=alertas_recentes
    )


@router.put("/{alerta_id}/resolver", response_model=AlertaEstoqueResponse)
def resolver_alerta(
    alerta_id: int,
    dados: ResolverAlertaRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session)
):
    """
    Resolve ou ignora um alerta de estoque negativo.
    
    Usado quando:
    - Produto foi reposto (status='resolvido')
    - Alerta é falso positivo (status='ignorado')
    """
    tenant_id = current_user.tenant_id
    
    alerta = db.query(AlertaEstoqueNegativo).filter(
        and_(
            AlertaEstoqueNegativo.id == alerta_id,
            AlertaEstoqueNegativo.tenant_id == tenant_id
        )
    ).first()
    
    if not alerta:
        raise HTTPException(status_code=404, detail="Alerta não encontrado")
    
    if dados.status not in ['resolvido', 'ignorado']:
        raise HTTPException(status_code=400, detail="Status inválido. Use 'resolvido' ou 'ignorado'")
    
    # Atualizar alerta
    alerta.status = dados.status
    alerta.data_resolucao = datetime.utcnow()
    alerta.usuario_resolucao_id = current_user.id
    alerta.observacao = dados.observacao
    
    db.commit()
    db.refresh(alerta)
    
    logger.info(
        f"✅ Alerta de estoque negativo {dados.status} - "
        f"ID: {alerta_id}, Produto: {alerta.produto_nome}, "
        f"Usuário: {current_user.username}"
    )
    
    return alerta


@router.delete("/{alerta_id}")
def excluir_alerta(
    alerta_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session)
):
    """
    Exclui um alerta de estoque (apenas para correção de erros).
    """
    tenant_id = current_user.tenant_id
    
    alerta = db.query(AlertaEstoqueNegativo).filter(
        and_(
            AlertaEstoqueNegativo.id == alerta_id,
            AlertaEstoqueNegativo.tenant_id == tenant_id
        )
    ).first()
    
    if not alerta:
        raise HTTPException(status_code=404, detail="Alerta não encontrado")
    
    db.delete(alerta)
    db.commit()
    
    logger.info(f"🗑️ Alerta de estoque negativo excluído - ID: {alerta_id}")
    
    return {"message": "Alerta excluído com sucesso"}


# ============================================================================
# VERIFICAÇÃO DE ESTOQUE PRÉ-VENDA
# ============================================================================

class ItemVerificarEstoque(BaseModel):
    produto_id: int
    quantidade: float


class VerificarEstoqueRequest(BaseModel):
    itens: List[ItemVerificarEstoque]


class ProdutoEstoqueNegativoResponse(BaseModel):
    produto_id: int
    produto_nome: str
    estoque_atual: float
    quantidade_solicitada: float
    estoque_resultante: float


@router.post("/verificar-estoque-negativo", response_model=List[ProdutoEstoqueNegativoResponse])
def verificar_estoque_negativo_pre_venda(
    request: VerificarEstoqueRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session)
):
    """
    Verifica se algum produto ficará com estoque negativo ao finalizar a venda.
    Retorna lista de produtos que ficarão com estoque negativo.
    """
    from app.produtos_models import Produto
    
    tenant_id = current_user.tenant_id
    produtos_negativos = []
    
    for item in request.itens:
        # Buscar produto
        produto = db.query(Produto).filter(
            and_(
                Produto.id == item.produto_id,
                Produto.tenant_id == tenant_id
            )
        ).first()
        
        if not produto:
            continue
        
        estoque_atual = produto.estoque_atual or 0
        estoque_resultante = estoque_atual - item.quantidade
        
        # Se ficará negativo, adicionar à lista
        if estoque_resultante < 0:
            produtos_negativos.append(
                ProdutoEstoqueNegativoResponse(
                    produto_id=produto.id,
                    produto_nome=produto.nome,
                    estoque_atual=estoque_atual,
                    quantidade_solicitada=item.quantidade,
                    estoque_resultante=estoque_resultante
                )
            )
    
    return produtos_negativos
