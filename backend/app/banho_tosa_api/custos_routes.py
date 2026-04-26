from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user_and_tenant
from app.banho_tosa_custos import (
    ComissaoRegra,
    EquipamentoUso,
    InsumoCusto,
    MaoObraEtapa,
    TaxiDogCusto,
    calcular_custo_agua,
    calcular_custo_comissao,
    calcular_custo_energia,
    calcular_custo_insumos,
    calcular_custo_mao_obra,
    calcular_custo_taxi_dog,
    calcular_snapshot_custo,
)
from app.banho_tosa_custos_reais import (
    obter_snapshot_existente_ou_previa,
    recalcular_snapshot_atendimento,
)
from app.banho_tosa_custos_helpers import serializar_snapshot_custo
from app.banho_tosa_schemas import (
    BanhoTosaCustoAtendimentoResponse,
    BanhoTosaCustoSimulacaoInput,
    BanhoTosaCustoSnapshotResponse,
)
from app.db import get_session
from app.veterinario_core import _get_tenant


router = APIRouter()


@router.post("/custos/simular", response_model=BanhoTosaCustoSnapshotResponse)
def simular_custo(body: BanhoTosaCustoSimulacaoInput):
    custo_insumos = calcular_custo_insumos([InsumoCusto(**item.model_dump()) for item in body.insumos])
    custo_agua = calcular_custo_agua(**body.agua.model_dump())
    custo_energia = calcular_custo_energia([EquipamentoUso(**item.model_dump()) for item in body.energia])
    custo_mao_obra = calcular_custo_mao_obra([MaoObraEtapa(**item.model_dump()) for item in body.mao_obra])
    custo_comissao = calcular_custo_comissao(ComissaoRegra(**body.comissao.model_dump()))
    custo_taxi_dog = calcular_custo_taxi_dog(TaxiDogCusto(**body.taxi_dog.model_dump()))

    return calcular_snapshot_custo(
        valor_cobrado=body.valor_cobrado,
        custo_insumos=custo_insumos,
        custo_agua=custo_agua,
        custo_energia=custo_energia,
        custo_mao_obra=custo_mao_obra,
        custo_comissao=custo_comissao,
        custo_taxi_dog=custo_taxi_dog,
        custo_taxas_pagamento=body.custo_taxas_pagamento,
        custo_rateio_operacional=body.custo_rateio_operacional,
    ).as_dict()


@router.get("/custos/atendimentos/{atendimento_id}", response_model=BanhoTosaCustoAtendimentoResponse)
def obter_custo_atendimento(
    atendimento_id: int,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    _, tenant_id = _get_tenant(current)
    snapshot = obter_snapshot_existente_ou_previa(db, tenant_id, atendimento_id)
    if not snapshot:
        raise HTTPException(status_code=404, detail="Atendimento nao encontrado")
    return snapshot


@router.post("/custos/atendimentos/{atendimento_id}/recalcular", response_model=BanhoTosaCustoAtendimentoResponse)
def recalcular_custo_atendimento(
    atendimento_id: int,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    _, tenant_id = _get_tenant(current)
    snapshot = recalcular_snapshot_atendimento(db, tenant_id, atendimento_id)
    if not snapshot:
        raise HTTPException(status_code=404, detail="Atendimento nao encontrado")

    db.commit()
    db.refresh(snapshot)
    return serializar_snapshot_custo(snapshot)
