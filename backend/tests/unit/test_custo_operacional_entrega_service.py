from datetime import datetime
from decimal import Decimal
from types import SimpleNamespace

from app.services.custo_operacional_entrega_service import (
    consolidar_custos_por_entrega,
    registrar_snapshot_custo_paradas,
)


def _entregador(**overrides):
    dados = {
        "controla_rh": False,
        "media_entregas_configurada": None,
        "custo_rh_ajustado": None,
        "modelo_custo_entrega": None,
        "taxa_fixa_entrega": None,
        "valor_por_km_entrega": None,
    }
    dados.update(overrides)
    return SimpleNamespace(**dados)


def _parada(distancia=Decimal("0"), tentativas=1):
    return SimpleNamespace(
        modelo_custo_operacional=None,
        valor_base_custo_operacional=None,
        distancia_trecho_real_km=distancia,
        distancia_custo_km=None,
        custo_operacional=None,
        custo_moto_rateado=None,
        custo_calculado_em=None,
        tentativas=tentativas,
    )


def test_taxa_fixa_de_seis_reais_fica_gravada_em_cada_entrega():
    entregador = _entregador(
        modelo_custo_entrega="taxa_fixa",
        taxa_fixa_entrega=Decimal("6"),
    )
    paradas = [_parada() for _ in range(5)]

    custos = consolidar_custos_por_entrega(
        paradas,
        entregador,
        distancia_total_km=Decimal("18"),
    )

    assert [p.custo_operacional for p in paradas] == [Decimal("6.00")] * 5
    assert custos.custo_entregador == Decimal("30.00")
    assert custos.custo_total == Decimal("30.00")


def test_snapshot_fixo_nao_muda_quando_configuracao_do_entregador_muda():
    entregador = _entregador(
        modelo_custo_entrega="taxa_fixa",
        taxa_fixa_entrega=Decimal("6"),
    )
    paradas = [_parada(), _parada()]
    registrar_snapshot_custo_paradas(
        paradas,
        entregador,
        registrado_em=datetime(2026, 7, 17, 10, 0),
    )

    entregador.taxa_fixa_entrega = Decimal("9")
    custos = consolidar_custos_por_entrega(
        paradas,
        entregador,
        distancia_total_km=Decimal("4"),
    )

    assert [p.valor_base_custo_operacional for p in paradas] == [Decimal("6")] * 2
    assert [p.custo_operacional for p in paradas] == [Decimal("6.00")] * 2
    assert custos.custo_total == Decimal("12.00")


def test_custo_por_km_rateia_distancia_real_e_fecha_no_total_exato():
    entregador = _entregador(
        modelo_custo_entrega="por_km",
        valor_por_km_entrega=Decimal("2.50"),
    )
    paradas = [_parada(Decimal("3")), _parada(Decimal("9"))]

    custos = consolidar_custos_por_entrega(
        paradas,
        entregador,
        distancia_total_km=Decimal("12"),
        custo_moto_total=Decimal("1"),
    )

    assert [p.distancia_custo_km for p in paradas] == [
        Decimal("3.000"),
        Decimal("9.000"),
    ]
    assert [p.custo_operacional for p in paradas] == [Decimal("7.50"), Decimal("22.50")]
    assert [p.custo_moto_rateado for p in paradas] == [Decimal("0.50"), Decimal("0.50")]
    assert custos.custo_entregador == Decimal("30.00")
    assert custos.custo_total == Decimal("31.00")


def test_tentativa_extra_fica_na_entrega_que_gerou_o_retrabalho():
    entregador = _entregador(
        modelo_custo_entrega="taxa_fixa",
        taxa_fixa_entrega=Decimal("6"),
    )
    paradas = [_parada(tentativas=2), _parada()]

    custos = consolidar_custos_por_entrega(
        paradas,
        entregador,
        distancia_total_km=Decimal("4"),
    )

    assert [p.custo_operacional for p in paradas] == [Decimal("12.00"), Decimal("6.00")]
    assert custos.custo_total == Decimal("18.00")
