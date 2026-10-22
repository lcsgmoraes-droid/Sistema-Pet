"""Etapa 0.7 do CRM: SAIR, quem recusou mensagens e LGPD nas conversas."""

import asyncio
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.whatsapp import consent_service as consent
from app.whatsapp import handoff_manager as handoff_manager_module
from app.whatsapp import lgpd_dados, webhook
from app.whatsapp import processor as processor_module
from app.whatsapp import sender as sender_module
from app.whatsapp import websocket as ws_module

TENANT = "11111111-1111-1111-1111-111111111111"
RAIZ = Path(__file__).resolve().parents[3]


# ---------------------------------------------------------------------------
# Reconhecer o pedido para parar
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "texto",
    ["SAIR", " sair! ", "Parar", "STOP", "Não quero receber", "descadastrar", "Sair."],
)
def test_mensagem_inteira_de_saida_e_reconhecida(texto):
    assert consent.e_pedido_de_saida(texto)


@pytest.mark.parametrize(
    "texto",
    [
        "quero sair do plano",
        "cancelar pedido 123",
        "sair de casa agora",
        "",
        None,
        "oi",
    ],
)
def test_frases_normais_com_a_palavra_nao_sao_pedido_de_saida(texto):
    assert not consent.e_pedido_de_saida(texto)


def test_contato_sem_cadastro_e_identificado_so_pelos_digitos():
    assert consent.chave_contato("+55 (11) 99999-8888") == "5511999998888"
    assert consent.chave_contato("266915104710838@LID") == "266915104710838@lid"


# ---------------------------------------------------------------------------
# Decidir se pode enviar
# ---------------------------------------------------------------------------


def _registro(consentiu, revogado, dia):
    return SimpleNamespace(
        id=dia,
        created_at=datetime(2026, 10, dia),
        consent_given=consentiu,
        revoked_at=datetime(2026, 10, dia) if revogado else None,
    )


def _com_registros(monkeypatch, cliente=None, contato=None):
    def _ultimo(_db, _tenant, tipo, _titular):
        return cliente if tipo == "customer" else contato

    monkeypatch.setattr(consent, "_ultimo_registro", _ultimo)


def test_sem_nenhum_registro_nao_ha_recusa(monkeypatch):
    _com_registros(monkeypatch)

    assert consent.recusou_mensagens(None, TENANT, "5511999998888", 5) is False


def test_recusa_do_cadastro_ou_do_contato_vale(monkeypatch):
    _com_registros(monkeypatch, cliente=_registro(False, True, 20))
    assert consent.recusou_mensagens(None, TENANT, "5511999998888", 5) is True

    _com_registros(monkeypatch, contato=_registro(False, True, 20))
    assert consent.recusou_mensagens(None, TENANT, "5511999998888", None) is True


def test_o_registro_mais_recente_manda(monkeypatch):
    # Recusou no dia 10 e autorizou de novo no dia 20: pode receber.
    _com_registros(
        monkeypatch,
        cliente=_registro(True, False, 20),
        contato=_registro(False, True, 10),
    )
    assert consent.recusou_mensagens(None, TENANT, "5511999998888", 5) is False

    # Autorizou no dia 10 e recusou no dia 20: nao pode.
    _com_registros(
        monkeypatch,
        cliente=_registro(True, False, 10),
        contato=_registro(False, True, 20),
    )
    assert consent.recusou_mensagens(None, TENANT, "5511999998888", 5) is True


def test_quem_recusou_nao_recebe_nada_exceto_resposta_se_a_loja_permitir(monkeypatch):
    _com_registros(monkeypatch, contato=_registro(False, True, 20))

    assert consent.pode_enviar_whatsapp(None, TENANT, "5511999998888") == (
        False,
        "recusou_mensagens",
    )
    assert consent.pode_enviar_whatsapp(
        None, TENANT, "5511999998888", resposta_ao_tutor=True
    ) == (False, "recusou_mensagens")
    assert consent.pode_enviar_whatsapp(
        None,
        TENANT,
        "5511999998888",
        resposta_ao_tutor=True,
        permitir_resposta_a_recusa=True,
    ) == (True, "")


def test_quem_nao_recusou_pode_receber(monkeypatch):
    _com_registros(monkeypatch)

    assert consent.pode_enviar_whatsapp(None, TENANT, "5511999998888") == (True, "")


class _DBRegistro:
    def __init__(self):
        self.adicionados = []
        self.commits = 0

    def add(self, objeto):
        self.adicionados.append(objeto)

    def commit(self):
        self.commits += 1


def test_registrar_recusa_de_quem_tem_cadastro_grava_no_cliente():
    db = _DBRegistro()

    registro = consent.registrar_recusa(db, TENANT, "5511999998888", cliente_id=5)

    assert registro.subject_type == "customer" and registro.subject_id == "5"
    assert registro.consent_given is False and registro.revoked_at is not None
    assert registro.revoke_reason == "sair_whatsapp"
    assert db.commits == 1


def test_registrar_recusa_de_lead_grava_no_contato_pelo_numero():
    db = _DBRegistro()

    registro = consent.registrar_recusa(db, TENANT, "+55 (11) 99999-8888")

    assert registro.subject_type == "contact"
    assert registro.subject_id == "5511999998888"


# ---------------------------------------------------------------------------
# Efeito no atendimento
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


def _preparar(monkeypatch, *, recusou=False, status="bot"):
    chamadas = {"ia": [], "recusas": [], "envios": [], "handoffs": []}
    sessao = SimpleNamespace(
        id="session-1",
        status=status,
        phone_number="5511999998888",
        cliente_id=None,
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
            chamadas["handoffs"].append(kw)
            return SimpleNamespace(
                id="h-1",
                phone_number=kw["phone_number"],
                reason=kw["reason"],
                priority=kw["priority"],
                status="pending",
            )

    async def _envio(**kw):
        chamadas["envios"].append(kw["message"])
        return SimpleNamespace(id="e-1")

    async def _evento(*_a, **_k):
        return None

    monkeypatch.setattr(processor_module, "MessageProcessor", _Processador)
    monkeypatch.setattr(sender_module, "send_whatsapp_message", _envio)
    monkeypatch.setattr(ws_module, "emit_new_handoff", _evento)
    monkeypatch.setattr(
        handoff_manager_module, "get_handoff_manager", lambda *_a: _Gerente()
    )
    monkeypatch.setattr(webhook, "recusou_mensagens", lambda *_a, **_k: recusou)
    monkeypatch.setattr(
        webhook,
        "registrar_recusa",
        lambda db, tenant, phone, cliente_id=None: chamadas["recusas"].append(
            (phone, cliente_id)
        ),
    )
    monkeypatch.setattr(webhook, "avaliar_limites", lambda *_a, **_k: None)
    monkeypatch.setattr(webhook, "get_or_create_session", lambda **_k: sessao)
    return chamadas, sessao


def _enviar(texto):
    return asyncio.run(
        webhook.process_incoming_message(
            tenant_id=TENANT,
            phone="5511999998888",
            message_content=texto,
            whatsapp_msg_id="wamid.1",
            db=_WebhookDB(),
        )
    )


def test_sair_registra_a_recusa_confirma_e_nao_chama_a_ia(monkeypatch):
    chamadas, _ = _preparar(monkeypatch)

    resultado = _enviar("SAIR")

    assert chamadas["ia"] == []
    assert chamadas["recusas"] == [("5511999998888", None)]
    assert chamadas["envios"] == [consent.CONFIRMACAO_DE_SAIDA]
    assert resultado["processor_result"] == {
        "action": "opt_out_registered",
        "confirmation_sent": True,
    }


def test_sair_vale_mesmo_com_atendimento_humano_em_andamento(monkeypatch):
    chamadas, _ = _preparar(monkeypatch, status="human")

    _enviar("parar")

    assert len(chamadas["recusas"]) == 1


def test_tutor_que_recusou_escreve_de_novo_vai_para_atendente_sem_ia_e_sem_aviso(
    monkeypatch,
):
    chamadas, _ = _preparar(monkeypatch, recusou=True)

    resultado = _enviar("Oi, tudo bem?")

    assert chamadas["ia"] == []
    assert len(chamadas["handoffs"]) == 1
    assert chamadas["handoffs"][0]["reason"] == "recusou_mensagens"
    assert chamadas["envios"] == []
    assert resultado["processor_result"]["action"] == "skipped_opt_out"


def test_tutor_que_recusou_nao_recebe_o_aviso_de_espera(monkeypatch):
    chamadas, _ = _preparar(monkeypatch, recusou=True, status="waiting_human")

    resultado = _enviar("alguem ai?")

    assert chamadas["envios"] == []
    assert resultado["processor_result"]["waiting_notice_sent"] is False


def test_tutor_que_nao_recusou_continua_atendido_pela_ia(monkeypatch):
    chamadas, _ = _preparar(monkeypatch, recusou=False)

    resultado = _enviar("Quero racao")

    assert len(chamadas["ia"]) == 1
    assert resultado["processor_result"] == {"action": "responded"}


# ---------------------------------------------------------------------------
# LGPD: exportar e anonimizar as conversas
# ---------------------------------------------------------------------------


class _ListaQuery:
    def __init__(self, itens):
        self.itens = itens

    def filter(self, *_a, **_k):
        return self

    def order_by(self, *_a):
        return self

    def all(self):
        return list(self.itens)

    def __iter__(self):
        return iter(self.itens)


class _DBLgpd:
    def __init__(self, sessoes, mensagens, atendimentos, notas, consentimentos):
        from app.whatsapp.models import WhatsAppMessage, WhatsAppSession
        from app.whatsapp.models_handoff import WhatsAppHandoff, WhatsAppInternalNote
        from app.whatsapp.security import DataPrivacyConsent

        self.por_modelo = {
            WhatsAppSession: sessoes,
            WhatsAppMessage: mensagens,
            WhatsAppHandoff: atendimentos,
            WhatsAppInternalNote: notas,
            DataPrivacyConsent: consentimentos,
        }

    def query(self, modelo):
        return _ListaQuery(self.por_modelo[modelo])


def _cenario_lgpd():
    sessao = SimpleNamespace(
        id="s-1",
        phone_number="5511999998888",
        cliente_id=5,
        status="human",
        context='{"produto": "racao"}',
        last_intent="compra",
        assigned_to=7,
        closed_at=None,
        started_at=datetime(2026, 10, 1, 9, 0),
    )
    mensagens = [
        SimpleNamespace(
            tipo="recebida",
            conteudo="Meu endereco e Rua A",
            message_metadata="{}",
            created_at=datetime(2026, 10, 1, 9, 1),
        ),
        SimpleNamespace(
            tipo="enviada",
            conteudo="Anotado",
            message_metadata=None,
            created_at=datetime(2026, 10, 1, 9, 2),
        ),
    ]
    atendimento = SimpleNamespace(
        phone_number="5511999998888",
        customer_name="Camila",
        reason_details="reclamacao",
        resolution_notes="devolvi o valor",
        rating_feedback="otimo",
        reason="reclamacao",
        status="resolved",
        created_at=datetime(2026, 10, 1, 10, 0),
    )
    nota = SimpleNamespace(note="ligar para a Camila no 11 99999-8888")
    contato = SimpleNamespace(
        subject_id="5511999998888",
        phone_number="5511999998888",
        email="x@y.com",
        revoked_at=None,
        revoke_reason=None,
    )
    db = _DBLgpd([sessao], mensagens, [atendimento], [nota], [contato])
    return db, sessao, mensagens, atendimento, nota, contato


def test_anonimizar_conversas_remove_mensagens_telefone_e_vinculo():
    db, sessao, mensagens, atendimento, nota, contato = _cenario_lgpd()
    agora = datetime(2026, 10, 22, 12, 0)

    resumo = lgpd_dados.anonimizar_conversas_do_tutor(
        db, TENANT, 5, ["(11) 99999-8888", None], agora
    )

    assert resumo == {
        "conversas": 1,
        "mensagens": 2,
        "atendimentos": 1,
        "notas": 1,
        "consentimentos_de_contato": 1,
    }
    assert all(m.conteudo == lgpd_dados.CONTEUDO_REMOVIDO for m in mensagens)
    assert sessao.phone_number.startswith("anon-") and "9999" not in sessao.phone_number
    assert (
        sessao.cliente_id is None
        and sessao.context is None
        and sessao.assigned_to is None
    )
    assert sessao.status == "closed" and sessao.closed_at == agora
    assert atendimento.customer_name is None and atendimento.resolution_notes is None
    assert (
        atendimento.phone_number == sessao.phone_number
        or atendimento.phone_number.startswith("anon-")
    )
    assert nota.note == lgpd_dados.CONTEUDO_REMOVIDO
    assert contato.subject_id.startswith("anon-") and contato.phone_number is None
    assert contato.email is None and contato.revoked_at == agora


def test_exportar_conversas_traz_mensagens_e_atendimentos():
    db, *_ = _cenario_lgpd()

    dossie = lgpd_dados.exportar_conversas_do_tutor(db, TENANT, 5, ["(11) 99999-8888"])

    assert len(dossie["conversas"]) == 1
    conversa = dossie["conversas"][0]
    assert conversa["status"] == "human"
    assert [m["conteudo"] for m in conversa["mensagens"]] == [
        "Meu endereco e Rua A",
        "Anotado",
    ]
    assert dossie["atendimentos"][0]["motivo"] == "reclamacao"


def test_anonimizacao_do_cliente_trata_as_conversas_antes_de_apagar_o_telefone():
    fonte = (RAIZ / "backend/app/services/lgpd_customer_data.py").read_text(
        encoding="utf-8"
    )

    chamada = fonte.index("anonimizar_conversas_do_tutor(")
    apaga_telefone = fonte.index('"telefone",\n            "celular"')
    assert chamada < apaga_telefone
    assert "exportar_conversas_do_tutor(" in fonte


def test_leitura_das_mensagens_de_uma_conversa_e_auditada():
    fonte = (RAIZ / "backend/app/api/endpoints/whatsapp.py").read_text(encoding="utf-8")

    assert (
        "_registrar_acesso_a_conversa(db, tenant_id, session_id, current_user)" in fonte
    )
    assert 'resource_type="whatsapp_conversa"' in fonte
