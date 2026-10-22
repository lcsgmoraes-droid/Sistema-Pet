"""Tempo real do atendimento WhatsApp separado por loja.

Nenhum evento pode chegar a atendentes de outra loja, e so entra na conexao
quem e atendente (cadastrado) daquela loja, com o modulo contratado.
"""

import asyncio
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.routers import whatsapp_websocket as ws_router
from app.whatsapp import websocket as ws


class _FakeSocket:
    def __init__(self, falha_ao_enviar=False):
        self.recebidos = []
        self.aceito = False
        self.falha_ao_enviar = falha_ao_enviar

    async def accept(self):
        self.aceito = True

    async def send_json(self, mensagem):
        if self.falha_ao_enviar:
            raise RuntimeError("conexao caiu")
        self.recebidos.append(mensagem)

    def eventos(self):
        return [m["event"] for m in self.recebidos if m["event"] != "connected"]


@pytest.fixture
def gerenciador(monkeypatch):
    novo = ws.ConnectionManager()
    monkeypatch.setattr(ws, "manager", novo)
    return novo


def _conectar(gerenciador, tenant, agente, socket=None):
    socket = socket or _FakeSocket()
    asyncio.run(gerenciador.connect(socket, agente, tenant))
    return socket


def test_evento_da_loja_nao_chega_em_outra_loja(gerenciador):
    a1 = _conectar(gerenciador, "loja-a", "agente-1")
    a2 = _conectar(gerenciador, "loja-a", "agente-2")
    b1 = _conectar(gerenciador, "loja-b", "agente-3")

    asyncio.run(ws.emit_handoff_resolved("handoff-1", "loja-a"))
    asyncio.run(ws.emit_agent_status_change({"id": "agente-1"}, "loja-a"))
    asyncio.run(ws.emit_new_message("sessao-1", {"id": "m1"}, "loja-a"))

    assert a1.eventos() == ["handoff_resolved", "agent_status_change", "new_message"]
    assert a2.eventos() == ["handoff_resolved", "agent_status_change", "new_message"]
    assert b1.eventos() == []


def test_mensagem_para_um_agente_nao_vaza_para_outros(gerenciador):
    a1 = _conectar(gerenciador, "loja-a", "agente-1")
    a2 = _conectar(gerenciador, "loja-a", "agente-2")

    asyncio.run(ws.emit_new_message("sessao-1", {"id": "m1"}, "loja-a", "agente-1"))

    assert a1.eventos() == ["new_message"]
    assert a2.eventos() == []


def test_desconectar_remove_a_conexao_da_loja(gerenciador):
    a1 = _conectar(gerenciador, "loja-a", "agente-1")
    gerenciador.disconnect(a1)

    asyncio.run(ws.emit_handoff_resolved("handoff-1", "loja-a"))

    assert a1.eventos() == []
    assert gerenciador.connection_tenants == {}
    assert gerenciador.agent_connections == {}


def test_conexao_morta_e_removida_sem_afetar_as_demais(gerenciador):
    morta = _conectar(gerenciador, "loja-a", "agente-1", _FakeSocket(True))
    viva = _conectar(gerenciador, "loja-a", "agente-2")

    asyncio.run(ws.emit_handoff_resolved("handoff-1", "loja-a"))

    assert viva.eventos() == ["handoff_resolved"]
    assert morta not in gerenciador.connection_tenants


def test_nao_existe_mais_envio_para_todas_as_lojas(gerenciador):
    assert not hasattr(gerenciador, "broadcast_to_all_agents")


# ---------------------------------------------------------------------------
# Autorizacao da conexao
# ---------------------------------------------------------------------------


class _Query:
    def __init__(self, agente):
        self.agente = agente

    def filter(self, *_args, **_kwargs):
        return self

    def first(self):
        return self.agente


class _DB:
    def __init__(self, agente):
        self.agente = agente

    def query(self, _model):
        return _Query(self.agente)


TENANT_VALIDO = "11111111-1111-1111-1111-111111111111"


def _preparar(monkeypatch, *, tenant_id=TENANT_VALIDO, modulo_ativo=True):
    usuario = SimpleNamespace(id=7)

    monkeypatch.setattr(ws_router, "get_current_user", lambda **_kw: usuario)

    async def _usuario_e_loja(**_kw):
        return usuario, tenant_id

    monkeypatch.setattr(ws_router, "get_current_user_and_tenant", _usuario_e_loja)
    monkeypatch.setattr(
        ws_router, "tenant_has_active_module", lambda *_a, **_kw: modulo_ativo
    )


def _autorizar(db, agent_id=None):
    return asyncio.run(
        ws_router.autorizar_conexao_agente("token", agent_id or str(uuid4()), db)
    )


def test_atendente_da_propria_loja_e_autorizado(monkeypatch):
    _preparar(monkeypatch)

    assert _autorizar(_DB(SimpleNamespace(id=uuid4()))) == TENANT_VALIDO


def test_atendente_de_outro_usuario_ou_loja_e_recusado(monkeypatch):
    # O filtro por usuario e loja nao acha o atendente: conexao recusada.
    _preparar(monkeypatch)

    assert _autorizar(_DB(None)) is None


def test_loja_sem_modulo_whatsapp_e_recusada(monkeypatch):
    _preparar(monkeypatch, modulo_ativo=False)

    assert _autorizar(_DB(SimpleNamespace(id=uuid4()))) is None


def test_usuario_sem_loja_e_recusado(monkeypatch):
    _preparar(monkeypatch, tenant_id=None)

    assert _autorizar(_DB(SimpleNamespace(id=uuid4()))) is None


def test_identificador_de_atendente_invalido_e_recusado(monkeypatch):
    _preparar(monkeypatch)

    assert _autorizar(_DB(SimpleNamespace(id=uuid4())), agent_id="nao-e-uuid") is None


def test_token_invalido_e_recusado(monkeypatch):
    def _falha(**_kw):
        raise RuntimeError("token invalido")

    monkeypatch.setattr(ws_router, "get_current_user", _falha)

    assert _autorizar(_DB(SimpleNamespace(id=uuid4()))) is None
