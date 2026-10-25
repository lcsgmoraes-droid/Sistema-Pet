"""Cruzamento local por IDs exatos e chegada tardia das cobrancas Financial."""

from datetime import date, datetime, timezone
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.schema import CreateTable

from app import caixa_models, financeiro_models, produtos_models  # noqa: F401 - relational registry
from app.models import Cliente  # noqa: F401 - relational registry
from app.ifood_financial_cost_models import IfoodFinancialSaleLink
from app.ifood_financial_models import (
    IfoodFinancialEvent,
    IfoodFinancialOrderCosts,
    IfoodFinancialSnapshot,
)
from app.ifood_integration_models import IfoodMerchantConfig
from app.ifood_order_models import IfoodOrder, IfoodPdvBridge
from app.integrations.ifood.financial import (
    IfoodFinancialError,
    SOURCE,
    import_financial_pages,
)
from app.integrations.ifood.sale_financials import (
    resolve_sale_financials,
    resolve_sales_financials,
)
from app.tenancy.context import tenant_context
from app.vendas_models import Venda, VendaItem
from app.vendas_devolucoes_models import VendaDevolucao

BEGIN = END = "2026-10-24"
NOW = datetime(2026, 10, 24, 23, 43, tzinfo=timezone.utc)


@pytest.fixture
def fixture(monkeypatch):
    monkeypatch.setattr(
        "app.integrations.ifood.sale_financials.settings.ENVIRONMENT", "development"
    )
    engine = create_engine("sqlite:///:memory:")
    # Este teste verifica consultas e isolamento. FKs reais da ponte ja possuem
    # ensaio PostgreSQL; nao e necessario criar todo o ERP nesta fixture.
    with engine.begin() as connection:
        for model in (
            IfoodMerchantConfig,
            IfoodOrder,
            IfoodPdvBridge,
            IfoodFinancialSaleLink,
            IfoodFinancialSnapshot,
            IfoodFinancialEvent,
            IfoodFinancialOrderCosts,
            Venda,
            VendaItem,
            VendaDevolucao,
        ):
            connection.execute(
                CreateTable(model.__table__, include_foreign_key_constraints=[])
            )
    db = sessionmaker(bind=engine)()
    tenant, merchant, order = uuid4(), str(uuid4()), str(uuid4())
    with tenant_context(tenant):
        db.execute(
            IfoodMerchantConfig.__table__.insert().values(
                tenant_id=tenant, merchant_id=merchant
            )
        )
        db.execute(
            Venda.__table__.insert().values(
                id=2,
                tenant_id=tenant,
                numero_venda="202610240002",
                vendedor_id=1,
                user_id=1,
                subtotal=65,
                total=73.9,
                status="finalizada",
                canal="ifood",
            )
        )
        db.execute(
            IfoodOrder.__table__.insert().values(
                tenant_id=tenant,
                merchant_id=merchant,
                ifood_order_id=order,
                status="CONFIRMED",
                payload={"operationMode": {"delivery": {"provider": "MERCHANT"}}},
            )
        )
        db.execute(
            IfoodPdvBridge.__table__.insert().values(
                tenant_id=tenant,
                merchant_id=merchant,
                ifood_order_id=order,
                sale_id=2,
                reservation_id=1,
                product_id=1,
                quantity=1,
                unit_price=65,
                evidence_hash="a" * 64,
                status="sold",
                actor_id=1,
                stock_decreased_at=NOW,
                online_financial_evidence={
                    "checkout": {
                        "items_total": 65,
                        "delivery_fee": 8.9,
                        "ifood_service_fee": 1.99,
                        "operational_total": 73.9,
                        "customer_total": 75.89,
                    }
                },
            )
        )
        db.commit()
        yield SimpleNamespace(
            db=db, engine=engine, tenant=tenant, merchant=merchant, order=order
        )
    db.close()
    engine.dispose()


def entry(f, name, amount, **changes):
    result = {
        "name": name,
        "description": "Evidencia ficticia apenas neste teste unitario",
        "product": "IFOOD",
        "trigger": "ORDER_CONCLUDED",
        "competence": "2026-10",
        "dateTime": "2026-10-24T23:50:00Z",
        "period": {"beginDate": BEGIN, "endDate": END},
        "reference": {"type": "ORDER", "id": f.order, "date": "2026-10-24T23:43:07Z"},
        "hasTransferImpact": True,
        "amount": {"value": str(amount)},
        "receiver": {"businessId": f.merchant, "businessType": "MERCHANT"},
        "payment": {"method": "CREDIT", "liability": "IFOOD"},
    }
    result.update(changes)
    return result


def imported(f, *events, source=SOURCE):
    import_financial_pages(
        f.db,
        f.tenant,
        f.merchant,
        BEGIN,
        END,
        [
            {
                "page": 1,
                "size": 100,
                "hasNextPage": False,
                "financialEvents": list(events),
            }
        ],
        actor_id=1,
        source=source,
    )
    f.db.commit()


def resolve(f, **kwargs):
    return resolve_sale_financials(f.db, f.tenant, 2, **kwargs)


def test_pedido_sem_financial_preserva_checkout_e_pendencias_individuais(fixture):
    result = resolve(fixture)
    assert result["charges"] == []
    assert result["fee_total"] is None
    assert {item["code"] for item in result["pending_components"]} == {
        "ORDER_COMMISSION",
        "PAYMENT_TRANSACTION_FEE",
    }
    assert result["delivery_provider"] == "MERCHANT"
    assert result["checkout"] == {
        "items_total": 65,
        "delivery_fee": 8.9,
        "ifood_service_fee": 1.99,
        "operational_total": 73.9,
        "customer_total": 75.89,
    }


def test_cobranca_parcial_persiste_e_nova_revisao_completa_sem_cache_ou_soma_dupla(
    fixture,
):
    f = fixture
    before = resolve(f)
    commission = entry(
        f,
        "ORDER_COMMISSION",
        "-9.75",
        billing={"baseValue": "65.00", "feePercentage": "15.00"},
    )
    imported(f, commission)
    partial = resolve(f)
    assert partial["charges"][0]["label"] == "Comissão iFood"
    assert partial["charges"][0]["amount"] == 9.75
    assert partial["charges"][0]["signed_amount"] == -9.75
    assert partial["charges"][0]["billing"] == {
        "base_value": "65.00",
        "fee_percentage": "15.00",
    }
    assert partial["fee_known_total"] == 9.75 and partial["fee_total"] is None
    assert [item["code"] for item in partial["pending_components"]] == [
        "PAYMENT_TRANSACTION_FEE"
    ]
    imported(f, commission, entry(f, "PAYMENT_TRANSACTION_FEE", "-1.95"))
    complete = resolve(f)
    assert complete["complete"] is True and complete["pending_components"] == []
    assert complete["fee_total"] == 11.7
    assert len(complete["charges"]) == 2 and complete["charges"][0]["revision"] == 2
    assert (
        len({before["fingerprint"], partial["fingerprint"], complete["fingerprint"]})
        == 3
    )
    assert resolve(f) == complete
    # Valor substituido na revisao atual tambem substitui o total anterior.
    imported(
        f,
        entry(f, "ORDER_COMMISSION", "-6.50"),
        entry(f, "PAYMENT_TRANSACTION_FEE", "0"),
    )
    assert resolve(f)["fee_total"] == 6.5


def test_zero_explicito_e_conhecido_sem_incluir_pagamento_subsidio_frete_ou_servico(
    fixture,
):
    f = fixture
    imported(
        f,
        entry(f, "ORDER_COMMISSION", "0"),
        entry(f, "PAYMENT_TRANSACTION_FEE", "0"),
        entry(f, "ORDER_PAYMENT", "73.90"),
        entry(f, "IFOOD_SUBSIDY", "5"),
        entry(f, "STORE_SUBSIDY", "-5", hasTransferImpact=False),
    )
    result = resolve(f)
    assert result["complete"] is True
    assert result["fee_total"] == 0
    assert len(result["charges"]) == 2
    assert len(result["non_fee_events"]) == 3
    assert result["checkout"]["delivery_fee"] == 8.9


@pytest.mark.parametrize("allow_synthetic", [False, True])
def test_massa_sintetica_nunca_libera_margem_real(fixture, allow_synthetic):
    f = fixture
    imported(
        f,
        entry(f, "ORDER_COMMISSION", "-9.75"),
        entry(f, "PAYMENT_TRANSACTION_FEE", "-1.95"),
        source="synthetic",
    )
    result = resolve(f, allow_synthetic=allow_synthetic)
    assert result["complete"] is False and result["fee_total"] is None
    assert result["simulated"] is True
    assert result["simulation_complete"] is allow_synthetic
    if allow_synthetic:
        assert result["simulation_fee_total"] == 11.7
        assert all(charge["status"] == "simulated" for charge in result["charges"])
    else:
        assert result["charges"] == [] and result["simulation_fee_total"] is None


@pytest.mark.parametrize(
    "problem",
    [
        "unknown",
        "adjustment",
        "unallocated",
        "cancelled",
        "delivery_ifood",
        "delivery_conflict",
    ],
)
def test_pendencias_preservam_cobrancas_conhecidas_sem_concluir_fechamento(
    fixture, problem
):
    f = fixture
    entries = [
        entry(f, "ORDER_COMMISSION", "-9.75"),
        entry(f, "PAYMENT_TRANSACTION_FEE", "-1.95"),
    ]
    if problem == "unknown":
        entries.append(
            entry(
                f,
                "DELIVERY_FEE",
                "-8.90",
                description="COBRANCA DE ENTREGA A CLASSIFICAR",
            )
        )
    elif problem == "adjustment":
        entries[0]["trigger"] = "ADJUSTMENT"
    elif problem == "unallocated":
        entries.append(entry(f, "Cobrança mensal", "-20", reference=None))
    elif problem == "cancelled":
        f.db.execute(
            IfoodOrder.__table__.update()
            .where(IfoodOrder.tenant_id == f.tenant)
            .values(status="CANCELLED")
        )
    elif problem == "delivery_ifood":
        f.db.execute(
            IfoodOrder.__table__.update()
            .where(IfoodOrder.tenant_id == f.tenant)
            .values(payload={"operationMode": {"delivery": {"provider": "IFOOD"}}})
        )
    elif problem == "delivery_conflict":
        f.db.execute(
            IfoodOrder.__table__.update()
            .where(IfoodOrder.tenant_id == f.tenant)
            .values(delivered_by="IFOOD")
        )
    imported(f, *entries)
    result = resolve(f)
    assert result["complete"] is False
    assert result["fee_known_total"] == 11.7 and result["fee_total"] is None
    assert (
        len([charge for charge in result["charges"] if charge["amount"] is not None])
        == 2
    )
    assert result["pending_components"]
    if problem == "unknown":
        unknown = result["charges"][-1]
        assert unknown["label"] == "COBRANCA DE ENTREGA A CLASSIFICAR"
        assert unknown["signed_amount"] == -8.9 and unknown["status"] == "unclassified"


def test_sinais_e_linhas_iguais_sao_preservados_sem_deduplicacao_incorreta(fixture):
    f = fixture
    imported(
        f,
        entry(f, "ORDER_COMMISSION", "-2"),
        entry(f, "ORDER_COMMISSION", "-2"),
        entry(f, "ORDER_COMMISSION", "1"),
        entry(f, "PAYMENT_TRANSACTION_FEE", "0"),
    )
    result = resolve(f)
    assert [charge["amount"] for charge in result["charges"]] == [2, 2, -1, 0]
    assert result["fee_total"] == 3


def test_vinculo_explicito_historico_e_conflito_com_ponte(fixture):
    f = fixture
    imported(
        f, entry(f, "ORDER_COMMISSION", "-1"), entry(f, "PAYMENT_TRANSACTION_FEE", "0")
    )
    f.db.execute(
        IfoodFinancialSaleLink.__table__.insert().values(
            tenant_id=f.tenant,
            merchant_id=f.merchant,
            mode="homologation",
            order_id=f.order,
            venda_id=2,
            source="explicit_confirmation",
            source_note="Conferido no ensaio",
            actor_id=1,
            item_manifest=[],
        )
    )
    f.db.commit()
    assert resolve(f)["complete"] is True
    f.db.execute(
        IfoodFinancialSaleLink.__table__.update()
        .where(IfoodFinancialSaleLink.tenant_id == f.tenant)
        .values(order_id=str(uuid4()))
    )
    f.db.commit()
    conflict = resolve(f)
    assert conflict["charges"] == []
    assert "link_conflict" in {item["code"] for item in conflict["pending_components"]}
    f.db.execute(
        IfoodPdvBridge.__table__.delete().where(IfoodPdvBridge.tenant_id == f.tenant)
    )
    f.db.execute(
        IfoodFinancialSaleLink.__table__.update()
        .where(IfoodFinancialSaleLink.tenant_id == f.tenant)
        .values(order_id=f.order)
    )
    f.db.commit()
    assert resolve(f)["complete"] is True
    assert resolve(f)["link_source"] == "explicit_confirmation"


def test_venda_ou_loja_diferente_nao_herda_cobrancas(fixture):
    f = fixture
    imported(
        f, entry(f, "ORDER_COMMISSION", "-1"), entry(f, "PAYMENT_TRANSACTION_FEE", "0")
    )
    assert resolve_sales_financials(f.db, f.tenant, [999])[999]["charges"] == []
    outsider = uuid4()
    with tenant_context(outsider):
        f.db.execute(
            IfoodMerchantConfig.__table__.insert().values(
                tenant_id=outsider, merchant_id=f.merchant
            )
        )
        f.db.commit()
        assert resolve_sales_financials(f.db, outsider, [2])[2]["charges"] == []
    with pytest.raises(IfoodFinancialError) as exc:
        resolve_sales_financials(f.db, outsider, [2])
    assert exc.value.status_code == 403
    f.db.execute(
        IfoodMerchantConfig.__table__.update()
        .where(IfoodMerchantConfig.tenant_id == f.tenant)
        .values(merchant_id=str(uuid4()))
    )
    f.db.commit()
    assert resolve(f)["charges"] == []


@pytest.mark.parametrize("scope", ["production", "mode"])
def test_homologacao_nunca_e_usada_em_producao_ou_outro_mode(
    fixture, monkeypatch, scope
):
    f = fixture

    def must_not_query(*_args):
        raise AssertionError("Ambiente bloqueado nao deve ler nem aplicar homologacao")

    monkeypatch.setattr(f.db, "execute", must_not_query)
    if scope == "production":
        monkeypatch.setattr(
            "app.integrations.ifood.sale_financials.settings.ENVIRONMENT", "production"
        )
        result = resolve(f)
    else:
        result = resolve(f, mode="production")
    assert result["complete"] is False and result["charges"] == []


@pytest.mark.parametrize("alias", ["APP_ENV", "ENV", "ENVIRONMENT"])
@pytest.mark.parametrize("environment", ["production", "prod", "staging"])
def test_alias_de_ambiente_estrito_impede_consulta_homologation_antes_do_banco(
    fixture, monkeypatch, alias, environment
):
    f = fixture
    for key in ("APP_ENV", "ENV", "ENVIRONMENT"):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv(alias, environment)

    def must_not_query(*_args):
        raise AssertionError("Alias estrito nao pode consultar dados de homologacao")

    monkeypatch.setattr(f.db, "execute", must_not_query)
    result = resolve(f, allow_synthetic=True)
    assert not result["complete"] and result["charges"] == []
    assert result["pending_components"][-1]["code"] == "environment"


def test_leitura_em_lote_nao_faz_flush_nem_n_mais_um(fixture):
    f = fixture
    imported(
        f, entry(f, "ORDER_COMMISSION", "-1"), entry(f, "PAYMENT_TRANSACTION_FEE", "0")
    )
    executed = []
    event.listen(
        f.engine,
        "before_cursor_execute",
        lambda _conn, _cursor, statement, *_args: executed.append(statement),
    )
    result = resolve_sales_financials(f.db, f.tenant, [2, *range(3, 203)])
    assert result[2]["complete"] is True
    assert len(result) == 201
    assert len(executed) == 7
    assert all(
        statement.lstrip().upper().startswith("SELECT") for statement in executed
    )
    assert not f.db.new and not f.db.dirty and not f.db.deleted


def test_multiplas_janelas_preservam_evidencia_sem_fechar_pedido(fixture):
    f = fixture
    imported(
        f,
        entry(f, "ORDER_COMMISSION", "-9.75"),
        entry(f, "PAYMENT_TRANSACTION_FEE", "-1.95"),
    )
    table = IfoodFinancialSnapshot.__table__
    sid = f.db.execute(
        table.insert().values(
            tenant_id=f.tenant,
            merchant_id=f.merchant,
            mode="homologation",
            begin_date=date(2026, 10, 25),
            end_date=date(2026, 10, 25),
            revision=1,
            active=True,
            source=SOURCE,
            payload_hash="b" * 64,
            page_count=1,
            event_count=1,
            actor_id=1,
        )
    ).inserted_primary_key[0]
    f.db.execute(
        IfoodFinancialEvent.__table__.insert().values(
            tenant_id=f.tenant,
            snapshot_id=sid,
            position=1,
            order_id=f.order,
            name="ORDER_COMMISSION",
            trigger="ORDER_CONCLUDED",
            amount=Decimal("2"),
            has_transfer_impact=True,
            evidence={},
        )
    )
    f.db.commit()
    result = resolve(f)
    assert result["fee_known_total"] == 9.7
    assert result["fee_total"] is None
    assert "multiple_windows" in {item["code"] for item in result["pending_components"]}
