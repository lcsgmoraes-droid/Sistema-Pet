from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from app.services.bling_nf_service import processar_nf_autorizada


def test_nf_autorizada_baixa_estoque_uma_vez(monkeypatch):
    db = Mock()
    pedido = SimpleNamespace(
        status="aberto",
        confirmado_em=None,
        tenant_id="tenant-1",
        id=77,
        pedido_bling_numero="#11397",
    )
    item = SimpleNamespace(sku="026209.1", quantidade=1, vendido_em=None)
    produto = SimpleNamespace(id=12)
    chamadas_baixa = []

    def fake_confirmar_venda(db_arg, item_arg):
        item_arg.vendido_em = "2026-03-24T00:00:00Z"

    def fake_buscar_produto(**kwargs):
        assert kwargs["sku"] == "026209.1"
        return produto

    def fake_baixar_estoque(**kwargs):
        chamadas_baixa.append(kwargs)
        return {"sucesso": True}

    monkeypatch.setattr(
        "app.services.bling_nf_service.buscar_produto_do_item",
        fake_buscar_produto,
    )
    monkeypatch.setattr(
        "app.services.bling_nf_service.EstoqueReservaService.confirmar_venda",
        fake_confirmar_venda,
    )
    monkeypatch.setattr(
        "app.estoque.service.EstoqueService.baixar_estoque",
        fake_baixar_estoque,
    )

    resposta_1 = processar_nf_autorizada(db=db, pedido=pedido, itens=[item], nf_id="98765")
    resposta_2 = processar_nf_autorizada(db=db, pedido=pedido, itens=[item], nf_id="98765")

    assert resposta_1 == "venda_confirmada"
    assert resposta_2 == "venda_ja_confirmada"
    assert pedido.status == "confirmado"
    assert item.vendido_em is not None
    assert len(chamadas_baixa) == 1
    assert chamadas_baixa[0]["produto_id"] == 12
    assert chamadas_baixa[0]["documento"] == "#11397"
    assert chamadas_baixa[0]["motivo"] == "venda_bling"
    assert db.add.call_count == 1
    assert db.commit.call_count == 1


def test_nf_autorizada_autocadastra_produto_e_baixa(monkeypatch):
    db = Mock()
    pedido = SimpleNamespace(
        status="aberto",
        confirmado_em=None,
        tenant_id="tenant-1",
        id=88,
        pedido_bling_numero="#22001",
    )
    item = SimpleNamespace(sku="SKU-NOVO-001", quantidade=2, vendido_em=None)
    produto_autocriado = SimpleNamespace(id=345)
    chamadas_baixa = []

    def fake_confirmar_venda(db_arg, item_arg):
        item_arg.vendido_em = "2026-03-24T00:00:00Z"

    def fake_buscar_produto(**kwargs):
        return None

    def fake_autocriar_produto(**kwargs):
        assert kwargs["sku"] == "SKU-NOVO-001"
        return produto_autocriado

    def fake_baixar_estoque(**kwargs):
        chamadas_baixa.append(kwargs)
        return {"sucesso": True}

    monkeypatch.setattr(
        "app.services.bling_nf_service.buscar_produto_do_item",
        fake_buscar_produto,
    )
    monkeypatch.setattr(
        "app.services.bling_nf_service.criar_produto_automatico_do_bling",
        fake_autocriar_produto,
    )
    monkeypatch.setattr(
        "app.services.bling_nf_service.EstoqueReservaService.confirmar_venda",
        fake_confirmar_venda,
    )
    monkeypatch.setattr(
        "app.estoque.service.EstoqueService.baixar_estoque",
        fake_baixar_estoque,
    )

    resposta = processar_nf_autorizada(db=db, pedido=pedido, itens=[item], nf_id="99100")

    assert resposta == "venda_confirmada"
    assert len(chamadas_baixa) == 1
    assert chamadas_baixa[0]["produto_id"] == 345
    assert chamadas_baixa[0]["quantidade"] == pytest.approx(2.0)