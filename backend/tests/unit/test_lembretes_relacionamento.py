from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app import lembretes_relacionamento_routes as routes
from app.campaigns.models import NotificationQueue
from app.services.lembretes_relacionamento import (
    ACTIVE_REMINDER_STATUSES,
    classify_reminder,
    suggested_message,
)

REPO_ROOT = Path(__file__).resolve().parents[2]


def _reminder(
    product_name="Produto recorrente",
    *,
    dose_total=None,
    eh_racao=False,
    source="configurado",
):
    return SimpleNamespace(
        cliente=SimpleNamespace(nome="Maria da Silva"),
        pet=SimpleNamespace(nome="Thor"),
        produto=SimpleNamespace(nome=product_name, eh_racao=eh_racao),
        dose_total=dose_total,
        origem_intervalo=source,
    )


def test_reminder_classification_keeps_protocol_ration_and_learned_cycle_distinct():
    assert classify_reminder(_reminder(dose_total=3)) == "protocolo"
    assert classify_reminder(_reminder(eh_racao=True)) == "racao"
    assert (
        classify_reminder(_reminder(source="aprendido_historico")) == "ciclo_aprendido"
    )
    assert classify_reminder(_reminder()) == "recorrencia"


def test_suggested_message_uses_product_context_and_remains_a_draft():
    message = suggested_message(_reminder("NexGard contra carrapatos"))

    assert message.startswith("Olá, Maria!")
    assert "pulgas e carrapatos" in message
    assert "Thor" in message
    assert message.endswith("Quer que eu separe para você?")


def test_notified_reminders_remain_active_until_repurchase():
    assert ACTIVE_REMINDER_STATUSES == ("pendente", "notificado")
    source = (REPO_ROOT / "app" / "lembretes.py").read_text(encoding="utf-8")
    assert "list_active_reminders" in source


def test_contact_routes_cover_whatsapp_push_history_and_report():
    source = (REPO_ROOT / "app" / "lembretes_relacionamento_routes.py").read_text(
        encoding="utf-8"
    )
    for literal in (
        '/{lembrete_id}/contatos",',
        '/{lembrete_id}/contatos/whatsapp",',
        '/{lembrete_id}/notificar-app",',
        '/relatorios/resumo",',
        "conversa_aberta",
        "push_manual",
    ):
        assert literal in source


def test_contact_migration_follows_current_head_and_is_reversible():
    source = (
        REPO_ROOT / "alembic" / "versions" / "zyx20260831a1_lembretes_contatos.py"
    ).read_text(encoding="utf-8")
    assert 'down_revision = "zyw20260830a1"' in source
    assert '"lembretes_contatos"' in source
    assert "legacy_notification:" in source
    assert "ALTER TABLE {TABLE_NAME} ENABLE ROW LEVEL SECURITY" in source
    assert "ALTER TABLE {TABLE_NAME} FORCE ROW LEVEL SECURITY" in source
    assert "CREATE POLICY {POLICY_NAME} ON {TABLE_NAME}" in source
    assert 'op.drop_table("lembretes_contatos")' in source


class _FakeQuery:
    def __init__(self, value):
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
        if model is NotificationQueue:
            return _FakeQuery(self.queue)
        return _FakeQuery(None)

    def add(self, value):
        value.id = value.id or len(self.added) + 1
        value.created_at = value.created_at or datetime.utcnow()
        self.added.append(value)

    def flush(self):
        return None

    def commit(self):
        return None

    def refresh(self, value):
        return None


def _active_reminder():
    return SimpleNamespace(
        id=12,
        cliente_id=34,
        produto_id=56,
        cliente=SimpleNamespace(celular="18999990000", telefone=None),
        notificacao_enviada=False,
        data_notificacao_enviada=None,
        status="pendente",
        metodo_notificacao="app",
    )


class _FakeContact:
    idempotency_key = None
    tenant_id = None

    def __init__(self, **values):
        self.id = None
        self.created_at = datetime.utcnow()
        self.operador = None
        self.cliente = None
        self.produto = None
        for key, value in values.items():
            setattr(self, key, value)


@pytest.mark.asyncio
async def test_manual_push_records_contact_and_keeps_opportunity_active(monkeypatch):
    db = _FakeDb()
    reminder = _active_reminder()
    tenant_id = uuid4()
    monkeypatch.setattr(routes, "get_active_reminder", lambda *args, **kwargs: reminder)
    monkeypatch.setattr(routes, "LembreteContato", _FakeContact)
    monkeypatch.setattr(
        routes, "resolve_customer_app_user_id", lambda *args, **kwargs: 99
    )
    monkeypatch.setattr(routes, "can_send_marketing_push", lambda *args, **kwargs: True)

    def enqueue(fake_db, **kwargs):
        fake_db.queue = SimpleNamespace(id=77, status="pending")
        return True

    monkeypatch.setattr(routes, "enqueue_push", enqueue)
    response = await routes.notificar_cliente_no_app(
        12,
        routes.ContatoRequest(mensagem="Mensagem de teste", chave_cliente=uuid4()),
        user_and_tenant=(SimpleNamespace(id=8), tenant_id),
        db=db,
    )

    assert reminder.status == "notificado"
    assert response["canal"] == "push"
    assert response["status"] == "pendente"
    assert db.added[0].notification_queue_id == 77


@pytest.mark.asyncio
async def test_whatsapp_records_opening_without_claiming_delivery(monkeypatch):
    db = _FakeDb()
    reminder = _active_reminder()
    tenant_id = uuid4()
    monkeypatch.setattr(routes, "get_active_reminder", lambda *args, **kwargs: reminder)
    monkeypatch.setattr(routes, "LembreteContato", _FakeContact)
    monkeypatch.setattr(
        routes, "can_send_marketing_whatsapp", lambda *args, **kwargs: True
    )
    response = await routes.registrar_contato_whatsapp(
        12,
        routes.ContatoRequest(mensagem="Mensagem de teste", chave_cliente=uuid4()),
        user_and_tenant=(SimpleNamespace(id=8), tenant_id),
        db=db,
    )

    assert response["status"] == "aberto"
    assert "envio não confirmado" in response["resultado"]
    assert db.added[0].acao == "conversa_aberta"
