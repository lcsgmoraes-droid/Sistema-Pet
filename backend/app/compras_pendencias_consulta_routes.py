"""Rotas de consulta e atualizacao de pendencias de compras."""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc
from sqlalchemy.orm import Session, joinedload

from .auth.dependencies import get_current_user_and_tenant
from .compras_pendencias_constants import (
    PENDENCIA_STATUS_FINAIS,
    PENDENCIA_STATUS_RESOLVIDA,
    PENDENCIA_STATUS_VALIDOS,
)
from .compras_pendencias_models import CompraPendenciaFornecedor
from .compras_pendencias_schemas import AtualizarPendenciaPayload
from .compras_pendencias_serializacao import (
    _adicionar_historico,
    _buscar_pendencia,
    _serializar_pendencia,
)
from .compras_pendencias_utils import _normalizar_texto
from .db import get_session
from .services.email_service import is_email_configured

router = APIRouter()


@router.get("/")
def listar_pendencias(
    status: Optional[str] = Query(default=None),
    fornecedor: Optional[str] = Query(default=None),
    nota_id: Optional[int] = Query(default=None),
    incluir_finalizadas: bool = Query(default=True),
    db: Session = Depends(get_session),
    current_user_and_tenant=Depends(get_current_user_and_tenant),
):
    _, tenant_id = current_user_and_tenant
    query = (
        db.query(CompraPendenciaFornecedor)
        .options(joinedload(CompraPendenciaFornecedor.itens))
        .filter(CompraPendenciaFornecedor.tenant_id == tenant_id)
    )
    if status:
        query = query.filter(CompraPendenciaFornecedor.status == status)
    elif not incluir_finalizadas:
        query = query.filter(
            ~CompraPendenciaFornecedor.status.in_(PENDENCIA_STATUS_FINAIS)
        )
    if fornecedor:
        termo = f"%{fornecedor.strip()}%"
        query = query.filter(CompraPendenciaFornecedor.fornecedor_nome.ilike(termo))
    if nota_id:
        query = query.filter(CompraPendenciaFornecedor.nota_entrada_id == nota_id)

    pendencias = (
        query.order_by(
            desc(CompraPendenciaFornecedor.updated_at),
            desc(CompraPendenciaFornecedor.id),
        )
        .limit(200)
        .all()
    )
    return [_serializar_pendencia(item) for item in pendencias]


@router.get("/envio/status")
def status_envio_pendencias(
    current_user_and_tenant=Depends(get_current_user_and_tenant),
):
    return {"email_configurado": is_email_configured()}


@router.get("/{pendencia_id}")
def obter_pendencia(
    pendencia_id: int,
    db: Session = Depends(get_session),
    current_user_and_tenant=Depends(get_current_user_and_tenant),
):
    _, tenant_id = current_user_and_tenant
    pendencia = _buscar_pendencia(db, tenant_id, pendencia_id)
    return _serializar_pendencia(pendencia, incluir_itens=True, incluir_historico=True)


@router.patch("/{pendencia_id}")
def atualizar_pendencia(
    pendencia_id: int,
    payload: AtualizarPendenciaPayload,
    db: Session = Depends(get_session),
    current_user_and_tenant=Depends(get_current_user_and_tenant),
):
    current_user, tenant_id = current_user_and_tenant
    pendencia = _buscar_pendencia(db, tenant_id, pendencia_id)
    status_anterior = pendencia.status

    if payload.status is not None:
        status_novo = payload.status.strip()
        if status_novo not in PENDENCIA_STATUS_VALIDOS:
            raise HTTPException(status_code=400, detail="Status de pendencia invalido.")
        pendencia.status = status_novo
        if status_novo == PENDENCIA_STATUS_RESOLVIDA:
            pendencia.resolvida_em = datetime.utcnow()
        elif status_anterior == PENDENCIA_STATUS_RESOLVIDA:
            pendencia.resolvida_em = None

    if payload.prazo_previsto is not None:
        pendencia.prazo_previsto = payload.prazo_previsto
    if payload.resolucao_observacao is not None:
        pendencia.resolucao_observacao = _normalizar_texto(payload.resolucao_observacao)
    pendencia.updated_at = datetime.utcnow()

    if payload.status is not None and status_anterior != pendencia.status:
        _adicionar_historico(
            pendencia,
            "status_alterado",
            current_user.id,
            payload.observacao,
            status_anterior,
            pendencia.status,
        )
    elif payload.observacao:
        _adicionar_historico(
            pendencia, "observacao", current_user.id, payload.observacao
        )

    db.commit()
    pendencia = _buscar_pendencia(db, tenant_id, pendencia_id)
    return _serializar_pendencia(pendencia, incluir_itens=True, incluir_historico=True)
