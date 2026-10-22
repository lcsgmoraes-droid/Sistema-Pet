"""Etapa 0.9 do CRM: a mensagem do tutor nao se perde quando algo falha."""

import asyncio
from datetime import datetime
from types import SimpleNamespace
from uuid import uuid4

from app import db as app_db
from app.api import whatsapp_orchestrator_internal_routes as interno
from app.whatsapp import handoff_manager as handoff_manager_module
from app.whatsapp import processor as processor_module
from app.whatsapp import sender as sender_module
from app.whatsapp import webhook
from app.whatsapp import websocket as ws_module

TENANT = "11111111-1111-1111-1111-111111111111"


class _Q:
    def __init__(self, db):
        self.db = db

    def filter(self, *_a, **_k):
        return self

    def first(self):
        self.db.consultas += 1
        # 1a consulta: duplicidade da mensagem (vazia). Depois: "ja respondeu?" etc.
        if self.db.consultas == 1:
            return None
        return self.db.resposta_existente


class _DB:
    def __init__(self, resposta_existente=None):
        self.messages = []
        self.pending = None
        self.consultas = 0
        self.resposta_existente = resposta_existente
        self.rollbacks = 0

    def query(self, *_a):
        return _Q(self)

    def add(self, m):
        self.pending = m

    def commit(self):
        self.pending.id = f"m-{len(self.messages) + 1}"
        self.pending.created_at = datetime(2026, 10, 22, 9, 0, 0)
        self.messages.append(self.pending)

    def rollback(self):
        self.rollbacks += 1


def _preparar(monkeypatch, falhas):
    """`falhas` = quantas vezes a IA falha antes de funcionar (None = sempre)."""
    estado = {"ia": 0, "handoffs": [], "avisos": []}
    sessao = SimpleNamespace(
        id="s1",
        status="bot",
        phone_number="5511999998888",
        cliente_id=None,
        message_count=0,
        last_message_at=None,
    )

    class _Processador:
        def __init__(self, *, db, tenant_id):
            pass

        async def process_message(self, **_kw):
            estado["ia"] += 1
            if falhas is None or estado["ia"] <= falhas:
                raise RuntimeError("openai indisponivel: chave-secreta-xyz")
            return {"action": "responded"}

    class _Gerente:
        def get_active_handoff(self, _sid):
            return None

        def create_handoff(self, **kw):
            estado["handoffs"].append(kw)
            sessao.status = "waiting_human"
            return SimpleNamespace(
                id="h1",
                phone_number=kw["phone_number"],
                reason=kw["reason"],
                priority=kw["priority"],
                status="pending",
            )

    async def _envio(**kw):
        estado["avisos"].append(kw["message"])
        return SimpleNamespace(id="a1")

    async def _evento(*_a, **_k):
        return None

    monkeypatch.setattr(processor_module, "MessageProcessor", _Processador)
    monkeypatch.setattr(sender_module, "send_whatsapp_message", _envio)
    monkeypatch.setattr(ws_module, "emit_new_handoff", _evento)
    monkeypatch.setattr(ws_module, "emit_new_message", _evento)
    monkeypatch.setattr(
        handoff_manager_module, "get_handoff_manager", lambda *_a: _Gerente()
    )
    monkeypatch.setattr(webhook, "avaliar_limites", lambda *_a, **_k: None)
    monkeypatch.setattr(webhook, "recusou_mensagens", lambda *_a, **_k: False)
    monkeypatch.setattr(webhook, "get_or_create_session", lambda **_k: sessao)
    monkeypatch.setattr(webhook, "ESPERAS_ENTRE_TENTATIVAS_SEGUNDOS", (0.0, 0.0))
    return estado, sessao


def _enviar(db):
    return asyncio.run(
        webhook.process_incoming_message(
            tenant_id=TENANT,
            phone="5511999998888",
            message_content="Quero racao",
            whatsapp_msg_id="wamid.1",
            db=db,
        )
    )


def test_falha_passageira_da_ia_e_repetida_e_o_tutor_e_atendido(monkeypatch):
    estado, _ = _preparar(monkeypatch, falhas=2)

    resultado = _enviar(_DB())

    assert estado["ia"] == 3
    assert estado["handoffs"] == []
    assert resultado["processor_result"] == {"action": "responded"}


def test_falha_definitiva_chama_atendente_e_avisa_o_tutor(monkeypatch):
    estado, sessao = _preparar(monkeypatch, falhas=None)
    db = _DB()

    resultado = _enviar(db)

    assert estado["ia"] == webhook.TENTATIVAS_DE_PROCESSAMENTO
    assert len(estado["handoffs"]) == 1
    assert estado["handoffs"][0]["reason"] == "falha_tecnica"
    assert estado["avisos"] == [webhook.AVISO_ESPERA_ATENDENTE]
    assert sessao.status == "waiting_human"
    assert resultado["processor_result"]["action"] == "processing_failed_handoff"
    assert len(db.messages) == 1  # a mensagem do tutor continua salva
    assert db.rollbacks >= webhook.TENTATIVAS_DE_PROCESSAMENTO


def test_falha_depois_de_ja_ter_respondido_nao_repete_nem_chama_atendente(monkeypatch):
    estado, _ = _preparar(monkeypatch, falhas=None)

    resultado = _enviar(_DB(resposta_existente=SimpleNamespace(id="r1")))

    assert estado["ia"] == 1
    assert estado["handoffs"] == []
    assert estado["avisos"] == []
    assert resultado["processor_result"] == {"action": "responded_before_failure"}


def test_erro_da_ia_nao_vaza_detalhes_para_o_resultado(monkeypatch):
    _preparar(monkeypatch, falhas=None)

    resultado = _enviar(_DB())

    assert "chave-secreta-xyz" not in str(resultado)


# ---------------------------------------------------------------------------
# Segundo plano com sessao propria
# ---------------------------------------------------------------------------


class _SessaoFalsa:
    def __init__(self):
        self.fechada = False
        self.rollbacks = 0

    def close(self):
        self.fechada = True

    def rollback(self):
        self.rollbacks += 1


def test_segundo_plano_usa_sessao_propria_e_sempre_a_fecha(monkeypatch):
    sessoes = []

    def _nova():
        sessoes.append(_SessaoFalsa())
        return sessoes[-1]

    usadas = []

    async def _processar(**kw):
        usadas.append(kw["db"])

    chamadas_depois = []
    monkeypatch.setattr(app_db, "SessionLocal", _nova)
    monkeypatch.setattr(webhook, "process_incoming_message", _processar)

    asyncio.run(
        webhook.processar_mensagem_em_segundo_plano(
            TENANT, "5511999998888", "oi", "w1", depois=chamadas_depois.append
        )
    )

    assert len(sessoes) == 1 and sessoes[0].fechada
    assert usadas == [sessoes[0]]
    assert chamadas_depois == [sessoes[0]]  # `depois` usa a mesma sessao


def test_segundo_plano_nunca_levanta_erro_e_fecha_a_sessao(monkeypatch):
    sessao = _SessaoFalsa()

    async def _quebra(**_kw):
        raise RuntimeError("falha inesperada")

    monkeypatch.setattr(app_db, "SessionLocal", lambda: sessao)
    monkeypatch.setattr(webhook, "process_incoming_message", _quebra)

    asyncio.run(webhook.processar_mensagem_em_segundo_plano(TENANT, "55", "oi", None))

    assert sessao.fechada and sessao.rollbacks == 1


class _Tarefas:
    def __init__(self):
        self.itens = []

    def add_task(self, funcao, **kwargs):
        self.itens.append((funcao, kwargs))


def test_webhook_enfileira_sem_passar_a_sessao_da_requisicao():
    tarefas = _Tarefas()
    carga = {
        "entry": [
            {
                "changes": [
                    {
                        "value": {
                            "messages": [
                                {
                                    "from": "5511999998888",
                                    "id": "w1",
                                    "type": "text",
                                    "text": {"body": "oi"},
                                }
                            ]
                        }
                    }
                ]
            }
        ]
    }

    total = asyncio.run(
        webhook.process_webhook_payload(
            tenant_id=TENANT, payload=carga, background_tasks=tarefas, db=object()
        )
    )

    assert total == 1
    funcao, kwargs = tarefas.itens[0]
    assert funcao is webhook.processar_mensagem_em_segundo_plano
    assert "db" not in kwargs


# ---------------------------------------------------------------------------
# Entrada do orquestrador (n8n): responde na hora
# ---------------------------------------------------------------------------


def test_entrada_do_orquestrador_aceita_na_hora_e_processa_em_segundo_plano(
    monkeypatch,
):
    async def _sem_midia(*_a, **_k):
        return None

    monkeypatch.setattr(interno, "_resolve_openai_api_key", lambda *_a, **_k: "")
    monkeypatch.setattr(interno, "_enrich_payload_media", _sem_midia)
    tarefas = _Tarefas()
    carga = interno.InternalIngestRequest(
        phone="5511999998888", message_type="text", text="oi", external_message_id="w9"
    )

    resposta = asyncio.run(
        interno._ingest_message_inner(
            TENANT, uuid4(), carga, db=object(), background_tasks=tarefas
        )
    )

    assert resposta.status == "accepted" and resposta.success is True
    funcao, kwargs = tarefas.itens[0]
    assert funcao is interno.processar_mensagem_em_segundo_plano
    assert kwargs["message_content"] == "oi"
    assert kwargs["whatsapp_msg_id"] == "w9"
    assert callable(kwargs["depois"])  # o fallback de atendente roda depois da IA
