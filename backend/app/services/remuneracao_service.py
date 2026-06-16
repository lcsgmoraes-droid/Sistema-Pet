from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from typing import Any


MONEY = Decimal("0.01")
REGIMES_SEM_ENCARGOS = {"sem_encargos", "estagio", "informal"}


def _decimal(value: Any, default: Decimal = Decimal("0.00")) -> Decimal:
    if value is None:
        return default
    try:
        return Decimal(str(value))
    except Exception:
        return default


def _money(value: Any) -> Decimal:
    return _decimal(value).quantize(MONEY, rounding=ROUND_HALF_UP)


def _percentual(valor_base: Decimal, percentual: Any) -> Decimal:
    return _money(valor_base * _decimal(percentual) / Decimal("100"))


def _attr(obj: Any, name: str, default: Any = None) -> Any:
    return getattr(obj, name, default)


def _regime(cargo: Any) -> str:
    return str(_attr(cargo, "regime_remuneracao", "clt") or "clt").strip().lower()


def _usa_encargos(cargo: Any) -> bool:
    if _regime(cargo) in REGIMES_SEM_ENCARGOS:
        return False
    return bool(_attr(cargo, "gera_encargos", True))


def calcular_composicao_remuneracao(
    cargo: Any, funcionario: Any | None = None
) -> dict[str, Decimal | str | bool]:
    """Calcula composicao gerencial mensal de remuneracao.

    O salario base representa a folha/holerite. Descontos do funcionario reduzem
    o liquido do holerite, mas nao reduzem o custo bruto de folha. O complemento
    interno cobre a diferenca entre o liquido combinado e o liquido do holerite.
    """

    funcionario = funcionario or object()
    salario_base = _money(
        _attr(funcionario, "salario_base_override", None)
        or _attr(cargo, "salario_base", 0)
    )
    regime = _regime(cargo)
    usa_encargos = _usa_encargos(cargo)

    if usa_encargos:
        inss_funcionario_valor = _money(_attr(cargo, "inss_funcionario_valor", 0))
        if inss_funcionario_valor == Decimal("0.00"):
            inss_funcionario_valor = _percentual(
                salario_base, _attr(cargo, "inss_funcionario_percentual", 0)
            )
        desconto_transporte = _money(_attr(cargo, "desconto_transporte_valor", 0))
        outros_descontos = _money(_attr(cargo, "outros_descontos_valor", 0))
    else:
        inss_funcionario_valor = Decimal("0.00")
        desconto_transporte = Decimal("0.00")
        outros_descontos = Decimal("0.00")

    descontos_total = _money(
        inss_funcionario_valor + desconto_transporte + outros_descontos
    )
    liquido_holerite = _money(salario_base - descontos_total)

    complemento_modo = (
        str(_attr(funcionario, "complemento_modo", "automatico") or "automatico")
        .strip()
        .lower()
    )
    liquido_combinado = _attr(funcionario, "liquido_combinado", None)
    complemento_fixo = _money(_attr(funcionario, "complemento_fixo_valor", 0))

    if complemento_modo == "manual":
        complemento_interno = complemento_fixo
    elif complemento_modo == "nenhum":
        complemento_interno = Decimal("0.00")
    elif liquido_combinado is not None:
        complemento_interno = max(
            Decimal("0.00"), _money(liquido_combinado) - liquido_holerite
        )
    else:
        complemento_interno = Decimal("0.00")

    if usa_encargos:
        inss_patronal = _percentual(
            salario_base, _attr(cargo, "inss_patronal_percentual", 0)
        )
        fgts_empresa = _percentual(salario_base, _attr(cargo, "fgts_percentual", 0))
        provisao_ferias = (
            _money(salario_base / Decimal("12"))
            if bool(_attr(cargo, "gera_ferias", True))
            else Decimal("0.00")
        )
        provisao_terco_ferias = (
            _money(salario_base / Decimal("36"))
            if bool(_attr(cargo, "gera_ferias", True))
            else Decimal("0.00")
        )
        provisao_13 = (
            _money(salario_base / Decimal("12"))
            if bool(_attr(cargo, "gera_decimo_terceiro", True))
            else Decimal("0.00")
        )
    else:
        inss_patronal = Decimal("0.00")
        fgts_empresa = Decimal("0.00")
        provisao_ferias = Decimal("0.00")
        provisao_terco_ferias = Decimal("0.00")
        provisao_13 = Decimal("0.00")

    encargos_total = _money(inss_patronal + fgts_empresa)
    provisoes_total = _money(provisao_ferias + provisao_terco_ferias + provisao_13)
    custo_total = _money(
        salario_base + complemento_interno + encargos_total + provisoes_total
    )

    return {
        "regime_remuneracao": regime,
        "usa_encargos": usa_encargos,
        "salario_base": salario_base,
        "inss_funcionario": inss_funcionario_valor,
        "desconto_transporte": desconto_transporte,
        "outros_descontos": outros_descontos,
        "descontos_funcionario_total": descontos_total,
        "liquido_holerite": liquido_holerite,
        "liquido_combinado": _money(liquido_combinado)
        if liquido_combinado is not None
        else Decimal("0.00"),
        "complemento_modo": complemento_modo,
        "complemento_interno": complemento_interno,
        "inss_patronal": inss_patronal,
        "fgts_empresa": fgts_empresa,
        "encargos_empresa_total": encargos_total,
        "provisao_ferias": provisao_ferias,
        "provisao_terco_ferias": provisao_terco_ferias,
        "provisao_13": provisao_13,
        "provisoes_total": provisoes_total,
        "custo_total_empresa": custo_total,
    }
