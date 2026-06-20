from datetime import datetime, timedelta
from types import SimpleNamespace

from app.services.customer_order_history import (
    build_checkout_history_entry,
    build_sale_history_entry,
    channel_label_for,
    merge_history_entries,
)


def _dt(minutes: int):
    return datetime(2026, 6, 20, 16, 0, 0) + timedelta(minutes=minutes)


def test_channel_label_for_explicit_customer_channels():
    assert channel_label_for("ecommerce") == "Ecommerce"
    assert channel_label_for("app") == "App mobile"
    assert channel_label_for("loja_fisica") == "Loja fisica / ERP"
    assert channel_label_for("mercado_livre") == "Mercado Livre"
    assert channel_label_for("canal_novo") == "Canal novo"


def test_build_checkout_history_entry_preserves_app_channel_and_items():
    pedido = SimpleNamespace(
        pedido_id="PED-APP-1",
        id=10,
        status="pendente",
        total=39.9,
        origem="app",
        created_at=_dt(1),
        tipo_retirada="app_loja",
        palavra_chave_retirada="patinha",
        is_drive=False,
        drive_chegou_at=None,
        drive_entregue_at=None,
    )
    item = SimpleNamespace(
        produto_id=7,
        nome="Racao",
        quantidade=2,
        preco_unitario=10.0,
        subtotal=20.0,
    )

    entry = build_checkout_history_entry(
        pedido,
        [item],
        payment_info={
            "payment_url": "https://mp.test",
            "payment_provider": "mercadopago",
        },
        venda_info={},
    )

    assert entry["historico_id"] == "pedido:PED-APP-1"
    assert entry["origem_tipo"] == "pedido_online"
    assert entry["canal"] == "app"
    assert entry["canal_label"] == "App mobile"
    assert entry["itens"][0]["nome"] == "Racao"
    assert entry["payment_url"] == "https://mp.test"


def test_build_sale_history_entry_uses_erp_channel_and_linked_order_data():
    item = SimpleNamespace(
        produto_id=8,
        produto_nome="Areia",
        servico_descricao=None,
        quantidade=1,
        preco_unitario=25.5,
        subtotal=25.5,
    )
    venda = SimpleNamespace(
        id=123,
        numero_venda="VEN-123",
        status="finalizada",
        status_entrega="pronto",
        canal="loja_fisica",
        total=25.5,
        data_venda=_dt(2),
        created_at=_dt(2),
        itens=[item],
        tem_entrega=False,
        tipo_retirada=None,
        palavra_chave_retirada=None,
        retirado_por=None,
    )
    pedido = SimpleNamespace(
        pedido_id="PED-WEB-9",
        payment_url="https://mp.test",
        payment_provider="mercadopago",
        payment_preference_id="pref-1",
        tipo_retirada="proprio",
        palavra_chave_retirada="coleira",
        is_drive=True,
        drive_chegou_at=None,
        drive_entregue_at=None,
    )

    entry = build_sale_history_entry(venda, linked_order=pedido)

    assert entry["historico_id"] == "venda:123"
    assert entry["origem_tipo"] == "venda"
    assert entry["pedido_id"] == "PED-WEB-9"
    assert entry["canal"] == "loja_fisica"
    assert entry["canal_label"] == "Loja fisica / ERP"
    assert entry["payment_url"] == "https://mp.test"
    assert entry["palavra_chave_retirada"] == "coleira"


def test_merge_history_entries_deduplicates_sale_linked_checkout_order():
    checkout = {
        "historico_id": "pedido:PED-1",
        "origem_tipo": "pedido_online",
        "pedido_id": "PED-1",
        "created_at": _dt(1).isoformat(),
    }
    sale = {
        "historico_id": "venda:9",
        "origem_tipo": "venda",
        "pedido_id": "PED-1",
        "created_at": _dt(3).isoformat(),
    }

    merged = merge_history_entries([checkout], [sale], limit=20)

    assert merged == [sale]
