"""Etapa 0.8 do CRM: o chat do atendente funciona de ponta a ponta."""

import asyncio
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.api.endpoints import whatsapp as endpoint
from app.whatsapp import consent_service
from app.whatsapp import sender as sender_module
from app.whatsapp import websocket as ws_module
from app.whatsapp.message_views import (
    quem_enviou,
    serializar_mensagem,
    serializar_para_historico_do_cliente,
)

RAIZ = Path(__file__).resolve().parents[3]
TENANT = uuid4()


def _msg(tipo="recebida", autor=None, conteudo="Oi", id_="m1"):
    return SimpleNamespace(
        id=id_,
        session_id="s1",
        tipo=tipo,
        conteudo=conteudo,
        sent_by_user_id=autor,
        created_at=datetime(2026, 10, 22, 9, 30, 0),
    )


# ---------------------------------------------------------------------------
# Formato unico da mensagem
# ---------------------------------------------------------------------------


def test_quem_enviou_distingue_tutor_atendente_e_ia():
    assert quem_enviou(_msg("recebida")) == "customer"
    assert quem_enviou(_msg("enviada", autor=7)) == "agent"
    assert quem_enviou(_msg("enviada")) == "bot"


def test_mensagem_traz_os_campos_que_a_tela_espera_e_os_nomes_antigos():
    dados = serializar_mensagem(_msg("enviada", autor=7, conteudo="Já vamos te ajudar"))

    # Contrato com a tela (interface Message de whatsappStore.ts).
    for campo in ("id", "session_id", "sender_type", "content", "timestamp", "read"):
        assert campo in dados
    assert dados["sender_type"] == "agent"
    assert dados["content"] == "Já vamos te ajudar"
    assert dados["timestamp"] == "2026-10-22T09:30:00"
    # Compatibilidade com quem lia o formato anterior.
    assert dados["tipo"] == "enviada" and dados["conteudo"] == "Já vamos te ajudar"


def test_contrato_da_tela_continua_igual_ao_formato_do_servidor():
    store = (RAIZ / "frontend/src/stores/whatsappStore.ts").read_text(encoding="utf-8")
    bloco = store[store.index("export interface Message") :].split("}")[0]

    for campo in ("id", "session_id", "sender_type", "content", "timestamp", "read"):
        assert f"{campo}:" in bloco
    servico = (RAIZ / "frontend/src/services/whatsappService.ts").read_text(
        encoding="utf-8"
    )
    # A tela envia {session_id, message}: o servidor espera exatamente isso.
    assert "session_id: sessionId," in servico and "message: content," in servico
    assert set(endpoint.AtendenteMensagem.model_fields) == {"session_id", "message"}


def test_historico_do_cliente_traz_os_campos_da_ficha():
    dados = serializar_para_historico_do_cliente(_msg("recebida", conteudo="x" * 300))

    assert dados["direcao"] == "recebida" and dados["status"] == "recebido"
    assert len(dados["preview"]) == 120 and len(dados["conteudo"]) == 300
    assert dados["created_at"] == "2026-10-22T09:30:00"
    assert serializar_para_historico_do_cliente(_msg("enviada"))["status"] == "enviado"


def test_ficha_do_cliente_le_os_campos_que_o_servidor_envia():
    tela = (RAIZ / "frontend/src/components/WhatsAppHistorico.jsx").read_text(
        encoding="utf-8"
    )
    for campo in ("direcao", "status", "created_at", "preview", "conteudo"):
        assert f"msg.{campo}" in tela


# ---------------------------------------------------------------------------
# Envio pelo atendente
# ---------------------------------------------------------------------------


class _Consulta:
    def __init__(self, sessao):
        self.sessao = sessao

    def filter(self, *_a, **_k):
        return self

    def first(self):
        return self.sessao


class _DB:
    def __init__(self, sessao):
        self.sessao = sessao

    def query(self, *_a):
        return _Consulta(self.sessao)


def _preparar(monkeypatch, *, status="human", permitido=True, envio="ok"):
    chamadas = {"envio": [], "evento": []}
    sessao = SimpleNamespace(
        id="s1", status=status, phone_number="5511999998888", cliente_id=None
    )

    async def _enviar(**kw):
        chamadas["envio"].append(kw)
        if envio == "falha":
            return None
        return _msg(
            "enviada", autor=kw["sent_by_user_id"], conteudo=kw["message"], id_="novo"
        )

    async def _evento(*args, **_k):
        chamadas["evento"].append(args)

    monkeypatch.setattr(sender_module, "send_whatsapp_message", _enviar)
    monkeypatch.setattr(ws_module, "emit_new_message", _evento)
    monkeypatch.setattr(
        consent_service,
        "pode_enviar_whatsapp",
        lambda *_a, **_k: (permitido, "" if permitido else "recusou_mensagens"),
    )
    return _DB(sessao), chamadas


def _enviar(db, texto="Já vou te ajudar"):
    return asyncio.run(
        endpoint.enviar_mensagem_do_atendente(
            request=endpoint.AtendenteMensagem(session_id="s1", message=texto),
            user_and_tenant=(SimpleNamespace(id=7), TENANT),
            db=db,
        )
    )


def test_atendente_envia_pelo_whatsapp_e_a_mensagem_fica_com_o_autor(monkeypatch):
    db, chamadas = _preparar(monkeypatch)

    resposta = _enviar(db, "  Já vou te ajudar  ")

    assert chamadas["envio"][0]["message"] == "Já vou te ajudar"
    assert chamadas["envio"][0]["sent_by_user_id"] == 7
    assert chamadas["envio"][0]["session_id"] == "s1"
    assert resposta["sender_type"] == "agent"
    assert resposta["content"] == "Já vou te ajudar"
    assert len(chamadas["evento"]) == 1  # os outros atendentes da loja veem


def test_conversa_com_a_ia_exige_assumir_antes(monkeypatch):
    db, chamadas = _preparar(monkeypatch, status="bot")

    with pytest.raises(HTTPException) as erro:
        _enviar(db)

    assert erro.value.status_code == 409
    assert chamadas["envio"] == []


def test_conversa_aguardando_atendente_aceita_resposta(monkeypatch):
    db, chamadas = _preparar(monkeypatch, status="waiting_human")

    _enviar(db)

    assert len(chamadas["envio"]) == 1


def test_tutor_que_recusou_nao_recebe_mensagem_do_atendente(monkeypatch):
    db, chamadas = _preparar(monkeypatch, permitido=False)

    with pytest.raises(HTTPException) as erro:
        _enviar(db)

    assert erro.value.status_code == 403
    assert chamadas["envio"] == []


def test_conversa_inexistente_ou_de_outra_loja_da_404(monkeypatch):
    db, _ = _preparar(monkeypatch)
    db.sessao = None

    with pytest.raises(HTTPException) as erro:
        _enviar(db)

    assert erro.value.status_code == 404


def test_falha_do_provedor_vira_erro_claro_e_nao_mensagem_falsa(monkeypatch):
    db, chamadas = _preparar(monkeypatch, envio="falha")

    with pytest.raises(HTTPException) as erro:
        _enviar(db)

    assert erro.value.status_code == 502
    assert chamadas["evento"] == []


def test_mensagem_em_branco_e_recusada_antes_de_enviar(monkeypatch):
    db, chamadas = _preparar(monkeypatch)

    with pytest.raises(HTTPException) as erro:
        _enviar(db, "   ")

    assert erro.value.status_code == 422
    assert chamadas["envio"] == []


def test_o_envio_simulado_antigo_nao_existe_mais():
    fonte = (RAIZ / "backend/app/api/endpoints/whatsapp.py").read_text(encoding="utf-8")
    assert "Obrigado pela mensagem" not in fonte
    assert "class MessageRequest" not in fonte


# ---------------------------------------------------------------------------
# Codigo morto removido e modelo de conversa unico
# ---------------------------------------------------------------------------


def test_codigo_sem_uso_foi_removido():
    base = RAIZ / "backend/app/whatsapp"
    sender = (base / "sender.py").read_text(encoding="utf-8")
    assert "send_bulk_messages" not in sender
    assert "send_notificacao_entrega" not in sender
    assert not (base / "notifications.py").exists()


def test_historico_do_cliente_nao_le_mais_o_modelo_de_conversa_paralelo():
    fonte = (RAIZ / "backend/app/routes/whatsapp_routes.py").read_text(encoding="utf-8")
    assert "aba6_aba9_models" not in fonte
    assert "ConversaWhatsApp" not in fonte
    assert "WhatsAppMessage" in fonte
