from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user_and_tenant
from app.banho_tosa_api.atendimentos_helpers import (
    STATUS_POR_TIPO_ETAPA,
    aplicar_status_atendimento,
    obter_atendimento_ou_404,
    obter_etapa_ou_404,
    query_atendimento_completo,
    validar_responsavel_recurso,
)
from app.banho_tosa_api.utils import (
    STATUS_ATENDIMENTO_FINAIS,
    serializar_atendimento,
    serializar_etapa,
)
from app.banho_tosa_custos import validar_transicao_status
from app.banho_tosa_cancelamento import cancelar_processo_atendimento
from app.banho_tosa_models import (
    BanhoTosaAtendimento,
    BanhoTosaEtapa,
)
from app.banho_tosa_schemas import (
    BanhoTosaCancelamentoInput,
    BanhoTosaCancelamentoResponse,
    BanhoTosaAtendimentoResponse,
    BanhoTosaAtendimentoStatusUpdate,
    BanhoTosaEtapaCreate,
    BanhoTosaEtapaFinalizarInput,
    BanhoTosaEtapaResponse,
    BanhoTosaEtapaUpdate,
)
from app.db import get_session
from app.veterinario_core import _get_tenant


router = APIRouter()


@router.get("/atendimentos", response_model=List[BanhoTosaAtendimentoResponse])
def listar_atendimentos(
    status: Optional[str] = Query(None),
    limit: int = Query(200, ge=1, le=500),
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    _, tenant_id = _get_tenant(current)
    query = query_atendimento_completo(db, tenant_id)
    if status:
        query = query.filter(BanhoTosaAtendimento.status == status)

    atendimentos = query.order_by(BanhoTosaAtendimento.checkin_em.desc()).limit(limit).all()
    return [serializar_atendimento(item) for item in atendimentos]


@router.get("/atendimentos/{atendimento_id}", response_model=BanhoTosaAtendimentoResponse)
def obter_atendimento(
    atendimento_id: int,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    _, tenant_id = _get_tenant(current)
    atendimento = obter_atendimento_ou_404(db, tenant_id, atendimento_id)
    return serializar_atendimento(atendimento)


@router.patch("/atendimentos/{atendimento_id}/status", response_model=BanhoTosaAtendimentoResponse)
def atualizar_status_atendimento(
    atendimento_id: int,
    body: BanhoTosaAtendimentoStatusUpdate,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    _, tenant_id = _get_tenant(current)
    atendimento = obter_atendimento_ou_404(db, tenant_id, atendimento_id)

    try:
        novo_status = validar_transicao_status(atendimento.status, body.status)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    aplicar_status_atendimento(db, tenant_id, atendimento, novo_status)
    if body.observacoes_saida is not None:
        atendimento.observacoes_saida = body.observacoes_saida

    db.commit()
    db.refresh(atendimento)
    atendimento = obter_atendimento_ou_404(db, tenant_id, atendimento.id)
    return serializar_atendimento(atendimento)


@router.post(
    "/atendimentos/{atendimento_id}/cancelar-processo",
    response_model=BanhoTosaCancelamentoResponse,
)
def cancelar_processo(
    atendimento_id: int,
    body: BanhoTosaCancelamentoInput,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    current_user, tenant_id = _get_tenant(current)
    return cancelar_processo_atendimento(
        db=db,
        tenant_id=tenant_id,
        user_id=current_user.id,
        atendimento_id=atendimento_id,
        motivo=body.motivo,
    )


@router.post("/atendimentos/{atendimento_id}/etapas", response_model=BanhoTosaEtapaResponse, status_code=201)
def iniciar_etapa(
    atendimento_id: int,
    body: BanhoTosaEtapaCreate,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    _, tenant_id = _get_tenant(current)
    atendimento = obter_atendimento_ou_404(db, tenant_id, atendimento_id)
    if atendimento.status in STATUS_ATENDIMENTO_FINAIS:
        raise HTTPException(status_code=422, detail="Atendimento finalizado nao aceita nova etapa")

    tipo = body.tipo.strip().lower()
    etapa_aberta = db.query(BanhoTosaEtapa).filter(
        BanhoTosaEtapa.tenant_id == tenant_id,
        BanhoTosaEtapa.atendimento_id == atendimento.id,
        BanhoTosaEtapa.tipo == tipo,
        BanhoTosaEtapa.fim_em.is_(None),
    ).first()
    if etapa_aberta:
        raise HTTPException(status_code=409, detail="Ja existe etapa aberta desse tipo")

    validar_responsavel_recurso(db, tenant_id, body.responsavel_id, body.recurso_id)
    etapa = BanhoTosaEtapa(
        tenant_id=tenant_id,
        atendimento_id=atendimento.id,
        tipo=tipo,
        responsavel_id=body.responsavel_id,
        recurso_id=body.recurso_id,
        inicio_em=datetime.now(),
        observacoes=body.observacoes,
    )
    db.add(etapa)

    novo_status = STATUS_POR_TIPO_ETAPA.get(tipo)
    if novo_status:
        aplicar_status_atendimento(db, tenant_id, atendimento, novo_status)

    db.commit()
    db.refresh(etapa)
    etapa = obter_etapa_ou_404(db, tenant_id, atendimento.id, etapa.id)
    return serializar_etapa(etapa)


@router.patch("/atendimentos/{atendimento_id}/etapas/{etapa_id}", response_model=BanhoTosaEtapaResponse)
def atualizar_etapa(
    atendimento_id: int,
    etapa_id: int,
    body: BanhoTosaEtapaUpdate,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    _, tenant_id = _get_tenant(current)
    obter_atendimento_ou_404(db, tenant_id, atendimento_id)
    etapa = obter_etapa_ou_404(db, tenant_id, atendimento_id, etapa_id)
    payload = body.model_dump(exclude_unset=True)

    validar_responsavel_recurso(
        db,
        tenant_id,
        payload.get("responsavel_id", etapa.responsavel_id),
        payload.get("recurso_id", etapa.recurso_id),
    )

    for campo, valor in payload.items():
        setattr(etapa, campo, valor)

    db.commit()
    db.refresh(etapa)
    etapa = obter_etapa_ou_404(db, tenant_id, atendimento_id, etapa.id)
    return serializar_etapa(etapa)


@router.post("/atendimentos/{atendimento_id}/etapas/{etapa_id}/finalizar", response_model=BanhoTosaEtapaResponse)
def finalizar_etapa(
    atendimento_id: int,
    etapa_id: int,
    body: BanhoTosaEtapaFinalizarInput,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    _, tenant_id = _get_tenant(current)
    obter_atendimento_ou_404(db, tenant_id, atendimento_id)
    etapa = obter_etapa_ou_404(db, tenant_id, atendimento_id, etapa_id)
    if etapa.fim_em:
        return serializar_etapa(etapa)

    fim = datetime.now()
    etapa.fim_em = fim
    if etapa.inicio_em:
        etapa.duracao_minutos = max(0, int((fim - etapa.inicio_em).total_seconds() // 60))
    if body.observacoes is not None:
        etapa.observacoes = body.observacoes

    db.commit()
    db.refresh(etapa)
    etapa = obter_etapa_ou_404(db, tenant_id, atendimento_id, etapa.id)
    return serializar_etapa(etapa)
