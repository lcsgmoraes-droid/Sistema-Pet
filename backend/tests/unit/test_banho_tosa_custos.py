from decimal import Decimal

import pytest

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
    calcular_custo_mensal_colaborador,
    calcular_custo_taxi_dog,
    calcular_snapshot_custo,
    validar_transicao_status,
)


def test_calcula_custo_insumos_com_desperdicio():
    total = calcular_custo_insumos(
        [
            InsumoCusto(quantidade_usada="30", quantidade_desperdicio="5", custo_unitario_snapshot="0.08"),
            InsumoCusto(quantidade_usada="1", quantidade_desperdicio="0", custo_unitario_snapshot="2.50"),
        ]
    )

    assert total == Decimal("5.30")


def test_calcula_custo_agua_por_tempo_real_ou_litros_estimados():
    por_tempo = calcular_custo_agua(
        custo_litro_agua="0.012",
        vazao_chuveiro_litros_min="8",
        minutos_banho="20",
    )
    estimado = calcular_custo_agua(custo_litro_agua="0.012", agua_padrao_litros="160")

    assert por_tempo == Decimal("1.92")
    assert estimado == Decimal("1.92")


def test_calcula_custo_energia_por_equipamento_e_manutencao():
    total = calcular_custo_energia(
        [
            EquipamentoUso(potencia_watts="1800", minutos_uso="30", custo_kwh="0.95"),
            EquipamentoUso(potencia_watts="500", minutos_uso="12", custo_kwh="0.95", custo_manutencao_hora="3"),
        ]
    )

    assert total == Decimal("1.55")


def test_calcula_custo_mao_obra_por_hora_produtiva():
    total = calcular_custo_mao_obra(
        [
            MaoObraEtapa(custo_mensal_funcionario="3200", horas_produtivas_mes="160", minutos_trabalhados="45"),
            MaoObraEtapa(custo_mensal_funcionario="2600", horas_produtivas_mes="130", minutos_trabalhados="30"),
        ]
    )

    assert total == Decimal("25.00")


def test_calcula_custo_mensal_colaborador_com_encargos_e_provisoes():
    total = calcular_custo_mensal_colaborador(
        salario_base="2200",
        inss_patronal_percentual="20",
        fgts_percentual="8",
        gera_ferias=True,
        gera_decimo_terceiro=True,
    )

    assert total == Decimal("3243.78")


def test_calcula_comissao_por_percentual_e_valor_fixo():
    assert calcular_custo_comissao(
        ComissaoRegra(modelo="percentual_valor", valor_base="120", percentual="10")
    ) == Decimal("12.00")
    assert calcular_custo_comissao(
        ComissaoRegra(modelo="valor_fixo", valor_fixo="18.5")
    ) == Decimal("18.50")


def test_calcula_taxi_dog_por_km_ou_custo_real():
    assert calcular_custo_taxi_dog(
        TaxiDogCusto(km_real="7.5", custo_km="1.80", custo_motorista="8", rateio_manutencao="2")
    ) == Decimal("23.50")
    assert calcular_custo_taxi_dog(TaxiDogCusto(custo_real_informado="19.999")) == Decimal("20.00")


def test_calcula_snapshot_com_margem():
    snapshot = calcular_snapshot_custo(
        valor_cobrado="120",
        custo_insumos="12.30",
        custo_agua="1.92",
        custo_energia="1.55",
        custo_mao_obra="25",
        custo_comissao="12",
        custo_taxi_dog="0",
        custo_taxas_pagamento="3.60",
        custo_rateio_operacional="4",
    )

    assert snapshot.custo_total == Decimal("60.37")
    assert snapshot.margem_valor == Decimal("59.63")
    assert snapshot.margem_percentual == Decimal("49.6917")


def test_status_final_nao_reabre_sem_permissao():
    assert validar_transicao_status("entregue", "entregue") == "entregue"
    with pytest.raises(ValueError, match="nao pode ser reaberto"):
        validar_transicao_status("entregue", "em_banho")

    assert validar_transicao_status("entregue", "em_banho", permitir_reabrir_finalizado=True) == "em_banho"
