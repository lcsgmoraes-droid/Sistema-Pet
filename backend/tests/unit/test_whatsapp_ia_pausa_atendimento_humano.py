import asyncio
from types import SimpleNamespace

import pytest

from app.whatsapp import processor as processor_module
from app.whatsapp import webhook

TENANT_ID = "11111111-1111-1111-1111-111111111111"


class _FakeQuery:
    def filter(self, *_args, **_kwargs):
        return self

    def first(self):
        return None


class _FakeDB:
    def __init__(self):
        self.messages = []
        self.pending = None

    def query(self, _model):
        return _FakeQuery()

    def add(self, message):
        self.pending = message

    def commit(self):
        self.pending.id = f"local-{len(self.messages) + 1}"
        self.messages.append(self.pending)
        self.pending = None

    def rollback(self):
        self.pending = None


def _processar(monkeypatch, status):
    calls = []

    class _FakeProcessor:
        def __init__(self, *, db, tenant_id):
            pass

        async def process_message(self, **kwargs):
            calls.append(kwargs)
            return {"action": "responded"}

    monkeypatch.setattr(processor_module, "MessageProcessor", _FakeProcessor)
    session = SimpleNamespace(
        id="session-1", status=status, message_count=0, last_message_at=None
    )
    monkeypatch.setattr(webhook, "get_or_create_session", lambda **_kwargs: session)
    db = _FakeDB()
    result = asyncio.run(
        webhook.process_incoming_message(
            tenant_id=TENANT_ID,
            phone="5511999999999",
            message_content="Oi, ainda estou esperando",
            whatsapp_msg_id="wamid.human-1",
            db=db,
        )
    )
    return result, calls, db, session


@pytest.mark.parametrize("status", ["human", "waiting_human"])
def test_ia_nao_responde_quando_atendimento_humano_esta_ativo(monkeypatch, status):
    result, calls, db, session = _processar(monkeypatch, status)

    assert calls == []
    assert result["status"] == "processed"
    assert result["processor_result"]["action"] == "skipped_human_handling"
    assert result["processor_result"]["session_status"] == status
    # A mensagem do tutor continua salva para o atendente ver.
    assert len(db.messages) == 1
    assert session.message_count == 1


def test_ia_responde_normalmente_quando_a_sessao_e_do_bot(monkeypatch):
    result, calls, db, _session = _processar(monkeypatch, "bot")

    assert len(calls) == 1
    assert result["processor_result"] == {"action": "responded"}
    assert len(db.messages) == 1


def test_helper_considera_apenas_human_e_waiting_human():
    assert webhook.atendimento_humano_ativo(SimpleNamespace(status="human"))
    assert webhook.atendimento_humano_ativo(SimpleNamespace(status="waiting_human"))
    assert not webhook.atendimento_humano_ativo(SimpleNamespace(status="bot"))
    assert not webhook.atendimento_humano_ativo(SimpleNamespace(status="closed"))
    assert not webhook.atendimento_humano_ativo(SimpleNamespace())
