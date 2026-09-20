from datetime import date, datetime
from types import SimpleNamespace

import os

os.environ["DATABASE_URL"] = os.environ.get("DATABASE_URL") or "sqlite:///./test.db"
os.environ["DEBUG"] = "false"

from app.estoque.transferencia_parceiro_extrato_service import (
    montar_extrato_transferencia_parceiro,
)


def _conta(
    conta_id,
    valor,
    emissao,
    *,
    recebido=0,
    recebimentos=None,
    status="pendente",
    data_recebimento=None,
):
    return SimpleNamespace(
        id=conta_id,
        documento=f"TRP-{conta_id}",
        valor_original=valor,
        valor_final=valor,
        valor_recebido=recebido,
        data_emissao=emissao,
        data_vencimento=emissao,
        data_recebimento=data_recebimento,
        created_at=datetime.combine(emissao, datetime.min.time()),
        updated_at=datetime.combine(data_recebimento or emissao, datetime.min.time()),
        status=status,
        observacoes=None,
        recebimentos=recebimentos or [],
        cliente=SimpleNamespace(nome="Veterinaria Dra. Maiara"),
    )


def test_extrato_unifica_dividas_pagamentos_e_devolucoes_com_saldo_corrido():
    recebimento = SimpleNamespace(
        id=90,
        valor_recebido=40,
        data_recebimento=date(2026, 9, 3),
        created_at=datetime(2026, 9, 3, 10, 0),
        forma_pagamento=SimpleNamespace(nome="Pix"),
        observacoes="Recebimento 03/09/2026: R$ 40,00",
    )
    contas = [
        _conta(
            1,
            100,
            date(2026, 9, 1),
            recebido=60,
            recebimentos=[recebimento],
            status="parcial",
            data_recebimento=date(2026, 9, 4),
        ),
        _conta(2, 50, date(2026, 9, 2)),
    ]
    resumos = {
        1: {
            "devolucoes": [
                {
                    "movimentacao_id": 80,
                    "produto_nome": "Racao",
                    "quantidade": 2,
                    "valor_total": 20,
                    "registrado_em": datetime(2026, 9, 4, 14, 0),
                    "observacao": "Produto devolvido 04/09/2026: R$ 20,00",
                }
            ]
        }
    }

    extrato = montar_extrato_transferencia_parceiro(
        parceiro_id=8406,
        contas=contas,
        itens_por_conta={
            1: [
                SimpleNamespace(
                    produto_id=10, produto_nome="Racao", quantidade=10, valor_total=100
                )
            ],
            2: [],
        },
        resumos_devolucao=resumos,
    )

    assert [item.tipo for item in reversed(extrato.items)] == [
        "divida",
        "divida",
        "pagamento",
        "devolucao",
    ]
    assert [item.saldo for item in reversed(extrato.items)] == [100, 150, 110, 90]
    assert extrato.totais.total_debitos == 150
    assert extrato.totais.total_creditos == 60
    assert extrato.totais.saldo_final == 90
    assert extrato.totais.documentos_em_aberto == 2


def test_extrato_de_periodo_informa_saldo_anterior_e_movimentos_do_intervalo():
    recebimento = SimpleNamespace(
        id=91,
        valor_recebido=25,
        data_recebimento=date(2026, 9, 10),
        created_at=datetime(2026, 9, 10, 12, 0),
        forma_pagamento=SimpleNamespace(nome="Dinheiro"),
        observacoes=None,
    )
    conta = _conta(
        3,
        100,
        date(2026, 8, 20),
        recebido=25,
        recebimentos=[recebimento],
        status="parcial",
        data_recebimento=date(2026, 9, 10),
    )

    extrato = montar_extrato_transferencia_parceiro(
        parceiro_id=8406,
        contas=[conta],
        itens_por_conta={},
        resumos_devolucao={},
        data_inicio=date(2026, 9, 1),
        data_fim=date(2026, 9, 30),
    )

    assert extrato.totais.saldo_anterior == 100
    assert extrato.totais.total_debitos == 0
    assert extrato.totais.total_creditos == 25
    assert extrato.totais.saldo_final == 75
    assert len(extrato.items) == 1
    assert extrato.items[0].tipo == "pagamento"


def test_extrato_representa_baixa_legada_e_cancelamento_sem_perder_conciliacao():
    conta_legada = _conta(
        4,
        100,
        date(2026, 8, 1),
        recebido=30,
        status="parcial",
        data_recebimento=date(2026, 8, 5),
    )
    conta_cancelada = _conta(5, 50, date(2026, 8, 2), status="cancelado")

    extrato = montar_extrato_transferencia_parceiro(
        parceiro_id=8406,
        contas=[conta_legada, conta_cancelada],
        itens_por_conta={},
        resumos_devolucao={},
    )

    tipos = [item.tipo for item in extrato.items]
    assert "ajuste" in tipos
    assert "cancelamento" in tipos
    assert extrato.totais.saldo_final == 70
