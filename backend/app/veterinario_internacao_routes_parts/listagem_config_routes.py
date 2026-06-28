"""Listagem e configuracao de internacoes veterinarias."""

from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..auth.dependencies import get_current_user_and_tenant
from ..db import get_session
from ..models import Pet
from ..veterinario_core import _get_tenant, _serializar_datetime_vet
from ..veterinario_internacao import (
    _resolver_tenant_id_vet,
    _resolver_user_id_vet,
    _split_motivo_baia,
)
from ..veterinario_models import InternacaoConfig, InternacaoVet
from ..veterinario_schemas import InternacaoConfigUpdate

router = APIRouter()


@router.get("/internacoes")
def listar_internacoes(
    status: Optional[str] = "internado",
    pet_id: Optional[int] = None,
    cliente_id: Optional[int] = None,
    data_saida_inicio: Optional[date] = Query(None),
    data_saida_fim: Optional[date] = Query(None),
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    user, tenant_id = _get_tenant(current)

    # Compatibilidade: telas antigas enviavam "ativa" para status de internação aberta.
    status_map = {
        "ativa": "internado",
    }
    status_normalizado = status_map.get(status, status)

    # Fallback defensivo: em alguns fluxos o tenant pode vir no usuário e não no retorno do Depends.
    if tenant_id is None:
        tenant_id = getattr(user, "tenant_id", None)
    if tenant_id is None and isinstance(user, dict):
        tenant_id = user.get("tenant_id")
    if tenant_id is None:
        raise HTTPException(
            status_code=401, detail="Tenant não identificado para listar internações"
        )

    q = db.query(InternacaoVet).filter(InternacaoVet.tenant_id == tenant_id)
    if status_normalizado:
        q = q.filter(InternacaoVet.status == status_normalizado)
    if pet_id:
        q = q.filter(InternacaoVet.pet_id == pet_id)
    if cliente_id:
        q = q.filter(InternacaoVet.pet.has(Pet.cliente_id == cliente_id))
    if data_saida_inicio:
        q = q.filter(func.date(InternacaoVet.data_saida) >= data_saida_inicio)
    if data_saida_fim:
        q = q.filter(func.date(InternacaoVet.data_saida) <= data_saida_fim)

    internacoes = q.order_by(InternacaoVet.data_entrada.desc()).all()
    result = []
    for i in internacoes:
        motivo_limpo, box = _split_motivo_baia(i.motivo)
        tutor = i.pet.cliente if i.pet and i.pet.cliente else None
        result.append(
            {
                "id": i.id,
                "pet_id": i.pet_id,
                "consulta_id": i.consulta_id,
                "veterinario_id": i.veterinario_id,
                "pet_nome": i.pet.nome if i.pet else None,
                "tutor_id": tutor.id if tutor else None,
                "tutor_nome": tutor.nome if tutor else None,
                "motivo": motivo_limpo,
                "box": box,
                "status": i.status,
                "data_entrada": _serializar_datetime_vet(i.data_entrada),
                "data_saida": _serializar_datetime_vet(i.data_saida),
                "observacoes_alta": i.observacoes,
            }
        )
    return result


@router.get("/internacoes/config")
def obter_config_internacao(
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    user, tenant_id = _get_tenant(current)
    tenant_id = _resolver_tenant_id_vet(
        user, tenant_id, "Tenant nao identificado para configuracao de internacao"
    )
    user_id = _resolver_user_id_vet(
        user, "Usuario invalido para configuracao de internacao"
    )

    config = (
        db.query(InternacaoConfig)
        .filter(InternacaoConfig.tenant_id == tenant_id)
        .first()
    )
    if not config:
        config = InternacaoConfig(
            tenant_id=tenant_id,
            user_id=user_id,
            total_baias=12,
        )
        db.add(config)
        db.commit()
        db.refresh(config)

    return {
        "id": config.id,
        "total_baias": config.total_baias,
    }


@router.put("/internacoes/config")
def atualizar_config_internacao(
    body: InternacaoConfigUpdate,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    user, tenant_id = _get_tenant(current)
    tenant_id = _resolver_tenant_id_vet(
        user, tenant_id, "Tenant nao identificado para configuracao de internacao"
    )
    user_id = _resolver_user_id_vet(
        user, "Usuario invalido para configuracao de internacao"
    )

    config = (
        db.query(InternacaoConfig)
        .filter(InternacaoConfig.tenant_id == tenant_id)
        .first()
    )
    if not config:
        config = InternacaoConfig(
            tenant_id=tenant_id,
            user_id=user_id,
            total_baias=body.total_baias,
        )
        db.add(config)
    else:
        config.user_id = user_id
        config.total_baias = body.total_baias

    db.commit()
    db.refresh(config)
    return {
        "id": config.id,
        "total_baias": config.total_baias,
    }
