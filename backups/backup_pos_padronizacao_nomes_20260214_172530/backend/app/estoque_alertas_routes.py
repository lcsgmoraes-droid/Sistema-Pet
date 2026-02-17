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


class ProdutoEstoqueNegativo(BaseModel):
    produto_id: int
    nome: str
    estoque_atual: float
    alertas_pendentes: int


class DashboardAlertasResponse(BaseModel):
    total_alertas: int  # Total de todos os alertas (pendentes + resolvidos)
    alertas_pendentes: int
    alertas_criticos: int
    alertas_resolvidos: int
    produtos_estoque_negativo: List[ProdutoEstoqueNegativo]


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
    from app.produtos_models import Produto
    tenant_id = current_user.tenant_id
    
    # Total de TODOS os alertas (independente do status)
    total_alertas = db.query(AlertaEstoqueNegativo).filter(
        AlertaEstoqueNegativo.tenant_id == tenant_id
    ).count()
    
    # Total de alertas pendentes
    alertas_pendentes = db.query(AlertaEstoqueNegativo).filter(
        and_(
            AlertaEstoqueNegativo.tenant_id == tenant_id,
            AlertaEstoqueNegativo.status == 'pendente'
        )
    ).count()
    
    # Total de alertas críticos PENDENTES
    alertas_criticos = db.query(AlertaEstoqueNegativo).filter(
        and_(
            AlertaEstoqueNegativo.tenant_id == tenant_id,
            AlertaEstoqueNegativo.status == 'pendente',
            AlertaEstoqueNegativo.critico == True
        )
    ).count()
    
    # Total de alertas resolvidos
    alertas_resolvidos = db.query(AlertaEstoqueNegativo).filter(
        and_(
            AlertaEstoqueNegativo.tenant_id == tenant_id,
            AlertaEstoqueNegativo.status.in_(['resolvido', 'ignorado'])
        )
    ).count()
    
    # Produtos com estoque negativo ATUAL
    produtos_negativos = db.query(
        Produto.id,
        Produto.nome,
        Produto.estoque_atual
    ).filter(
        and_(
            Produto.tenant_id == tenant_id,
            Produto.estoque_atual < 0
        )
    ).all()
    
    produtos_estoque_negativo = []
    for produto_id, nome, estoque_atual in produtos_negativos:
        # Contar alertas pendentes para este produto
        count_alertas = db.query(AlertaEstoqueNegativo).filter(
            and_(
                AlertaEstoqueNegativo.tenant_id == tenant_id,
                AlertaEstoqueNegativo.produto_id == produto_id,
                AlertaEstoqueNegativo.status == 'pendente'
            )
        ).count()
        
        produtos_estoque_negativo.append(
            ProdutoEstoqueNegativo(
                produto_id=produto_id,
                nome=nome,
                estoque_atual=estoque_atual,
                alertas_pendentes=count_alertas
            )
        )
    
    return DashboardAlertasResponse(
        total_alertas=total_alertas,
        alertas_pendentes=alertas_pendentes,
        alertas_criticos=alertas_criticos,
        alertas_resolvidos=alertas_resolvidos,
        produtos_estoque_negativo=produtos_estoque_negativo
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
        f"Usuário: {current_user.nome or current_user.email}"
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
