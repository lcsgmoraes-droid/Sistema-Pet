"""Detalhe e historico de internacoes veterinarias."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..auth.dependencies import get_current_user_and_tenant
from ..db import get_session
from ..models import Pet
from ..veterinario_core import _get_tenant, _serializar_datetime_vet
from ..veterinario_internacao import (
    _resolver_data_entrada_exibicao_internacao,
    _separar_evolucoes_e_procedimentos,
    _split_motivo_baia,
)
from ..veterinario_models import EvolucaoInternacao, InternacaoVet

router = APIRouter()


@router.get("/internacoes/{internacao_id}")
def obter_internacao(
    internacao_id: int,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    user, tenant_id = _get_tenant(current)

    i = db.query(InternacaoVet).filter(InternacaoVet.id == internacao_id).first()
    if not i:
        raise HTTPException(404, "Internação não encontrada")

    if tenant_id is not None and i.tenant_id is not None and i.tenant_id != tenant_id:
        raise HTTPException(404, "Internação não encontrada")

    evolucoes = (
        db.query(EvolucaoInternacao)
        .filter(EvolucaoInternacao.internacao_id == internacao_id)
        .order_by(EvolucaoInternacao.data_hora.desc())
        .all()
    )

    motivo_limpo, box = _split_motivo_baia(i.motivo)

    evolucoes_formatadas, procedimentos_formatados = _separar_evolucoes_e_procedimentos(
        evolucoes
    )

    data_entrada_exibicao = _resolver_data_entrada_exibicao_internacao(i, evolucoes)

    return {
        "id": i.id,
        "pet_id": i.pet_id,
        "consulta_id": i.consulta_id,
        "veterinario_id": i.veterinario_id,
        "pet_nome": i.pet.nome if i.pet else None,
        "tutor_id": i.pet.cliente.id if i.pet and i.pet.cliente else None,
        "tutor_nome": i.pet.cliente.nome if i.pet and i.pet.cliente else None,
        "motivo": motivo_limpo,
        "box": box,
        "status": i.status,
        "data_entrada": data_entrada_exibicao,
        "data_saida": _serializar_datetime_vet(i.data_saida),
        "observacoes_alta": i.observacoes,
        "evolucoes": evolucoes_formatadas,
        "procedimentos": procedimentos_formatados,
    }


@router.get("/pets/{pet_id}/internacoes-historico")
def obter_historico_internacoes_pet(
    pet_id: int,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    user, tenant_id = _get_tenant(current)

    if tenant_id is None:
        tenant_id = getattr(user, "tenant_id", None)
    if tenant_id is None and isinstance(user, dict):
        tenant_id = user.get("tenant_id")
    if tenant_id is None:
        raise HTTPException(status_code=401, detail="Tenant não identificado")

    pet = db.query(Pet).filter(Pet.id == pet_id, Pet.tenant_id == tenant_id).first()
    if not pet:
        raise HTTPException(404, "Pet não encontrado")

    internacoes = (
        db.query(InternacaoVet)
        .filter(InternacaoVet.pet_id == pet_id, InternacaoVet.tenant_id == tenant_id)
        .order_by(InternacaoVet.data_entrada.desc())
        .all()
    )

    historico = []
    for internacao in internacoes:
        motivo_limpo, box = _split_motivo_baia(internacao.motivo)
        registros = (
            db.query(EvolucaoInternacao)
            .filter(EvolucaoInternacao.internacao_id == internacao.id)
            .order_by(EvolucaoInternacao.data_hora.desc())
            .all()
        )
        evols, procs = _separar_evolucoes_e_procedimentos(registros)

        data_entrada_exibicao = _resolver_data_entrada_exibicao_internacao(
            internacao, registros
        )

        historico.append(
            {
                "internacao_id": internacao.id,
                "status": internacao.status,
                "motivo": motivo_limpo,
                "box": box,
                "data_entrada": data_entrada_exibicao,
                "data_saida": _serializar_datetime_vet(internacao.data_saida),
                "observacoes_alta": internacao.observacoes,
                "evolucoes": evols,
                "procedimentos": procs,
            }
        )

    return {
        "pet_id": pet.id,
        "pet_nome": pet.nome,
        "historico": historico,
    }
