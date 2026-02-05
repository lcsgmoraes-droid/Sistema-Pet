from decimal import Decimal
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


def calcular_custo_entrega(entregador: Cliente, km: Decimal, tentativas: int, moto_da_loja: bool) -> Decimal:
    """
    Calcula o custo REAL da entrega (gerencial).
    """
    if km is None:
        km = Decimal("0")

    # 1️⃣ RATEIO RH (FUNCIONÁRIO)
    if entregador.controla_rh:
        if not entregador.media_entregas_configurada or entregador.media_entregas_configurada == 0:
            custo_base = Decimal("0")
        else:
            custo_mensal = entregador.custo_rh_ajustado or calcular_custo_total_funcionario(entregador)
            custo_base = custo_mensal / Decimal(entregador.media_entregas_configurada)

    # 2️⃣ TAXA FIXA
    elif entregador.modelo_custo_entrega == "taxa_fixa":
        custo_base = entregador.taxa_fixa_entrega or Decimal("0")

    # 3️⃣ POR KM
    elif entregador.modelo_custo_entrega == "por_km":
        custo_base = (entregador.valor_por_km_entrega or Decimal("0")) * km

    else:
        custo_base = Decimal("0")

    custo_total = custo_base * Decimal(tentativas)

    # ➕ CUSTO DA MOTO DA LOJA
    if moto_da_loja:
        custo_total += calcular_custo_moto(km)

    return custo_total
