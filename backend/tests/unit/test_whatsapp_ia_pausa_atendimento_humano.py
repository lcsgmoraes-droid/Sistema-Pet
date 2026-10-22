import asyncio
from types import SimpleNamespace

import pytest

from app.whatsapp import processor as processor_module
from app.whatsapp import sender as sender_module
from app.whatsapp import webhook

TENANT_ID = "11111111-1111-1111-1111-111111111111"


class _FakeQuery:
    def __init__(self, db):
        self.db = db

    def filter(self, *_args, **_kwargs):
        return self

    def first(self):
        # 1a consulta: checagem de mensagem duplicada (sempre vazia).
        # Demais consultas: busca do aviso de espera recente.
        self.db.consultas += 1
        return None if self.db.consultas == 1 else self.db.aviso_recente


class _FakeDB:
    def __init__(self, aviso_recente=None):
        self.messages = []
        self.pending = None
        self.aviso_recente = aviso_recente
        self.consultas = 0

    def query(self, _model):
        return _FakeQuery(self)

    def add(self, message):
        self.pending = message

    def commit(self):
        self.pending.id = f"local-{len(self.messages) + 1}"
        self.messages.append(self.pending)
        self.pending = None

    def rollback(self):
        self.pending = None


def _processar(monkeypatch, status, aviso_recente=None, envio_falha=False):
    calls = []
    avisos = []

    async def _fake_envio(**kwargs):
        if envio_falha:
            raise RuntimeError("provedor fora do ar")
        avisos.append(kwargs)
        return SimpleNamespace(id="aviso-1")

    monkeypatch.setattr(sender_module, "send_whatsapp_message", _fake_envio)

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
    db = _FakeDB(aviso_recente=aviso_recente)
    result = asyncio.run(
        webhook.process_incoming_message(
            tenant_id=TENANT_ID,
            phone="5511999999999",
            message_content="Oi, ainda estou esperando",
            whatsapp_msg_id="wamid.human-1",
            db=db,
        )
    )
    return result, calls, db, session, avisos


@pytest.mark.parametrize("status", ["human", "waiting_human"])
def test_ia_nao_responde_quando_atendimento_humano_esta_ativo(monkeypatch, status):
    result, calls, db, session, _avisos = _processar(monkeypatch, status)

    assert calls == []
    assert result["status"] == "processed"
    assert result["processor_result"]["action"] == "skipped_human_handling"
    assert result["processor_result"]["session_status"] == status
    # A mensagem do tutor continua salva para o atendente ver.
    assert len(db.messages) == 1
    assert session.message_count == 1


def test_ia_responde_normalmente_quando_a_sessao_e_do_bot(monkeypatch):
    result, calls, db, _session, avisos = _processar(monkeypatch, "bot")

    assert len(calls) == 1
    assert result["processor_result"] == {"action": "responded"}
    assert len(db.messages) == 1
    assert avisos == []


def test_helper_considera_apenas_human_e_waiting_human():
    assert webhook.atendimento_humano_ativo(SimpleNamespace(status="human"))
    assert webhook.atendimento_humano_ativo(SimpleNamespace(status="waiting_human"))
    assert not webhook.atendimento_humano_ativo(SimpleNamespace(status="bot"))
    assert not webhook.atendimento_humano_ativo(SimpleNamespace(status="closed"))
    assert not webhook.atendimento_humano_ativo(SimpleNamespace())


def test_aviso_de_espera_e_enviado_quando_aguarda_atendente(monkeypatch):
    result, calls, _db, _session, avisos = _processar(monkeypatch, "waiting_human")

    assert calls == []
    assert len(avisos) == 1
    assert avisos[0]["message"] == webhook.AVISO_ESPERA_ATENDENTE
    assert avisos[0]["session_id"] == "session-1"
    assert result["processor_result"]["waiting_notice_sent"] is True


def test_aviso_de_espera_nao_se_repete_dentro_da_janela(monkeypatch):
    result, _calls, _db, _session, avisos = _processar(
        monkeypatch, "waiting_human", aviso_recente=SimpleNamespace(id="antigo")
    )

    assert avisos == []
    assert result["processor_result"]["waiting_notice_sent"] is False


def test_sem_aviso_quando_o_atendente_ja_assumiu(monkeypatch):
    result, _calls, _db, _session, avisos = _processar(monkeypatch, "human")

    assert avisos == []
    assert result["processor_result"]["waiting_notice_sent"] is False


def test_falha_no_aviso_nao_derruba_o_processamento(monkeypatch):
    result, calls, db, _session, _avisos = _processar(
        monkeypatch, "waiting_human", envio_falha=True
    )

    assert calls == []
    assert result["status"] == "processed"
    assert result["processor_result"]["waiting_notice_sent"] is False
    assert len(db.messages) == 1
