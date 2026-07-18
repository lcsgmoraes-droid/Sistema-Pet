from decimal import Decimal, ROUND_HALF_UP
from app.models import Cliente


def calcular_custo_total_funcionario(entregador: Cliente) -> Decimal:
    """
    Retorna o custo mensal total do funcionário.
    Stub por enquanto.
    """
    # FUTURO: buscar salário + encargos + benefícios
    return Decimal("0.00")


def calcular_custo_moto(km: Decimal) -> Decimal:
    """
    Custo operacional da moto da loja (stub).
    """
    # FUTURO: combustível, manutenção, etc
    return Decimal("0.00")


def calcular_custo_entrega(
    entregador: Cliente | None,
    km: Decimal,
    tentativas: int,
    moto_da_loja: bool,
    quantidade_entregas: int = 1,
) -> Decimal:
    """
    Calcula o custo REAL da rota (gerencial).

    Custos de RH e taxa fixa sao definidos por entrega e, por isso, sao
    multiplicados pela quantidade de entregas da rota mais eventuais tentativas
    extras. O modelo por KM usa a distancia total real percorrida e nao deve ser
    multiplicado novamente.
    """
    km = max(Decimal(str(km or 0)), Decimal("0"))
    tentativas = max(int(tentativas or 1), 1)
    quantidade_entregas = max(int(quantidade_entregas or 1), 1)
    multiplicar_por_entregas = False

    if entregador is None:
        custo_base = Decimal("0")

    # 1️⃣ RATEIO RH (FUNCIONÁRIO)
    elif entregador.controla_rh:
        if (
            not entregador.media_entregas_configurada
            or entregador.media_entregas_configurada == 0
        ):
            custo_base = Decimal("0")
        else:
            custo_mensal = (
                entregador.custo_rh_ajustado
                or calcular_custo_total_funcionario(entregador)
            )
            custo_base = custo_mensal / Decimal(entregador.media_entregas_configurada)
            multiplicar_por_entregas = True

    # 2️⃣ TAXA FIXA
    elif entregador.modelo_custo_entrega == "taxa_fixa":
        custo_base = entregador.taxa_fixa_entrega or Decimal("0")
        multiplicar_por_entregas = True

    # 3️⃣ POR KM
    elif entregador.modelo_custo_entrega == "por_km":
        custo_base = (entregador.valor_por_km_entrega or Decimal("0")) * km

    else:
        custo_base = Decimal("0")

    if multiplicar_por_entregas:
        tentativas_extras = max(tentativas - 1, 0)
        custo_base *= Decimal(quantidade_entregas + tentativas_extras)

    custo_total = custo_base

    # ➕ CUSTO DA MOTO DA LOJA
    if moto_da_loja:
        custo_total += calcular_custo_moto(km)

    return custo_total.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
