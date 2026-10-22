"""Ciclo do atendimento humano: assumir, resolver e devolver a conversa ao bot.

Garante que a conversa (sessao) acompanha o estado do atendimento: a IA para
quando o atendente assume e volta, ou a conversa encerra, so por escolha
explicita ao resolver.
"""

import asyncio
from datetime import datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.routers import whatsapp_handoff as router
from app.whatsapp import webhook
from app.whatsapp.handoff_manager import sessao_assumida, sessao_encerrada
from app.whatsapp.models_handoff import (
    HANDOFF_STATUS_EM_ABERTO,
    HANDOFF_STATUS_EM_ATENDIMENTO,
    WhatsAppAgent,
    WhatsAppHandoff,
)

TENANT_ID = uuid4()
USUARIO = SimpleNamespace(tenant_id=TENANT_ID)


class _Query:
    def __init__(self, db, model):
        self.db = db
        self.model = model

    def filter(self, *_args, **_kwargs):
        return self

    def first(self):
        return self.db.objetos.get(self.model)

    def count(self):
        return self.db.contagens.get(self.model, 0)


class _DB:
    def __init__(self, handoff, agente):
        self.objetos = {WhatsAppHandoff: handoff, WhatsAppAgent: agente}
        self.contagens = {}

    def query(self, model):
        return _Query(self, model)

    def commit(self):
        pass

    def refresh(self, _obj):
        pass


@pytest.fixture(autouse=True)
def _sem_websocket(monkeypatch):
    async def _noop(*_args, **_kwargs):
        return None

    monkeypatch.setattr(router, "emit_handoff_assigned", _noop)
    monkeypatch.setattr(router, "emit_handoff_resolved", _noop)


def _cenario(status_handoff="pending", status_sessao="waiting_human"):
    sessao = SimpleNamespace(status=status_sessao, assigned_to=None, closed_at=None)
    handoff = SimpleNamespace(
        id=uuid4(),
        tenant_id=TENANT_ID,
        session_id=str(uuid4()),
        session=sessao,
        phone_number="5511999999999",
        customer_name=None,
        reason="manual_request",
        reason_details=None,
        priority="medium",
        status=status_handoff,
        assigned_to=None,
        assigned_at=None,
        resolved_at=None,
        resolution_notes=None,
        rating=None,
        rating_feedback=None,
        created_at=datetime(2026, 10, 22, 9, 0, 0),
        updated_at=datetime(2026, 10, 22, 9, 0, 0),
    )
    agente = SimpleNamespace(
        id=uuid4(),
        user_id=7,
        status="online",
        max_concurrent_chats=5,
        current_chats=0,
    )
    return _DB(handoff, agente), handoff, agente, sessao


def _assumir(db, handoff, agente):
    return asyncio.run(
        router.assign_handoff(
            handoff_id=str(handoff.id),
            assign_data=SimpleNamespace(agent_id=agente.id),
            db=db,
            current_user=USUARIO,
        )
    )


def _resolver(db, handoff, devolver_ao_bot=False):
    return asyncio.run(
        router.resolve_handoff(
            handoff_id=str(handoff.id),
            resolve_data=SimpleNamespace(
                resolution_notes="Tutor atendido", return_to_bot=devolver_ao_bot
            ),
            db=db,
            current_user=USUARIO,
        )
    )


def test_assumir_muda_o_handoff_e_a_conversa_e_pausa_a_ia():
    db, handoff, agente, sessao = _cenario()

    resposta = _assumir(db, handoff, agente)

    assert handoff.status == "active"
    assert resposta["status"] == "active"
    assert sessao.status == "human"
    # assigned_to da conversa e o id do usuario, nao o id do atendente (UUID).
    assert sessao.assigned_to == 7
    assert agente.current_chats == 1
    assert webhook.atendimento_humano_ativo(sessao)


def test_resolver_por_padrao_encerra_a_conversa():
    db, handoff, agente, sessao = _cenario()
    _assumir(db, handoff, agente)

    resposta = _resolver(db, handoff)

    assert handoff.status == "resolved"
    assert resposta["status"] == "resolved"
    assert sessao.status == "closed"
    assert sessao.closed_at is not None


def test_resolver_pode_devolver_a_conversa_ao_bot():
    db, handoff, agente, sessao = _cenario()
    _assumir(db, handoff, agente)
    assert webhook.atendimento_humano_ativo(sessao)

    _resolver(db, handoff, devolver_ao_bot=True)

    assert handoff.status == "resolved"
    assert sessao.status == "bot"
    assert sessao.assigned_to is None
    # De volta ao bot: a IA volta a responder.
    assert not webhook.atendimento_humano_ativo(sessao)


def test_resolver_duas_vezes_e_recusado():
    db, handoff, agente, _sessao = _cenario()
    _assumir(db, handoff, agente)
    _resolver(db, handoff)

    with pytest.raises(HTTPException) as erro:
        _resolver(db, handoff)

    assert erro.value.status_code == 400


def test_registro_antigo_assigned_ainda_pode_ser_reatribuido():
    db, handoff, agente, sessao = _cenario(
        status_handoff="assigned", status_sessao="human"
    )

    _assumir(db, handoff, agente)

    assert handoff.status == "active"
    assert sessao.assigned_to == 7


def test_nao_atribui_handoff_ja_resolvido():
    db, handoff, agente, _sessao = _cenario(status_handoff="resolved")

    with pytest.raises(HTTPException) as erro:
        _assumir(db, handoff, agente)

    assert erro.value.status_code == 400


def test_vocabulario_de_estados_tolera_valores_antigos():
    assert "active" in HANDOFF_STATUS_EM_ATENDIMENTO
    assert {"assigned", "in_progress"} <= set(HANDOFF_STATUS_EM_ATENDIMENTO)
    assert HANDOFF_STATUS_EM_ABERTO[0] == "pending"
    assert "resolved" not in HANDOFF_STATUS_EM_ABERTO


def test_helpers_aceitam_sessao_ausente():
    sessao_assumida(None, SimpleNamespace(user_id=1))
    sessao_encerrada(None, devolver_ao_bot=True)
