from decimal import Decimal
from types import SimpleNamespace

from app.services.custo_entrega_service import calcular_custo_entrega


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


def test_taxa_fixa_e_calculada_por_entrega_da_rota():
    entregador = _entregador(
        modelo_custo_entrega="taxa_fixa",
        taxa_fixa_entrega=Decimal("12.50"),
    )

    custo = calcular_custo_entrega(
        entregador=entregador,
        km=Decimal("18"),
        tentativas=1,
        moto_da_loja=False,
        quantidade_entregas=4,
    )

    assert custo == Decimal("50.00")


def test_rateio_rh_e_calculado_por_entrega_da_rota():
    entregador = _entregador(
        controla_rh=True,
        media_entregas_configurada=200,
        custo_rh_ajustado=Decimal("3000"),
        modelo_custo_entrega="rateio_rh",
    )

    custo = calcular_custo_entrega(
        entregador=entregador,
        km=Decimal("10"),
        tentativas=1,
        moto_da_loja=False,
        quantidade_entregas=3,
    )

    assert custo == Decimal("45.00")


def test_custo_por_km_usa_distancia_total_sem_multiplicar_paradas():
    entregador = _entregador(
        modelo_custo_entrega="por_km",
        valor_por_km_entrega=Decimal("2.50"),
    )

    custo = calcular_custo_entrega(
        entregador=entregador,
        km=Decimal("12"),
        tentativas=1,
        moto_da_loja=False,
        quantidade_entregas=5,
    )

    assert custo == Decimal("30.00")


def test_tentativa_extra_acrescenta_uma_entrega_sem_multiplicar_rota_inteira():
    entregador = _entregador(
        modelo_custo_entrega="taxa_fixa",
        taxa_fixa_entrega=Decimal("10"),
    )

    custo = calcular_custo_entrega(
        entregador=entregador,
        km=Decimal("12"),
        tentativas=2,
        moto_da_loja=False,
        quantidade_entregas=4,
    )

    assert custo == Decimal("50.00")


def test_tentativa_nao_multiplica_distancia_real_do_modelo_por_km():
    entregador = _entregador(
        modelo_custo_entrega="por_km",
        valor_por_km_entrega=Decimal("2"),
    )

    custo = calcular_custo_entrega(
        entregador=entregador,
        km=Decimal("15"),
        tentativas=3,
        moto_da_loja=False,
        quantidade_entregas=2,
    )

    assert custo == Decimal("30.00")


def test_quantidade_omitida_preserva_compatibilidade_com_rota_simples():
    entregador = _entregador(
        modelo_custo_entrega="taxa_fixa",
        taxa_fixa_entrega=Decimal("9.90"),
    )

    custo = calcular_custo_entrega(
        entregador=entregador,
        km=Decimal("3"),
        tentativas=1,
        moto_da_loja=False,
    )

    assert custo == Decimal("9.90")
