"""Motor de calculo de custos do modulo Banho & Tosa.

As funcoes aqui sao puras para facilitar testes, auditoria e reutilizacao em
rotas, jobs, fechamento financeiro e simulacoes de preco.
"""

from dataclasses import asdict, dataclass
from decimal import Decimal, ROUND_HALF_UP
from typing import Iterable, Literal, Optional


CENTAVOS = Decimal("0.01")
QUATRO_CASAS = Decimal("0.0001")

STATUS_FINAIS = {"entregue", "cancelado", "no_show"}


def _decimal(value, default: str = "0") -> Decimal:
    if value is None or value == "":
        return Decimal(default)
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def _moeda(value: Decimal) -> Decimal:
    return value.quantize(CENTAVOS, rounding=ROUND_HALF_UP)


def _percentual(value: Decimal) -> Decimal:
    return value.quantize(QUATRO_CASAS, rounding=ROUND_HALF_UP)


@dataclass(frozen=True)
class InsumoCusto:
    quantidade_usada: Decimal | int | float | str = Decimal("0")
    quantidade_desperdicio: Decimal | int | float | str = Decimal("0")
    custo_unitario_snapshot: Decimal | int | float | str = Decimal("0")


@dataclass(frozen=True)
class EquipamentoUso:
    potencia_watts: Decimal | int | float | str = Decimal("0")
    minutos_uso: Decimal | int | float | str = Decimal("0")
    custo_kwh: Decimal | int | float | str = Decimal("0")
    custo_manutencao_hora: Decimal | int | float | str = Decimal("0")
    kwh_real: Decimal | int | float | str | None = None


@dataclass(frozen=True)
class MaoObraEtapa:
    custo_mensal_funcionario: Decimal | int | float | str = Decimal("0")
    horas_produtivas_mes: Decimal | int | float | str = Decimal("0")
    minutos_trabalhados: Decimal | int | float | str = Decimal("0")


@dataclass(frozen=True)
class ComissaoRegra:
    modelo: Literal["nenhum", "percentual_valor", "valor_fixo", "percentual_margem"] = "nenhum"
    valor_base: Decimal | int | float | str = Decimal("0")
    percentual: Decimal | int | float | str = Decimal("0")
    valor_fixo: Decimal | int | float | str = Decimal("0")


@dataclass(frozen=True)
class TaxiDogCusto:
    km_real: Decimal | int | float | str = Decimal("0")
    custo_km: Decimal | int | float | str = Decimal("0")
    custo_motorista: Decimal | int | float | str = Decimal("0")
    rateio_manutencao: Decimal | int | float | str = Decimal("0")
    custo_real_informado: Decimal | int | float | str | None = None


@dataclass(frozen=True)
class CustoSnapshot:
    valor_cobrado: Decimal
    custo_insumos: Decimal
    custo_agua: Decimal
    custo_energia: Decimal
    custo_mao_obra: Decimal
    custo_comissao: Decimal
    custo_taxi_dog: Decimal
    custo_taxas_pagamento: Decimal
    custo_rateio_operacional: Decimal
    custo_total: Decimal
    margem_valor: Decimal
    margem_percentual: Decimal

    def as_dict(self) -> dict[str, Decimal]:
        return asdict(self)


def calcular_custo_insumos(insumos: Iterable[InsumoCusto]) -> Decimal:
    total = Decimal("0")
    for item in insumos:
        quantidade = _decimal(item.quantidade_usada) + _decimal(item.quantidade_desperdicio)
        total += quantidade * _decimal(item.custo_unitario_snapshot)
    return _moeda(total)


def calcular_custo_agua(
    *,
    custo_litro_agua,
    vazao_chuveiro_litros_min=None,
    minutos_banho=None,
    litros_usados=None,
    agua_padrao_litros=None,
) -> Decimal:
    if litros_usados is not None:
        litros = _decimal(litros_usados)
    elif minutos_banho is not None:
        litros = _decimal(vazao_chuveiro_litros_min) * _decimal(minutos_banho)
    else:
        litros = _decimal(agua_padrao_litros)

    return _moeda(litros * _decimal(custo_litro_agua))


def calcular_custo_energia(usos: Iterable[EquipamentoUso]) -> Decimal:
    total = Decimal("0")
    for uso in usos:
        minutos = _decimal(uso.minutos_uso)
        if uso.kwh_real is not None:
            kwh = _decimal(uso.kwh_real)
        else:
            kwh = (_decimal(uso.potencia_watts) / Decimal("1000")) * (minutos / Decimal("60"))
        manutencao = _decimal(uso.custo_manutencao_hora) * (minutos / Decimal("60"))
        total += (kwh * _decimal(uso.custo_kwh)) + manutencao
    return _moeda(total)


def calcular_custo_mao_obra(etapas: Iterable[MaoObraEtapa]) -> Decimal:
    total = Decimal("0")
    for etapa in etapas:
        horas_produtivas = _decimal(etapa.horas_produtivas_mes)
        if horas_produtivas <= 0:
            continue
        custo_hora = _decimal(etapa.custo_mensal_funcionario) / horas_produtivas
        total += custo_hora * (_decimal(etapa.minutos_trabalhados) / Decimal("60"))
    return _moeda(total)


def calcular_custo_mensal_colaborador(
    *,
    salario_base,
    inss_patronal_percentual=0,
    fgts_percentual=0,
    gera_ferias=True,
    gera_decimo_terceiro=True,
) -> Decimal:
    salario = _decimal(salario_base)
    encargos = salario * (_decimal(inss_patronal_percentual) + _decimal(fgts_percentual)) / Decimal("100")
    provisoes = Decimal("0")
    if gera_ferias:
        provisoes += salario / Decimal("12")
        provisoes += salario / Decimal("36")
    if gera_decimo_terceiro:
        provisoes += salario / Decimal("12")
    return _moeda(salario + encargos + provisoes)


def calcular_custo_comissao(regra: ComissaoRegra) -> Decimal:
    modelo = regra.modelo or "nenhum"
    if modelo == "percentual_valor":
        return _moeda(_decimal(regra.valor_base) * _decimal(regra.percentual) / Decimal("100"))
    if modelo == "percentual_margem":
        return _moeda(_decimal(regra.valor_base) * _decimal(regra.percentual) / Decimal("100"))
    if modelo == "valor_fixo":
        return _moeda(_decimal(regra.valor_fixo))
    return Decimal("0.00")


def calcular_custo_taxi_dog(custo: TaxiDogCusto) -> Decimal:
    if custo.custo_real_informado is not None:
        return _moeda(_decimal(custo.custo_real_informado))
    total = (
        _decimal(custo.km_real) * _decimal(custo.custo_km)
        + _decimal(custo.custo_motorista)
        + _decimal(custo.rateio_manutencao)
    )
    return _moeda(total)


def calcular_snapshot_custo(
    *,
    valor_cobrado,
    custo_insumos=0,
    custo_agua=0,
    custo_energia=0,
    custo_mao_obra=0,
    custo_comissao=0,
    custo_taxi_dog=0,
    custo_taxas_pagamento=0,
    custo_rateio_operacional=0,
) -> CustoSnapshot:
    valor = _moeda(_decimal(valor_cobrado))
    custos = {
        "custo_insumos": _moeda(_decimal(custo_insumos)),
        "custo_agua": _moeda(_decimal(custo_agua)),
        "custo_energia": _moeda(_decimal(custo_energia)),
        "custo_mao_obra": _moeda(_decimal(custo_mao_obra)),
        "custo_comissao": _moeda(_decimal(custo_comissao)),
        "custo_taxi_dog": _moeda(_decimal(custo_taxi_dog)),
        "custo_taxas_pagamento": _moeda(_decimal(custo_taxas_pagamento)),
        "custo_rateio_operacional": _moeda(_decimal(custo_rateio_operacional)),
    }
    custo_total = _moeda(sum(custos.values(), Decimal("0")))
    margem_valor = _moeda(valor - custo_total)
    margem_percentual = Decimal("0.0000") if valor == 0 else _percentual((margem_valor / valor) * Decimal("100"))

    return CustoSnapshot(
        valor_cobrado=valor,
        custo_total=custo_total,
        margem_valor=margem_valor,
        margem_percentual=margem_percentual,
        **custos,
    )


def validar_transicao_status(
    status_atual: Optional[str],
    novo_status: str,
    *,
    permitir_reabrir_finalizado: bool = False,
) -> str:
    atual = (status_atual or "").strip().lower()
    novo = (novo_status or "").strip().lower()
    if not novo:
        raise ValueError("Informe o novo status do atendimento.")
    if atual == novo:
        return novo
    if atual in STATUS_FINAIS and not permitir_reabrir_finalizado:
        raise ValueError("Atendimento finalizado nao pode ser reaberto sem permissao de gestor.")
    return novo
