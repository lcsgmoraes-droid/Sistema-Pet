from datetime import date
from decimal import Decimal
from types import SimpleNamespace

from app.banho_tosa_pacotes import (
    calcular_saldo_creditos,
    calcular_validade_pacote,
    credito_disponivel,
)


def test_calcula_saldo_creditos_sem_ficar_negativo():
    assert calcular_saldo_creditos("4", "1", "0") == Decimal("3")
    assert calcular_saldo_creditos("4", "6", "0") == Decimal("0")


def test_calcula_validade_do_pacote_por_data_inicio():
    assert calcular_validade_pacote(date(2026, 4, 26), 90) == date(2026, 7, 25)


def test_credito_disponivel_considera_status_validade_e_saldo():
    credito = SimpleNamespace(
        status="ativo",
        data_validade=date(2026, 5, 26),
        creditos_total=Decimal("4"),
        creditos_usados=Decimal("3"),
        creditos_cancelados=Decimal("0"),
    )

    assert credito_disponivel(credito, hoje=date(2026, 4, 26)) is True

    credito.creditos_usados = Decimal("4")
    assert credito_disponivel(credito, hoje=date(2026, 4, 26)) is False
