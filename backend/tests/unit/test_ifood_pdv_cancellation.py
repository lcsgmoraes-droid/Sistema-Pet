"""Cancelamento local do piloto: prova original, escopo e recomposicao FIFO."""

from copy import deepcopy
from datetime import datetime, timedelta
import json
from uuid import uuid4

from fastapi import HTTPException
import pytest
from sqlalchemy.schema import CreateTable
from sqlalchemy.orm.attributes import flag_modified

from app.caixa_models import MovimentacaoCaixa
from app.config import settings
from app.financeiro_models import LancamentoManual, MovimentacaoFinanceira
from app.ifood_order_models import IfoodPdvBridge
from app.integrations.ifood.pdv_pilot import (
    complete_pilot_cancellation,
    finalize_online_pdv_pilot,
    import_pdv_pilot,
    pdv_bridge_summary,
    prepare_pilot_cancellation,
)
from app.integrations.ifood.pdv_pilot_cancellation import estornar_item_piloto
from app.produtos_models import EstoqueMovimentacao, ProdutoLote, ProdutoBlingSync
from app.vendas_models import Venda, VendaItem, VendaPagamento
from tests.unit.test_ifood_pdv_pilot import (
    online_virtual_bag,
    pilot_db,
    received_online_event,
)

__all__ = ["pilot_db"]


@pytest.fixture
def cancellation_db(pilot_db, monkeypatch):
    c = pilot_db
    for model in (
        ProdutoLote,
        EstoqueMovimentacao,
        LancamentoManual,
        MovimentacaoCaixa,
        MovimentacaoFinanceira,
        ProdutoBlingSync,
    ):
        with c.db.bind.begin() as conn:
            conn.execute(
                CreateTable(model.__table__, include_foreign_key_constraints=[])
            )
    monkeypatch.setattr("app.estoque.service._agenda_sync_bling", lambda *a, **kw: None)
    monkeypatch.setattr(
        "app.estoque.service.EstoqueService._ajustar_estoque_canal_online",
        lambda *a, **kw: None,
    )
    c.order.payload = online_virtual_bag(c.order.payload)
    received_online_event(c)
    import_pdv_pilot(
        c.db, tenant_id=c.tenant_id, order_id=c.order.ifood_order_id, actor_id=c.user_id
    )
    c.sale = c.db.query(Venda).one()
    c.item = c.db.query(VendaItem).one()
    c.bridge = c.db.query(IfoodPdvBridge).one()
    c.lot = ProdutoLote(
        tenant_id=c.tenant_id,
        produto_id=c.product.id,
        nome_lote="Origem FIFO",
        quantidade_inicial=1,
        quantidade_disponivel=1,
        ordem_entrada=1,
        custo_unitario=43.94,
        status="ativo",
    )
    c.db.add(c.lot)
    c.db.flush()
    return c


def _conclude(c):
    def fifo(**kw):
        before = c.product.estoque_atual
        c.product.estoque_atual -= 1
        c.lot.quantidade_disponivel = 0
        c.lot.status = "esgotado"
        move = EstoqueMovimentacao(
            tenant_id=c.tenant_id,
            produto_id=c.product.id,
            user_id=c.user_id,
            tipo="saida",
            motivo="venda",
            quantidade=1,
            quantidade_anterior=before,
            quantidade_nova=c.product.estoque_atual,
            custo_unitario=43.94,
            valor_total=43.94,
            referencia_id=c.sale.id,
            referencia_tipo="venda",
            lotes_consumidos=json.dumps([{"lote_id": c.lot.id, "quantidade": 1}]),
        )
        c.db.add(move)
        c.db.flush()
        c.item.lote_id = c.lot.id
        return [
            {
                "produto_id": c.product.id,
                "movimentacao_id": move.id,
                "quantidade": 1,
                "valor_total": 43.94,
            }
        ]

    finalize_online_pdv_pilot(
        c.db,
        tenant_id=c.tenant_id,
        order_id=c.order.ifood_order_id,
        actor_id=c.user_id,
        processar_baixa_estoque_item=fifo,
    )
    c.proof = deepcopy(c.item.custo_original_saida)
    c.product.preco_custo = 9999
    c.db.flush()


def test_reserved_cancellation_only_releases_and_marks_external_refund_pending(
    cancellation_db,
):
    c = cancellation_db
    prepare_pilot_cancellation(c.db, c.sale)
    complete_pilot_cancellation(c.db, c.bridge)
    c.db.flush()
    summary = pdv_bridge_summary(c.db, c.order)
    assert c.product.estoque_atual == 31
    assert c.lot.quantidade_disponivel == 1
    assert c.db.query(EstoqueMovimentacao).count() == 0
    assert c.db.query(VendaPagamento).count() == 0
    assert summary["stock_restored"] is False
    assert summary["cancellation"]["refund_status"] == "pending_provider_review"
    assert summary["cancellation"]["refunded_amount"] is None
    assert summary["cancellation"]["provider_cancellation_confirmed"] is False


def test_sold_cancellation_recomposes_original_lot_and_cost_without_rewriting_proof(
    cancellation_db,
):
    c = cancellation_db
    _conclude(c)
    original_payment = deepcopy(c.bridge.online_financial_evidence["payment"])
    prepare_pilot_cancellation(c.db, c.sale)
    result = estornar_item_piloto(c.db, c.bridge, c.sale, c.item, c.user_id, "QA local")
    complete_pilot_cancellation(c.db, c.bridge)
    c.db.flush()
    entry = c.db.get(EstoqueMovimentacao, result["movimentacao_id"])
    assert c.product.estoque_atual == 31
    assert c.lot.quantidade_disponivel == 1 and c.lot.status == "ativo"
    assert c.item.custo_original_saida == c.proof
    assert entry.valor_total == 43.94 and entry.custo_unitario == 43.94
    assert entry.lote_id == c.lot.id
    assert json.loads(entry.lotes_consumidos)[0]["venda_item_id"] == c.item.id
    assert c.bridge.online_financial_evidence["payment"] == original_payment
    assert (
        c.bridge.online_financial_evidence["receivable"]["status"]
        == "cancelled_pending_provider_review"
    )
    summary = pdv_bridge_summary(c.db, c.order)
    assert summary["stock_restored"] is True
    assert summary["stock_decreased"] is True  # Preserva que a baixa original ocorreu.
    assert summary["cancellation"]["stock_reversal"]["movement_id"] == entry.id
    assert summary["cancellation"]["refunded_amount"] is None


@pytest.mark.parametrize(
    "status,validity,expected",
    [
        ("bloqueado", None, "bloqueado"),
        ("vencido", None, "vencido"),
        ("esgotado", datetime.now() - timedelta(days=2), "vencido"),
    ],
)
def test_recomposition_does_not_release_blocked_or_expired_lot(
    cancellation_db, status, validity, expected
):
    c = cancellation_db
    _conclude(c)
    c.lot.status, c.lot.data_validade = status, validity
    prepare_pilot_cancellation(c.db, c.sale)
    estornar_item_piloto(c.db, c.bridge, c.sale, c.item, c.user_id, "QA")
    assert c.lot.quantidade_disponivel == 1
    assert c.lot.status == expected


@pytest.mark.parametrize(
    "field,value",
    [
        ("movimentacao_id", True),
        ("venda_item_id", True),
        ("versao", True),
        ("tenant_estoque_id", str(uuid4())),
        ("movimentacao_id", 99999),
        ("quantidade", "2"),
        ("custo_total", "0"),
        ("custo_total", "NaN"),
        ("capturado_em", None),
        ("capturado_em", "bad"),
        ("capturado_em", "2026-10-24"),
    ],
)
def test_invalid_original_proof_blocks_return_before_stock_change(
    cancellation_db, field, value
):
    c = cancellation_db
    _conclude(c)
    c.item.custo_original_saida = {**c.proof, field: value}
    # O comparador Python considera True == 1; force o JSON corrompido a ser
    # persistido para reproduzir uma prova carregada do banco, nao um dirty noop.
    flag_modified(c.item, "custo_original_saida")
    prepare_pilot_cancellation(c.db, c.sale)
    with pytest.raises(HTTPException) as exc:
        estornar_item_piloto(c.db, c.bridge, c.sale, c.item, c.user_id, "QA")
    assert exc.value.status_code == 409
    assert c.product.estoque_atual == 30 and c.lot.quantidade_disponivel == 0
    assert c.db.query(EstoqueMovimentacao).filter_by(tipo="entrada").count() == 0


@pytest.mark.parametrize(
    "field,value",
    [
        ("valor_total", 77),
        ("quantidade", 2),
        ("motivo", "ajuste"),
        ("status", "cancelado"),
    ],
)
def test_inconsistent_original_exit_blocks_return(cancellation_db, field, value):
    c = cancellation_db
    _conclude(c)
    setattr(c.db.query(EstoqueMovimentacao).one(), field, value)
    prepare_pilot_cancellation(c.db, c.sale)
    with pytest.raises(HTTPException):
        estornar_item_piloto(c.db, c.bridge, c.sale, c.item, c.user_id, "QA")
    assert c.product.estoque_atual == 30 and c.lot.quantidade_disponivel == 0


def test_prior_stock_return_blocks_second_return(cancellation_db):
    c = cancellation_db
    _conclude(c)
    prepare_pilot_cancellation(c.db, c.sale)
    estornar_item_piloto(c.db, c.bridge, c.sale, c.item, c.user_id, "QA")
    with pytest.raises(HTTPException):
        estornar_item_piloto(c.db, c.bridge, c.sale, c.item, c.user_id, "QA repetido")
    assert c.product.estoque_atual == 31 and c.lot.quantidade_disponivel == 1
    assert c.db.query(EstoqueMovimentacao).filter_by(tipo="entrada").count() == 1


def test_cannot_mark_sold_bridge_cancelled_without_stock_reversal(cancellation_db):
    c = cancellation_db
    _conclude(c)
    prepare_pilot_cancellation(c.db, c.sale)
    with pytest.raises(HTTPException):
        complete_pilot_cancellation(c.db, c.bridge)
    assert c.bridge.status == "sold" and c.product.estoque_atual == 30


@pytest.mark.parametrize(
    "key,value",
    [
        ("IFOOD_PDV_PILOT_ORDER_ID", str(uuid4())),
        ("IFOOD_PDV_PILOT_MERCHANT_ID", str(uuid4())),
        ("IFOOD_PDV_PILOT_ENABLED", False),
        ("ENVIRONMENT", "production"),
    ],
)
def test_cancellation_enforces_exact_pilot_scope(
    cancellation_db, monkeypatch, key, value
):
    c = cancellation_db
    monkeypatch.setattr(settings, key, value)
    with pytest.raises(HTTPException):
        prepare_pilot_cancellation(c.db, c.sale)
    assert c.bridge.status == "reserved" and c.product.estoque_atual == 31


@pytest.mark.parametrize(
    "field,value",
    [
        ("gateway_payment_id", "altered"),
        ("valor", 1),
        ("caixa_id", 77),
        ("status", "estornado"),
    ],
)
def test_changed_online_payment_is_not_silently_cancelled(
    cancellation_db, field, value
):
    c = cancellation_db
    _conclude(c)
    setattr(c.db.query(VendaPagamento).one(), field, value)
    with pytest.raises(HTTPException):
        prepare_pilot_cancellation(c.db, c.sale)
    assert c.bridge.status == "sold" and c.product.estoque_atual == 30


def test_remote_cancelled_status_allows_explicit_local_cancellation_only(
    cancellation_db,
):
    c = cancellation_db
    c.order.status = "CANCELLED"
    prepare_pilot_cancellation(c.db, c.sale)
    assert c.bridge.status == "reserved" and c.product.estoque_atual == 31
    complete_pilot_cancellation(c.db, c.bridge)
    assert c.bridge.status == "cancelled"


def test_unrelated_channel_does_not_query_pilot_tables():
    from types import SimpleNamespace

    assert prepare_pilot_cancellation(None, SimpleNamespace(canal="app")) is None
