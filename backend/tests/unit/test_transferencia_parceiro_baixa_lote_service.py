from datetime import date
from decimal import Decimal
from types import SimpleNamespace
import os

import pytest
from fastapi import HTTPException

os.environ["DATABASE_URL"] = os.environ.get("DATABASE_URL") or "sqlite:///./test.db"
os.environ["DEBUG"] = "false"

from app.estoque.transferencia_parceiro_baixa_lote_service import (
    aplicar_baixa_lote_transferencia,
    criar_conta_pagar_acerto_lote,
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


class _FakeSession:
    def __init__(self):
        self.added = []

    def add(self, item):
        self.added.append(item)

    def flush(self):
        for index, item in enumerate(self.added, start=1):
            if getattr(item, "id", None) is None:
                item.id = index


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


def test_criar_conta_pagar_acerto_lote_vincula_parceiro_e_valor_total():
    db = _FakeSession()
    payload = SimpleNamespace(
        descricao="Compra mercadoria parceira",
        valor=250,
        data_vencimento=date(2026, 7, 10),
        documento="ACERTO-1",
        observacao="Produtos pegos no parceiro",
        categoria_id=None,
        dre_subcategoria_id=None,
        tipo_despesa_id=None,
    )

    conta = criar_conta_pagar_acerto_lote(
        db,
        tenant_id="tenant-1",
        parceiro_id=8406,
        user_id=99,
        data_emissao=date(2026, 7, 1),
        payload=payload,
        documento_lote="TRP-LOTE-1",
    )

    assert conta.id == 1
    assert conta.fornecedor_id == 8406
    assert conta.valor_original == Decimal("250.00")
    assert conta.valor_final == Decimal("250.00")
    assert conta.valor_pago == Decimal("0.00")
    assert conta.status == "pendente"
    assert conta.documento == "ACERTO-1"
    assert "TRP-LOTE-1" in conta.observacoes


def test_nova_conta_pagar_acerto_so_pode_ser_usada_no_modo_acerto():
    payload = SimpleNamespace(
        modo_baixa="recebimento",
        nova_conta_pagar_acerto=SimpleNamespace(valor=100),
        aplicacoes=[],
    )

    with pytest.raises(HTTPException) as exc_info:
        aplicar_baixa_lote_transferencia(
            _FakeSession(),
            tenant_id="tenant-1",
            user_id=99,
            payload=payload,
        )

    assert exc_info.value.status_code == 400
    assert "modo acerto" in exc_info.value.detail.lower()
