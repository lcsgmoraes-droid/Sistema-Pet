from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session, joinedload

from app.auth.dependencies import get_current_user_and_tenant
from app.db import get_session
from app.estoque_validade_models import EstoqueValidadeBloqueio
from app.estoque_validade_service import EstoqueValidadeService
from app.models import Tenant
from app.security.permissions_decorator import require_permission

router = APIRouter(prefix="/estoque/validade", tags=["Estoque - Validade"])


class DecisaoValidadePayload(BaseModel):
    observacao: Optional[str] = None


def _buscar_tenant(db: Session, tenant_id: str) -> Tenant:
    tenant = db.query(Tenant).filter(Tenant.id == str(tenant_id)).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Empresa nao encontrada")
    return tenant


def _buscar_bloqueio(db: Session, tenant_id: str, bloqueio_id: int) -> EstoqueValidadeBloqueio:
    item = (
        db.query(EstoqueValidadeBloqueio)
        .options(joinedload(EstoqueValidadeBloqueio.produto), joinedload(EstoqueValidadeBloqueio.lote))
        .filter(
            EstoqueValidadeBloqueio.id == bloqueio_id,
            EstoqueValidadeBloqueio.tenant_id == tenant_id,
        )
        .first()
    )
    if not item:
        raise HTTPException(status_code=404, detail="Bloqueio de validade nao encontrado")
    return item


def _serializar(item: EstoqueValidadeBloqueio) -> dict:
    return {
        "id": item.id,
        "produto_id": item.produto_id,
        "produto_nome": item.produto.nome if item.produto else None,
        "lote_id": item.lote_id,
        "lote_nome": item.lote.nome_lote if item.lote else None,
        "status": item.status,
        "decisao": item.decisao,
        "origem": item.origem,
        "created_at": item.created_at.isoformat() if item.created_at else None,
        "decidido_em": item.decidido_em.isoformat() if item.decidido_em else None,
        "data_validade": item.data_validade.isoformat() if item.data_validade else None,
        "quantidade_bloqueada": float(item.quantidade_bloqueada or 0),
        "quantidade_resolvida": float(item.quantidade_resolvida or 0),
        "custo_unitario": float(item.custo_unitario or 0),
        "custo_total_estimado": float(item.custo_total_estimado or 0),
        "observacao": item.observacao,
    }


@router.post("/processar")
@require_permission("produtos.editar")
def processar_validade(
    user_and_tenant=Depends(get_current_user_and_tenant),
    db: Session = Depends(get_session),
):
    current_user, tenant_id = user_and_tenant
    resultado = EstoqueValidadeService.processar_lotes_em_risco(
        db=db,
        tenant=_buscar_tenant(db, tenant_id),
        user_id=current_user.id,
    )
    db.commit()
    return {
        "processados": resultado["processados"],
        "bloqueios": [_serializar(item) for item in resultado["bloqueios"]],
    }


@router.get("/pendencias")
def listar_pendencias(
    user_and_tenant=Depends(get_current_user_and_tenant),
    db: Session = Depends(get_session),
):
    _current_user, tenant_id = user_and_tenant
    itens = (
        db.query(EstoqueValidadeBloqueio)
        .options(joinedload(EstoqueValidadeBloqueio.produto), joinedload(EstoqueValidadeBloqueio.lote))
        .filter(
            EstoqueValidadeBloqueio.tenant_id == tenant_id,
            EstoqueValidadeBloqueio.status == "pendente",
        )
        .order_by(EstoqueValidadeBloqueio.data_validade.asc())
        .all()
    )
    return {"total": len(itens), "items": [_serializar(item) for item in itens]}


@router.post("/{bloqueio_id}/descartar")
@require_permission("produtos.editar")
def descartar_bloqueio(
    bloqueio_id: int,
    payload: DecisaoValidadePayload,
    user_and_tenant=Depends(get_current_user_and_tenant),
    db: Session = Depends(get_session),
):
    current_user, tenant_id = user_and_tenant
    item = EstoqueValidadeService.descartar_bloqueio(
        db=db,
        tenant_id=tenant_id,
        user_id=current_user.id,
        bloqueio=_buscar_bloqueio(db, tenant_id, bloqueio_id),
        observacao=payload.observacao,
    )
    db.commit()
    return _serializar(item)


@router.post("/{bloqueio_id}/trocar-fornecedor")
@require_permission("produtos.editar")
def trocar_fornecedor(
    bloqueio_id: int,
    payload: DecisaoValidadePayload,
    user_and_tenant=Depends(get_current_user_and_tenant),
    db: Session = Depends(get_session),
):
    current_user, tenant_id = user_and_tenant
    item = EstoqueValidadeService.trocar_com_fornecedor(
        db=db,
        tenant_id=tenant_id,
        user_id=current_user.id,
        bloqueio=_buscar_bloqueio(db, tenant_id, bloqueio_id),
        observacao=payload.observacao,
    )
    db.commit()
    return _serializar(item)


@router.post("/{bloqueio_id}/retornar-vendavel")
@require_permission("produtos.editar")
def retornar_vendavel(
    bloqueio_id: int,
    payload: DecisaoValidadePayload,
    user_and_tenant=Depends(get_current_user_and_tenant),
    db: Session = Depends(get_session),
):
    current_user, tenant_id = user_and_tenant
    item = EstoqueValidadeService.retornar_ao_vendavel(
        db=db,
        tenant_id=tenant_id,
        user_id=current_user.id,
        bloqueio=_buscar_bloqueio(db, tenant_id, bloqueio_id),
        observacao=payload.observacao,
    )
    db.commit()
    return _serializar(item)


@router.get("/pdv-alertas")
def alertas_pdv(
    produto_ids: list[int] = Query(default=[]),
    user_and_tenant=Depends(get_current_user_and_tenant),
    db: Session = Depends(get_session),
):
    _current_user, tenant_id = user_and_tenant
    if not produto_ids:
        return {"total": 0, "items": []}

    itens = (
        db.query(EstoqueValidadeBloqueio)
        .options(joinedload(EstoqueValidadeBloqueio.produto), joinedload(EstoqueValidadeBloqueio.lote))
        .filter(
            EstoqueValidadeBloqueio.tenant_id == tenant_id,
            EstoqueValidadeBloqueio.status == "pendente",
            EstoqueValidadeBloqueio.produto_id.in_(produto_ids),
        )
        .all()
    )
    return {"total": len(itens), "items": [_serializar(item) for item in itens]}


@router.get("/relatorio-perdas")
@require_permission("relatorios.gerencial")
def relatorio_perdas(
    data_inicio: Optional[datetime] = None,
    data_fim: Optional[datetime] = None,
    incluir_todos_status: bool = False,
    user_and_tenant=Depends(get_current_user_and_tenant),
    db: Session = Depends(get_session),
):
    _current_user, tenant_id = user_and_tenant
    query = (
        db.query(EstoqueValidadeBloqueio)
        .options(joinedload(EstoqueValidadeBloqueio.produto), joinedload(EstoqueValidadeBloqueio.lote))
        .filter(
            EstoqueValidadeBloqueio.tenant_id == tenant_id,
        )
    )
    if incluir_todos_status:
        query = query.filter(
            EstoqueValidadeBloqueio.status.in_(
                ["descartado", "trocado_fornecedor", "retornado_vendavel", "pendente"]
            )
        )
    else:
        query = query.filter(EstoqueValidadeBloqueio.status == "descartado")
    if data_inicio:
        query = query.filter(EstoqueValidadeBloqueio.created_at >= data_inicio)
    if data_fim:
        query = query.filter(EstoqueValidadeBloqueio.created_at <= data_fim)

    itens = query.order_by(EstoqueValidadeBloqueio.created_at.desc()).all()
    perda_total = sum(float(item.custo_total_estimado or 0) for item in itens if item.status == "descartado")
    return {"total": len(itens), "perda_total": perda_total, "items": [_serializar(item) for item in itens]}
