from decimal import Decimal
from types import SimpleNamespace
from uuid import UUID

import pytest
from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy.sql import operators

import app.db.base  # noqa: F401 - relacionamentos dos modelos fiscais/venda
from app.nfe import correcao_routes as routes
from app.produtos_estoque_models import EstoqueMovimentacao


TENANT = UUID("11111111-1111-1111-1111-111111111111")
OUTRO_TENANT = UUID("22222222-2222-2222-2222-222222222222")


class Query:
    """Aplica os filtros ORM reais sobre registros do cenário de teste."""

    def __init__(self, db, entity):
        self.db = db
        self.model = getattr(entity, "class_", entity)
        self.column = getattr(entity, "key", None)
        self.rows = list(db.rows.get(self.model, []))

    def filter(self, *criteria):
        for criterion in criteria:
            key, value = criterion.left.key, getattr(criterion.right, "value", None)
            def matches(row):
                atual = getattr(row, key)
                if criterion.operator in (operators.ne, operators.is_not):
                    return atual != value
                return atual == value
            self.rows = [row for row in self.rows if matches(row)]
        return self

    def populate_existing(self):
        return self

    def with_for_update(self):
        self.db.locked.append(self.model)
        return self

    def first(self):
        return self.rows[0] if self.rows else None

    def all(self):
        return [(getattr(row, self.column),) for row in self.rows] if self.column else self.rows


class Db:
    def __init__(self, rows):
        self.rows = rows
        self.locked = []
        self.added = []
        self.commits = 0
        self.rollbacks = 0

    def query(self, model):
        return Query(self, model)

    def add(self, record):
        self.added.append(record)
        self.rows.setdefault(type(record), []).append(record)

    def flush(self):
        pass

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1


def scenario(monkeypatch, *, lot=True, inferred=False, kit=False, config=True):
    sale = SimpleNamespace(
        id=42, tenant_id=TENANT, status="finalizada", total=Decimal("39.90"),
        nfe_status="REJEITADA", nfe_provider="intnfe", nfe_bling_id=None,
        nfe_protocolo=None, nfe_data_autorizacao=None,
        nfe_correlation_id="rejeicao-42", nfe_codigo_erro="778",
    )
    product = SimpleNamespace(
        id=9, tenant_id=TENANT, nome="Coleira", tipo_produto="KIT" if kit else "SIMPLES",
        ncm="42010090", cest="2800100", origem="0", cfop="5102",
        aliquota_icms=18, aliquota_pis=1.65, aliquota_cofins=7.6, estoque_atual=12,
    )
    item = SimpleNamespace(
        id=23, tenant_id=TENANT, venda_id=42, produto_id=9, produto=product,
        tipo="produto", lote_id=71 if lot and not inferred else None,
        estoque_origem_tenant_id=None, quantidade=1, subtotal=Decimal("39.90"),
    )
    fiscal = SimpleNamespace(
        id=4, tenant_id=TENANT, produto_id=9, produto_kit_id=9,
        ncm="42010090", cest="2800100", origem_mercadoria="0", cfop_venda="5102",
        cst_icms="102", pis_cst="49", cofins_cst="49",
        icms_aliquota=Decimal("18"), pis_aliquota=Decimal("1.65"),
        cofins_aliquota=Decimal("7.60"), icms_st=False, herdado_da_empresa=False,
    )
    lote = SimpleNamespace(
        id=71, tenant_id=TENANT, produto_id=9, fiscal_ncm="42010000",
        fiscal_cest="2800100", fiscal_origem_mercadoria="0", fiscal_icms_st=False,
        quantidade_disponivel=2, quantidade_reservada=0,
    )
    company = SimpleNamespace(
        id=1, tenant_id=TENANT, simples_ativo=True, regime_tributario="Simples Nacional",
        cfop_venda_interna="5102", cfop_venda_interestadual="6102",
        icms_aliquota_interna=Decimal("18"), pis_cst_padrao="49", cofins_cst_padrao="49",
        pis_aliquota=Decimal("1.65"), cofins_aliquota=Decimal("7.60"),
    )
    movements = [SimpleNamespace(
        tenant_id=TENANT, produto_id=9, referencia_id=42, referencia_tipo="venda",
        status="ativo", lotes_consumidos='[{"lote_id":71,"quantidade":1}]',
    )] if inferred else []
    db = Db({
        routes.Venda: [sale], routes.VendaItem: [item], routes.Produto: [product],
        routes.ProdutoLote: [lote] if lot else [],
        routes.ProdutoConfigFiscal: [fiscal] if config and not kit else [],
        routes.KitConfigFiscal: [fiscal] if config and kit else [],
        routes.EmpresaConfigFiscal: [company], EstoqueMovimentacao: movements,
    })
    audit = []
    monkeypatch.setattr(routes, "log_action", lambda *args, **kw: audit.append(kw))
    monkeypatch.setattr(routes, "get_tenant", lambda *_args: SimpleNamespace(uf="SP"))
    return SimpleNamespace(db=db, sale=sale, product=product, item=item, fiscal=fiscal, lote=lote, company=company, audit=audit)


def save(ctx, **patch):
    return routes.salvar_fiscal_item_rejeitado(
        42, 23, routes.CorrecaoFiscalItemRequest(**patch),
        db=ctx.db, user_and_tenant=(SimpleNamespace(id=5), TENANT),
    )


@pytest.mark.parametrize("inferred", [False, True])
def test_ncm_patch_updates_actual_lot_and_catalog_without_changing_sale(monkeypatch, inferred):
    ctx = scenario(monkeypatch, inferred=inferred)
    sale_before, item_before = vars(ctx.sale).copy(), vars(ctx.item).copy()
    result = save(ctx, ncm="4201.00.90")

    assert ctx.lote.fiscal_ncm == ctx.fiscal.ncm == ctx.product.ncm == "42010090"
    assert ctx.fiscal.cest == "2800100" and ctx.fiscal.pis_cst == "49"
    assert ctx.fiscal.icms_aliquota == Decimal("18")
    assert ctx.product.estoque_atual == 12 and ctx.lote.quantidade_disponivel == 2
    assert vars(ctx.sale) == sale_before and vars(ctx.item) == item_before
    assert {entry["tipo"] for entry in result["fontes_atualizadas"]} == {"produto", "lote"}
    assert ctx.db.commits == 1 and ctx.db.rollbacks == 0
    assert {routes.Venda, routes.VendaItem, routes.Produto, routes.ProdutoLote, routes.ProdutoConfigFiscal} <= set(ctx.db.locked)
    assert ctx.audit[0]["commit"] is False
    assert ctx.audit[0]["old_value"] == {"ncm": "42010000"}


def test_get_exposes_snapshot_used_by_emission(monkeypatch):
    ctx = scenario(monkeypatch, inferred=True)
    result = routes.obter_fiscal_item_rejeitado(42, 23, ctx.db, (SimpleNamespace(id=5), TENANT))
    assert result["fiscal"]["ncm"] == "42010000"
    assert result["fiscal"]["cst_pis"] == "49"
    assert result["fontes_fiscais"]["ncm"] == {"tipo": "lote", "id": 71}
    assert ctx.db.commits == 0 and ctx.db.added == []


@pytest.mark.parametrize("tipo,ie,st,cfop", [
    ("nfce", None, False, "5102"),
    ("nfe", "123", False, "6102"),
    ("nfe", None, True, "6108"),
])
def test_get_uses_document_destination_and_non_contributor_st_rule(monkeypatch, tipo, ie, st, cfop):
    ctx = scenario(monkeypatch)
    ctx.sale.nfe_tipo = tipo
    ctx.sale.cliente = SimpleNamespace(estado="MS", inscricao_estadual=ie)
    ctx.lote.fiscal_icms_st = st
    result = routes.obter_fiscal_item_rejeitado(42, 23, ctx.db, (SimpleNamespace(id=5), TENANT))
    assert result["fiscal"]["cfop"] == cfop


@pytest.mark.parametrize("status", ["autorizada", "processando", "aguardando", "cancelada", None])
def test_edit_rejects_non_rejected_note_before_any_write(monkeypatch, status):
    ctx = scenario(monkeypatch)
    ctx.sale.nfe_status = status
    with pytest.raises(HTTPException) as exc:
        save(ctx, ncm="42010090")
    assert exc.value.status_code == 409
    assert ctx.lote.fiscal_ncm == "42010000" and ctx.db.commits == 0


@pytest.mark.parametrize("field,value", [
    ("nfe_protocolo", "123"), ("nfe_data_autorizacao", "2026-10-13"),
    ("nfe_bling_id", "bling:123"), ("nfe_provider", "bling"),
])
def test_edit_rejects_external_or_authorized_data_even_if_status_says_rejected(monkeypatch, field, value):
    ctx = scenario(monkeypatch)
    setattr(ctx.sale, field, value)
    with pytest.raises(HTTPException) as exc:
        save(ctx, ncm="42010090")
    assert exc.value.status_code == 409 and ctx.db.commits == 0


@pytest.mark.parametrize("record,status", [("sale", 404), ("item", 404), ("product", 409), ("lote", 409)])
def test_tenant_is_checked_for_sale_item_product_and_lot(monkeypatch, record, status):
    ctx = scenario(monkeypatch)
    getattr(ctx, record).tenant_id = OUTRO_TENANT
    with pytest.raises(HTTPException) as exc:
        save(ctx, ncm="42010090")
    assert exc.value.status_code == status and ctx.db.commits == 0
    assert ctx.lote.fiscal_ncm == "42010000"


def test_item_and_lot_must_belong_to_sale_and_product(monkeypatch):
    ctx = scenario(monkeypatch)
    ctx.item.venda_id = 99
    with pytest.raises(HTTPException) as exc:
        save(ctx, ncm="42010090")
    assert exc.value.status_code == 404
    ctx.item.venda_id = 42
    ctx.lote.produto_id = 99
    with pytest.raises(HTTPException) as exc:
        save(ctx, ncm="42010090")
    assert exc.value.status_code == 409


def test_kit_priority_only_updates_kit_not_lower_priority_lot(monkeypatch):
    ctx = scenario(monkeypatch, kit=True)
    result = save(ctx, ncm="42010099")
    assert ctx.fiscal.ncm == ctx.product.ncm == "42010099"
    assert ctx.lote.fiscal_ncm == "42010000"
    assert result["fontes_atualizadas"] == [{"tipo": "kit", "id": 9, "campos": ["ncm"]}]


def test_new_v2_record_keeps_unpatched_legacy_identification(monkeypatch):
    ctx = scenario(monkeypatch, lot=False, config=False)
    save(ctx, cst_icms="102")
    config = ctx.db.rows[routes.ProdutoConfigFiscal][0]
    assert config.ncm == "42010090" and config.cest == "2800100"
    assert config.origem_mercadoria == "0" and config.cfop_venda == "5102"
    assert config.icms_aliquota is None  # Continua usando a alíquota da empresa.


def test_zero_rate_is_saved_and_does_not_clear_other_fields(monkeypatch):
    ctx = scenario(monkeypatch, lot=False)
    save(ctx, aliquota_pis=0)
    assert ctx.fiscal.pis_aliquota == ctx.product.aliquota_pis == 0
    assert ctx.fiscal.cofins_aliquota == Decimal("7.60")
    assert ctx.fiscal.cst_icms == "102"


def test_ineffective_override_of_automatic_st_rule_is_not_committed(monkeypatch):
    ctx = scenario(monkeypatch)
    ctx.lote.fiscal_icms_st = True
    with pytest.raises(HTTPException) as exc:
        save(ctx, cfop="5102")
    assert exc.value.status_code == 409
    assert ctx.db.commits == 0 and ctx.db.rollbacks == 1


@pytest.mark.parametrize("patch", [
    {"produto_id": 99}, {"lote_id": 22}, {"subtotal": 1},
    {"ncm": "00000000"}, {"ncm": "123"}, {"origem_mercadoria": "9"},
    {"cfop": "1102"}, {"cst_pis": "1"}, {"aliquota_icms": -1},
    {"aliquota_cofins": "7.601"}, {"aliquota_pis": "NaN"},
])
def test_patch_rejects_foreign_ids_non_fiscal_fields_and_malformed_codes(patch):
    with pytest.raises(ValidationError):
        routes.CorrecaoFiscalItemRequest(**patch)
