from datetime import date
from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.financeiro.crediario_parcelamento import (
    gerar_vencimentos_crediario,
    montar_plano_crediario,
    normalizar_intervalo_crediario,
)
from app.financeiro.contas_receber_service import ContasReceberService


class _FakeSession:
    def __init__(self):
        self.added = []

    def add(self, item):
        item.id = len(self.added) + 1
        self.added.append(item)

    def flush(self):
        return None


def test_gera_intervalos_fixos_de_sete_e_quinze_dias():
    primeira = date(2026, 9, 5)

    assert gerar_vencimentos_crediario(primeira, 3, "7_dias") == [
        date(2026, 9, 5),
        date(2026, 9, 12),
        date(2026, 9, 19),
    ]
    assert gerar_vencimentos_crediario(primeira, 3, "15_dias") == [
        date(2026, 9, 5),
        date(2026, 9, 20),
        date(2026, 10, 5),
    ]


def test_mensal_preserva_dia_original_apos_mes_curto():
    assert gerar_vencimentos_crediario(date(2027, 1, 31), 4, "mensal") == [
        date(2027, 1, 31),
        date(2027, 2, 28),
        date(2027, 3, 31),
        date(2027, 4, 30),
    ]


def test_plano_preserva_total_e_ultima_parcela_absorve_centavos():
    plano = montar_plano_crediario(
        valor_total=Decimal("200.00"),
        numero_parcelas=3,
        primeira_data=date(2026, 9, 5),
        intervalo="mensal",
    )

    assert [item["valor"] for item in plano] == [
        Decimal("66.67"),
        Decimal("66.67"),
        Decimal("66.66"),
    ]
    assert sum(item["valor"] for item in plano) == Decimal("200.00")
    assert [item["data_vencimento"] for item in plano] == [
        date(2026, 9, 5),
        date(2026, 10, 5),
        date(2026, 11, 5),
    ]


def test_uma_parcela_nao_exige_intervalo_e_intervalo_invalido_falha():
    assert normalizar_intervalo_crediario(None, numero_parcelas=1) is None
    with pytest.raises(ValueError, match="Intervalo do crediario invalido"):
        normalizar_intervalo_crediario("30_dias", numero_parcelas=2)


def test_contas_receber_sao_gravadas_com_valores_datas_e_identificacao_da_parcela():
    db = _FakeSession()
    resultado = ContasReceberService._criar_contas_parceladas(
        venda=SimpleNamespace(
            id=77,
            numero_venda="VD-77",
            cliente_id=12,
            canal="app_funcionario",
            tenant_id="tenant-teste",
        ),
        pagamento=SimpleNamespace(
            valor=Decimal("200.00"),
            data_recebimento_prevista=date(2027, 1, 31),
            intervalo_crediario="mensal",
        ),
        forma_pag=SimpleNamespace(id=9, tipo="crediario"),
        numero_parcelas=3,
        categoria_receitas=SimpleNamespace(id=1),
        user_id=4,
        db=db,
    )

    assert resultado["contas_ids"] == [1, 2, 3]
    assert [conta.descricao for conta in db.added] == [
        "Venda VD-77 - Parcela 1/3",
        "Venda VD-77 - Parcela 2/3",
        "Venda VD-77 - Parcela 3/3",
    ]
    assert [conta.valor_final for conta in db.added] == [
        Decimal("66.67"),
        Decimal("66.67"),
        Decimal("66.66"),
    ]
    assert [conta.data_vencimento for conta in db.added] == [
        date(2027, 1, 31),
        date(2027, 2, 28),
        date(2027, 3, 31),
    ]


def test_crediario_com_vencimento_hoje_permanece_pendente():
    db = _FakeSession()
    ContasReceberService._criar_conta_simples(
        venda=SimpleNamespace(
            id=88,
            numero_venda="VD-88",
            cliente_id=12,
            canal="loja_fisica",
            tenant_id="tenant-teste",
        ),
        pagamento={
            "forma_pagamento": "Crediário",
            "valor": Decimal("50.00"),
            "prazo_recebimento_dias": 0,
            "data_recebimento_prevista": date.today(),
        },
        forma_pag=SimpleNamespace(id=9, tipo="crediario", prazo_dias=0),
        categoria_receitas=SimpleNamespace(id=1),
        user_id=4,
        db=db,
    )

    assert len(db.added) == 1
    assert db.added[0].status == "pendente"
    assert db.added[0].valor_recebido == Decimal("0")
    assert db.added[0].data_recebimento is None
