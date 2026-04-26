"""Montagem do snapshot de custo real do atendimento de Banho & Tosa."""

from decimal import Decimal
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.banho_tosa_api.utils import obter_ou_criar_configuracao
from app.banho_tosa_custos import (
    MaoObraEtapa,
    TaxiDogCusto,
    calcular_custo_energia,
    calcular_custo_insumos,
    calcular_custo_mao_obra,
    calcular_custo_mensal_colaborador,
    calcular_custo_taxi_dog,
    calcular_snapshot_custo,
)
from app.banho_tosa_custos_helpers import (
    dec,
    minutos_etapa,
    montar_detalhes_snapshot,
    serializar_snapshot_custo,
)
from app.banho_tosa_custos_reais_helpers import (
    calcular_agua_atendimento,
    mapear_equipamentos_custo,
    mapear_insumos_custo,
    valor_cobrado_atendimento,
)
from app.banho_tosa_models import (
    BanhoTosaAgendamento,
    BanhoTosaAtendimento,
    BanhoTosaCustoSnapshot,
    BanhoTosaEtapa,
    BanhoTosaInsumoUsado,
    BanhoTosaParametroPorte,
    BanhoTosaTaxiDog,
)
from app.cargo_models import Cargo


def obter_snapshot_existente_ou_previa(db: Session, tenant_id, atendimento_id: int) -> Optional[dict]:
    registro = _obter_snapshot(db, tenant_id, atendimento_id)
    if registro:
        return serializar_snapshot_custo(registro)

    calculado = montar_snapshot_atendimento(db, tenant_id, atendimento_id)
    if not calculado:
        return None

    atendimento, snapshot, detalhes = calculado
    return {
        "id": None,
        "atendimento_id": atendimento.id,
        "detalhes_json": detalhes,
        **snapshot.as_dict(),
    }


def recalcular_snapshot_atendimento(db: Session, tenant_id, atendimento_id: int) -> Optional[BanhoTosaCustoSnapshot]:
    calculado = montar_snapshot_atendimento(db, tenant_id, atendimento_id)
    if not calculado:
        return None

    atendimento, snapshot, detalhes = calculado
    registro = _obter_snapshot(db, tenant_id, atendimento_id)
    if not registro:
        registro = BanhoTosaCustoSnapshot(tenant_id=tenant_id, atendimento_id=atendimento.id)
        db.add(registro)

    for campo, valor in snapshot.as_dict().items():
        setattr(registro, campo, valor)
    registro.detalhes_json = detalhes
    db.flush()
    atendimento.custo_snapshot_id = registro.id
    return registro


def montar_snapshot_atendimento(db: Session, tenant_id, atendimento_id: int):
    atendimento = _obter_atendimento(db, tenant_id, atendimento_id)
    if not atendimento:
        return None

    config = obter_ou_criar_configuracao(db, tenant_id)
    parametro = _obter_parametro_porte(db, tenant_id, atendimento)
    valor_cobrado = valor_cobrado_atendimento(atendimento)
    custo_insumos = calcular_custo_insumos(mapear_insumos_custo(atendimento.insumos_usados))
    custo_agua = calcular_agua_atendimento(atendimento, config, parametro)
    custo_energia = calcular_custo_energia(mapear_equipamentos_custo(atendimento, config, parametro))
    custo_mao_obra, mao_obra_detalhes = _calcular_mao_obra(db, tenant_id, atendimento, config)
    custo_taxi_dog, taxi_detalhes = _calcular_taxi_dog(db, tenant_id, atendimento)
    custo_taxas = valor_cobrado * dec(config.percentual_taxas_padrao) / Decimal("100")
    custo_rateio = (
        dec(config.custo_rateio_operacional_padrao)
        + dec(config.custo_toalha_padrao)
        + dec(config.custo_higienizacao_padrao)
    )

    snapshot = calcular_snapshot_custo(
        valor_cobrado=valor_cobrado,
        custo_insumos=custo_insumos,
        custo_agua=custo_agua,
        custo_energia=custo_energia,
        custo_mao_obra=custo_mao_obra,
        custo_taxi_dog=custo_taxi_dog,
        custo_taxas_pagamento=custo_taxas,
        custo_rateio_operacional=custo_rateio,
    )
    detalhes = montar_detalhes_snapshot(atendimento, parametro, mao_obra_detalhes, taxi_detalhes)
    return atendimento, snapshot, detalhes


def _obter_snapshot(db: Session, tenant_id, atendimento_id: int) -> Optional[BanhoTosaCustoSnapshot]:
    return db.query(BanhoTosaCustoSnapshot).filter(
        BanhoTosaCustoSnapshot.tenant_id == tenant_id,
        BanhoTosaCustoSnapshot.atendimento_id == atendimento_id,
    ).first()


def _obter_atendimento(db: Session, tenant_id, atendimento_id: int) -> Optional[BanhoTosaAtendimento]:
    return (
        db.query(BanhoTosaAtendimento)
        .options(
            joinedload(BanhoTosaAtendimento.agendamento).joinedload(BanhoTosaAgendamento.servicos),
            joinedload(BanhoTosaAtendimento.etapas).joinedload(BanhoTosaEtapa.responsavel),
            joinedload(BanhoTosaAtendimento.etapas).joinedload(BanhoTosaEtapa.recurso),
            joinedload(BanhoTosaAtendimento.insumos_usados).joinedload(BanhoTosaInsumoUsado.produto),
        )
        .filter(BanhoTosaAtendimento.tenant_id == tenant_id, BanhoTosaAtendimento.id == atendimento_id)
        .first()
    )


def _obter_parametro_porte(db: Session, tenant_id, atendimento: BanhoTosaAtendimento):
    porte = (atendimento.porte_snapshot or getattr(atendimento.pet, "porte", None) or "").strip().lower()
    if not porte:
        return None
    return db.query(BanhoTosaParametroPorte).filter(
        BanhoTosaParametroPorte.tenant_id == tenant_id,
        BanhoTosaParametroPorte.ativo == True,
        func.lower(BanhoTosaParametroPorte.porte) == porte,
    ).first()


def _calcular_mao_obra(db: Session, tenant_id, atendimento, config) -> tuple[Decimal, list[dict]]:
    itens = []
    detalhes = []
    horas_produtivas = dec(config.horas_produtivas_mes_padrao, "176")
    for etapa in atendimento.etapas or []:
        minutos = minutos_etapa(etapa)
        responsavel = etapa.responsavel
        if minutos <= 0 or not responsavel or not responsavel.cargo_id:
            continue
        cargo = db.query(Cargo).filter(Cargo.id == responsavel.cargo_id, Cargo.tenant_id == tenant_id).first()
        if not cargo:
            continue
        custo_mensal = calcular_custo_mensal_colaborador(
            salario_base=cargo.salario_base,
            inss_patronal_percentual=cargo.inss_patronal_percentual,
            fgts_percentual=cargo.fgts_percentual,
            gera_ferias=cargo.gera_ferias,
            gera_decimo_terceiro=cargo.gera_decimo_terceiro,
        )
        itens.append(MaoObraEtapa(custo_mensal_funcionario=custo_mensal, horas_produtivas_mes=horas_produtivas, minutos_trabalhados=minutos))
        detalhes.append(
            {
                "etapa": etapa.tipo,
                "responsavel_id": responsavel.id,
                "responsavel_nome": responsavel.nome,
                "cargo": cargo.nome,
                "minutos": minutos,
                "custo_mensal": str(custo_mensal),
                "horas_produtivas_mes": str(horas_produtivas),
            }
        )
    return calcular_custo_mao_obra(itens), detalhes


def _calcular_taxi_dog(db: Session, tenant_id, atendimento) -> tuple[Decimal, Optional[dict]]:
    agendamento = atendimento.agendamento
    if not agendamento or not agendamento.taxi_dog_id:
        return Decimal("0.00"), None
    taxi = db.query(BanhoTosaTaxiDog).filter(
        BanhoTosaTaxiDog.id == agendamento.taxi_dog_id,
        BanhoTosaTaxiDog.tenant_id == tenant_id,
    ).first()
    if not taxi:
        return Decimal("0.00"), None
    custo = calcular_custo_taxi_dog(
        TaxiDogCusto(
            km_real=taxi.km_real or taxi.km_estimado,
            custo_real_informado=taxi.custo_real if dec(taxi.custo_real) > 0 else None,
        )
    )
    return custo, {"taxi_dog_id": taxi.id, "status": taxi.status, "km_real": str(taxi.km_real), "custo": str(custo)}
