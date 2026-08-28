import asyncio
from pathlib import Path
from types import SimpleNamespace

from sqlalchemy.exc import IntegrityError

from app.whatsapp import processor as processor_module
from app.whatsapp import webhook


TENANT_ID = "11111111-1111-1111-1111-111111111111"


class _FakeMessageQuery:
    def __init__(self, db):
        self.db = db

    def filter(self, *_args, **_kwargs):
        return self

    def first(self):
        if self.db.rolled_back and self.db.winning_message is not None:
            return self.db.winning_message
        return self.db.messages[0] if self.db.messages else None


class _FakeDB:
    def __init__(self, *, fail_commit=False, winning_message=None):
        self.fail_commit = fail_commit
        self.winning_message = winning_message
        self.messages = []
        self.pending = None
        self.rolled_back = False

    def query(self, _model):
        return _FakeMessageQuery(self)

    def add(self, message):
        self.pending = message

    def commit(self):
        if self.fail_commit:
            raise IntegrityError("INSERT", {}, Exception("unique constraint"))
        self.pending.id = f"local-{len(self.messages) + 1}"
        self.messages.append(self.pending)
        self.pending = None

    def rollback(self):
        self.rolled_back = True
        self.pending = None


def _install_fake_processor(monkeypatch, calls):
    class _FakeProcessor:
        def __init__(self, *, db, tenant_id):
            self.db = db
            self.tenant_id = tenant_id

        async def process_message(self, **kwargs):
            calls.append(kwargs)
            return {"action": "responded"}

    monkeypatch.setattr(processor_module, "MessageProcessor", _FakeProcessor)


def test_replay_do_mesmo_provider_id_e_processado_uma_unica_vez(monkeypatch):
    db = _FakeDB()
    session = SimpleNamespace(id="session-1", message_count=0, last_message_at=None)
    processor_calls = []
    monkeypatch.setattr(webhook, "get_or_create_session", lambda **_kwargs: session)
    _install_fake_processor(monkeypatch, processor_calls)

    first = asyncio.run(
        webhook.process_incoming_message(
            tenant_id=TENANT_ID,
            phone="5511999999999",
            message_content="Quero comprar racao",
            whatsapp_msg_id="wamid.123",
            db=db,
        )
    )
    replay = asyncio.run(
        webhook.process_incoming_message(
            tenant_id=TENANT_ID,
            phone="5511999999999",
            message_content="Quero comprar racao",
            whatsapp_msg_id=" wamid.123 ",
            db=db,
        )
    )

    assert first["status"] == "processed"
    assert replay == {
        "status": "duplicate",
        "whatsapp_message_id": "wamid.123",
        "message_id": "local-1",
    }
    assert len(db.messages) == 1
    assert session.message_count == 1
    assert len(processor_calls) == 1


def test_mensagens_sem_id_externo_nao_recebem_chave_falsa(monkeypatch):
    db = _FakeDB()
    session = SimpleNamespace(id="session-1", message_count=0, last_message_at=None)
    processor_calls = []
    monkeypatch.setattr(webhook, "get_or_create_session", lambda **_kwargs: session)
    _install_fake_processor(monkeypatch, processor_calls)

    results = [
        asyncio.run(
            webhook.process_incoming_message(
                tenant_id=TENANT_ID,
                phone="5511999999999",
                message_content=content,
                whatsapp_msg_id=None,
                db=db,
            )
        )
        for content in ("Primeira mensagem", "Segunda mensagem")
    ]

    assert [result["status"] for result in results] == ["processed", "processed"]
    assert [message.whatsapp_message_id for message in db.messages] == [None, None]
    assert session.message_count == 2
    assert len(processor_calls) == 2


def test_indice_unico_fecha_corrida_entre_dois_processadores(monkeypatch):
    winning_message = SimpleNamespace(id="winner-1")
    db = _FakeDB(fail_commit=True, winning_message=winning_message)
    session = SimpleNamespace(id="session-1", message_count=0, last_message_at=None)
    processor_calls = []
    monkeypatch.setattr(webhook, "get_or_create_session", lambda **_kwargs: session)
    _install_fake_processor(monkeypatch, processor_calls)

    result = asyncio.run(
        webhook.process_incoming_message(
            tenant_id=TENANT_ID,
            phone="5511999999999",
            message_content="Mensagem simultanea",
            whatsapp_msg_id="wamid.race",
            db=db,
        )
    )

    assert result == {
        "status": "duplicate",
        "whatsapp_message_id": "wamid.race",
        "message_id": "winner-1",
    }
    assert db.rolled_back is True
    assert processor_calls == []


def test_orquestrador_nao_inventa_id_repetido_quando_provedor_nao_informa():
    route_source = (
        Path(__file__).resolve().parents[2]
        / "app/api/whatsapp_orchestrator_internal_routes.py"
    ).read_text(encoding="utf-8")
    assert "whatsapp_msg_id=payload.external_message_id" in route_source
    assert 'f"internal_{tenant_id}_{normalized_phone}"' not in route_source
