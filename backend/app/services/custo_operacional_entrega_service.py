from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, ROUND_DOWN, ROUND_HALF_UP
from typing import Iterable, Sequence

from app.models import Cliente
from app.rotas_entrega_models import RotaEntregaParada
from app.services.custo_entrega_service import calcular_custo_total_funcionario


CENTAVO = Decimal("0.01")
MILESIMO_KM = Decimal("0.001")


@dataclass(frozen=True)
class CustoOperacionalRota:
    custo_entregador: Decimal
    custo_moto: Decimal
    custo_total: Decimal


def _decimal(valor) -> Decimal:
    return Decimal(str(valor or 0))


def _moeda(valor) -> Decimal:
    return _decimal(valor).quantize(CENTAVO, rounding=ROUND_HALF_UP)


def resolver_snapshot_custo_entregador(
    entregador: Cliente | None,
) -> tuple[str, Decimal]:
    """Retorna modelo e valor unitario que devem ficar congelados na entrega."""
    if entregador is None:
        return "sem_configuracao", Decimal("0")

    if bool(getattr(entregador, "controla_rh", False)):
        media = _decimal(getattr(entregador, "media_entregas_configurada", 0))
        if media <= 0:
            return "rateio_rh", Decimal("0")
        custo_mensal = _decimal(
            getattr(entregador, "custo_rh_ajustado", None)
            or calcular_custo_total_funcionario(entregador)
        )
        return "rateio_rh", custo_mensal / media

    modelo = str(getattr(entregador, "modelo_custo_entrega", "") or "")
    if modelo == "taxa_fixa":
        return modelo, _decimal(getattr(entregador, "taxa_fixa_entrega", 0))
    if modelo == "por_km":
        return modelo, _decimal(getattr(entregador, "valor_por_km_entrega", 0))
    return "sem_configuracao", Decimal("0")


def registrar_snapshot_custo_paradas(
    paradas: Iterable[RotaEntregaParada],
    entregador: Cliente | None,
    *,
    registrado_em: datetime | None = None,
) -> None:
    """Congela a regra vigente sem sobrescrever snapshots ja existentes."""
    modelo, valor_base = resolver_snapshot_custo_entregador(entregador)
    momento = registrado_em or datetime.now()

    for parada in paradas:
        if getattr(parada, "modelo_custo_operacional", None):
            continue
        parada.modelo_custo_operacional = modelo
        parada.valor_base_custo_operacional = valor_base
        parada.tentativas = max(int(getattr(parada, "tentativas", 1) or 1), 1)
        parada.custo_moto_rateado = Decimal("0")

        if modelo in {"taxa_fixa", "rateio_rh"}:
            parada.distancia_custo_km = Decimal("0")
            parada.custo_operacional = _moeda(
                valor_base * Decimal(parada.tentativas)
            )
            parada.custo_calculado_em = momento
        elif modelo == "sem_configuracao":
            parada.distancia_custo_km = Decimal("0")
            parada.custo_operacional = Decimal("0")
            parada.custo_calculado_em = momento
        else:
            # Por KM: a taxa fica congelada agora; distancia/custo fecham no fim.
            parada.distancia_custo_km = None
            parada.custo_operacional = None
            parada.custo_calculado_em = None


def _ratear(
    total: Decimal,
    pesos: Sequence[Decimal],
    *,
    quantum: Decimal,
) -> list[Decimal]:
    if not pesos:
        return []

    total = max(_decimal(total), Decimal("0")).quantize(
        quantum, rounding=ROUND_HALF_UP
    )
    pesos_positivos = [max(_decimal(peso), Decimal("0")) for peso in pesos]
    soma_pesos = sum(pesos_positivos, Decimal("0"))
    if soma_pesos <= 0:
        pesos_positivos = [Decimal("1") for _ in pesos]
        soma_pesos = Decimal(len(pesos_positivos))

    rateio: list[Decimal] = []
    acumulado = Decimal("0")
    for indice, peso in enumerate(pesos_positivos):
        if indice == len(pesos_positivos) - 1:
            parcela = total - acumulado
        else:
            parcela = (total * peso / soma_pesos).quantize(
                quantum, rounding=ROUND_DOWN
            )
            acumulado += parcela
        rateio.append(parcela.quantize(quantum, rounding=ROUND_HALF_UP))
    return rateio


def consolidar_custos_por_entrega(
    paradas: Sequence[RotaEntregaParada],
    entregador: Cliente | None,
    *,
    distancia_total_km: Decimal,
    custo_moto_total: Decimal = Decimal("0"),
    calculado_em: datetime | None = None,
) -> CustoOperacionalRota:
    """Calcula e grava cada entrega; o total da rota vira a soma das paradas."""
    momento = calculado_em or datetime.now()
    registrar_snapshot_custo_paradas(paradas, entregador, registrado_em=momento)

    distancia_total = max(_decimal(distancia_total_km), Decimal("0"))
    paradas_por_km = [
        parada
        for parada in paradas
        if parada.modelo_custo_operacional == "por_km"
    ]
    if paradas_por_km:
        pesos = [
            _decimal(getattr(parada, "distancia_trecho_real_km", 0))
            for parada in paradas_por_km
        ]
        distancias_rateadas = _ratear(
            distancia_total,
            pesos,
            quantum=MILESIMO_KM,
        )
        taxa_padrao = _decimal(
            paradas_por_km[0].valor_base_custo_operacional
        )
        custo_km_total = _moeda(distancia_total * taxa_padrao)
        custos_rateados = _ratear(custo_km_total, pesos, quantum=CENTAVO)

        for parada, distancia, custo in zip(
            paradas_por_km, distancias_rateadas, custos_rateados
        ):
            parada.distancia_custo_km = distancia
            parada.custo_operacional = custo
            parada.custo_calculado_em = momento

    for parada in paradas:
        if parada.modelo_custo_operacional in {"taxa_fixa", "rateio_rh"}:
            tentativas = max(int(getattr(parada, "tentativas", 1) or 1), 1)
            parada.custo_operacional = _moeda(
                _decimal(parada.valor_base_custo_operacional) * Decimal(tentativas)
            )
            parada.distancia_custo_km = Decimal("0")
            parada.custo_calculado_em = momento
        elif parada.custo_operacional is None:
            parada.custo_operacional = Decimal("0")
            parada.custo_calculado_em = momento

    custo_moto = _moeda(custo_moto_total)
    rateio_moto = _ratear(
        custo_moto,
        [Decimal("1") for _ in paradas],
        quantum=CENTAVO,
    )
    for parada, custo_rateado in zip(paradas, rateio_moto):
        parada.custo_moto_rateado = custo_rateado

    custo_entregador = _moeda(
        sum((_decimal(parada.custo_operacional) for parada in paradas), Decimal("0"))
    )
    custo_total = _moeda(custo_entregador + custo_moto)
    return CustoOperacionalRota(
        custo_entregador=custo_entregador,
        custo_moto=custo_moto,
        custo_total=custo_total,
    )
