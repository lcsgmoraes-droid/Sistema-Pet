"""O piloto nao usa devolucao, pagamento ou entrega genericos para mudar estado."""

import asyncio
from types import SimpleNamespace
from uuid import uuid4

from fastapi import HTTPException
import pytest

from app.config import settings
from app.caixa_models import Caixa, MovimentacaoCaixa
from app.vendas import devolucoes_routes, entrega_routes, exclusao_pagamento
from app.vendas.schemas import MarcarEntregueRequest
from app.vendas_models import Venda, VendaPagamento


class _Query:
    def __init__(self, db, models):
        self.db = db
        self.models = models
        self.filters = {}

    def filter_by(self, **kwargs):
        self.filters.update(kwargs)
        return self

    def filter(self, *conditions):
        for condition in conditions:
            if getattr(condition.left, "key", None) in {"id", "tenant_id"}:
                self.filters[condition.left.key] = condition.right.value
        return self

    def order_by(self, *_args):
        return self

    def populate_existing(self):
        return self

    def with_for_update(self):
        return self

    def _rows(self):
        if len(self.models) == 1 and self.models[0] is Venda:
            rows = [self.db.sale]
        elif len(self.models) == 2 or self.models[0] is VendaPagamento:
            rows = [self.db.payment]
        elif self.models[0] is Caixa or self.models[0] is MovimentacaoCaixa.caixa_id:
            rows = []
        else:
            raise AssertionError(
                "O bloqueio consultou tabelas fora da busca de venda/pagamento."
            )
        return [
            row
            for row in rows
            if all(
                getattr(row, key, None) == value for key, value in self.filters.items()
            )
        ]

    def first(self):
        rows = self._rows()
        return rows[0] if rows else None

    def all(self):
        return self._rows()


class _Db:
    def __init__(self, sale):
        self.sale = sale
        self.payment = SimpleNamespace(
            id=7,
            venda_id=sale.id,
            tenant_id=sale.tenant_id,
            caixa_id=None,
            baixa_lote_id=None,
        )
        self.queries = []
        self.mutations = []
        self.commits = 0
        self.rollbacks = 0

    def query(self, *models):
        query = _Query(self, models)
        self.queries.append(query)
        return query

    def add(self, value):
        self.mutations.append(("add", value))

    def delete(self, value):
        self.mutations.append(("delete", value))

    def flush(self):
        self.mutations.append(("flush", None))

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1


@pytest.fixture
def context(monkeypatch):
    for name in ("APP_ENV", "ENV", "ENVIRONMENT"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(settings, "ENVIRONMENT", "test")
    monkeypatch.setattr(settings, "IFOOD_PDV_PILOT_ENABLED", False)
    tenant = uuid4()
    sale = SimpleNamespace(
        id=8,
        tenant_id=tenant,
        canal="ifood",
        status="finalizada",
        numero_venda="DEV0008",
        tem_entrega=False,
        status_entrega="pendente",
        data_entrega=None,
        retirado_por=None,
    )
    user = SimpleNamespace(id=1)
    return SimpleNamespace(tenant=tenant, sale=sale, user=user, db=_Db(sale))


def _invoke(action, context, *, tenant=None):
    auth = (context.user, tenant or context.tenant)
    if action == "return-preview":
        return devolucoes_routes.prever_devolucao(
            8,
            {},
            db=context.db,
            user_and_tenant=auth,
        )
    if action == "return":
        return devolucoes_routes.registrar_devolucao(
            8,
            {},
            db=context.db,
            user_and_tenant=auth,
        )
    if action == "payment-delete":
        return exclusao_pagamento.excluir_pagamento_atomico(
            db=context.db,
            pagamento_id=7,
            tenant_id=tenant or context.tenant,
            current_user=context.user,
        )
    if action == "ready":
        return asyncio.run(
            entrega_routes.marcar_venda_pronta_retirada(
                8,
                db=context.db,
                user_and_tenant=auth,
            )
        )
    if action == "delivered":
        return asyncio.run(
            entrega_routes.marcar_venda_entregue(
                8,
                MarcarEntregueRequest(retirado_por="Testador"),
                db=context.db,
                user_and_tenant=auth,
            )
        )
    raise AssertionError(action)


@pytest.mark.parametrize(
    "action", ["return-preview", "return", "payment-delete", "ready", "delivered"]
)
def test_ifood_alternative_routes_fail_before_any_mutation(
    context, action, monkeypatch
):
    notifications = []
    monkeypatch.setattr(
        entrega_routes,
        "notify_sale_order_event",
        lambda *a, **kw: notifications.append(kw),
    )
    with pytest.raises(HTTPException) as error:
        _invoke(action, context)
    assert error.value.status_code == 409
    assert "piloto" in str(error.value.detail).lower()
    assert context.db.mutations == []
    assert context.db.commits == 0
    assert context.sale.status == "finalizada"
    assert context.sale.status_entrega == "pendente"
    assert context.sale.data_entrega is None
    assert notifications == []


@pytest.mark.parametrize("action", ["return-preview", "return", "ready", "delivered"])
def test_alternative_routes_keep_tenant_lookup_before_pilot_guard(context, action):
    with pytest.raises(HTTPException) as error:
        _invoke(action, context, tenant=uuid4())
    assert error.value.status_code == 404
    assert context.db.mutations == []
    assert context.db.commits == 0


@pytest.mark.parametrize("channel", ["app", "ecommerce", "whatsapp", "loja_fisica"])
@pytest.mark.parametrize("action", ["ready", "delivered"])
def test_existing_channels_keep_delivery_actions_without_extra_queries(
    context, channel, action, monkeypatch
):
    context.sale.canal = channel
    notifications = []
    monkeypatch.setattr(
        entrega_routes,
        "notify_sale_order_event",
        lambda *a, **kw: notifications.append(kw),
    )
    result = _invoke(action, context)
    assert result["status_entrega"] == ("pronto" if action == "ready" else "entregue")
    assert len(context.db.queries) == 1
    assert context.db.commits == 1
    assert len(notifications) == 1


@pytest.mark.parametrize("channel", ["app", "ecommerce", "whatsapp", "loja_fisica"])
def test_other_channel_payment_keeps_existing_reopen_validation(context, channel):
    context.sale.canal = channel
    with pytest.raises(HTTPException) as error:
        _invoke("payment-delete", context)
    assert error.value.status_code == 400
    assert "Reabra a venda" in error.value.detail
    assert len(context.db.queries) == 5
    assert context.db.mutations == []
    assert context.db.commits == 0


@pytest.mark.parametrize("channel", ["app", "ecommerce", "whatsapp", "loja_fisica"])
def test_other_channel_return_keeps_original_status_validation(context, channel):
    context.sale.canal = channel
    context.sale.status = "aberta"
    with pytest.raises(HTTPException) as error:
        _invoke("return", context)
    assert error.value.status_code == 400
    assert "situação que permita devolução" in error.value.detail
    assert len(context.db.queries) == 1
    assert context.db.mutations == []
    assert context.db.commits == 0
