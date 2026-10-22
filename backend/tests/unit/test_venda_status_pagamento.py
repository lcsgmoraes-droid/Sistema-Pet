from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from app.vendas.status_pagamento import calcular_resumo_pagamento_venda


def _conta(
    *,
    valor_final=50,
    valor_recebido=0,
    status="pendente",
    forma_pagamento_id=10,
):
    return SimpleNamespace(
        valor_final=valor_final,
        valor_recebido=valor_recebido,
        status=status,
        forma_pagamento_id=forma_pagamento_id,
    )


def _pagamento(*, valor, forma_pagamento, forma_pagamento_id=10, status="pendente"):
    return SimpleNamespace(
        valor=valor,
        forma_pagamento=forma_pagamento,
        forma_pagamento_id=forma_pagamento_id,
        intervalo_crediario=None,
        status=status,
    )


@pytest.mark.parametrize("forma_pagamento", ["Débito", "Crédito", "PIX", "Dinheiro"])
def test_pagamento_do_cliente_fica_pago_mesmo_com_repasse_pendente(forma_pagamento):
    resumo = calcular_resumo_pagamento_venda(
        total=31.90,
        contas_receber=[_conta(valor_final=31.90, valor_recebido=0, status="pendente")],
        pagamentos=[_pagamento(valor=31.90, forma_pagamento=forma_pagamento)],
    )

    assert resumo["status_pagamento"] == "pago"
    assert resumo["valor_pago"] == Decimal("31.90")
    assert resumo["valor_restante"] == 0


@pytest.mark.parametrize("legado", [False, True])
@pytest.mark.parametrize(
    "total, recebido, status, restante",
    [
        ("1.00", "0.99", "parcial", "0.01"),
        ("1.00", "0.01", "parcial", "0.99"),
        ("0.01", "0.00", "em_aberto", "0.01"),
        ("0.01", "0.01", "pago", "0.00"),
    ],
)
def test_status_preserva_centavo_a_receber_e_centavo_pago(
    legado, total, recebido, status, restante
):
    resumo = calcular_resumo_pagamento_venda(
        total=Decimal(total),
        pagamentos=[]
        if legado
        else [_pagamento(valor=Decimal(recebido), forma_pagamento="PIX")],
        contas_receber=[_conta(valor_recebido=Decimal(recebido))] if legado else [],
    )

    assert resumo["status_pagamento"] == status
    assert resumo["valor_pago"] == Decimal(recebido)
    assert resumo["valor_restante"] == Decimal(restante)


def test_crediario_aberto_nao_conta_plano_como_pagamento():
    resumo = calcular_resumo_pagamento_venda(
        total=100,
        contas_receber=[_conta(), _conta()],
        pagamentos=[_pagamento(valor=100, forma_pagamento="Crediário")],
    )

    assert resumo["status_pagamento"] == "em_aberto"
    assert resumo["valor_pago"] == 0
    assert resumo["valor_restante"] == 100
    assert resumo["total_recebido"] == 0


def test_crediario_fica_parcial_depois_da_primeira_baixa():
    resumo = calcular_resumo_pagamento_venda(
        total=100,
        contas_receber=[
            _conta(valor_final=50, valor_recebido=20, status="parcial"),
            _conta(),
        ],
        pagamentos=[_pagamento(valor=100, forma_pagamento="Crediário")],
    )

    assert resumo["status_pagamento"] == "parcial"
    assert resumo["valor_pago"] == 20
    assert resumo["valor_restante"] == 80


def test_crediario_fica_pago_quando_todas_as_parcelas_forem_baixadas():
    resumo = calcular_resumo_pagamento_venda(
        total=100,
        contas_receber=[
            _conta(valor_final=50, valor_recebido=50, status="recebido"),
            _conta(valor_final=50, valor_recebido=50, status="recebido"),
        ],
        pagamentos=[_pagamento(valor=100, forma_pagamento="Crediário")],
    )

    assert resumo["status_pagamento"] == "pago"
    assert resumo["valor_pago"] == 100
    assert resumo["valor_restante"] == 0


def test_pagamento_misto_soma_parte_imediata_com_baixa_do_crediario():
    resumo = calcular_resumo_pagamento_venda(
        total=100,
        contas_receber=[
            _conta(
                valor_final=30,
                valor_recebido=0,
                status="pendente",
                forma_pagamento_id=20,
            ),
            _conta(
                valor_final=70,
                valor_recebido=20,
                status="parcial",
                forma_pagamento_id=30,
            ),
        ],
        pagamentos=[
            _pagamento(
                valor=30,
                forma_pagamento="Débito",
                forma_pagamento_id=20,
            ),
            _pagamento(
                valor=70,
                forma_pagamento="Crediário",
                forma_pagamento_id=30,
            ),
        ],
    )

    assert resumo["status_pagamento"] == "parcial"
    assert resumo["valor_pago"] == 50
    assert resumo["valor_restante"] == 50


@pytest.mark.parametrize("total", [20, 60, 80])
def test_recebido_historico_preservado_apos_reducao_e_aumento_da_venda(total):
    resumo = calcular_resumo_pagamento_venda(
        total=total,
        pagamentos=[
            _pagamento(valor=40, forma_pagamento="PIX"),
            _pagamento(valor=20, forma_pagamento="PIX"),
        ],
    )

    assert resumo["total_recebido"] == Decimal("60.00")
    assert resumo["valor_pago"] == min(Decimal(total), Decimal("60.00"))
    assert resumo["valor_restante"] == max(Decimal(total) - 60, 0)


def test_recebido_sem_limite_nao_confunde_plano_crediario_com_baixa():
    resumo = calcular_resumo_pagamento_venda(
        total=20,
        contas_receber=[
            _conta(valor_final=70, valor_recebido=20, forma_pagamento_id=30),
            _conta(valor_final=30, valor_recebido=30, forma_pagamento_id=20),
        ],
        pagamentos=[
            _pagamento(valor=30, forma_pagamento="Debito", forma_pagamento_id=20),
            _pagamento(valor=70, forma_pagamento="Crediario", forma_pagamento_id=30),
        ],
    )

    assert resumo["total_recebido"] == Decimal("50.00")
    assert resumo["valor_pago"] == Decimal("20.00")


def test_venda_legada_preserva_recebido_e_ignora_conta_cancelada():
    resumo = calcular_resumo_pagamento_venda(
        total=20,
        contas_receber=[
            _conta(valor_final=60, valor_recebido=60, status="recebido"),
            _conta(valor_final=40, valor_recebido=40, status="cancelado"),
        ],
    )

    assert resumo["total_recebido"] == Decimal("60.00")
    assert resumo["valor_pago"] == Decimal("20.00")


def test_recebido_em_dinheiro_usa_valor_alocado_sem_somar_troco():
    pagamento = _pagamento(valor=60, forma_pagamento="Dinheiro")
    pagamento.valor_recebido = 100
    pagamento.troco = 40
    resumo = calcular_resumo_pagamento_venda(total=20, pagamentos=[pagamento])

    assert resumo["total_recebido"] == Decimal("60.00")


@pytest.mark.parametrize("forma", ["PIX", "Dinheiro", "Crédito"])
def test_contrapartida_do_estorno_desfaz_recebimento_e_preserva_outro_pagamento(forma):
    resumo = calcular_resumo_pagamento_venda(
        total=100,
        pagamentos=[
            _pagamento(valor=40, forma_pagamento="Débito", status="confirmado"),
            _pagamento(valor=60, forma_pagamento=forma, status="confirmado"),
            _pagamento(valor=-60, forma_pagamento=forma, status="confirmado"),
        ],
    )

    assert resumo["total_recebido"] == Decimal("40.00")
    assert resumo["valor_pago"] == Decimal("40.00")
    assert resumo["valor_restante"] == Decimal("60.00")
    assert resumo["status_pagamento"] == "parcial"


def test_contrapartida_do_estorno_integral_reabre_saldo_da_venda():
    resumo = calcular_resumo_pagamento_venda(
        total=100,
        pagamentos=[
            _pagamento(valor=100, forma_pagamento="PIX", status="confirmado"),
            _pagamento(valor=-100, forma_pagamento="PIX", status="confirmado"),
        ],
    )

    assert resumo["total_recebido"] == Decimal("0.00")
    assert resumo["valor_pago"] == Decimal("0.00")
    assert resumo["valor_restante"] == Decimal("100.00")
    assert resumo["status_pagamento"] == "em_aberto"


@pytest.mark.parametrize("status", ["estornado", "recusado", "cancelado", "cancelada"])
def test_pagamento_invalidado_nao_conta_como_recebimento(status):
    resumo = calcular_resumo_pagamento_venda(
        total=20,
        contas_receber=[_conta(valor_final=60, valor_recebido=60, status="recebido")],
        pagamentos=[_pagamento(valor=60, forma_pagamento="PIX", status=status)],
    )

    assert resumo["total_recebido"] == 0
    assert resumo["valor_pago"] == 0
    assert resumo["status_pagamento"] == "em_aberto"


def test_rota_preserva_total_pago_e_expoe_recebido_real_para_reabertura(monkeypatch):
    from app.vendas import pagamentos_routes
    from app.vendas_models import Venda, VendaPagamento

    tenant_id = "tenant-local"
    monkeypatch.setattr(
        pagamentos_routes,
        "_validar_tenant_e_obter_usuario",
        lambda _: (SimpleNamespace(id=1), tenant_id),
    )
    venda = SimpleNamespace(
        id=42,
        numero_venda="TESTE-42",
        total=Decimal("20.00"),
        status="aberta",
        contas_receber=[],
    )
    pagamentos = [
        VendaPagamento(id=1, valor=40, forma_pagamento="PIX", status="pendente"),
        VendaPagamento(id=2, valor=20, forma_pagamento="PIX", status="pendente"),
    ]
    monkeypatch.setattr(
        pagamentos_routes,
        "snapshot_pagamentos_excedente",
        lambda *_: {
            "total_ja_pago": Decimal("60.00"),
            "recebido_monetario": Decimal("60.00"),
            "creditos_utilizados": Decimal("0.00"),
            "crediario_pendente": Decimal("0.00"),
        },
    )
    consulta_venda, consulta_pagamentos = MagicMock(), MagicMock()
    consulta_venda.options.return_value = consulta_venda
    consulta_venda.filter_by.return_value.populate_existing.return_value.first.return_value = venda
    consulta_pagamentos.filter_by.return_value.order_by.return_value.populate_existing.return_value.all.return_value = pagamentos
    db = MagicMock()
    db.query.side_effect = [consulta_venda, consulta_pagamentos]

    resposta = pagamentos_routes.listar_pagamentos_venda(42, db, (None, tenant_id))

    consulta_venda.filter_by.assert_called_once_with(id=42, tenant_id=tenant_id)
    assert db.query.call_args_list[0].args == (Venda,)
    assert db.query.call_args_list[1].args == (VendaPagamento,)
    assert resposta["total_pago"] == 20
    assert resposta["total_recebido"] == 60
    assert resposta["valor_restante"] == 0
    assert [p["valor"] for p in resposta["pagamentos"]] == [40, 20]
