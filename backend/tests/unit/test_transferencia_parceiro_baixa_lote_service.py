from datetime import date
from decimal import Decimal
from types import SimpleNamespace
import os

import pytest
from fastapi import HTTPException

os.environ["DATABASE_URL"] = os.environ.get("DATABASE_URL") or "sqlite:///./test.db"
os.environ["DEBUG"] = "false"

from app.estoque.transferencia_parceiro_baixa_lote_service import (
    distribuir_baixa_transferencias,
    normalizar_modo_baixa_lote,
    resolver_data_recebimento_financeiro,
    validar_devolucao_estoque_integral,
)


def _conta(conta_id, data_emissao, saldo_aberto, valor_recebido=0):
    return SimpleNamespace(
        id=conta_id,
        data_emissao=date.fromisoformat(data_emissao),
        data_vencimento=date.fromisoformat(data_emissao),
        valor_original=Decimal(str(saldo_aberto)) + Decimal(str(valor_recebido)),
        valor_final=Decimal(str(saldo_aberto)) + Decimal(str(valor_recebido)),
        valor_recebido=Decimal(str(valor_recebido)),
        documento=f"TRP-{conta_id}",
    )


def test_distribuir_valor_mais_antigo_primeiro_deixa_ultima_parcial():
    contas = [
        _conta(1, "2026-06-01", 400),
        _conta(2, "2026-06-02", 400),
        _conta(3, "2026-06-03", 400),
    ]

    resultado = distribuir_baixa_transferencias(contas, 1000, ordem="antiga")

    assert [
        (item["conta_receber_id"], item["valor_baixado"]) for item in resultado
    ] == [
        (1, Decimal("400.00")),
        (2, Decimal("400.00")),
        (3, Decimal("200.00")),
    ]


def test_distribuir_valor_mais_novo_primeiro_respeita_ordem_descendente():
    contas = [
        _conta(1, "2026-06-01", 400),
        _conta(2, "2026-06-02", 400),
        _conta(3, "2026-06-03", 400),
    ]

    resultado = distribuir_baixa_transferencias(contas, 700, ordem="nova")

    assert [
        (item["conta_receber_id"], item["valor_baixado"]) for item in resultado
    ] == [
        (3, Decimal("400.00")),
        (2, Decimal("300.00")),
    ]


def test_distribuir_valor_ignora_conta_sem_saldo_aberto():
    contas = [
        _conta(1, "2026-06-01", 0, valor_recebido=400),
        _conta(2, "2026-06-02", 400),
    ]

    resultado = distribuir_baixa_transferencias(contas, 150, ordem="antiga")

    assert resultado == [
        {
            "conta_receber_id": 2,
            "valor_baixado": Decimal("150.00"),
            "saldo_anterior": Decimal("400.00"),
            "saldo_restante": Decimal("250.00"),
        }
    ]


def test_produto_devolvido_com_estoque_rejeita_baixa_parcial():
    conta = _conta(1, "2026-06-01", 400)

    with pytest.raises(HTTPException) as exc_info:
        validar_devolucao_estoque_integral(conta, Decimal("200.00"))

    assert exc_info.value.status_code == 400
    assert "devolucao com entrada no estoque" in exc_info.value.detail.lower()


def test_normalizar_modo_baixa_lote_aceita_produto_devolvido():
    assert normalizar_modo_baixa_lote("produto_devolvido") == "produto_devolvido"


def test_resolver_data_recebimento_financeiro_respeita_prazo_cartao():
    forma = SimpleNamespace(
        tipo="cartao_credito",
        prazo_recebimento=30,
        prazo_dias=30,
        dias_recebimento_antecipado=None,
    )

    data_resolvida = resolver_data_recebimento_financeiro(
        date(2026, 7, 1),
        forma,
    )

    assert data_resolvida == date(2026, 7, 31)


def test_resolver_data_recebimento_financeiro_prefere_antecipacao_configurada():
    forma = SimpleNamespace(
        tipo="cartao_credito",
        prazo_recebimento=30,
        prazo_dias=30,
        dias_recebimento_antecipado=2,
    )

    data_resolvida = resolver_data_recebimento_financeiro(
        date(2026, 7, 1),
        forma,
    )

    assert data_resolvida == date(2026, 7, 3)
