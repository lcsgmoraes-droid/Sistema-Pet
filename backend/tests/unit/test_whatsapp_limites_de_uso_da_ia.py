"""Etapa 0.6 do CRM: limites de uso da IA no atendimento por WhatsApp."""

import asyncio
from types import SimpleNamespace

import pytest

from app.whatsapp import handoff_manager as handoff_manager_module
from app.whatsapp import processor as processor_module
from app.whatsapp import sender as sender_module
from app.whatsapp import usage_limits as limites
from app.whatsapp import webhook
from app.whatsapp import websocket as ws_module

TENANT = "11111111-1111-1111-1111-111111111111"


@pytest.fixture(autouse=True)
def _ambiente_limpo(monkeypatch):
    for nome in (
        "WHATSAPP_IA_DAILY_TOKEN_LIMIT",
        "WHATSAPP_IA_MAX_MESSAGES_PER_WINDOW",
        "WHATSAPP_IA_WINDOW_MINUTES",
    ):
        monkeypatch.delenv(nome, raising=False)


# ---------------------------------------------------------------------------
# Regras de limite (banco simulado)
# ---------------------------------------------------------------------------


class _Consulta:
    def __init__(self, db):
        self.db = db

    def filter(self, *_a, **_k):
        return self

    def scalar(self):
        return self.db.respostas.pop(0)


class _DB:
    """Devolve, em ordem, os valores de cada consulta feita."""

    def __init__(self, *respostas):
        self.respostas = list(respostas)

    def query(self, *_cols):
        return _Consulta(self)


def test_padroes_de_limite():
    assert limites.limite_diario_tokens() == 1_000_000
    assert limites.limite_mensagens_por_janela() == (15, 10)


def test_valores_do_ambiente_sao_respeitados_e_invalidos_voltam_ao_padrao(monkeypatch):
    monkeypatch.setenv("WHATSAPP_IA_DAILY_TOKEN_LIMIT", "5000")
    monkeypatch.setenv("WHATSAPP_IA_MAX_MESSAGES_PER_WINDOW", "abc")

    assert limites.limite_diario_tokens() == 5000
    assert limites.limite_mensagens_por_janela()[0] == 15


def test_limite_diario_de_tokens_bloqueia_a_ia(monkeypatch):
    monkeypatch.setenv("WHATSAPP_IA_DAILY_TOKEN_LIMIT", "1000")

    assert limites.avaliar_limites(_DB(1000), TENANT, "s1") == limites.LIMITE_DIARIO
    assert limites.avaliar_limites(_DB(2500), TENANT, "s1") == limites.LIMITE_DIARIO


def test_abaixo_dos_limites_a_ia_responde(monkeypatch):
    monkeypatch.setenv("WHATSAPP_IA_DAILY_TOKEN_LIMIT", "1000")

    # 999 tokens usados hoje e 15 mensagens na janela (o maximo ainda e permitido).
    assert limites.avaliar_limites(_DB(999, 15), TENANT, "s1") is None


def test_excesso_de_mensagens_na_janela_bloqueia_a_ia():
    # Sem uso de tokens e 16 mensagens na janela (acima do maximo de 15).
    assert (
        limites.avaliar_limites(_DB(0, 16), TENANT, "s1")
        == limites.EXCESSO_DE_MENSAGENS
    )


def test_limite_zero_desliga_cada_regra(monkeypatch):
    monkeypatch.setenv("WHATSAPP_IA_DAILY_TOKEN_LIMIT", "0")
    monkeypatch.setenv("WHATSAPP_IA_MAX_MESSAGES_PER_WINDOW", "0")

    # Nenhuma consulta deveria ser feita.
    assert limites.avaliar_limites(_DB(), TENANT, "s1") is None


# ---------------------------------------------------------------------------
# Efeito no atendimento (webhook)
# ---------------------------------------------------------------------------


class _Q:
    def filter(self, *_a, **_k):
        return self

    def first(self):
        return None


class _WebhookDB:
    def __init__(self):
        self.messages = []
        self.pending = None

    def query(self, *_a):
        return _Q()

    def add(self, m):
        self.pending = m

    def commit(self):
        self.pending.id = f"m-{len(self.messages) + 1}"
        self.messages.append(self.pending)

    def rollback(self):
        pass


def _preparar(monkeypatch, *, motivo=None, falha_ao_avaliar=False):
    chamadas = {"ia": [], "handoff": [], "aviso": [], "evento": []}
    sessao = SimpleNamespace(
        id="session-1",
        status="bot",
        phone_number="5511999998888",
        message_count=0,
        last_message_at=None,
    )

    class _Processador:
        def __init__(self, *, db, tenant_id):
            pass

        async def process_message(self, **kw):
            chamadas["ia"].append(kw)
            return {"action": "responded"}

    class _Gerente:
        def get_active_handoff(self, _sid):
            return None

        def create_handoff(self, **kw):
            chamadas["handoff"].append(kw)
            sessao.status = "waiting_human"
            return SimpleNamespace(
                id="h-1",
                phone_number=kw["phone_number"],
                reason=kw["reason"],
                priority=kw["priority"],
                status="pending",
            )

    async def _envio(**kw):
        chamadas["aviso"].append(kw)
        return SimpleNamespace(id="a-1")

    async def _evento(*a, **k):
        chamadas["evento"].append(a)

    def _avaliar(*_a, **_k):
        if falha_ao_avaliar:
            raise RuntimeError("banco indisponivel")
        return motivo

    monkeypatch.setattr(processor_module, "MessageProcessor", _Processador)
    monkeypatch.setattr(sender_module, "send_whatsapp_message", _envio)
    monkeypatch.setattr(ws_module, "emit_new_handoff", _evento)
    monkeypatch.setattr(
        handoff_manager_module, "get_handoff_manager", lambda *_a: _Gerente()
    )
    monkeypatch.setattr(webhook, "avaliar_limites", _avaliar)
    monkeypatch.setattr(webhook, "get_or_create_session", lambda **_k: sessao)
    return chamadas, sessao


def _enviar(db=None):
    return asyncio.run(
        webhook.process_incoming_message(
            tenant_id=TENANT,
            phone="5511999998888",
            message_content="oi",
            whatsapp_msg_id="wamid.1",
            db=db or _WebhookDB(),
        )
    )


def test_limite_diario_nao_chama_a_ia_e_leva_a_conversa_para_atendente(monkeypatch):
    chamadas, sessao = _preparar(monkeypatch, motivo=limites.LIMITE_DIARIO)

    resultado = _enviar()

    assert chamadas["ia"] == []
    assert len(chamadas["handoff"]) == 1
    assert chamadas["handoff"][0]["reason"] == "ia_limite_diario"
    assert sessao.status == "waiting_human"
    assert len(chamadas["evento"]) == 1
    assert len(chamadas["aviso"]) == 1  # aviso de espera ao tutor
    assert resultado["processor_result"]["action"] == "skipped_ia_limit"
    assert resultado["processor_result"]["reason"] == limites.LIMITE_DIARIO


def test_excesso_de_mensagens_pausa_a_ia_em_silencio(monkeypatch):
    chamadas, sessao = _preparar(monkeypatch, motivo=limites.EXCESSO_DE_MENSAGENS)

    resultado = _enviar()

    assert chamadas["ia"] == []
    assert chamadas["handoff"] == []
    assert chamadas["aviso"] == []
    assert sessao.status == "bot"
    assert resultado["processor_result"]["reason"] == limites.EXCESSO_DE_MENSAGENS


def test_dentro_dos_limites_a_ia_responde(monkeypatch):
    chamadas, _sessao = _preparar(monkeypatch, motivo=None)

    resultado = _enviar()

    assert len(chamadas["ia"]) == 1
    assert resultado["processor_result"] == {"action": "responded"}


def test_falha_ao_conferir_limites_nao_derruba_o_atendimento(monkeypatch):
    chamadas, _sessao = _preparar(monkeypatch, falha_ao_avaliar=True)

    resultado = _enviar()

    assert len(chamadas["ia"]) == 1
    assert resultado["status"] == "processed"
