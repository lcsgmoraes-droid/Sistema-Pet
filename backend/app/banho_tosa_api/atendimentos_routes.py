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
from app.banho_tosa_api.fluxo import (
    ETAPAS_OPERACIONAIS,
    calcular_tempo_previsto_etapa,
    fechar_etapa_aberta,
    fluxo_da_config,
    ordem_fluxo_para,
    status_por_etapa,
)
from app.banho_tosa_api.utils import (
    STATUS_ATENDIMENTO_FINAIS,
    obter_ou_criar_configuracao,
    serializar_atendimento,
    serializar_etapa,
)
from app.banho_tosa_custos import validar_transicao_status
from app.banho_tosa_custos_reais import recalcular_snapshot_atendimento
from app.banho_tosa_cancelamento import cancelar_processo_atendimento
from app.banho_tosa_vendas import gerar_venda_atendimento
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
    BanhoTosaMoverEtapaInput,
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

    atendimentos = (
        query.order_by(BanhoTosaAtendimento.checkin_em.desc()).limit(limit).all()
    )
    config = obter_ou_criar_configuracao(db, tenant_id)
    return [serializar_atendimento(item, config) for item in atendimentos]


@router.get(
    "/atendimentos/{atendimento_id}", response_model=BanhoTosaAtendimentoResponse
)
def obter_atendimento(
    atendimento_id: int,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    _, tenant_id = _get_tenant(current)
    atendimento = obter_atendimento_ou_404(db, tenant_id, atendimento_id)
    config = obter_ou_criar_configuracao(db, tenant_id)
    return serializar_atendimento(atendimento, config)


@router.patch(
    "/atendimentos/{atendimento_id}/status", response_model=BanhoTosaAtendimentoResponse
)
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
    config = obter_ou_criar_configuracao(db, tenant_id)
    return serializar_atendimento(atendimento, config)


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


@router.post(
    "/atendimentos/{atendimento_id}/mover-etapa",
    response_model=BanhoTosaAtendimentoResponse,
)
def mover_etapa_atendimento(
    atendimento_id: int,
    body: BanhoTosaMoverEtapaInput,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    current_user, tenant_id = _get_tenant(current)
    atendimento = obter_atendimento_ou_404(db, tenant_id, atendimento_id)
    if atendimento.status in STATUS_ATENDIMENTO_FINAIS:
        raise HTTPException(
            status_code=422, detail="Atendimento finalizado nao aceita mudanca de etapa"
        )

    tipo = body.tipo.strip().lower()
    config = obter_ou_criar_configuracao(db, tenant_id)
    fluxo = fluxo_da_config(config)
    etapas_validas = set(fluxo) | {"entregue"}
    if tipo not in etapas_validas:
        raise HTTPException(
            status_code=422, detail="Etapa nao faz parte do fluxo configurado"
        )
    if tipo in ETAPAS_OPERACIONAIS and body.iniciar_timer:
        validar_responsavel_recurso(db, tenant_id, body.responsavel_id, body.recurso_id)

    agora = datetime.now()
    if body.resetar_fluxo:
        if tipo != "chegou":
            raise HTTPException(
                status_code=422,
                detail="Reset de fluxo deve retornar para a etapa chegou",
            )
        for etapa in list(atendimento.etapas or []):
            db.delete(etapa)
        atendimento.status = "chegou"
        atendimento.inicio_em = None
        atendimento.fim_em = None
        atendimento.entregue_em = None
        aplicar_status_atendimento(db, tenant_id, atendimento, "chegou")
        db.commit()
        atendimento = obter_atendimento_ou_404(db, tenant_id, atendimento.id)
        return serializar_atendimento(atendimento, config)

    etapas_abertas = (
        db.query(BanhoTosaEtapa)
        .filter(
            BanhoTosaEtapa.tenant_id == tenant_id,
            BanhoTosaEtapa.atendimento_id == atendimento.id,
            BanhoTosaEtapa.fim_em.is_(None),
        )
        .all()
    )
    if etapas_abertas and not body.finalizar_etapa_atual:
        raise HTTPException(
            status_code=409, detail="Finalize a etapa aberta antes de iniciar outra"
        )
    for etapa in etapas_abertas:
        fechar_etapa_aberta(etapa, fim=agora)

    if tipo in ETAPAS_OPERACIONAIS and body.iniciar_timer:
        etapa = BanhoTosaEtapa(
            tenant_id=tenant_id,
            atendimento_id=atendimento.id,
            tipo=tipo,
            responsavel_id=body.responsavel_id,
            recurso_id=body.recurso_id,
            ordem_fluxo=ordem_fluxo_para(tipo, fluxo),
            tempo_previsto_minutos=body.tempo_previsto_minutos
            if body.tempo_previsto_minutos is not None
            else calcular_tempo_previsto_etapa(db, tenant_id, atendimento, tipo),
            inicio_em=agora,
            observacoes=body.observacoes,
        )
        db.add(etapa)

    aplicar_status_atendimento(db, tenant_id, atendimento, status_por_etapa(tipo))
    if tipo == "entregue" and body.observacoes_saida is not None:
        atendimento.observacoes_saida = body.observacoes_saida.strip() or None
    if tipo == "entregue" and not atendimento.pacote_credito_id:
        gerar_venda_atendimento(db, tenant_id, current_user.id, atendimento.id)
    if tipo in {"pronto", "entregue"}:
        db.flush()
        recalcular_snapshot_atendimento(db, tenant_id, atendimento.id)
    db.commit()
    atendimento = obter_atendimento_ou_404(db, tenant_id, atendimento.id)
    return serializar_atendimento(atendimento, config)


@router.post(
    "/atendimentos/{atendimento_id}/etapas",
    response_model=BanhoTosaEtapaResponse,
    status_code=201,
)
def iniciar_etapa(
    atendimento_id: int,
    body: BanhoTosaEtapaCreate,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    _, tenant_id = _get_tenant(current)
    atendimento = obter_atendimento_ou_404(db, tenant_id, atendimento_id)
    if atendimento.status in STATUS_ATENDIMENTO_FINAIS:
        raise HTTPException(
            status_code=422, detail="Atendimento finalizado nao aceita nova etapa"
        )

    tipo = body.tipo.strip().lower()
    if tipo not in ETAPAS_OPERACIONAIS:
        raise HTTPException(
            status_code=422, detail="Apenas etapas operacionais podem iniciar contador"
        )

    etapa_aberta = (
        db.query(BanhoTosaEtapa)
        .filter(
            BanhoTosaEtapa.tenant_id == tenant_id,
            BanhoTosaEtapa.atendimento_id == atendimento.id,
            BanhoTosaEtapa.fim_em.is_(None),
        )
        .first()
    )
    if etapa_aberta:
        raise HTTPException(
            status_code=409,
            detail="Finalize ou resete a etapa aberta antes de iniciar outra",
        )

    validar_responsavel_recurso(db, tenant_id, body.responsavel_id, body.recurso_id)
    config = obter_ou_criar_configuracao(db, tenant_id)
    fluxo = fluxo_da_config(config)
    etapa = BanhoTosaEtapa(
        tenant_id=tenant_id,
        atendimento_id=atendimento.id,
        tipo=tipo,
        responsavel_id=body.responsavel_id,
        recurso_id=body.recurso_id,
        ordem_fluxo=ordem_fluxo_para(tipo, fluxo),
        tempo_previsto_minutos=body.tempo_previsto_minutos
        if body.tempo_previsto_minutos is not None
        else calcular_tempo_previsto_etapa(db, tenant_id, atendimento, tipo),
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


@router.patch(
    "/atendimentos/{atendimento_id}/etapas/{etapa_id}",
    response_model=BanhoTosaEtapaResponse,
)
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


@router.post(
    "/atendimentos/{atendimento_id}/etapas/{etapa_id}/resetar",
    response_model=BanhoTosaAtendimentoResponse,
)
def resetar_etapa(
    atendimento_id: int,
    etapa_id: int,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    _, tenant_id = _get_tenant(current)
    atendimento = obter_atendimento_ou_404(db, tenant_id, atendimento_id)
    if atendimento.status in STATUS_ATENDIMENTO_FINAIS:
        raise HTTPException(
            status_code=422, detail="Atendimento finalizado nao aceita reset de etapa"
        )
    etapa = obter_etapa_ou_404(db, tenant_id, atendimento_id, etapa_id)
    if etapa.fim_em:
        raise HTTPException(
            status_code=422, detail="Apenas etapa aberta pode ter contador resetado"
        )

    tipo = etapa.tipo
    db.delete(etapa)
    aplicar_status_atendimento(db, tenant_id, atendimento, status_por_etapa(tipo))
    db.commit()
    atendimento = obter_atendimento_ou_404(db, tenant_id, atendimento.id)
    config = obter_ou_criar_configuracao(db, tenant_id)
    return serializar_atendimento(atendimento, config)


@router.post(
    "/atendimentos/{atendimento_id}/etapas/{etapa_id}/finalizar",
    response_model=BanhoTosaEtapaResponse,
)
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

    fechar_etapa_aberta(etapa, observacoes=body.observacoes)

    db.commit()
    db.refresh(etapa)
    etapa = obter_etapa_ou_404(db, tenant_id, atendimento_id, etapa.id)
    return serializar_etapa(etapa)
