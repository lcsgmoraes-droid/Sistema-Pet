from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.vendas.devolucoes_routes import consultar_saldos_devolucao
from app.vendas_models import Venda, VendaItem
from app.vendas_devolucoes_models import VendaDevolucao


def _consultas(venda, itens, eventos):
    db = MagicMock()
    consultas = {modelo: MagicMock() for modelo in (Venda, VendaItem, VendaDevolucao)}
    db.query.side_effect = lambda modelo: consultas[modelo]
    consultas[Venda].filter_by.return_value.first.return_value = venda
    consultas[VendaItem].filter.return_value.all.return_value = itens
    consultas[VendaDevolucao].filter.return_value.all.return_value = eventos
    return db, consultas


def test_consulta_saldo_da_mesma_linha_apos_devolucao_parcial(monkeypatch):
    tenant_id = uuid4()
    monkeypatch.setattr(
        "app.vendas.devolucoes_routes._validar_tenant_e_obter_usuario",
        lambda autenticacao: autenticacao,
    )
    venda = SimpleNamespace(status="finalizada_devolucao")
    item = SimpleNamespace(id=7, quantidade=Decimal("2"))
    evento = SimpleNamespace(
        itens=[{"venda_item_id": 7, "quantidade": "1", "is_componente_kit": False}]
    )
    db, consultas = _consultas(venda, [item], [evento])

    resposta = consultar_saldos_devolucao(4, db, (SimpleNamespace(), tenant_id))

    assert resposta == {
        "venda_id": 4,
        "itens": [
            {
                "item_id": 7,
                "quantidade_vendida": 2.0,
                "quantidade_devolvida": 1.0,
                "quantidade_disponivel": 1.0,
            }
        ],
    }
    consultas[Venda].filter_by.assert_called_once_with(id=4, tenant_id=tenant_id)


def test_devolucao_legada_sem_evento_nao_expoe_saldo_inseguro(monkeypatch):
    monkeypatch.setattr(
        "app.vendas.devolucoes_routes._validar_tenant_e_obter_usuario",
        lambda autenticacao: autenticacao,
    )
    db, _ = _consultas(SimpleNamespace(status="finalizada_devolucao"), [], [])

    with pytest.raises(HTTPException) as erro:
        consultar_saldos_devolucao(4, db, (SimpleNamespace(), uuid4()))

    assert erro.value.status_code == 409
