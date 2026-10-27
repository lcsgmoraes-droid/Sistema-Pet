"""Livro-razao de mensagens de WhatsApp: estado de entrega, cobranca e consumo por periodo."""

from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from app.db import Base
from app.tenancy.context import clear_current_tenant, set_current_tenant
from app.whatsapp import ledger_service as ledger
from app.whatsapp import models_handoff  # noqa: F401  (mapeia WhatsAppHandoff)
from app.whatsapp.ledger_models import WhatsAppLedger
from app.whatsapp.models import WhatsAppMessage, WhatsAppSession

RAIZ = Path(__file__).resolve().parents[2]
TENANT = uuid4()


@pytest.fixture()
def db():
    engine = create_engine("sqlite:///:memory:")

    @event.listens_for(engine, "connect")
    def _now(conexao, _registro):
        conexao.create_function("now", 0, lambda: "2026-10-26 09:00:00")

    Base.metadata.create_all(
        engine,
        tables=[
            Base.metadata.tables[nome]
            for nome in (
                "whatsapp_ledger",
                "whatsapp_ia_sessions",
                "whatsapp_ia_messages",
            )
        ],
    )
    sessao = sessionmaker(bind=engine)()
    set_current_tenant(TENANT)
    yield sessao
    clear_current_tenant()
    sessao.close()


def _sessao_com_mensagens(db, recebida_ha=None):
    sessao = WhatsAppSession(
        tenant_id=TENANT, phone_number="5511999998888", status="bot"
    )
    db.add(sessao)
    db.flush()
    if recebida_ha is not None:
        db.add(
            WhatsAppMessage(
                session_id=sessao.id,
                tenant_id=TENANT,
                tipo="recebida",
                conteudo="oi",
                created_at=(datetime.now(UTC) - recebida_ha).replace(tzinfo=None),
            )
        )
    db.commit()
    return sessao


def _linha_de_envio(db, sessao, wa_id="wamid.1", origem="ia"):
    mensagem = SimpleNamespace(id="m1")
    assert ledger.anotar_envio(
        db,
        tenant_id=TENANT,
        provedor="meta_cloud",
        session=sessao,
        message_row=mensagem,
        wa_message_id=wa_id,
        origem=origem,
    )
    return db.query(WhatsAppLedger).filter_by(wa_message_id=wa_id).one()


# --- janela de 24h -------------------------------------------------------------


def test_envio_dentro_de_24h_do_tutor_marca_janela_aberta(db):
    sessao = _sessao_com_mensagens(db, recebida_ha=timedelta(hours=3))

    assert _linha_de_envio(db, sessao).janela_24h is True


def test_envio_depois_de_24h_ou_sem_mensagem_do_tutor_fica_fora_da_janela(db):
    velha = _sessao_com_mensagens(db, recebida_ha=timedelta(hours=30))
    assert _linha_de_envio(db, velha, "wamid.a").janela_24h is False

    sem_mensagem = _sessao_com_mensagens(db)
    assert _linha_de_envio(db, sem_mensagem, "wamid.b").janela_24h is False


# --- avisos de estado da Meta ---------------------------------------------------


def _aviso(wa_id, status, **extra):
    return {"id": wa_id, "status": status, "timestamp": "1790000000", **extra}


def test_estados_so_avancam_e_guardam_o_horario_de_cada_etapa(db):
    sessao = _sessao_com_mensagens(db, timedelta(hours=1))
    linha = _linha_de_envio(db, sessao)

    ledger.aplicar_estado_da_meta(db, TENANT, _aviso("wamid.1", "delivered"))
    ledger.aplicar_estado_da_meta(
        db, TENANT, _aviso("wamid.1", "sent")
    )  # atrasado: ignora o recuo
    db.flush()
    assert linha.estado == "entregue" and linha.entregue_em is not None

    ledger.aplicar_estado_da_meta(db, TENANT, _aviso("wamid.1", "read"))
    db.flush()
    assert linha.estado == "lida" and linha.lido_em is not None


def test_cobranca_informada_pela_meta_e_guardada(db):
    linha = _linha_de_envio(db, _sessao_com_mensagens(db))

    ledger.aplicar_estado_da_meta(
        db,
        TENANT,
        _aviso(
            "wamid.1",
            "sent",
            pricing={"billable": True, "pricing_model": "PMP", "category": "marketing"},
        ),
    )
    db.flush()

    assert linha.cobravel is True
    assert linha.categoria_cobranca == "marketing" and linha.modelo_de_preco == "PMP"


def test_falha_guarda_codigo_e_motivo_mas_nao_desfaz_mensagem_entregue(db):
    sessao = _sessao_com_mensagens(db)
    falhou = _linha_de_envio(db, sessao, "wamid.f")
    entregue = _linha_de_envio(db, sessao, "wamid.e")
    erro = {"errors": [{"code": 131047, "title": "Fora da janela de 24 horas"}]}

    ledger.aplicar_estado_da_meta(db, TENANT, _aviso("wamid.f", "failed", **erro))
    ledger.aplicar_estado_da_meta(db, TENANT, _aviso("wamid.e", "delivered"))
    ledger.aplicar_estado_da_meta(db, TENANT, _aviso("wamid.e", "failed", **erro))
    db.flush()

    assert falhou.estado == "falhou" and falhou.erro_codigo == "131047"
    assert "24 horas" in falhou.erro_mensagem
    assert entregue.estado == "entregue"


def test_aviso_de_mensagem_desconhecida_vira_linha_para_nao_perder_cobranca(db):
    resultado = ledger.aplicar_estado_da_meta(
        db,
        TENANT,
        _aviso(
            "wamid.externa",
            "sent",
            recipient_id="5511988887777",
            pricing={"billable": True, "category": "utility"},
        ),
    )
    db.flush()

    linha = db.query(WhatsAppLedger).filter_by(wa_message_id="wamid.externa").one()
    assert resultado == "criada"
    assert linha.origem == "desconhecida" and linha.cobravel is True


def test_aviso_invalido_e_ignorado(db):
    assert (
        ledger.aplicar_estado_da_meta(db, TENANT, {"id": "", "status": "sent"})
        == "ignorada"
    )
    assert (
        ledger.aplicar_estado_da_meta(db, TENANT, _aviso("x", "inventado"))
        == "ignorada"
    )


def test_falha_de_envio_fica_registrada_com_o_motivo(db):
    sessao = _sessao_com_mensagens(db)

    assert ledger.anotar_falha_de_envio(
        db,
        tenant_id=TENANT,
        provedor="meta_cloud",
        session=sessao,
        session_id=sessao.id,
        origem="atendente",
        erro_codigo=190,
        erro_mensagem="O token de acesso é inválido",
    )

    linha = db.query(WhatsAppLedger).one()
    assert (linha.estado, linha.origem, linha.erro_codigo) == (
        "falhou",
        "atendente",
        "190",
    )


def test_recebimento_do_tutor_e_registrado(db):
    sessao = _sessao_com_mensagens(db, timedelta(minutes=1))
    mensagem = db.query(WhatsAppMessage).one()

    assert ledger.anotar_recebimento(
        db,
        tenant_id=TENANT,
        provedor="meta_cloud",
        session=sessao,
        message_row=mensagem,
        wa_message_id="wamid.in",
    )

    linha = db.query(WhatsAppLedger).one()
    assert (linha.direcao, linha.origem, linha.estado) == (
        "recebida",
        "tutor",
        "recebida",
    )


def test_mesmo_id_da_meta_nao_duplica(db):
    sessao = _sessao_com_mensagens(db)
    _linha_de_envio(db, sessao, "wamid.dup")

    repetida = ledger.anotar_envio(
        db,
        tenant_id=TENANT,
        provedor="meta_cloud",
        session=sessao,
        message_row=SimpleNamespace(id="m2"),
        wa_message_id="wamid.dup",
        origem="ia",
    )

    assert repetida is False and db.query(WhatsAppLedger).count() == 1


# --- resumo ---------------------------------------------------------------------


def test_resumo_separa_enviadas_recebidas_falhas_e_cobraveis(db):
    sessao = _sessao_com_mensagens(db, timedelta(hours=1))
    _linha_de_envio(db, sessao, "wamid.1", origem="ia")
    _linha_de_envio(db, sessao, "wamid.2", origem="atendente")
    _linha_de_envio(db, sessao, "wamid.3", origem="ia")
    ledger.aplicar_estado_da_meta(
        db,
        TENANT,
        _aviso("wamid.1", "sent", pricing={"billable": True, "category": "marketing"}),
    )
    ledger.aplicar_estado_da_meta(
        db,
        TENANT,
        _aviso("wamid.2", "sent", pricing={"billable": False, "category": "service"}),
    )
    ledger.aplicar_estado_da_meta(db, TENANT, _aviso("wamid.3", "failed"))
    ledger.anotar_recebimento(
        db,
        tenant_id=TENANT,
        provedor="meta_cloud",
        session=sessao,
        message_row=db.query(WhatsAppMessage).one(),
        wa_message_id="wamid.in",
    )
    db.commit()
    inicio, fim = ledger.periodo_do_mes(None)

    resumo = ledger.resumo_do_periodo(db, TENANT, inicio, fim)

    assert resumo["totais"] == {
        "enviadas": 3,
        "recebidas": 1,
        "falhas": 1,
        "cobraveis": 1,
        "sem_informacao_de_cobranca": 0,
    }
    assert resumo["cobraveis_por_categoria"] == {"marketing": 1}
    assert resumo["enviadas_por_origem"] == {"ia": 2, "atendente": 1}


def test_periodo_do_mes_trata_virada_de_ano_e_mes_invalido():
    inicio, fim = ledger.periodo_do_mes("2026-12")
    assert (inicio.month, fim.year, fim.month) == (12, 2027, 1)
    with pytest.raises(ValueError, match="AAAA-MM"):
        ledger.periodo_do_mes("outubro")


def test_ledger_nunca_derruba_o_atendimento():
    class _DbQuebrado:
        def begin_nested(self):
            raise RuntimeError("banco fora")

        def query(self, *_a):
            raise RuntimeError("banco fora")

        def rollback(self):
            pass

    sessao = SimpleNamespace(id="s1", phone_number="55")

    assert (
        ledger.anotar_envio(
            _DbQuebrado(),
            tenant_id=TENANT,
            provedor="meta_cloud",
            session=sessao,
            message_row=SimpleNamespace(id="m"),
            wa_message_id="w",
            origem="ia",
        )
        is False
    )


# --- ligacoes com o envio e o webhook -------------------------------------------


def test_envio_e_webhook_alimentam_o_livro_razao():
    sender = (RAIZ / "app/whatsapp/sender.py").read_text(encoding="utf-8")
    webhook = (RAIZ / "app/whatsapp/webhook.py").read_text(encoding="utf-8")

    assert "ledger_service.anotar_envio(" in sender
    assert sender.count("ledger_service.anotar_falha_de_envio(") == 2
    assert "ledger_service.aplicar_avisos_de_estado(" in webhook
    assert "_anotar_recebimento_no_ledger(" in webhook


def test_origem_do_envio_e_o_provedor():
    assert ledger.origem_do_envio("text", 7) == "atendente"
    assert ledger.origem_do_envio("notificacao_sistema", None) == "sistema"
    assert ledger.origem_do_envio("text", None) == "ia"
    assert ledger.provedor_do_cliente(type("MetaCloudClient", (), {})()) == "meta_cloud"
    assert ledger.provedor_do_cliente(type("Dialog360Client", (), {})()) == "360dialog"
