from datetime import date, datetime
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest

from app import lembretes_aniversarios_routes as routes
from app.campaigns.models import NotificationQueue
from app.models import Cliente, Pet
from app.services.lembretes_aniversarios import (
    birthday_message,
    list_upcoming_birthdays,
    next_birthday,
)

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_next_birthday_handles_year_boundary_and_leap_day():
    assert next_birthday(date(1990, 1, 2), today=date(2026, 12, 31)) == date(2027, 1, 2)
    assert next_birthday(date(2020, 2, 29), today=date(2027, 2, 1)) == date(2027, 2, 28)


def test_birthday_messages_distinguish_tutor_and_pet():
    customer_message = birthday_message(customer_name="maria da silva", days_until=0)
    pet_message = birthday_message(
        customer_name="Maria da Silva", pet_name="Thor", days_until=1
    )

    assert customer_message.startswith("Olá, Maria!")
    assert "Hoje é o seu aniversário" in customer_message
    assert "Amanhã é aniversário do Thor" in pet_message
    assert "🐾" in pet_message


def test_upcoming_list_combines_tutor_pet_and_app_availability(
    db_session, tenant_factory, tenant_context, user_factory
):
    tenant = tenant_factory(nome="Loja aniversários")
    tenant_context(tenant.id)
    user = user_factory(str(tenant.id), nome="Maria", email="maria@app.test")
    customer = Cliente(
        user_id=user.id,
        auth_user_id=user.id,
        nome="Maria da Silva",
        email=user.email,
        celular="18999990000",
        data_nascimento=datetime(1990, 9, 19),
        tipo_cadastro="cliente",
        ativo=True,
    )
    db_session.add(customer)
    db_session.flush()
    pet = Pet(
        cliente_id=customer.id,
        user_id=user.id,
        codigo="PET-THOR",
        nome="Thor",
        especie="Cão",
        data_nascimento=datetime(2020, 9, 20),
        ativo=True,
    )
    db_session.add(pet)
    db_session.flush()

    result = list_upcoming_birthdays(
        db_session,
        tenant_id=UUID(str(tenant.id)),
        days=7,
        today=date(2026, 9, 19),
    )

    assert result["total"] == 2
    assert [item["tipo_aniversario"] for item in result["aniversariantes"]] == [
        "tutor",
        "pet",
    ]
    assert all(item["cliente_tem_app"] for item in result["aniversariantes"])
    assert result["aniversariantes"][1]["mensagem_sugerida"].startswith("Olá, Maria!")


def test_birthday_routes_allow_repeat_manual_push_with_client_uuid():
    source = (REPO_ROOT / "app" / "lembretes_aniversarios_routes.py").read_text(
        encoding="utf-8"
    )
    for literal in (
        '@router.get("", summary="Listar próximos aniversários de tutores e pets")',
        '"/{tipo}/{referencia_id}/contatos"',
        '"/{tipo}/{referencia_id}/contatos/whatsapp"',
        '"/{tipo}/{referencia_id}/notificar-app"',
        "payload.chave_cliente",
        'kind="birthday_pet" if target.pet is not None else "birthday_customer"',
    ):
        assert literal in source
    assert "Já foi disparada uma notificação" not in source


def test_birthday_migration_is_single_head_tenant_scoped_and_reversible():
    source = (
        REPO_ROOT / "alembic" / "versions" / "zzx20260919a1_aniversarios_contatos.py"
    ).read_text(encoding="utf-8")
    assert 'down_revision = "zzw20260919a1"' in source
    assert 'TABLE_NAME = "aniversarios_contatos"' in source
    assert "ENABLE ROW LEVEL SECURITY" in source
    assert "FORCE ROW LEVEL SECURITY" in source
    assert "CREATE POLICY" in source
    assert "op.drop_table(TABLE_NAME)" in source


def test_birthday_router_is_registered_before_dynamic_contact_routes():
    source = (REPO_ROOT / "app" / "main_routers.py").read_text(encoding="utf-8")
    assert source.index(
        "app.include_router(\n        lembretes_aniversarios_router"
    ) < source.index("app.include_router(\n        lembretes_relacionamento_router")


class _FakeContact:
    idempotency_key = None
    tenant_id = None

    def __init__(self, **values):
        self.id = None
        self.created_at = datetime.utcnow()
        self.operador = None
        for key, value in values.items():
            setattr(self, key, value)


class _FakeQuery:
    def __init__(self, value=None):
        self.value = value

    def filter(self, *args):
        return self

    def first(self):
        return self.value


class _FakeDb:
    def __init__(self):
        self.added = []
        self.queue = None

    def query(self, model):
        return _FakeQuery(self.queue if model is NotificationQueue else None)

    def add(self, value):
        value.id = len(self.added) + 1
        self.added.append(value)

    def commit(self):
        return None

    def flush(self):
        return None

    def refresh(self, value):
        return None


@pytest.mark.asyncio
async def test_whatsapp_opening_is_recorded_without_claiming_delivery(monkeypatch):
    tenant_id = uuid4()
    customer = SimpleNamespace(id=21, celular="18999990000", telefone=None)
    target = SimpleNamespace(
        tipo="pet",
        cliente=customer,
        pet=SimpleNamespace(id=31, nome="Thor"),
        aniversario_em=date(2026, 9, 19),
    )
    db = _FakeDb()
    monkeypatch.setattr(routes, "_target_or_404", lambda *args, **kwargs: target)
    monkeypatch.setattr(routes, "AniversarioContato", _FakeContact)
    monkeypatch.setattr(
        routes, "can_send_marketing_whatsapp", lambda *args, **kwargs: True
    )

    response = await routes.registrar_whatsapp_aniversario(
        "pet",
        31,
        routes.BirthdayContactRequest(
            mensagem="Feliz aniversário, Thor!", chave_cliente=uuid4()
        ),
        user_and_tenant=(SimpleNamespace(id=8), tenant_id),
        db=db,
    )

    assert response["status"] == "aberto"
    assert "envio não confirmado" in response["resultado"]
    assert db.added[0].cliente_id == 21
    assert db.added[0].pet_id == 31


@pytest.mark.asyncio
async def test_manual_push_can_be_sent_again_with_a_new_client_key(monkeypatch):
    tenant_id = uuid4()
    customer = SimpleNamespace(id=21, auth_user_id=99)
    target = SimpleNamespace(
        tipo="tutor",
        cliente=customer,
        pet=None,
        aniversario_em=date(2026, 9, 19),
    )
    db = _FakeDb()
    queue_keys = []
    monkeypatch.setattr(routes, "_target_or_404", lambda *args, **kwargs: target)
    monkeypatch.setattr(routes, "AniversarioContato", _FakeContact)
    monkeypatch.setattr(
        routes, "resolve_customer_app_user_id", lambda *args, **kwargs: 99
    )
    monkeypatch.setattr(routes, "can_send_marketing_push", lambda *args, **kwargs: True)

    def enqueue(fake_db, **kwargs):
        queue_keys.append(kwargs["idempotency_key"])
        fake_db.queue = SimpleNamespace(id=70 + len(queue_keys), status="pending")
        return True

    monkeypatch.setattr(routes, "enqueue_push", enqueue)

    for _ in range(2):
        response = await routes.notificar_aniversario_no_app(
            "tutor",
            21,
            routes.BirthdayContactRequest(
                mensagem="Feliz aniversário!", chave_cliente=uuid4()
            ),
            user_and_tenant=(SimpleNamespace(id=8), tenant_id),
            db=db,
        )
        assert response["status"] == "pendente"

    assert len(set(queue_keys)) == 2
    assert all(
        key.startswith(f"birthday_manual:{tenant_id}:tutor:21:") for key in queue_keys
    )
