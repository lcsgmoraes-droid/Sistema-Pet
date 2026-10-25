"""Cancelamento comum recompõe os lotes históricos e alimenta somente estoque DEV.

Usa apenas o PostgreSQL local ifood_pdv_test/schema UUID do fixture canônico e
um provider em memória. Não amplia a ponte de pedidos do SKU 018631.1.
"""

from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import datetime
from decimal import Decimal
import json
from threading import Barrier

from fastapi import HTTPException
import pytest
from sqlalchemy import event
from sqlalchemy.orm import Session

from tests.integration.test_ifood_stock_sync_postgres import (
    _snapshot,
    _tick,
    pg_engine,  # noqa: F401 - fixture canônico com guard de destino
    stock_pg_engine,  # noqa: F401 - migration real da fila de estoque
    stock_pilot,  # noqa: F401 - fixture de empresa/produto/provider falsos
)


def _decimal(value):
    return Decimal(str(value))


def _lots(db, c, tenant=None, product=None):
    from app.produtos_models import ProdutoLote

    return (
        db.query(ProdutoLote)
        .filter_by(
            tenant_id=tenant or c.tenant_id,
            produto_id=product or c.product_id,
        )
        .order_by(ProdutoLote.ordem_entrada, ProdutoLote.id)
        .all()
    )


def _protected(c):
    from app.tenancy.context import tenant_context

    snapshot = _snapshot(c)
    result = {key: snapshot[key] for key in (c.control_id, c.other_product_id)}
    for tenant, product in (
        (c.tenant_id, c.control_id),
        (c.other_tenant, c.other_product_id),
    ):
        with tenant_context(tenant), Session(c.engine) as db:
            result[f"lots-{product}"] = [
                {col.key: getattr(row, col.key) for col in row.__mapper__.columns}
                for row in _lots(db, c, tenant, product)
            ]
    return result


@pytest.fixture
def lot_pilot(stock_pilot):  # noqa: F811 - fixture importado
    from app.produtos_models import Produto, ProdutoLote
    from app.tenancy.context import tenant_context

    c = stock_pilot
    c.lot_ids = []
    with tenant_context(c.tenant_id), Session(c.engine) as db:
        product = (
            db.query(Produto).filter_by(id=c.product_id, tenant_id=c.tenant_id).one()
        )
        product.controle_lote = True
        for index, (quantity, cost) in enumerate(((4, 80), (7, 100), (10, 120)), 1):
            lot = ProdutoLote(
                tenant_id=c.tenant_id,
                produto_id=c.product_id,
                nome_lote=f"PG-CANCEL-{index}",
                quantidade_inicial=quantity,
                quantidade_disponivel=quantity,
                quantidade_reservada=0,
                status="ativo",
                apenas_identificacao=True,
                ordem_entrada=100 + index,
                custo_unitario=cost,
                data_validade=datetime(2032, 1, index),
            )
            db.add(lot)
            db.flush()
            c.lot_ids.append(lot.id)
        db.add(
            ProdutoLote(
                tenant_id=c.tenant_id,
                produto_id=c.control_id,
                nome_lote="CONTROLE-NAO-TOCAR",
                quantidade_inicial=29,
                quantidade_disponivel=29,
                quantidade_reservada=0,
                status="ativo",
                ordem_entrada=1,
                custo_unitario=43.94,
            )
        )
        db.commit()
    with tenant_context(c.other_tenant), Session(c.engine) as db:
        lot = ProdutoLote(
            tenant_id=c.other_tenant,
            produto_id=c.other_product_id,
            nome_lote="OUTRA-EMPRESA-NAO-TOCAR",
            quantidade_inicial=41,
            quantidade_disponivel=41,
            quantidade_reservada=0,
            status="ativo",
            ordem_entrada=1,
            custo_unitario=70,
        )
        db.add(lot)
        db.flush()
        c.other_lot_id = lot.id
        db.commit()
    c.before_protected = _protected(c)
    c.before_prices = _state(c)["prices"]
    return c


def _state(c, sale_id=None):
    from app.produtos_models import EstoqueMovimentacao, Produto
    from app.tenancy.context import tenant_context
    from app.vendas_models import Venda, VendaItem

    with tenant_context(c.tenant_id), Session(c.engine) as db:
        product = (
            db.query(Produto).filter_by(id=c.product_id, tenant_id=c.tenant_id).one()
        )
        result = {
            "physical": _decimal(product.estoque_atual),
            "lots": {
                lot.id: {
                    "available": _decimal(lot.quantidade_disponivel),
                    "initial": _decimal(lot.quantidade_inicial),
                    "cost": _decimal(lot.custo_unitario),
                    "status": lot.status,
                }
                for lot in _lots(db, c)
            },
            "prices": {
                key: getattr(product, key)
                for key in (
                    "preco_venda",
                    "preco_custo",
                    "preco_app",
                    "preco_ecommerce",
                    "preco_ifood",
                    "preco_app_promo",
                    "preco_ecommerce_promo",
                    "preco_ifood_promo",
                    "anunciar_app",
                    "anunciar_ecommerce",
                )
            },
        }
        if sale_id is not None:
            sale = db.query(Venda).filter_by(tenant_id=c.tenant_id, id=sale_id).one()
            result["sale_status"] = sale.status
            result["proofs"] = {
                item.id: deepcopy(item.custo_original_saida)
                for item in db.query(VendaItem)
                .filter_by(tenant_id=c.tenant_id, venda_id=sale_id)
                .order_by(VendaItem.id)
            }
            result["movements"] = [
                {
                    "id": move.id,
                    "type": move.tipo,
                    "quantity": _decimal(move.quantidade),
                    "cost": None
                    if move.custo_unitario is None
                    else _decimal(move.custo_unitario),
                    "total": None
                    if move.valor_total is None
                    else _decimal(move.valor_total),
                    "lots": json.loads(move.lotes_consumidos)
                    if move.lotes_consumidos
                    else None,
                    "reason": move.motivo,
                    "status": move.status,
                }
                for move in db.query(EstoqueMovimentacao)
                .filter_by(
                    tenant_id=c.tenant_id,
                    produto_id=c.product_id,
                    referencia_tipo="venda",
                    referencia_id=sale_id,
                )
                .order_by(EstoqueMovimentacao.id)
            ]
        return result


def _sale(c, quantities=(6,), *, finalize=True):
    from app.tenancy.context import tenant_context
    from app.vendas.service import VendaService

    with tenant_context(c.tenant_id), Session(c.engine) as db:
        result = VendaService.criar_venda(
            {
                "tenant_id": c.tenant_id,
                "canal": "loja_fisica",
                "caixa_id": c.caixa_id,
                "observacoes": "PG ficticio: cancelamento lotes SKU227",
                "itens": [
                    {
                        "produto_id": c.product_id,
                        "tipo": "produto",
                        "quantidade": quantity,
                        "preco_unitario": 142.9,
                        "subtotal": 142.9 * quantity,
                    }
                    for quantity in quantities
                ],
            },
            c.user_id,
            db,
        )
        sale_id = result["id"]
        if finalize:
            _finalize(c, sale_id, db=db)
        return sale_id


def _finalize(c, sale_id, *, db=None, barrier=None):
    from app.tenancy.context import tenant_context
    from app.vendas.service import VendaService
    from app.vendas_models import Venda

    if db is None:
        with tenant_context(c.tenant_id), Session(c.engine) as session:
            return _finalize(c, sale_id, db=session, barrier=barrier)
    sale = db.query(Venda).filter_by(tenant_id=c.tenant_id, id=sale_id).one()
    amount = float(sale.total)
    if barrier:
        barrier.wait(timeout=15)
    return VendaService.finalizar_venda(
        sale_id,
        [{"forma_pagamento": "Dinheiro", "valor": amount}],
        c.user_id,
        "PG cancelamento lotes",
        c.tenant_id,
        db,
        caixa_id=c.caixa_id,
    )


def _cancel(c, sale_id, *, barrier=None, db=None):
    from app.tenancy.context import tenant_context
    from app.vendas.service import VendaService

    if db is None:
        with tenant_context(c.tenant_id), Session(c.engine) as session:
            return _cancel(c, sale_id, barrier=barrier, db=session)
    if barrier:
        barrier.wait(timeout=15)
    return VendaService.cancelar_venda(
        sale_id,
        "PG ficticio: cancelamento lotes",
        c.user_id,
        c.tenant_id,
        db,
    )


def _assert_protected(c, *, current_cost=None):
    assert _protected(c) == c.before_protected
    current = _snapshot(c)[c.product_id]
    prices = {key: current[key] for key in c.before_prices}
    expected = dict(c.before_prices)
    if current_cost is not None:
        expected["preco_custo"] = current_cost
    assert prices == expected
    for merchant, items, method, reset in c.provider.calls:
        assert merchant == c.merchant_id and method == "PATCH" and reset is False
        assert items == [
            {
                "barcode": "7898242031448",
                "inventory": {"stock": items[0]["inventory"]["stock"]},
            }
        ]


def test_multilot_cancel_and_replenishment_sync_only_stock_with_original_cost(
    lot_pilot,
):
    from app.estoque_entrada_manual_routes import EntradaEstoqueRequest, entrada_estoque
    from app.models import User
    from app.tenancy.context import tenant_context

    c = lot_pilot
    original = _state(c)
    assert _tick(c)["status"] == "unchanged" and not c.provider.calls
    sale_id = _sale(c)
    sold = _state(c, sale_id)
    assert sold["physical"] == 15
    assert [row["available"] for row in sold["lots"].values()] == [0, 5, 10]
    exits = [row for row in sold["movements"] if row["type"] == "saida"]
    # A baixa atual congela o custo do cadastro (100), nao uma nova valoracao
    # pelos custos dos lotes. O retorno precisa preservar essa prova real.
    assert len(exits) == 1 and exits[0]["total"] == 600
    assert _tick(c, 36)["sent_stock"] == 15
    _cancel(c, sale_id)
    cancelled = _state(c, sale_id)
    assert cancelled["physical"] == 21
    assert cancelled["lots"] == original["lots"]
    assert cancelled["proofs"] == sold["proofs"]
    returns = [row for row in cancelled["movements"] if row["type"] == "entrada"]
    assert len(returns) == 1 and returns[0]["total"] == exits[0]["total"]
    assert {
        part["lote_id"]: _decimal(part["quantidade"]) for part in returns[0]["lots"]
    } == {c.lot_ids[0]: 4, c.lot_ids[1]: 2}
    assert _tick(c, 72)["sent_stock"] == 21
    assert _tick(c, 108)["status"] == "unchanged" and len(c.provider.calls) == 2
    with tenant_context(c.tenant_id), Session(c.engine) as db:
        user = db.query(User).filter_by(tenant_id=c.tenant_id, id=c.user_id).one()
        entrada_estoque(
            EntradaEstoqueRequest(
                produto_id=c.product_id,
                quantidade=2,
                custo_unitario=None,
                motivo="ajuste",
                criar_lote=True,
                numero_lote="PG-REPOSICAO",
                data_validade="2033-01-01",
            ),
            db=db,
            user_and_tenant=(user, c.tenant_id),
        )
    replenished = _state(c)
    assert replenished["physical"] == 23
    assert len(replenished["lots"]) == 4
    assert all(
        replenished["lots"][key] == value for key, value in original["lots"].items()
    )
    assert _tick(c, 144)["sent_stock"] == 23
    _assert_protected(c)


def test_duplicate_sku_lines_restore_each_item_original_lots_once(lot_pilot):
    c = lot_pilot
    original = _state(c)
    sale_id = _sale(c, (3, 4))
    sold = _state(c, sale_id)
    assert sold["physical"] == 14
    assert len(sold["proofs"]) == 2
    _cancel(c, sale_id)
    restored = _state(c, sale_id)
    assert restored["lots"] == original["lots"] and restored["physical"] == 21
    assert restored["proofs"] == sold["proofs"]
    returns = [move for move in restored["movements"] if move["type"] == "entrada"]
    assert len(returns) == 2 and sum(move["total"] for move in returns) == 700
    proof_ids = set(sold["proofs"])
    assert {
        part["venda_item_id"] for move in returns for part in move["lots"]
    } == proof_ids
    for move in returns:
        item_id = move["lots"][0]["venda_item_id"]
        assert move["total"] == _decimal(sold["proofs"][item_id]["custo_total"])
    with pytest.raises(HTTPException) as exc:
        _cancel(c, sale_id)
    assert exc.value.status_code == 400
    assert _state(c, sale_id) == restored
    _assert_protected(c)


def test_legacy_single_item_without_cost_json_uses_its_original_exit_and_lots(
    lot_pilot,
):
    from app.produtos_models import Produto
    from app.tenancy.context import tenant_context
    from app.vendas_models import VendaItem

    c = lot_pilot
    original = _state(c)
    sale_id = _sale(c)
    sold = _state(c, sale_id)
    original_exit = next(row for row in sold["movements"] if row["type"] == "saida")
    with tenant_context(c.tenant_id), Session(c.engine) as db:
        item = (
            db.query(VendaItem).filter_by(tenant_id=c.tenant_id, venda_id=sale_id).one()
        )
        item.custo_original_saida = None
        db.query(Produto).filter_by(
            tenant_id=c.tenant_id, id=c.product_id
        ).one().preco_custo = 999
        db.commit()
    _cancel(c, sale_id)
    restored = _state(c, sale_id)
    assert restored["physical"] == 21 and restored["lots"] == original["lots"]
    returned = [row for row in restored["movements"] if row["type"] == "entrada"]
    assert len(returned) == 1 and returned[0]["total"] == original_exit["total"]
    assert list(restored["proofs"].values()) == [None]
    _assert_protected(c, current_cost=999)


def test_later_cost_and_new_lot_do_not_change_original_return(lot_pilot):
    from app.produtos_models import Produto, ProdutoLote
    from app.tenancy.context import tenant_context

    c = lot_pilot
    original = _state(c)
    sale_id = _sale(c)
    with tenant_context(c.tenant_id), Session(c.engine) as db:
        product = (
            db.query(Produto).filter_by(tenant_id=c.tenant_id, id=c.product_id).one()
        )
        product.preco_custo = 999
        product.estoque_atual += 2
        newer = ProdutoLote(
            tenant_id=c.tenant_id,
            produto_id=c.product_id,
            nome_lote="NOVA-COMPRA",
            quantidade_inicial=2,
            quantidade_disponivel=2,
            quantidade_reservada=0,
            status="ativo",
            ordem_entrada=0,
            custo_unitario=999,
        )
        db.add(newer)
        db.flush()
        new_id = newer.id
        db.commit()
    _cancel(c, sale_id)
    restored = _state(c, sale_id)
    assert restored["physical"] == 23
    assert restored["lots"][new_id]["available"] == 2
    assert all(
        restored["lots"][key] == value for key, value in original["lots"].items()
    )
    returns = [move for move in restored["movements"] if move["type"] == "entrada"]
    assert len(returns) == 1 and returns[0]["total"] == 600
    assert new_id not in {part["lote_id"] for part in returns[0]["lots"]}
    _assert_protected(c, current_cost=999)


def test_two_cancellations_restore_stock_and_lots_only_once(lot_pilot):
    c = lot_pilot
    original = _state(c)
    sale_id = _sale(c)
    barrier = Barrier(2)
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(_cancel, c, sale_id, barrier=barrier) for _ in range(2)]
        outcomes = []
        for future in futures:
            try:
                outcomes.append(future.result(timeout=30)["venda"]["status"])
            except HTTPException as exc:
                outcomes.append(exc.status_code)
    assert sorted(str(value) for value in outcomes) == ["400", "cancelada"]
    restored = _state(c, sale_id)
    assert restored["physical"] == 21 and restored["lots"] == original["lots"]
    assert (
        len([move for move in restored["movements"] if move["type"] == "entrada"]) == 1
    )
    _assert_protected(c)


def test_finalize_racing_cancel_never_reconsumes_restored_lots(lot_pilot):
    c = lot_pilot
    original = _state(c)
    sale_id = _sale(c, finalize=False)
    barrier = Barrier(2)
    with ThreadPoolExecutor(max_workers=2) as pool:
        finalizer = pool.submit(_finalize, c, sale_id, barrier=barrier)
        canceller = pool.submit(_cancel, c, sale_id, barrier=barrier)
        assert canceller.result(timeout=30)["venda"]["status"] == "cancelada"
        try:
            assert finalizer.result(timeout=30)["venda"]["status"] == "finalizada"
        except HTTPException as exc:
            assert exc.status_code in (400, 409)
    restored = _state(c, sale_id)
    assert restored["sale_status"] == "cancelada"
    assert restored["physical"] == 21 and restored["lots"] == original["lots"]
    assert (
        len([move for move in restored["movements"] if move["type"] == "entrada"]) == 1
    )
    _assert_protected(c)


def test_failure_after_lot_return_rolls_back_sale_stock_lots_and_movement(lot_pilot):
    from app.tenancy.context import tenant_context
    from app.vendas_models import Venda

    c = lot_pilot
    sale_id = _sale(c)
    before = _state(c, sale_id)
    observed = []
    with tenant_context(c.tenant_id), Session(c.engine) as db:

        def fail_before_commit(session):
            sale = (
                session.query(Venda).filter_by(tenant_id=c.tenant_id, id=sale_id).one()
            )
            if sale.status == "cancelada":
                assert (
                    sum(
                        _decimal(row.quantidade_disponivel) for row in _lots(session, c)
                    )
                    == 21
                )
                observed.append(True)
                raise RuntimeError("PG cancel rollback after actual lot restoration")

        event.listen(db, "before_commit", fail_before_commit)
        try:
            with pytest.raises((HTTPException, RuntimeError)):
                _cancel(c, sale_id, db=db)
        finally:
            event.remove(db, "before_commit", fail_before_commit)
            db.rollback()
    assert observed == [True]
    assert _state(c, sale_id) == before
    _cancel(c, sale_id)
    assert _state(c, sale_id)["physical"] == 21
    _assert_protected(c)


def test_cross_tenant_original_lot_is_rejected_before_any_cancellation_write(lot_pilot):
    from app.produtos_models import EstoqueMovimentacao
    from app.tenancy.context import tenant_context

    c = lot_pilot
    sale_id = _sale(c)
    with tenant_context(c.tenant_id), Session(c.engine) as db:
        move = (
            db.query(EstoqueMovimentacao)
            .filter_by(
                tenant_id=c.tenant_id,
                produto_id=c.product_id,
                referencia_id=sale_id,
                referencia_tipo="venda",
                tipo="saida",
            )
            .one()
        )
        move.lotes_consumidos = json.dumps(
            [{"lote_id": c.other_lot_id, "quantidade": 6}]
        )
        db.commit()
    before = _state(c, sale_id)
    with pytest.raises(HTTPException) as exc:
        _cancel(c, sale_id)
    assert exc.value.status_code == 409
    assert _state(c, sale_id) == before
    _assert_protected(c)


def _guard_snapshot(c, sale_id):
    """Comparacao canonica inclui valores NaN, que nao sao iguais a si mesmos."""
    from app.produtos_models import EstoqueMovimentacao, Produto, ProdutoLote
    from app.tenancy.context import tenant_context
    from app.vendas_models import Venda, VendaItem, VendaPagamento

    result = {}
    with tenant_context(c.tenant_id), Session(c.engine) as db:
        for model in (
            Produto,
            ProdutoLote,
            Venda,
            VendaItem,
            VendaPagamento,
            EstoqueMovimentacao,
        ):
            query = db.query(model).filter(model.tenant_id == c.tenant_id)
            if model is Produto:
                query = query.filter(Produto.id == c.product_id)
            elif model is ProdutoLote:
                query = query.filter(ProdutoLote.produto_id == c.product_id)
            elif model is Venda:
                query = query.filter(Venda.id == sale_id)
            elif model is EstoqueMovimentacao:
                query = query.filter(
                    EstoqueMovimentacao.referencia_tipo == "venda",
                    EstoqueMovimentacao.referencia_id == sale_id,
                )
            else:
                query = query.filter(model.venda_id == sale_id)
            result[model.__tablename__] = [
                {col.key: getattr(row, col.key) for col in row.__mapper__.columns}
                for row in query.order_by(model.id)
            ]
    return json.dumps(result, sort_keys=True, default=str)


@pytest.mark.parametrize(
    "balance",
    [None, float("nan"), float("inf"), float("-inf")],
    ids=["null", "nan", "positive-inf", "negative-inf"],
)
def test_unknown_or_nonfinite_balance_blocks_cancel_without_mutating_lots_or_payments(
    lot_pilot, balance
):
    from app.produtos_models import Produto
    from app.tenancy.context import tenant_context

    c = lot_pilot
    sale_id = _sale(c)
    with tenant_context(c.tenant_id), Session(c.engine) as db:
        product = (
            db.query(Produto).filter_by(tenant_id=c.tenant_id, id=c.product_id).one()
        )
        product.estoque_atual = balance
        db.commit()
    before = _guard_snapshot(c, sale_id)
    with pytest.raises(HTTPException) as exc:
        _cancel(c, sale_id)
    assert exc.value.status_code == 409
    assert _guard_snapshot(c, sale_id) == before
    _assert_protected(c)


@pytest.mark.parametrize(
    "quantity",
    [Decimal("0"), Decimal("-1"), Decimal("NaN")],
    ids=["zero", "negative", "numeric-nan"],
)
def test_corrupt_legacy_quantity_is_rejected_before_aggregate_fallback(
    stock_pilot,  # noqa: F811 - fixture importado
    quantity,
):
    from app.produtos_models import EstoqueMovimentacao
    from app.tenancy.context import tenant_context
    from app.vendas_models import VendaItem

    c = stock_pilot
    sale_id = _sale(c)
    with tenant_context(c.tenant_id), Session(c.engine) as db:
        item = (
            db.query(VendaItem).filter_by(tenant_id=c.tenant_id, venda_id=sale_id).one()
        )
        item.quantidade = quantity
        item.custo_original_saida = None
        # Emula historico legado sem comprovante nem movimentos/lotes. O
        # destino e apenas o schema aleatorio do banco descartavel canônico.
        for move in db.query(EstoqueMovimentacao).filter_by(
            tenant_id=c.tenant_id,
            produto_id=c.product_id,
            referencia_tipo="venda",
            referencia_id=sale_id,
        ):
            db.delete(move)
        db.commit()
    before = _guard_snapshot(c, sale_id)
    with pytest.raises(HTTPException) as exc:
        _cancel(c, sale_id)
    assert exc.value.status_code == 409
    assert _guard_snapshot(c, sale_id) == before
    snapshot = _snapshot(c)
    assert snapshot[c.control_id] == c.before[c.control_id]
    assert snapshot[c.other_product_id] == c.before[c.other_product_id]


def test_known_negative_balance_accepts_the_exact_positive_original_return(lot_pilot):
    from app.produtos_models import Produto
    from app.tenancy.context import tenant_context

    c = lot_pilot
    original = _state(c)
    sale_id = _sale(c)
    with tenant_context(c.tenant_id), Session(c.engine) as db:
        db.query(Produto).filter_by(
            tenant_id=c.tenant_id, id=c.product_id
        ).one().estoque_atual = -1
        db.commit()
    _cancel(c, sale_id)
    after = _state(c, sale_id)
    assert after["sale_status"] == "cancelada"
    assert after["physical"] == 5  # -1 atual + 6 comprovadas, sem fabricar 21.
    assert after["lots"] == original["lots"]
    _assert_protected(c)
