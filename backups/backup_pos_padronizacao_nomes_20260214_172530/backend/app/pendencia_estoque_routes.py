"""
Rotas para Sistema de Pendências de Estoque
Lista de espera para produtos sem estoque com notificação automática
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel

from app.db import get_session
from app.auth import get_current_user_and_tenant
from app.pendencia_estoque_models import PendenciaEstoque
from app.models import Cliente, User
from app.produtos_models import Produto

router = APIRouter(prefix="/pendencias-estoque", tags=["Pendências de Estoque"])


# Schemas
class PendenciaCreate(BaseModel):
    cliente_id: int
    produto_id: int
    quantidade_desejada: float
    observacoes: Optional[str] = None
    prioridade: int = 0


class PendenciaUpdate(BaseModel):
    status: Optional[str] = None
    observacoes: Optional[str] = None
    prioridade: Optional[int] = None
    motivo_cancelamento: Optional[str] = None


@router.post("/", response_model=dict)
def criar_pendencia(
    pendencia: PendenciaCreate,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """
    Registra uma nova pendência de estoque.
    Usado pelo PDV quando cliente deseja produto sem estoque.
    """
    user, tenant = user_and_tenant
    
    # Validar cliente
    cliente = db.query(Cliente).filter(
        Cliente.id == pendencia.cliente_id,
        Cliente.tenant_id == tenant
    ).first()
    
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")
    
    # Validar produto
    produto = db.query(Produto).filter(
        Produto.id == pendencia.produto_id,
        Produto.tenant_id == tenant
    ).first()
    
    if not produto:
        raise HTTPException(status_code=404, detail="Produto não encontrado")
    
    # Verificar se já existe pendência ativa deste cliente para este produto
    pendencia_existente = db.query(PendenciaEstoque).filter(
        and_(
            PendenciaEstoque.tenant_id == tenant,
            PendenciaEstoque.cliente_id == pendencia.cliente_id,
            PendenciaEstoque.produto_id == pendencia.produto_id,
            PendenciaEstoque.status == 'pendente'
        )
    ).first()
    
    if pendencia_existente:
        # Atualiza quantidade se já existe
        pendencia_existente.quantidade_desejada += pendencia.quantidade_desejada
        if pendencia.observacoes:
            pendencia_existente.observacoes = (pendencia_existente.observacoes or "") + "\n" + pendencia.observacoes
        db.commit()
        db.refresh(pendencia_existente)
        
        return {
            "message": "Quantidade adicionada à pendência existente",
            "pendencia": pendencia_existente.to_dict()
        }
    
    # Criar nova pendência
    nova_pendencia = PendenciaEstoque(
        tenant_id=tenant,
        cliente_id=pendencia.cliente_id,
        produto_id=pendencia.produto_id,
        usuario_registrou_id=user.id,
        quantidade_desejada=pendencia.quantidade_desejada,
        valor_referencia=produto.preco_venda,
        observacoes=pendencia.observacoes,
        prioridade=pendencia.prioridade,
        status='pendente'
    )
    
    db.add(nova_pendencia)
    db.commit()
    db.refresh(nova_pendencia)
    
    return {
        "message": "Pendência registrada com sucesso",
        "pendencia": nova_pendencia.to_dict()
    }


@router.get("/", response_model=dict)
def listar_pendencias(
    status: Optional[str] = Query(None, description="Filtrar por status"),
    cliente_id: Optional[int] = Query(None, description="Filtrar por cliente"),
    produto_id: Optional[int] = Query(None, description="Filtrar por produto"),
    prioridade: Optional[int] = Query(None, description="Filtrar por prioridade"),
    limit: int = Query(100, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """
    Lista pendências de estoque com filtros opcionais.
    """
    user, tenant = user_and_tenant
    
    query = db.query(PendenciaEstoque).filter(
        PendenciaEstoque.tenant_id == tenant
    )
    
    if status:
        query = query.filter(PendenciaEstoque.status == status)
    
    if cliente_id:
        query = query.filter(PendenciaEstoque.cliente_id == cliente_id)
    
    if produto_id:
        query = query.filter(PendenciaEstoque.produto_id == produto_id)
    
    if prioridade is not None:
        query = query.filter(PendenciaEstoque.prioridade == prioridade)
    
    # Ordenar por prioridade e data
    query = query.order_by(
        desc(PendenciaEstoque.prioridade),
        desc(PendenciaEstoque.data_registro)
    )
    
    total = query.count()
    pendencias = query.offset(offset).limit(limit).all()
    
    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "pendencias": [p.to_dict() for p in pendencias]
    }


@router.get("/cliente/{cliente_id}", response_model=dict)
def listar_pendencias_cliente(
    cliente_id: int,
    apenas_ativas: bool = Query(True, description="Mostrar apenas pendências ativas"),
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """
    Lista todas as pendências de um cliente específico.
    Útil para mostrar no PDV quando o cliente é selecionado.
    """
    user, tenant = user_and_tenant
    
    query = db.query(PendenciaEstoque).filter(
        and_(
            PendenciaEstoque.tenant_id == tenant,
            PendenciaEstoque.cliente_id == cliente_id
        )
    )
    
    if apenas_ativas:
        query = query.filter(PendenciaEstoque.status.in_(['pendente', 'notificado']))
    
    pendencias = query.order_by(desc(PendenciaEstoque.data_registro)).all()
    
    return {
        "cliente_id": cliente_id,
        "total": len(pendencias),
        "pendencias": [p.to_dict() for p in pendencias]
    }


@router.get("/produto/{produto_id}/pendentes", response_model=dict)
def listar_pendencias_produto(
    produto_id: int,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """
    Lista todas as pendências ativas de um produto.
    Usado para verificar quantas pessoas estão aguardando o produto.
    """
    user, tenant = user_and_tenant
    
    pendencias = db.query(PendenciaEstoque).filter(
        and_(
            PendenciaEstoque.tenant_id == tenant,
            PendenciaEstoque.produto_id == produto_id,
            PendenciaEstoque.status == 'pendente'
        )
    ).order_by(
        desc(PendenciaEstoque.prioridade),
        PendenciaEstoque.data_registro
    ).all()
    
    total_quantidade = sum(p.quantidade_desejada for p in pendencias)
    
    return {
        "produto_id": produto_id,
        "total_clientes": len(pendencias),
        "quantidade_total": total_quantidade,
        "pendencias": [p.to_dict() for p in pendencias]
    }


@router.put("/{pendencia_id}", response_model=dict)
def atualizar_pendencia(
    pendencia_id: int,
    update: PendenciaUpdate,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """
    Atualiza uma pendência existente.
    """
    user, tenant = user_and_tenant
    
    pendencia = db.query(PendenciaEstoque).filter(
        and_(
            PendenciaEstoque.id == pendencia_id,
            PendenciaEstoque.tenant_id == tenant
        )
    ).first()
    
    if not pendencia:
        raise HTTPException(status_code=404, detail="Pendência não encontrada")
    
    if update.status:
        pendencia.status = update.status
        
        if update.status in ['finalizado', 'cancelado']:
            pendencia.data_finalizacao = datetime.utcnow()
        
        if update.status == 'cancelado' and update.motivo_cancelamento:
            pendencia.motivo_cancelamento = update.motivo_cancelamento
    
    if update.observacoes is not None:
        pendencia.observacoes = update.observacoes
    
    if update.prioridade is not None:
        pendencia.prioridade = update.prioridade
    
    db.commit()
    db.refresh(pendencia)
    
    return {
        "message": "Pendência atualizada com sucesso",
        "pendencia": pendencia.to_dict()
    }


@router.delete("/{pendencia_id}")
def cancelar_pendencia(
    pendencia_id: int,
    motivo: Optional[str] = Query(None, description="Motivo do cancelamento"),
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """
    Cancela uma pendência.
    """
    user, tenant = user_and_tenant
    
    pendencia = db.query(PendenciaEstoque).filter(
        and_(
            PendenciaEstoque.id == pendencia_id,
            PendenciaEstoque.tenant_id == tenant
        )
    ).first()
    
    if not pendencia:
        raise HTTPException(status_code=404, detail="Pendência não encontrada")
    
    pendencia.status = 'cancelado'
    pendencia.data_finalizacao = datetime.utcnow()
    pendencia.motivo_cancelamento = motivo or "Cancelado manualmente"
    
    db.commit()
    
    return {
        "message": "Pendência cancelada com sucesso",
        "pendencia_id": pendencia_id
    }


@router.get("/dashboard/resumo", response_model=dict)
def dashboard_pendencias(
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """
    Dashboard com resumo das pendências.
    """
    user, tenant = user_and_tenant
    
    total_pendentes = db.query(PendenciaEstoque).filter(
        and_(
            PendenciaEstoque.tenant_id == tenant,
            PendenciaEstoque.status == 'pendente'
        )
    ).count()
    
    total_notificados = db.query(PendenciaEstoque).filter(
        and_(
            PendenciaEstoque.tenant_id == tenant,
            PendenciaEstoque.status == 'notificado'
        )
    ).count()
    
    total_finalizados_mes = db.query(PendenciaEstoque).filter(
        and_(
            PendenciaEstoque.tenant_id == tenant,
            PendenciaEstoque.status == 'finalizado',
            PendenciaEstoque.data_finalizacao >= datetime.now().replace(day=1)
        )
    ).count()
    
    # Top 5 produtos mais aguardados
    from sqlalchemy import func
    produtos_mais_aguardados = db.query(
        PendenciaEstoque.produto_id,
        func.count(PendenciaEstoque.id).label('total_pendencias'),
        func.sum(PendenciaEstoque.quantidade_desejada).label('quantidade_total')
    ).filter(
        and_(
            PendenciaEstoque.tenant_id == tenant,
            PendenciaEstoque.status == 'pendente'
        )
    ).group_by(
        PendenciaEstoque.produto_id
    ).order_by(
        desc('total_pendencias')
    ).limit(5).all()
    
    produtos_detalhes = []
    for produto_id, total, qtd in produtos_mais_aguardados:
        produto = db.query(Produto).filter(Produto.id == produto_id).first()
        if produto:
            produtos_detalhes.append({
                'produto_id': produto_id,
                'produto_nome': produto.nome,
                'produto_codigo': produto.codigo,
                'total_clientes': total,
                'quantidade_total': float(qtd) if qtd else 0
            })
    
    return {
        "resumo": {
            "pendentes": total_pendentes,
            "notificados": total_notificados,
            "finalizados_mes": total_finalizados_mes
        },
        "produtos_mais_aguardados": produtos_detalhes
    }

