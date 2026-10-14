"""Toda alteração do saldo usa o mesmo bloqueio de linha por tenant."""

from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

from app.clientes import credito_routes
from app.clientes.schemas import AjustarCreditoRequest
from app.models import Cliente
from app.vendas.finalizacao_pagamentos import processar_pagamentos_finalizacao


def _consulta_cliente(cliente):
    consulta = MagicMock()
    consulta.filter.return_value = consulta
    consulta.filter_by.return_value = consulta
    consulta.populate_existing.return_value = consulta
    consulta.with_for_update.return_value = consulta
    consulta.first.return_value = cliente
    return consulta


def test_adicao_e_remocao_manual_bloqueiam_saldo_antes_de_alterar(monkeypatch):
    tenant_id = uuid4()
    cliente = SimpleNamespace(
        id=47,
        nome="Cliente",
        ativo=True,
        credito=Decimal("10.00"),
        updated_at=None,
    )
    consulta = _consulta_cliente(cliente)
    db = MagicMock()
    db.query.return_value = consulta
    usuario = SimpleNamespace(id=22, nome="Atendente")
    monkeypatch.setattr(credito_routes, "log_update", lambda *_args: None)

    credito_routes.adicionar_credito(
        cliente_id=cliente.id,
        dados=AjustarCreditoRequest(valor=20, motivo="Ajuste"),
        db=db,
        user_and_tenant=(usuario, tenant_id),
    )
    credito_routes.remover_credito(
        cliente_id=cliente.id,
        dados=AjustarCreditoRequest(valor=15, motivo="Ajuste"),
        db=db,
        user_and_tenant=(usuario, tenant_id),
    )

    assert cliente.credito == Decimal("15.0")
    assert consulta.populate_existing.call_count == 2
    assert consulta.with_for_update.call_count == 2
    assert db.commit.call_count == 2


def test_pagamento_com_credito_bloqueia_cliente_do_mesmo_tenant():
    tenant_id = uuid4()
    cliente = SimpleNamespace(id=47, credito=Decimal("30.00"))
    consulta = _consulta_cliente(cliente)
    db = MagicMock()
    db.query.side_effect = lambda modelo: consulta if modelo is Cliente else None
    venda = SimpleNamespace(id=8, cliente_id=cliente.id)

    movimentacoes = processar_pagamentos_finalizacao(
        venda=venda,
        pagamentos=[{"forma_pagamento": "credito_cliente", "valor": 20}],
        user_id=22,
        user_nome="Atendente",
        tenant_id=tenant_id,
        db=db,
        caixa_aberto_id=1,
    )

    assert movimentacoes == []
    assert cliente.credito == Decimal("10.0")
    consulta.filter_by.assert_called_once_with(id=cliente.id, tenant_id=tenant_id)
    consulta.populate_existing.assert_called_once()
    consulta.with_for_update.assert_called_once()
