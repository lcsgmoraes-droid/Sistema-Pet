"""Carteira, isolamento e auditoria do acompanhamento de cashback."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from itertools import count
from pathlib import Path
from uuid import UUID, uuid4

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
import pytest
from sqlalchemy import event, insert

from app.db import base as _model_registry  # noqa: F401 - metadata completo para o fixture SQLite
from app.auth.dependencies import get_current_user_and_tenant
from app.campaigns import cashback_crm_routes as routes
from app.campaigns.cashback_crm_models import CashbackContato
from app.campaigns.cashback_crm_service import (
    create_contact,
    list_contacts,
    list_customers,
    normalize_phone,
)
from app.campaigns.models import CashbackSourceTypeEnum, CashbackTransaction
from app.db import get_session
from app.models import Cliente
from app.utils.timezone import now_brasilia
from app.whatsapp.security import DataPrivacyConsent


_TRANSACTION_IDS = count(700000)


@pytest.fixture
def setup_crm(db_session, tenant_factory, user_factory, tenant_context):
    tenant = tenant_factory(nome="CRM cashback")
    tenant_id = UUID(str(tenant.id))
    user = user_factory(str(tenant_id), nome="Operadora CRM")
    tenant_context(tenant_id)

    def customer(name="Maria", phone="(18) 99999-8888", active=True):
        row = Cliente(
            tenant_id=tenant_id,
            user_id=user.id,
            nome=name,
            codigo=f"CRM-{uuid4().hex[:8]}",
            celular=phone,
            ativo=active,
            is_cliente=True,
        )
        db_session.add(row)
        db_session.flush()
        return row

    def transaction(
        person,
        amount="10.00",
        source=CashbackSourceTypeEnum.manual,
        expires=None,
        source_id=None,
        created=None,
    ):
        transaction_id = next(_TRANSACTION_IDS)
        db_session.execute(
            insert(CashbackTransaction).values(
                id=transaction_id,
                tenant_id=tenant_id,
                customer_id=person.id,
                amount=Decimal(amount),
                source_type=source,
                source_id=source_id,
                tx_type="credit" if Decimal(amount) > 0 else "debit",
                expires_at=expires,
                created_at=created or datetime.now(timezone.utc) - timedelta(minutes=5),
            )
        )
        db_session.flush()
        return transaction_id

    return tenant_id, user, customer, transaction


def test_list_uses_real_wallet_expiration_and_reversal_in_one_ledger_query(
    db_session, setup_crm
):
    tenant_id, _, customer, tx = setup_crm
    now = datetime.now(timezone.utc)
    expired, available, revoked = (
        customer("Expirado"),
        customer("Saldo atual", active=False),
        customer("Estornado"),
    )
    tx(
        expired,
        "50.00",
        expires=now - timedelta(days=1),
        created=now - timedelta(days=2),
    )
    credit = tx(available, "30.00", expires=now + timedelta(days=7))
    tx(available, "-5.00", source=CashbackSourceTypeEnum.redemption)
    tx(available, "-3.00", source=CashbackSourceTypeEnum.reversal, source_id=credit)
    original = tx(revoked, "20.00")
    tx(revoked, "-20.00", source=CashbackSourceTypeEnum.reversal, source_id=original)
    ledger_queries = []

    def capture(_connection, _cursor, statement, _params, _context, _executemany):
        if "SELECT" in statement.upper() and "cashback_transactions" in statement:
            ledger_queries.append(statement)

    event.listen(db_session.get_bind(), "before_cursor_execute", capture)
    try:
        result = list_customers(db_session, tenant_id=tenant_id)
    finally:
        event.remove(db_session.get_bind(), "before_cursor_execute", capture)

    assert len(ledger_queries) == 1
    assert result["resumo"] == {
        "total_clientes": 1,
        "saldo_total": 22.0,
        "sem_contato": 1,
        "retornos_pendentes": 0,
    }
    assert result["clientes"][0]["cliente_id"] == available.id
    assert result["clientes"][0]["ativo"] is False
    assert result["clientes"][0]["valor_a_expirar"] == 22.0


def test_list_pagination_search_and_global_summary(db_session, setup_crm):
    tenant_id, _, customer, tx = setup_crm
    for name, amount in (("Ana", "10"), ("Bia", "20"), ("Clara", "30")):
        tx(customer(name), amount)
    result = list_customers(db_session, tenant_id=tenant_id, page=2, per_page=2)
    assert [row["nome"] for row in result["clientes"]] == ["Ana"]
    assert result["paginacao"] == {
        "pagina": 2,
        "por_pagina": 2,
        "total": 3,
        "paginas": 2,
    }
    filtered = list_customers(db_session, tenant_id=tenant_id, search="bia")
    assert [row["nome"] for row in filtered["clientes"]] == ["Bia"]
    assert filtered["resumo"]["saldo_total"] == 60.0


def test_every_customer_remains_accessible_after_the_old_500_customer_limit(
    db_session, setup_crm
):
    tenant_id, _, customer, tx = setup_crm
    for index in range(501):
        tx(customer(f"Cliente {index:03d}"))
    result = list_customers(db_session, tenant_id=tenant_id, page=21, per_page=25)
    assert result["paginacao"]["total"] == 501
    assert result["resumo"]["total_clientes"] == 501
    assert [row["nome"] for row in result["clientes"]] == ["Cliente 500"]


def test_opening_is_idempotent_and_does_not_claim_delivery(db_session, setup_crm):
    tenant_id, user, customer, tx = setup_crm
    person = customer()
    tx(person, "42.50")
    key = uuid4()
    kwargs = dict(
        tenant_id=tenant_id,
        customer_id=person.id,
        user=user,
        request_key=key,
        message="Olá! Você tem R$ 42,50 🐾",
    )
    first = create_contact(db_session, **kwargs)
    retry = create_contact(db_session, **kwargs)
    assert first.id == retry.id
    assert first.acao == "conversa_aberta"
    assert first.status == "conversa_aberta"
    assert first.telefone == "5518999998888"
    assert first.saldo_cashback == Decimal("42.50")
    history = list_contacts(db_session, tenant_id=tenant_id, customer_id=person.id)
    assert history["total"] == 1
    assert history["contatos"][0]["operador_nome"] == "Operadora CRM"
    assert history["contatos"][0]["mensagem"] == kwargs["message"]


def test_status_notes_return_and_reopening_preserve_history(db_session, setup_crm):
    tenant_id, user, customer, tx = setup_crm
    person = customer()
    tx(person)
    due = now_brasilia().date() - timedelta(days=1)
    first = create_contact(
        db_session,
        tenant_id=tenant_id,
        customer_id=person.id,
        user=user,
        request_key=uuid4(),
        message="Seu pet merece esse carinho!",
    )
    first_open_id = first.id
    opening_time = first.created_at
    followup = create_contact(
        db_session,
        tenant_id=tenant_id,
        customer_id=person.id,
        user=user,
        request_key=uuid4(),
        crm_status="retornar_depois",
        note="Prefere conversar na sexta.",
        next_contact=due,
    )
    assert followup.id != first_open_id
    listing = list_customers(db_session, tenant_id=tenant_id, due_only=True)
    row = listing["clientes"][0]
    assert row["ultimo_contato"] == opening_time.isoformat()
    assert row["proximo_contato_em"] == due.isoformat()
    assert row["status"] == "retornar_depois"
    assert listing["resumo"]["retornos_pendentes"] == 1
    reopened = create_contact(
        db_session,
        tenant_id=tenant_id,
        customer_id=person.id,
        user=user,
        request_key=uuid4(),
        message="Passando para lembrar do seu cashback!",
    )
    assert reopened.status == "retornar_depois"
    assert reopened.proximo_contato_em == due
    history = list_contacts(
        db_session, tenant_id=tenant_id, customer_id=person.id, page=2, per_page=2
    )
    assert history["total"] == 3
    assert history["contatos"][0]["id"] == first_open_id
    assert history["paginacao"]["paginas"] == 2


def test_do_not_contact_blocks_whatsapp_but_does_not_set_global_consent(
    db_session, setup_crm
):
    tenant_id, user, customer, tx = setup_crm
    person = customer()
    tx(person)
    key = uuid4()
    kwargs = dict(
        tenant_id=tenant_id,
        customer_id=person.id,
        user=user,
        request_key=key,
        crm_status="nao_contatar",
        note="Pediu para não receber lembretes de saldo.",
        next_contact=now_brasilia().date(),
    )
    first = create_contact(db_session, **kwargs)
    assert create_contact(db_session, **kwargs).id == first.id
    assert first.proximo_contato_em is None
    with pytest.raises(HTTPException) as exc:
        create_contact(
            db_session,
            tenant_id=tenant_id,
            customer_id=person.id,
            user=user,
            request_key=uuid4(),
            message="Olá",
        )
    assert exc.value.status_code == 403
    row = list_customers(db_session, tenant_id=tenant_id)["clientes"][0]
    assert row["whatsapp_disponivel"] is False
    assert "não contatar" in row["motivo_bloqueio"]
    assert (
        db_session.query(DataPrivacyConsent)
        .filter(DataPrivacyConsent.tenant_id == tenant_id)
        .count()
        == 0
    )


def test_optout_and_invalid_phone_are_blocked(db_session, setup_crm):
    tenant_id, user, customer, tx = setup_crm
    opted_out, invalid = customer("Opt-out"), customer("Sem DDD", phone="12345")
    tx(opted_out)
    tx(invalid)
    db_session.add(
        DataPrivacyConsent(
            tenant_id=tenant_id,
            subject_type="customer",
            subject_id=str(opted_out.id),
            consent_type="marketing_whatsapp",
            consent_given=False,
            consent_text="Recusa",
        )
    )
    db_session.flush()
    for person, status_code in ((opted_out, 403), (invalid, 422)):
        with pytest.raises(HTTPException) as exc:
            create_contact(
                db_session,
                tenant_id=tenant_id,
                customer_id=person.id,
                user=user,
                request_key=uuid4(),
                message="Olá",
            )
        assert exc.value.status_code == status_code
    result = list_customers(db_session, tenant_id=tenant_id)
    assert all(row["whatsapp_disponivel"] is False for row in result["clientes"])


def test_idempotent_whatsapp_retry_rechecks_new_do_not_contact_status(
    db_session, setup_crm
):
    tenant_id, user, customer, tx = setup_crm
    person = customer()
    tx(person)
    key = uuid4()
    opening = dict(
        tenant_id=tenant_id,
        customer_id=person.id,
        user=user,
        request_key=key,
        message="Olá!",
    )
    create_contact(db_session, **opening)
    create_contact(
        db_session,
        tenant_id=tenant_id,
        customer_id=person.id,
        user=user,
        request_key=uuid4(),
        crm_status="nao_contatar",
    )
    with pytest.raises(HTTPException) as exc:
        create_contact(db_session, **opening)
    assert exc.value.status_code == 403
    assert (
        list_contacts(db_session, tenant_id=tenant_id, customer_id=person.id)["total"]
        == 2
    )


def test_expired_balance_rechecked_but_history_and_followup_survive_zero_balance(
    db_session, setup_crm
):
    tenant_id, user, customer, tx = setup_crm
    person = customer()
    tx(
        person,
        expires=datetime.now(timezone.utc) - timedelta(days=1),
        created=datetime.now(timezone.utc) - timedelta(days=2),
    )
    with pytest.raises(HTTPException) as exc:
        create_contact(
            db_session,
            tenant_id=tenant_id,
            customer_id=person.id,
            user=user,
            request_key=uuid4(),
            message="Olá",
        )
    assert exc.value.status_code == 409
    create_contact(
        db_session,
        tenant_id=tenant_id,
        customer_id=person.id,
        user=user,
        request_key=uuid4(),
        crm_status="concluido",
        note="Saldo expirou antes do contato.",
    )
    assert (
        list_contacts(db_session, tenant_id=tenant_id, customer_id=person.id)["total"]
        == 1
    )
    assert list_customers(db_session, tenant_id=tenant_id)["clientes"] == []


def test_other_tenant_cannot_read_or_write_customer(
    db_session, setup_crm, tenant_factory, tenant_context
):
    tenant_id, user, customer, tx = setup_crm
    person = customer()
    tx(person)
    other = tenant_factory(nome="Outra loja")
    other_id = UUID(str(other.id))
    tenant_context(other_id)
    assert list_customers(db_session, tenant_id=other_id)["clientes"] == []
    with pytest.raises(HTTPException) as read_error:
        list_contacts(db_session, tenant_id=other_id, customer_id=person.id)
    with pytest.raises(HTTPException) as write_error:
        create_contact(
            db_session,
            tenant_id=other_id,
            customer_id=person.id,
            user=user,
            request_key=uuid4(),
            message="Olá",
        )
    assert read_error.value.status_code == write_error.value.status_code == 404
    tenant_context(tenant_id)
    assert db_session.query(CashbackContato).count() == 0


def test_request_validation_and_permissions_are_enforced(
    db_session, setup_crm, monkeypatch
):
    tenant_id, user, customer, tx = setup_crm
    person = customer()
    tx(person)
    app = FastAPI()
    app.include_router(routes.router, prefix="/campanhas")
    app.dependency_overrides[get_current_user_and_tenant] = lambda: (user, tenant_id)
    app.dependency_overrides[get_session] = lambda: db_session
    permissions = []

    def allowed(_db, _user_id, permission, _tenant_id, **_kwargs):
        permissions.append(permission)

    monkeypatch.setattr("app.security.permissions_decorator.check_permission", allowed)
    with TestClient(app) as client:
        assert (
            client.get("/campanhas/cashback/clientes?status=inexistente").status_code
            == 422
        )
        assert client.get("/campanhas/cashback/clientes?pagina=0").status_code == 422
        assert client.get("/campanhas/cashback/clientes").status_code == 200
        response = client.post(
            f"/campanhas/cashback/clientes/{person.id}/contatos/whatsapp",
            json={"mensagem": "Olá, Maria! 🐾", "chave_cliente": str(uuid4())},
        )
        assert response.status_code == 200
        assert response.json()["whatsapp_url"].startswith(
            "https://wa.me/5518999998888?text="
        )
        assert response.json()["contato"]["status"] == "conversa_aberta"
        assert response.json()["cliente"]["status"] == "conversa_aberta"
        assert response.json()["cliente"]["whatsapp_disponivel"] is True
        blocked = client.post(
            f"/campanhas/cashback/clientes/{person.id}/acompanhamento",
            json={"status": "nao_contatar", "chave_cliente": str(uuid4())},
        )
        assert blocked.json()["cliente"]["whatsapp_disponivel"] is False
        unblocked = client.post(
            f"/campanhas/cashback/clientes/{person.id}/acompanhamento",
            json={"status": "interessado", "chave_cliente": str(uuid4())},
        )
        assert unblocked.json()["cliente"]["whatsapp_disponivel"] is True
        assert (
            client.post(
                f"/campanhas/cashback/clientes/{person.id}/acompanhamento",
                json={"status": "retornar_depois", "chave_cliente": str(uuid4())},
            ).status_code
            == 422
        )

        assert (
            client.post(
                f"/campanhas/cashback/clientes/{person.id}/contatos/whatsapp",
                json={"mensagem": "   ", "chave_cliente": str(uuid4())},
            ).status_code
            == 422
        )

        def denied(*_args, **_kwargs):
            raise HTTPException(status_code=403, detail="Sem permissão")

        monkeypatch.setattr(
            "app.security.permissions_decorator.check_permission", denied
        )
        assert client.get("/campanhas/cashback/clientes").status_code == 403
        assert (
            client.post(
                f"/campanhas/cashback/clientes/{person.id}/contatos/whatsapp",
                json={"mensagem": "Olá", "chave_cliente": str(uuid4())},
            ).status_code
            == 403
        )
    assert "clientes.visualizar" in permissions
    assert "clientes.editar" in permissions


@pytest.mark.parametrize(
    "phone,expected",
    [
        ("(18) 99999-8888", "5518999998888"),
        ("5518999998888", "5518999998888"),
        ("+55 18 99999-8888", "5518999998888"),
        ("123", None),
        ("", None),
    ],
)
def test_phone_normalization(phone, expected):
    assert normalize_phone(phone) == expected


def test_migration_follows_current_head_and_enables_rls():
    source = (
        Path(__file__).resolve().parents[2]
        / "alembic"
        / "versions"
        / "zzzzf20261019a1_cashback_contatos.py"
    ).read_text(encoding="utf-8")
    assert 'down_revision = "zzzze20261019a1"' in source
    assert "ENABLE ROW LEVEL SECURITY" in source
    assert "FORCE ROW LEVEL SECURITY" in source
    assert "WITH CHECK ({TENANT_GUARD})" in source
    assert "op.drop_table(TABLE_NAME)" in source
