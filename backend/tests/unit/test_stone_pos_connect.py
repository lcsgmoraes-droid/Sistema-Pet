from decimal import Decimal
import os
from types import SimpleNamespace

import pytest

os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")

from app.stone_api_client import PagarmeConnectClient
from app.stone_routes import (
    _extrair_dados_pagamento_pos,
    _montar_payment_setup_pos,
    _montar_pedido_pos_da_venda,
)


class CapturingPagarmeClient(PagarmeConnectClient):
    def __init__(self):
        super().__init__(secret_key="sk_test_123")
        self.calls = []

    async def _request(self, method, path, json=None, params=None):
        self.calls.append(
            {
                "method": method,
                "path": path,
                "json": json,
                "params": params,
            }
        )
        return {"id": "or_123", "status": "pending"}


@pytest.mark.asyncio
async def test_criar_pedido_pos_envia_display_name_dentro_do_poi_settings():
    client = CapturingPagarmeClient()

    await client.criar_pedido_pos(
        items=[{"amount": 12500, "description": "Venda PDV", "quantity": 1, "code": "1"}],
        customer={"name": "Cliente"},
        serial_number="4AJ15FJ63",
        payment_setup={"type": "credit", "installments": 3, "installment_type": "merchant"},
        metadata={"external_id": "VENDA-42", "display_name": "Venda #42"},
    )

    call = client.calls[0]
    body = call["json"]

    assert call["method"] == "POST"
    assert call["path"] == "/orders"
    assert body["closed"] is False
    assert "display_name" not in body
    assert body["poi_payment_settings"]["display_name"] == "Venda #42"
    assert body["poi_payment_settings"]["devices_serial_number"] == ["4AJ15FJ63"]
    assert body["poi_payment_settings"]["payment_setup"] == {
        "type": "credit",
        "installments": 3,
        "installment_type": "merchant",
    }


@pytest.mark.asyncio
async def test_cancelar_pedido_usa_endpoint_closed_sem_barra_final():
    client = CapturingPagarmeClient()

    await client.cancelar_pedido("or_123")

    assert client.calls == [
        {
            "method": "PATCH",
            "path": "/orders/or_123/closed",
            "json": {"status": "canceled"},
            "params": None,
        }
    ]


def test_extrai_dados_de_pagamento_pos_do_webhook_charge_paid():
    dados = _extrair_dados_pagamento_pos(
        {
            "type": "charge.paid",
            "data": {
                "id": "ch_abc",
                "code": "38332544765625",
                "paid_amount": 12500,
                "payment_method": "cash",
                "paid_at": "2023-10-10T20:28:13.5135427Z",
                "order": {"id": "or_123", "metadata": {"external_id": "VENDA-42"}},
                "metadata": {
                    "scheme_name": "MasterCard",
                    "account_funding_source": "Credit",
                    "authorization_code": "M21111",
                    "installment_quantity": "3",
                    "terminal_serial_number": "6N021234",
                },
            },
        }
    )

    assert dados.order_id == "or_123"
    assert dados.charge_id == "ch_abc"
    assert dados.valor == Decimal("125.00")
    assert dados.tipo_forma_pagamento == "cartao_credito"
    assert dados.bandeira == "MasterCard"
    assert dados.nsu == "38332544765625"
    assert dados.numero_autorizacao == "M21111"
    assert dados.parcelas == 3
    assert dados.terminal_serial_number == "6N021234"


def test_payment_setup_pos_mantem_parcelas_apenas_para_credito():
    assert _montar_payment_setup_pos("cartao_credito", 3) == {
        "type": "credit",
        "installments": 3,
        "installment_type": "merchant",
    }
    assert _montar_payment_setup_pos("cartao_debito", 3) == {"type": "debit"}
    assert _montar_payment_setup_pos("pix", 3) == {"type": "pix"}


def test_monta_pedido_pos_da_venda_com_total_dos_itens_e_cliente():
    venda = SimpleNamespace(
        id=42,
        numero_venda="202605310001",
        total=Decimal("25.00"),
        cliente=SimpleNamespace(
            nome="Tony Stark",
            email="tony@example.com",
            cpf="123.456.789-09",
            cnpj=None,
        ),
        itens=[
            SimpleNamespace(
                id=1,
                quantidade=Decimal("2"),
                preco_unitario=Decimal("10.50"),
                subtotal=Decimal("21.00"),
                servico_descricao=None,
                produto_id=10,
                produto=SimpleNamespace(nome="Racao", codigo="SKU-10"),
            ),
            SimpleNamespace(
                id=2,
                quantidade=Decimal("1"),
                preco_unitario=Decimal("4.00"),
                subtotal=Decimal("4.00"),
                servico_descricao="Banho",
                produto_id=None,
                produto=None,
            ),
        ],
    )

    payload = _montar_pedido_pos_da_venda(
        venda,
        payment_type="cartao_credito",
        installments=3,
    )

    assert payload["items"] == [
        {"amount": 2100, "description": "Racao x2", "quantity": 1, "code": "SKU-10"},
        {"amount": 400, "description": "Banho x1", "quantity": 1, "code": "2"},
    ]
    assert payload["customer"] == {
        "name": "Tony Stark",
        "type": "individual",
        "email": "tony@example.com",
        "document": "12345678909",
    }
    assert payload["amount"] == Decimal("25.00")
    assert payload["display_name"] == "Venda 202605310001"
    assert payload["payment_setup"] == {
        "type": "credit",
        "installments": 3,
        "installment_type": "merchant",
    }
