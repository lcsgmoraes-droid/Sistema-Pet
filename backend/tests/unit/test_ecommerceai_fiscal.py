"""Fluxo fiscal externo com dados fictícios e emissor simulado, sem efeitos comerciais."""

from copy import deepcopy
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import UUID
import re

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from lxml import etree
from pydantic import ValidationError
from sqlalchemy import create_engine, event, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.auth.dependencies import get_current_user_and_tenant
from app.db import get_session
import app.db.base  # noqa: F401 - registro canônico de FKs e relacionamentos
from app.ecommerceai_fiscal import payload, routes, service, configuration
from app.ecommerceai_fiscal.models import (
    FiscalAccount,
    FiscalSkuMapping,
    ExternalFiscalOrder,
)
from app.ecommerceai_fiscal.schemas import OrderInput
from app.intnfe.client import IntNFeError
from app.intnfe.models import IntNFeConnection
from app.models import AuditLog
from app.models import Tenant
from app.ecommerceai_integration_models import (
    EcommerceAIConnection,
    EcommerceAIConnectionRequest,
)
from app.routes import ecommerceai_integration_routes as integration_routes
from app.nfe_cache_models import BlingNotaFiscalCache
from app.produtos_models import Produto
from app.tenancy.context import tenant_context
from tests.helpers.signed_nfe import make_key, sign_nfe

TENANT = UUID("11111111-1111-1111-1111-111111111111")
OTHER = UUID("22222222-2222-2222-2222-222222222222")
CNPJ = "11222333000181"
NOW = datetime(2026, 10, 27, 13, tzinfo=timezone.utc)
PREFIX = "/api/integracoes/ecommerceai/fiscal"
KEY = make_key("352610" + CNPJ + "55001" + f"{777:09}" + "1" + "12345678")


def facts():
    return {
        "schema_version": "1.0",
        "channel": "amazon",
        "seller_id": "SELLER_TESTE",
        "marketplace_id": "A2Q3Y263D00KWC",
        "external_order_id": "701-0000000-0000000",
        "source_revision": 1,
        "order_status": "Unshipped",
        "purchased_at": "2026-10-27T12:00:00Z",
        "source_updated_at": "2026-10-27T12:01:00Z",
        "emitter_cnpj": CNPJ,
        "recipient": {
            "name": "Cliente Ficticio",
            "document": "12345678909",
            "ie_status": "9",
            "address": {
                "street": "Rua Teste",
                "number": "10",
                "district": "Centro",
                "city": "Sao Paulo",
                "municipality_code": "3550308",
                "state": "SP",
                "postal_code": "01001000",
            },
        },
        "items": [
            {
                "external_item_id": "ITEM_TESTE",
                "seller_sku": "KIT_TESTE_2",
                "asin": "ASIN_TESTE",
                "quantity": "1",
                "unit_price": "100.00",
                "gross_amount": "100.00",
                "discount_amount": "0.00",
            }
        ],
        "totals": {
            "currency": "BRL",
            "products": "100.00",
            "discount": "0.00",
            "freight": "0.00",
            "invoice_total": "100.00",
        },
        "payments": [
            {"fiscal_method": "03", "amount": "100.00", "integration_type": "2"}
        ],
        "buyer_paid_total": "100.00",
        "source_evidence": {
            "tax": "available",
            "recipient": "available",
            "payment": "available",
        },
    }


def signed_document(data, *, wrong_recipient=False):
    ns = "http://www.portalfiscal.inf.br/nfe"  # NOSONAR - namespace only
    root = etree.Element("{" + ns + "}nfeProc", nsmap={None: ns}, versao="4.00")

    def node(parent, name, value=None, **attrs):
        item = etree.SubElement(parent, "{" + ns + "}" + name, **attrs)
        if value is not None:
            item.text = str(value)
        return item

    nfe = node(root, "NFe")
    info = node(nfe, "infNFe", Id="NFe" + KEY, versao="4.00")
    ide = node(info, "ide")
    for tag, value in {
        "dhEmi": "2026-10-27T10:00:00-03:00",
        "tpAmb": "1",
        "indPres": "2",
        "indIntermed": "1",
    }.items():
        node(ide, tag, value)
    emit = node(info, "emit")
    node(emit, "CNPJ", CNPJ)
    dest = node(info, "dest")
    node(dest, "CPF", "52998224725" if wrong_recipient else data["destinatario"]["cpf"])
    node(dest, "xNome", data["destinatario"]["razaoSocial"])
    address = node(dest, "enderDest")
    for tag, key in {
        "xLgr": "logradouro",
        "nro": "numero",
        "xBairro": "bairro",
        "xMun": "municipio",
        "cMun": "codigoMunicipio",
        "UF": "uf",
        "CEP": "cep",
    }.items():
        node(address, tag, data["destinatario"]["endereco"][key])
    if data["destinatario"]["endereco"].get("complemento"):
        node(address, "xCpl", data["destinatario"]["endereco"]["complemento"])
    for i, p in enumerate(data["produtos"], 1):
        prod = node(node(info, "det", nItem=str(i)), "prod")
        for tag, key in {
            "cProd": "codigoProduto",
            "xProd": "descricao",
            "qCom": "quantidade",
            "vUnCom": "valorUnitario",
            "vProd": "valorTotal",
        }.items():
            node(prod, tag, p[key])
        node(prod, "vDesc", p.get("desconto", 0))
    totals = node(node(info, "total"), "ICMSTot")
    node(totals, "vProd", sum(p["valorTotal"] for p in data["produtos"]))
    node(totals, "vDesc", sum(p.get("desconto", 0) for p in data["produtos"]))
    node(totals, "vFrete", data["frete"]["valor"])
    node(totals, "vNF", sum(p["valor"] for p in data["pagamentos"]))
    payment = node(info, "pag")
    for p in data["pagamentos"]:
        det = node(payment, "detPag")
        node(det, "tPag", p["formaPagamento"])
        node(det, "vPag", p["valor"])
        if p.get("tipoIntegracao"):
            node(node(det, "card"), "tpIntegra", p["tipoIntegracao"])
    intermediary = node(info, "infIntermed")
    node(intermediary, "CNPJ", data["intermediador"]["cnpj"])
    node(intermediary, "idCadIntTran", data["intermediador"]["identificadorCadastro"])
    node(node(info, "infAdic"), "infCpl", data["informacoesAdicionais"])
    protocol = node(node(root, "protNFe", versao="4.00"), "infProt")
    node(protocol, "chNFe", KEY)
    node(protocol, "cStat", "100")
    return sign_nfe(etree.tostring(root))


@pytest.fixture
def ctx(monkeypatch):
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    for model in (
        Tenant,
        EcommerceAIConnectionRequest,
        EcommerceAIConnection,
        IntNFeConnection,
        Produto,
        FiscalAccount,
        FiscalSkuMapping,
        ExternalFiscalOrder,
        AuditLog,
        BlingNotaFiscalCache,
    ):
        model.__table__.create(engine)
    statements = []
    event.listen(
        engine,
        "before_cursor_execute",
        lambda _c, _cur, statement, _params, _context, _many: statements.append(
            statement
        ),
    )
    db = Session(engine, expire_on_commit=False)
    tenant = SimpleNamespace(id=TENANT, cnpj=CNPJ, status="active")
    connection = SimpleNamespace(
        id=1, tenant_id=TENANT, scopes=["fiscal:prepare", "fiscal:issue", "fiscal:read"]
    )
    fiscal_connection = SimpleNamespace(
        cnpj=CNPJ, emission_environment=1, nfe_series="1"
    )
    account = FiscalAccount(
        tenant_id=TENANT,
        channel="amazon",
        seller_id="SELLER_TESTE",
        marketplace_id="A2Q3Y263D00KWC",
        emitter_cnpj=CNPJ,
        active=True,
        auto_issue_enabled=True,
        activated_at=NOW - timedelta(days=1),
        discount_policy="source_discounts",
        approved_by_user_id=77,
    )
    product = Produto(
        tenant_id=TENANT,
        user_id=77,
        codigo="KIT_INTERNO",
        nome="Kit Ficticio Duas Unidades",
        tipo_produto="KIT",
        unidade="UN",
        ativo=True,
        situacao=True,
    )
    denied = set()

    def permission(_db, _user, code, _tenant, **kw):
        if code in denied:
            raise HTTPException(403, "Permissão negada")

    monkeypatch.setattr(routes, "check_permission", permission)
    monkeypatch.setattr(routes, "get_tenant", lambda *_a: tenant)
    monkeypatch.setattr(service, "get_tenant", lambda *_a: tenant)
    monkeypatch.setattr(configuration, "get_tenant", lambda *_a: tenant)
    monkeypatch.setattr(service, "_connection", lambda *_a, **_kw: fiscal_connection)
    monkeypatch.setattr(routes, "_connection", lambda *_a, **_kw: fiscal_connection)
    monkeypatch.setattr(service, "_access_token", lambda *_a: "token-ficticio")
    monkeypatch.setattr(routes, "_access_token", lambda *_a: "token-ficticio")
    monkeypatch.setattr(service, "now", lambda: NOW)
    emitter = {
        "cnpj": CNPJ,
        "crt": "3",
        "razaoSocial": "Empresa Ficticia",
        "endereco": {"uf": "SP"},
    }
    monkeypatch.setattr(payload, "local_profile", lambda *_a: (deepcopy(emitter), []))
    fiscal = {
        "ncm": "38089199",
        "origem_mercadoria": "0",
        "cfop_interno": "5102",
        "cfop_interestadual": "6102",
        "cfop_interestadual_nao_contribuinte": "6102",
        "cst_icms": "00",
        "icms_aliquota": 18,
        "pis_cst": "01",
        "pis_aliquota": 1.65,
        "cofins_cst": "01",
        "cofins_aliquota": 7.6,
    }
    monkeypatch.setattr(
        payload, "_resolver_fiscal_item_nfe", lambda *_a: deepcopy(fiscal)
    )
    monkeypatch.setattr(
        payload.requests,
        "get",
        lambda *_a, **_kw: SimpleNamespace(
            status_code=200,
            json=lambda: {"localidade": "São Paulo", "uf": "SP", "ibge": "3550308"},
        ),
    )
    provider = SimpleNamespace(status=2, payload=None, wrong_recipient=False)
    api = Mock()

    def send(_access, _kind, body, key):
        provider.payload = deepcopy(body)
        return {"correlationId": "correlacao-ficticia"}

    api.issue_document.side_effect = send
    api.document_status.side_effect = lambda *_a: {
        "status": provider.status,
        "numero": 777 if provider.status in {3, 5} else None,
        "chaveAcesso": KEY if provider.status in {3, 5} else None,
        "protocolo": "135260000000001" if provider.status in {3, 5} else None,
    }
    api.document_xml.side_effect = lambda *_a: signed_document(
        provider.payload, wrong_recipient=provider.wrong_recipient
    )
    api.document_danfe.return_value = b"%PDF-ficticio"
    app = FastAPI()
    app.include_router(routes.router, prefix="/api")
    app.include_router(integration_routes.router, prefix="/api")
    app.dependency_overrides[get_session] = lambda: db
    app.dependency_overrides[get_current_user_and_tenant] = lambda: (
        SimpleNamespace(id=77),
        TENANT,
    )
    app.dependency_overrides[routes.machine_connection] = lambda: connection
    app.dependency_overrides[routes.api_client] = lambda: api
    with tenant_context(TENANT):
        db.add_all([account, product])
        db.flush()
        db.add(
            FiscalSkuMapping(
                tenant_id=TENANT,
                account_id=account.id,
                seller_sku="KIT_TESTE_2",
                product_id=product.id,
                active=True,
                approved_by_user_id=77,
            )
        )
        db.commit()
        with TestClient(app) as client:
            yield SimpleNamespace(
                db=db,
                engine=engine,
                tenant=tenant,
                account=account,
                connection=connection,
                product=product,
                client=client,
                app=app,
                api=api,
                provider=provider,
                denied=denied,
                fiscal=fiscal,
                statements=statements,
            )
    db.close()
    engine.dispose()


def prepare(ctx, source=None):
    return service.upsert(
        ctx.db,
        ctx.connection,
        OrderInput.model_validate(source or facts()).model_dump(mode="json"),
    )


def emit(ctx, view):
    return service.issue(
        ctx.db,
        TENANT,
        view["id"],
        view["source_revision"],
        view["payload_hash"],
        ctx.api,
    )


def test_order_is_independent_ready_and_reuses_fiscal_product_mapping(ctx):
    result = prepare(ctx)
    row = service.get_order(ctx.db, TENANT, result["id"])
    assert result["status"] == "ready" and result["totals"]["invoice_total"] == "100.00"
    assert row.payload["produtos"][0]["codigoProduto"] == "KIT_INTERNO"
    assert row.payload["produtos"][0]["impostos"]["icms"]["valor"] == 18
    assert row.payload["intermediador"]["identificadorCadastro"] == "SELLER_TESTE"
    writes = [
        statement
        for statement in ctx.statements
        if statement.lstrip().upper().startswith(("INSERT", "UPDATE", "DELETE"))
    ]
    assert not any(
        re.search(
            r"\b(vendas|vendas_pagamentos|contas_receber|estoque_movimentacoes|caixa_movimentacoes)\b",
            statement,
        )
        for statement in writes
    )
    ctx.api.issue_document.assert_not_called()


def test_identity_survives_reconnect_and_same_revision_is_idempotent(ctx):
    first = prepare(ctx)
    ctx.connection.id = 99
    assert prepare(ctx)["id"] == first["id"]
    changed = facts()
    changed["recipient"]["name"] = "Outro nome"
    with pytest.raises(HTTPException) as error:
        prepare(ctx, changed)
    assert error.value.status_code == 409
    changed["source_revision"] = 2
    assert prepare(ctx, changed)["source_revision"] == 2
    with pytest.raises(HTTPException):
        prepare(ctx)


def test_identity_unique_is_enforced_by_database(ctx):
    result = prepare(ctx)
    row = service.get_order(ctx.db, TENANT, result["id"])
    duplicate = ExternalFiscalOrder(
        tenant_id=TENANT,
        connection_id=2,
        channel=row.channel,
        seller_id=row.seller_id,
        external_order_id=row.external_order_id,
        source_revision=1,
        source_hash=row.source_hash,
        source=row.source,
        purchased_at=row.purchased_at,
        status="blocked",
        blockers=[],
    )
    ctx.db.add(duplicate)
    with pytest.raises(IntegrityError):
        ctx.db.flush()


@pytest.mark.parametrize(
    "field,value,code",
    [
        ("document", None, "recipient_document_missing"),
        ("document", "***78909", "recipient_document_invalid"),
        ("document", "12345678908", "recipient_document_invalid"),
        ("name", "***", "recipient_name_missing"),
    ],
)
def test_missing_or_masked_buyer_blocks_without_emission(ctx, field, value, code):
    source = facts()
    source["recipient"][field] = value
    result = prepare(ctx, source)
    assert result["status"] == "blocked" and result["blockers"][0]["code"] == code
    ctx.api.issue_document.assert_not_called()


def test_unknown_sku_never_matches_description_or_another_tenant(ctx):
    source = facts()
    source["items"][0]["seller_sku"] = "KIT_INTERNO"
    result = prepare(ctx, source)
    assert result["blockers"][0]["code"] == "sku_unmapped"


def test_geography_completion_requires_matching_city_state_even_with_code(ctx):
    source = facts()
    source["recipient"]["address"]["municipality_code"] = None
    assert prepare(ctx, source)["status"] == "ready"
    source["source_revision"] = 2
    source["recipient"]["address"]["city"] = "Outra Cidade"
    assert prepare(ctx, source)["blockers"][0]["code"] == "geography_mismatch"


def test_geography_does_not_invent_street_number(ctx):
    source = facts()
    source["recipient"]["address"]["number"] = None
    assert prepare(ctx, source)["blockers"][0]["code"] == "address_missing"


def test_discount_difference_requires_human_account_policy(ctx):
    source = facts()
    source["buyer_paid_total"] = "96.11"
    source["payments"][0]["amount"] = "96.11"
    assert prepare(ctx, source)["blockers"][0]["code"] == "payment_total_mismatch"
    ctx.account.discount_policy = "buyer_payment_total"
    ctx.db.commit()
    result = prepare(ctx, source)
    row = service.get_order(ctx.db, TENANT, result["id"])
    assert result["status"] == "ready" and result["totals"]["discount"] == "3.89"
    assert (
        row.discount_audit["source_discount"] == "0.00"
        and row.discount_audit["extra_discount"] == "3.89"
    )
    assert row.payload["produtos"][0]["desconto"] == 3.89


def test_explicit_discount_and_mixed_payments_are_preserved(ctx):
    source = facts()
    source["totals"].update(discount="5.00", invoice_total="95.00")
    source["buyer_paid_total"] = "95.00"
    source["payments"] = [
        {"fiscal_method": "03", "amount": "50.00", "integration_type": "2"},
        {"fiscal_method": "17", "amount": "45.00", "integration_type": "2"},
    ]
    result = prepare(ctx, source)
    row = service.get_order(ctx.db, TENANT, result["id"])
    assert result["status"] == "ready"
    assert row.payload["pagamentos"] == [
        {"formaPagamento": "03", "valor": 50.0, "tipoIntegracao": "2"},
        {"formaPagamento": "17", "valor": 45.0, "tipoIntegracao": "2"},
    ]
    assert row.payload["produtos"][0]["desconto"] == 5


def test_freight_is_allocated_to_product_and_tax_base(ctx):
    source = facts()
    source["totals"].update(freight="10.00", invoice_total="110.00")
    source["buyer_paid_total"] = "110.00"
    source["payments"][0]["amount"] = "110.00"
    result = prepare(ctx, source)
    p = service.get_order(ctx.db, TENANT, result["id"]).payload["produtos"][0]
    assert p["frete"] == 10 and p["impostos"]["icms"]["valor"] == 19.8
    assert p["impostos"]["pis"]["baseCalculo"] == 110


def test_historical_cutoff_needs_explicit_human_review(ctx):
    source = facts()
    source["purchased_at"] = "2026-10-25T12:00:00Z"
    result = prepare(ctx, source)
    assert (
        result["status"] == "blocked"
        and result["blockers"][0]["code"] == "historical_order_requires_review"
    )
    assert service.review(ctx.db, TENANT, result["id"], 77)["status"] == "ready"
    source["source_revision"] = 2
    source["purchased_at"] = "2026-10-27T12:00:00Z"
    with pytest.raises(HTTPException):
        prepare(ctx, source)


def test_automatic_off_does_not_authorize_machine_issue(ctx):
    ctx.account.auto_issue_enabled = False
    ctx.db.commit()
    result = prepare(ctx)
    with pytest.raises(HTTPException) as error:
        emit(ctx, result)
    assert error.value.detail["code"] == "automatic_emission_disabled"
    ctx.api.issue_document.assert_not_called()


def test_snapshot_is_frozen_and_first_issue_is_not_repeated(ctx):
    result = prepare(ctx)
    assert emit(ctx, result)["status"] == "processing"
    assert emit(ctx, result)["status"] == "processing"
    assert ctx.api.issue_document.call_count == 1
    changed = facts()
    changed["source_revision"] = 2
    with pytest.raises(HTTPException):
        prepare(ctx, changed)


def test_configuration_change_requires_new_expected_payload_hash(ctx):
    result = prepare(ctx)
    ctx.product.nome = "Descrição revisada"
    ctx.db.commit()
    with pytest.raises(HTTPException) as error:
        emit(ctx, result)
    assert error.value.detail["code"] == "snapshot_conflict"
    ctx.api.issue_document.assert_not_called()


def test_lease_prevents_snapshot_change_before_idempotency_is_committed(ctx):
    result = prepare(ctx)
    row = service.get_order(ctx.db, TENANT, result["id"])
    token = service._claim(ctx.db, row)
    changed = facts()
    changed["source_revision"] = 2
    changed["recipient"]["name"] = "Novo nome"
    with pytest.raises(HTTPException) as error:
        prepare(ctx, changed)
    assert error.value.detail["code"] == "fiscal_operation_in_progress"
    assert (
        service.get_order(ctx.db, TENANT, row.id).payload_hash == result["payload_hash"]
    )
    with pytest.raises(HTTPException):
        service._claim(ctx.db, row)
    assert service.get_order(ctx.db, TENANT, row.id).lease_token == token


def test_timeout_recovers_same_frozen_key_and_never_renews_expired_key(ctx):
    result = prepare(ctx)
    ctx.api.issue_document.side_effect = IntNFeError(
        "EmissorIndisponivel", uncertain=True
    )
    assert emit(ctx, result)["status"] == "unknown"
    row = service.get_order(ctx.db, TENANT, result["id"])
    key = row.idempotency_key
    frozen = deepcopy(row.payload)
    row.submitted_at = NOW - timedelta(minutes=3)
    ctx.db.commit()
    service.consult(ctx.db, TENANT, row.id, ctx.api)
    assert ctx.api.issue_document.call_count == 2
    assert ctx.api.issue_document.call_args.args[2:] == (frozen, key)
    row.submitted_at = NOW - timedelta(hours=23)
    ctx.db.commit()
    assert (
        service.consult(ctx.db, TENANT, row.id, ctx.api)["blockers"][0]["code"]
        == "idempotency_window_expired"
    )
    assert ctx.api.issue_document.call_count == 2 and row.idempotency_key == key


def test_authorized_xml_is_mathematically_verified_bound_and_returned_intact(ctx):
    result = prepare(ctx)
    ctx.provider.status = 3
    authorized = emit(ctx, result)
    assert authorized["status"] == "authorized" and authorized["xml_available"]
    row, content = service.xml_document(ctx.db, TENANT, result["id"])
    assert content is row.xml
    assert service.xml_document(ctx.db, TENANT, row.id)[1] == content
    cache = (
        ctx.db.query(BlingNotaFiscalCache)
        .filter(BlingNotaFiscalCache.bling_id == "fiscal-externa-" + str(row.id))
        .one()
    )
    assert cache.venda_id is None and cache.source == "ecommerceai_fiscal"


def test_authorized_but_wrong_buyer_xml_is_never_delivered(ctx):
    result = prepare(ctx)
    ctx.provider.status = 3
    ctx.provider.wrong_recipient = True
    authorized = emit(ctx, result)
    assert authorized["status"] == "authorized" and not authorized["xml_available"]
    with pytest.raises(HTTPException):
        service.xml_document(ctx.db, TENANT, result["id"])


def test_cancellation_and_temporary_status_never_regress_confirmed_state(ctx):
    result = prepare(ctx)
    ctx.provider.status = 3
    emit(ctx, result)
    ctx.provider.status = 2
    assert (
        service.consult(ctx.db, TENANT, result["id"], ctx.api)["status"] == "authorized"
    )
    ctx.provider.status = 5
    assert (
        service.consult(ctx.db, TENANT, result["id"], ctx.api)["status"] == "canceled"
    )
    with pytest.raises(HTTPException):
        service.xml_document(ctx.db, TENANT, result["id"])


@pytest.mark.parametrize(
    "scope,path,method",
    [
        ("fiscal:prepare", "/orders", "post"),
        ("fiscal:read", "/orders/1", "get"),
        ("fiscal:issue", "/orders/1/emitir", "post"),
    ],
)
def test_legacy_tokens_do_not_gain_fiscal_power(ctx, scope, path, method):
    ctx.connection.scopes = ["catalog:read", "events:write"]
    body = (
        facts()
        if path == "/orders"
        else {"expected_revision": 1, "expected_payload_hash": "a" * 64}
    )
    response = getattr(ctx.client, method)(
        PREFIX + path, **({"json": body} if method == "post" else {})
    )
    assert response.status_code == 403
    ctx.api.issue_document.assert_not_called()


def test_machine_auth_and_human_permissions_are_required(ctx):
    del ctx.app.dependency_overrides[routes.machine_connection]
    assert ctx.client.get(PREFIX + "/orders/1").status_code == 401
    ctx.denied.add("configuracoes.editar")
    body = {"seller_id": "OTHER_SELLER", "emitter_cnpj": CNPJ}
    assert ctx.client.post(PREFIX + "/manage/accounts", json=body).status_code == 403


def test_cross_tenant_rows_are_hidden_in_management_and_machine(ctx):
    result = prepare(ctx)
    ctx.connection.tenant_id = OTHER
    assert ctx.client.get(PREFIX + f"/orders/{result['id']}").status_code == 404
    assert ctx.client.get(PREFIX + "/manage/orders/999").status_code == 404


def test_management_records_cutoff_and_rejects_client_backdate(ctx):
    body = {
        "seller_id": "NEW_SELLER",
        "emitter_cnpj": CNPJ,
        "active": True,
        "auto_issue_enabled": True,
        "discount_policy": "buyer_payment_total",
    }
    response = ctx.client.post(PREFIX + "/manage/accounts", json=body)
    assert response.status_code == 200 and response.json()["activated_at"].startswith(
        "2026-10-27T13:00:00"
    )
    assert (
        ctx.db.query(AuditLog)
        .filter(AuditLog.action == "eai_fiscal_account_save")
        .count()
        == 1
    )
    body["activated_at"] = "2020-01-01T00:00:00Z"
    assert ctx.client.post(PREFIX + "/manage/accounts", json=body).status_code == 422


@pytest.mark.parametrize(
    "mutation",
    [
        lambda f: f.update(ncm="38089199"),
        lambda f: f["items"][0].update(unit_price=100.0),
        lambda f: f.update(purchased_at="2026-10-27T12:00:00"),
    ],
)
def test_source_schema_forbids_tax_injection_floats_and_naive_dates(mutation):
    source = facts()
    mutation(source)
    with pytest.raises(ValidationError):
        OrderInput.model_validate(source)


@pytest.mark.parametrize("change", ["auto_off", "cutoff", "mapping"])
def test_claim_interstice_rechecks_consent_cutoff_and_snapshot_before_intent(
    ctx, monkeypatch, change
):
    result = prepare(ctx)
    original = service._claim

    def interstice(db, row):
        token = original(db, row)
        if change == "auto_off":
            ctx.account.auto_issue_enabled = False
        elif change == "cutoff":
            ctx.account.activated_at = NOW + timedelta(hours=1)
        else:
            ctx.product.nome = "Outra identidade de apresentação"
        db.commit()
        return token

    monkeypatch.setattr(service, "_claim", interstice)
    with pytest.raises(HTTPException) as error:
        emit(ctx, result)
    assert error.value.detail["code"] == "snapshot_conflict"
    row = service.get_order(ctx.db, TENANT, result["id"])
    assert row.idempotency_key is None and row.lease_token is None
    ctx.api.issue_document.assert_not_called()


def test_lease_compare_and_set_works_across_database_sessions(ctx):
    result = prepare(ctx)
    row = service.get_order(ctx.db, TENANT, result["id"])
    service._claim(ctx.db, row)
    with Session(ctx.engine) as competing:
        other = service.get_order(competing, TENANT, row.id)
        with pytest.raises(HTTPException) as error:
            service._claim(competing, other)
        assert error.value.detail["code"] == "fiscal_operation_in_progress"


def test_non_identity_integrity_failure_does_not_recurse(ctx):
    ctx.connection.id = None
    with pytest.raises(HTTPException) as error:
        prepare(ctx)
    assert (
        error.value.status_code == 503
        and error.value.detail["code"] == "storage_conflict"
    )
    assert ctx.db.query(ExternalFiscalOrder).count() == 0


def test_http_end_to_end_returns_exact_xml_and_pdf_and_central_discriminator(ctx):
    created = ctx.client.post(PREFIX + "/orders", json=facts())
    assert created.status_code == 200
    state = created.json()
    ctx.provider.status = 3
    authorized = ctx.client.post(
        PREFIX + f"/orders/{state['id']}/emitir",
        json={
            "expected_revision": state["source_revision"],
            "expected_payload_hash": state["payload_hash"],
        },
    )
    assert authorized.status_code == 200 and authorized.json()["xml_available"]
    expected = service.get_order(ctx.db, TENANT, state["id"]).xml
    xml = ctx.client.get(PREFIX + f"/orders/{state['id']}/xml")
    assert xml.status_code == 200 and xml.content == expected
    pdf = ctx.client.get(PREFIX + f"/orders/{state['id']}/danfe")
    assert pdf.status_code == 200 and pdf.content == b"%PDF-ficticio"
    from app.services.nfe_cache_service import serializar_nota_cache, FONTES_NFE_LOCAIS

    cache = ctx.db.query(BlingNotaFiscalCache).one()
    central = serializar_nota_cache(cache)
    assert central["fiscal_order_id"] == state["id"] and central["venda_id"] is None
    assert central["origem"] == "fiscal_externa" and central["provedor"] == "intnfe"
    assert (
        central["status"] == "autorizada" and "ecommerceai_fiscal" in FONTES_NFE_LOCAIS
    )


def test_cache_tampering_never_releases_xml_even_after_authorization(ctx):
    state = prepare(ctx)
    ctx.provider.status = 3
    emit(ctx, state)
    row = service.get_order(ctx.db, TENANT, state["id"])
    row.xml = row.xml.replace(b"Cliente Ficticio", b"Cliente Divergente")
    ctx.db.commit()
    response = ctx.client.get(PREFIX + f"/orders/{row.id}/xml")
    assert (
        response.status_code == 502
        and response.json()["detail"]["code"] == "xml_not_verified"
    )
    assert b"Cliente Divergente" not in response.content


def test_management_mapping_and_review_cannot_access_other_tenant(ctx):
    source = facts()
    source["purchased_at"] = "2026-10-25T12:00:00Z"
    state = prepare(ctx, source)
    reviewed = ctx.client.post(
        PREFIX + f"/manage/orders/{state['id']}/review",
        json={"acknowledge_historical": True},
    )
    assert reviewed.status_code == 200 and reviewed.json()["status"] == "ready"
    row = service.get_order(ctx.db, TENANT, state["id"])
    assert row.reviewed_by_user_id == 77 and row.historical_reviewed_at
    assert (
        ctx.client.post(
            PREFIX + "/manage/orders/999/review", json={"acknowledge_historical": True}
        ).status_code
        == 404
    )
    body = {"account_id": 999, "seller_sku": "OUTRO", "product_id": ctx.product.id}
    assert ctx.client.post(PREFIX + "/manage/mappings", json=body).status_code == 404


def test_fiscal_scopes_require_explicit_human_consent_and_permission(ctx, monkeypatch):
    request = EcommerceAIConnectionRequest(
        request_id="request-fiscal",
        request_nonce="nonce-fiscal",
        client_id="ecommerceai",
        ecommerceai_user_id="test-user",
        callback_url="https://api.ecommerceai.com.br/callback",
        state="s" * 32,
        requested_scopes=["fiscal:prepare", "fiscal:issue", "fiscal:read"],
        status="pending",
        expires_at=NOW + timedelta(days=1),
    )
    ctx.db.add(request)
    ctx.db.commit()
    endpoint = "/api/integracoes/ecommerceai/requests/request-fiscal/approve"
    assert ctx.client.post(endpoint).status_code == 403
    assert ctx.db.query(EcommerceAIConnection).count() == 0
    import app.security.permissions_service as permissions

    monkeypatch.setattr(permissions, "check_permission", lambda *_a, **_kw: None)
    monkeypatch.setattr(
        integration_routes.settings,
        "ECOMMERCEAI_INTEGRATION_BOOTSTRAP_SECRET",
        "s" * 32,
    )
    monkeypatch.setattr(
        integration_routes.httpx,
        "post",
        lambda *_a, **_kw: SimpleNamespace(raise_for_status=lambda: None),
    )
    accepted = ctx.client.post(endpoint, json={"confirm_fiscal_scopes": True})
    assert accepted.status_code == 200
    saved = ctx.db.query(EcommerceAIConnection).one()
    assert set(saved.scopes) == {"fiscal:prepare", "fiscal:issue", "fiscal:read"}
    assert (
        saved.tenant_id == TENANT and saved.token_hash and saved.status == "connected"
    )


def test_legacy_request_defaults_never_implicitly_request_new_fiscal_scopes():
    request = integration_routes.ConnectionRequestPayload(
        client_id="ecommerceai",
        ecommerceai_user_id="test",
        callback_url="https://example.invalid/callback",
        state="s" * 32,
    )
    assert set(request.requested_scopes) == {"catalog:read", "events:write"}


def config(ctx):
    response = ctx.client.get(PREFIX + "/configuration/accounts")
    assert response.status_code == 200, response.text
    return response.json()


def account_body(ctx, **changes):
    current = {
        "channel": "amazon",
        "seller_id": ctx.account.seller_id,
        "marketplace_id": ctx.account.marketplace_id,
        "emitter_cnpj": ctx.account.emitter_cnpj,
        "active": ctx.account.active,
        "auto_issue_enabled": ctx.account.auto_issue_enabled,
        "upload_enabled": ctx.account.upload_enabled,
        "discount_policy": ctx.account.discount_policy,
    }
    current.update(changes)
    return current


def test_machine_configuration_is_safe_scoped_and_stable(ctx):
    first = config(ctx)
    assert first["schema_version"] == "1.1"
    assert first["corepet_settings_url"].endswith("/configuracoes/integracoes")
    assert len(first["configuration_revision"]) == 64 and len(first["accounts"]) == 1
    account = first["accounts"][0]
    allowed = {
        "id",
        "channel",
        "seller_id",
        "marketplace_id",
        "emitter_cnpj",
        "active",
        "auto_issue_enabled",
        "upload_enabled",
        "discount_policy",
        "activated_at",
        "configuration_revision",
    }
    assert set(account) == allowed and account["upload_enabled"] is False
    assert config(ctx) == first
    assert "snapshot" not in str(first) and "12345678909" not in str(first)
    ctx.connection.scopes = ["fiscal:prepare"]
    assert ctx.client.get(PREFIX + "/configuration/accounts").status_code == 403


def test_configuration_excludes_other_tenants_and_handles_empty_authority(ctx):
    with tenant_context(OTHER):
        ctx.db.add(
            FiscalAccount(
                tenant_id=OTHER,
                channel="amazon",
                seller_id="PRIVATE_OTHER",
                marketplace_id="A2Q3Y263D00KWC",
                emitter_cnpj=CNPJ,
                approved_by_user_id=88,
            )
        )
        ctx.db.commit()
    assert [row["seller_id"] for row in config(ctx)["accounts"]] == ["SELLER_TESTE"]
    ctx.db.query(FiscalSkuMapping).filter(FiscalSkuMapping.tenant_id == TENANT).delete()
    ctx.db.query(FiscalAccount).filter(FiscalAccount.tenant_id == TENANT).delete()
    ctx.db.commit()
    result = config(ctx)
    assert result["accounts"] == [] and len(result["configuration_revision"]) == 64


def test_active_and_upload_default_off_and_upload_does_not_move_cutoff(ctx):
    created = ctx.client.post(
        PREFIX + "/manage/accounts",
        json={"seller_id": "OFF_DEFAULT", "emitter_cnpj": CNPJ},
    )
    assert created.status_code == 200
    body = created.json()
    assert (
        body["active"] is False
        and body["auto_issue_enabled"] is False
        and body["upload_enabled"] is False
    )
    assert body["activated_at"] is None
    before = ctx.account.activated_at
    response = ctx.client.put(
        PREFIX + f"/manage/accounts/{ctx.account.id}",
        json=account_body(ctx, upload_enabled=True),
    )
    assert response.status_code == 200 and response.json()["upload_enabled"] is True
    assert service.aware(ctx.account.activated_at) == service.aware(before)


@pytest.mark.parametrize("flag", ["auto_issue_enabled", "upload_enabled"])
def test_inactive_master_cannot_authorize_new_automatic_posts(ctx, flag):
    body = account_body(
        ctx, active=False, auto_issue_enabled=False, upload_enabled=False
    )
    body[flag] = True
    response = ctx.client.put(PREFIX + f"/manage/accounts/{ctx.account.id}", json=body)
    assert (
        response.status_code == 422
        and response.json()["detail"]["code"] == "account_invalid"
    )


def test_master_activation_and_automatic_issue_restart_server_cutoff(ctx, monkeypatch):
    response = ctx.client.put(
        PREFIX + f"/manage/accounts/{ctx.account.id}",
        json=account_body(
            ctx, active=False, auto_issue_enabled=False, upload_enabled=False
        ),
    )
    assert response.status_code == 200
    activated = ctx.client.put(
        PREFIX + f"/manage/accounts/{ctx.account.id}",
        json=account_body(ctx, active=True, auto_issue_enabled=False),
    )
    assert (
        activated.status_code == 200 and service.aware(ctx.account.activated_at) == NOW
    )
    later = NOW + timedelta(hours=1)
    monkeypatch.setattr(service, "now", lambda: later)
    auto = ctx.client.put(
        PREFIX + f"/manage/accounts/{ctx.account.id}",
        json=account_body(ctx, auto_issue_enabled=True),
    )
    assert auto.status_code == 200 and service.aware(ctx.account.activated_at) == later


def test_configuration_revision_tracks_mapping_and_effective_fiscal_fixes(ctx):
    original = config(ctx)
    mapping = ctx.db.query(FiscalSkuMapping).one()
    changed = ctx.client.put(
        PREFIX + f"/manage/mappings/{mapping.id}",
        json={
            "account_id": ctx.account.id,
            "seller_sku": "SKU_REVIEWED",
            "product_id": ctx.product.id,
            "active": True,
        },
    )
    assert changed.status_code == 200
    mapped = config(ctx)
    assert mapped["configuration_revision"] != original["configuration_revision"]
    assert (
        mapped["accounts"][0]["configuration_revision"]
        != original["accounts"][0]["configuration_revision"]
    )
    ctx.fiscal["ncm"] = "23091000"
    fixed = config(ctx)
    assert fixed["configuration_revision"] != mapped["configuration_revision"]
    assert (
        fixed["accounts"][0]["configuration_revision"]
        != mapped["accounts"][0]["configuration_revision"]
    )


def test_configuration_changes_without_hashing_stock_or_catalog_price(ctx):
    before = config(ctx)
    ctx.product.estoque_atual = 42
    ctx.product.preco_venda = 999
    ctx.db.commit()
    assert config(ctx)["configuration_revision"] == before["configuration_revision"]


def test_inactive_master_blocks_new_emission_but_preserves_authorized_documents(ctx):
    state = prepare(ctx)
    ctx.provider.status = 3
    emit(ctx, state)
    content = service.xml_document(ctx.db, TENANT, state["id"])[1]
    disabled = ctx.client.put(
        PREFIX + f"/manage/accounts/{ctx.account.id}",
        json=account_body(
            ctx, active=False, auto_issue_enabled=False, upload_enabled=False
        ),
    )
    assert disabled.status_code == 200
    assert service.xml_document(ctx.db, TENANT, state["id"])[1] == content
    fresh = facts()
    fresh["external_order_id"] = "701-0000000-0000001"
    blocked = prepare(ctx, fresh)
    assert blocked["status"] == "blocked"
    ctx.api.issue_document.assert_called_once()


@pytest.mark.parametrize(
    "url",
    [
        "javascript:alert(1)",
        "https://user:private@corepet.com.br",
        "https://corepet.com.br/api",
        "https://[::1",
    ],
)
def test_authority_settings_url_never_exposes_credentials_or_unsafe_scheme(
    ctx, monkeypatch, url
):
    monkeypatch.setattr(configuration.settings, "COREPET_FRONTEND_URL", url)
    result = config(ctx)
    assert result["corepet_settings_url"] is None
    assert "private" not in str(result)


def test_database_defaults_do_not_activate_master_or_upload(ctx):
    ctx.db.execute(
        text(
            "INSERT INTO ecommerceai_fiscal_accounts "
            "(tenant_id,channel,seller_id,marketplace_id,emitter_cnpj,auto_issue_enabled,discount_policy,approved_by_user_id) "
            "VALUES (:tenant,'amazon','RAW_DEFAULT','A2Q3Y263D00KWC',:cnpj,0,'source_discounts',77)"
        ),
        {"tenant": TENANT.hex, "cnpj": CNPJ},
    )
    ctx.db.commit()
    row = (
        ctx.db.query(FiscalAccount)
        .filter(
            FiscalAccount.tenant_id == TENANT, FiscalAccount.seller_id == "RAW_DEFAULT"
        )
        .one()
    )
    assert (
        row.active is False
        and row.upload_enabled is False
        and row.configuration_version == 1
    )
