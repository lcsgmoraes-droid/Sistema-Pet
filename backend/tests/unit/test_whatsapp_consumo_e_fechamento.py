"""Tarifas, custo estimado, fechamento mensal, fatura da Meta e envio de modelo."""

import asyncio
from datetime import UTC, date, datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from app.db import Base
from app.models import Tenant
from app.ops_tenant_log_models import OpsTenantChangeLog
from app.services import ops_whatsapp_consumo_service as consumo
from app.tenancy.context import clear_current_tenant, set_current_tenant
from app.whatsapp import consent_service
from app.whatsapp import ledger_service as ledger
from app.whatsapp import models_handoff  # noqa: F401  (mapeia WhatsAppHandoff)
from app.whatsapp import sender as sender_module
from app.whatsapp.consumo_models import WhatsAppFechamento
from app.whatsapp.ledger_models import WhatsAppLedger
from app.whatsapp.models import WhatsAppMessage, WhatsAppSession

TENANT = uuid4()
ADMIN = SimpleNamespace(id=1, email="ops@corepet.test")
HOJE = datetime.now(UTC)
MES = f"{HOJE.year:04d}-{HOJE.month:02d}"


@pytest.fixture()
def db():
    engine = create_engine("sqlite:///:memory:")

    @event.listens_for(engine, "connect")
    def _now(conexao, _registro):
        conexao.create_function("now", 0, lambda: HOJE.strftime("%Y-%m-%d %H:%M:%S"))

    nomes = (
        "tenants",
        "whatsapp_ledger",
        "whatsapp_tarifas",
        "whatsapp_fechamentos",
        "whatsapp_ia_sessions",
        "whatsapp_ia_messages",
        "ops_tenant_change_log",
    )
    Base.metadata.create_all(
        engine, tables=[Base.metadata.tables[nome] for nome in nomes]
    )
    sessao = sessionmaker(bind=engine)()
    sessao.add(Tenant(id=str(TENANT), name="Loja Teste", name_normalized="loja teste"))
    sessao.commit()
    set_current_tenant(TENANT)
    yield sessao
    clear_current_tenant()
    sessao.close()


def _tarifa(db, categoria="marketing", valor="0.36", desde=date(2026, 1, 1)):
    return consumo.cadastrar_tarifa(
        db, categoria=categoria, valor=valor, vigente_desde=desde, admin_email="ops@x"
    )


def _envio_cobravel(db, wa_id, categoria="marketing", cobravel=True):
    sessao = db.query(WhatsAppSession).first() or WhatsAppSession(
        tenant_id=TENANT, phone_number="5511999998888", status="bot"
    )
    db.add(sessao)
    db.flush()
    ledger.anotar_envio(
        db,
        tenant_id=TENANT,
        provedor="meta_cloud",
        session=sessao,
        message_row=SimpleNamespace(id=wa_id),
        wa_message_id=wa_id,
        origem="automacao",
        tipo_conteudo="modelo",
        template_nome="aniversario",
        template_categoria=categoria,
    )
    ledger.aplicar_estado_da_meta(
        db,
        TENANT,
        {
            "id": wa_id,
            "status": "sent",
            "timestamp": str(int(HOJE.timestamp())),
            "pricing": {"billable": cobravel, "category": categoria},
        },
    )
    db.commit()


# --- tarifas ----------------------------------------------------------------------


def test_tarifa_nova_vale_a_partir_da_data_e_nao_sobrescreve(db):
    _tarifa(db, valor="0.36", desde=date(2026, 1, 1))
    _tarifa(db, valor="0.40", desde=date(2026, 7, 1))
    db.commit()

    assert float(ledger.tarifa_vigente(db, "marketing", date(2026, 3, 1))) == 0.36
    assert float(ledger.tarifa_vigente(db, "marketing", date(2026, 8, 1))) == 0.40
    assert ledger.tarifa_vigente(db, "marketing", date(2025, 12, 31)) is None
    assert ledger.tarifa_vigente(db, "utility", date(2026, 8, 1)) is None
    with pytest.raises(consumo.ConsumoError) as erro:
        _tarifa(db, valor="0.99", desde=date(2026, 7, 1))
    assert erro.value.status_code == 409


def test_tarifa_invalida_e_recusada(db):
    with pytest.raises(consumo.ConsumoError, match="Categoria"):
        _tarifa(db, categoria="inventada")
    with pytest.raises(consumo.ConsumoError, match="entre 0 e 100"):
        _tarifa(db, valor="500")


# --- custo estimado ---------------------------------------------------------------


def test_custo_estimado_usa_a_tarifa_quando_a_meta_informa_a_cobranca(db):
    _tarifa(db)
    db.commit()
    _envio_cobravel(db, "wamid.1")

    linha = db.query(WhatsAppLedger).filter_by(wa_message_id="wamid.1").one()

    assert float(linha.custo_estimado) == 0.36 and linha.moeda == "BRL"


def test_mensagem_nao_cobravel_nao_tem_custo(db):
    _tarifa(db)
    db.commit()
    _envio_cobravel(db, "wamid.2", cobravel=False)

    linha = db.query(WhatsAppLedger).filter_by(wa_message_id="wamid.2").one()

    assert linha.custo_estimado is None


def test_cobraveis_sem_tarifa_aparecem_e_somem_depois_de_recalcular(db):
    _envio_cobravel(db, "wamid.3", categoria="utility")
    inicio, fim = ledger.periodo_do_mes(None)

    antes = ledger.resumo_do_periodo(db, TENANT, inicio, fim)
    assert antes["totais"]["cobraveis_sem_tarifa"] == 1 and antes["custo_estimado"] == 0

    _tarifa(db, categoria="utility", valor="0.07")
    db.commit()
    assert ledger.recalcular_custos(db, TENANT, inicio, fim) == 1
    db.commit()
    depois = ledger.resumo_do_periodo(db, TENANT, inicio, fim)
    assert (
        depois["totais"]["cobraveis_sem_tarifa"] == 0
        and depois["custo_estimado"] == 0.07
    )


# --- fechamento -------------------------------------------------------------------


def test_fechar_o_mes_fotografa_o_consumo_com_margem(db):
    _tarifa(db)
    db.commit()
    for numero in range(3):
        _envio_cobravel(db, f"wamid.f{numero}")

    resultado = consumo.fechar_mes(db, mes=MES, margem_percentual=20, admin=ADMIN)
    db.commit()

    fechamento = db.query(WhatsAppFechamento).one()
    assert resultado["fechados_agora"] == 1
    assert (fechamento.enviadas, fechamento.cobraveis) == (3, 3)
    assert float(fechamento.custo_estimado) == 1.08  # 3 x 0,36
    assert float(fechamento.valor_repasse) == 1.30  # 1,08 + 20% (arredondado)
    assert fechamento.fechado_por == "ops@corepet.test"


def test_mes_ja_fechado_nao_muda_e_nao_duplica(db):
    _tarifa(db)
    db.commit()
    _envio_cobravel(db, "wamid.g1")
    consumo.fechar_mes(db, mes=MES, margem_percentual=10, admin=ADMIN)
    db.commit()
    _envio_cobravel(db, "wamid.g2")

    de_novo = consumo.fechar_mes(db, mes=MES, margem_percentual=50, admin=ADMIN)
    db.commit()

    fechamento = db.query(WhatsAppFechamento).one()
    assert de_novo["fechados_agora"] == 0 and de_novo["ja_fechados"] == 1
    assert fechamento.enviadas == 1 and float(fechamento.margem_percentual) == 10


def test_mes_sem_movimento_nao_gera_fechamento(db):
    consumo.fechar_mes(db, mes=MES, margem_percentual=0, admin=ADMIN)

    assert db.query(WhatsAppFechamento).count() == 0


def test_margem_invalida_e_recusada(db):
    with pytest.raises(consumo.ConsumoError, match="margem"):
        consumo.fechar_mes(db, mes=MES, margem_percentual=-5, admin=ADMIN)


def test_fatura_da_meta_calcula_divergencia_e_deixa_historico(db):
    _tarifa(db)
    db.commit()
    _envio_cobravel(db, "wamid.h1")
    consumo.fechar_mes(db, mes=MES, margem_percentual=0, admin=ADMIN)
    db.commit()
    fechamento = db.query(WhatsAppFechamento).one()

    resposta = consumo.informar_fatura(
        db,
        fechamento_id=fechamento.id,
        fatura_meta=0.50,
        observacao="Fatura de outubro",
        admin=ADMIN,
    )
    db.commit()

    assert resposta["fatura_meta"] == 0.50 and resposta["divergencia"] == 0.14
    assert resposta["conferido"] is True
    historico = (
        db.query(OpsTenantChangeLog).filter_by(categoria="consumo_whatsapp").all()
    )
    assert {linha.campo for linha in historico} == {
        f"fechamento {MES}",
        f"fatura da Meta {MES}",
    }


def test_consumo_do_mes_mostra_ao_vivo_e_o_fechamento(db):
    _tarifa(db)
    db.commit()
    _envio_cobravel(db, "wamid.i1")

    antes = consumo.consumo_do_mes(db, MES)
    assert antes["lojas"][0]["fechamento"] is None
    assert antes["totais"]["custo_estimado"] == 0.36

    consumo.fechar_mes(db, mes=MES, margem_percentual=0, admin=ADMIN)
    db.commit()
    depois = consumo.consumo_do_mes(db, MES)
    assert depois["lojas"][0]["fechamento"]["valor_repasse"] == 0.36


# --- envio de modelo ------------------------------------------------------------


class MetaCloudClient:  # o nome decide o provedor registrado
    def __init__(self):
        self.chamadas = []

    async def send_template_message(self, to, template_name, language_code, parameters):
        self.chamadas.append((to, template_name, language_code, parameters))
        return {"messages": [{"id": "wamid.modelo"}]}


def _sessao(db, cliente_id=None):
    sessao = WhatsAppSession(
        tenant_id=TENANT,
        phone_number="5511999998888",
        status="bot",
        cliente_id=cliente_id,
    )
    db.add(sessao)
    db.commit()
    return sessao


def test_modelo_enviado_fica_no_chat_e_no_livro_razao_com_a_categoria(db, monkeypatch):
    cliente = MetaCloudClient()
    monkeypatch.setattr(sender_module, "_build_whatsapp_client", lambda *_a: cliente)
    monkeypatch.setattr(
        consent_service, "pode_enviar_whatsapp", lambda *_a, **_k: (True, "")
    )
    sessao = _sessao(db)

    mensagem = asyncio.run(
        sender_module.send_whatsapp_template(
            db,
            TENANT,
            sessao.id,
            "aniversario_pet",
            "marketing",
            parameters=["Rex"],
            texto_para_chat="Feliz aniversário, Rex!",
        )
    )

    linha = db.query(WhatsAppLedger).one()
    assert mensagem is not None and mensagem.conteudo == "Feliz aniversário, Rex!"
    assert cliente.chamadas[0][1:] == ("aniversario_pet", "pt_BR", ["Rex"])
    assert (linha.tipo_conteudo, linha.template_nome, linha.template_categoria) == (
        "modelo",
        "aniversario_pet",
        "marketing",
    )
    assert (linha.origem, linha.provedor, linha.janela_24h) == (
        "automacao",
        "meta_cloud",
        False,
    )


def test_modelo_para_quem_recusou_nao_sai_e_o_bloqueio_fica_registrado(db, monkeypatch):
    cliente = MetaCloudClient()
    monkeypatch.setattr(sender_module, "_build_whatsapp_client", lambda *_a: cliente)
    monkeypatch.setattr(
        consent_service,
        "pode_enviar_whatsapp",
        lambda *_a, **_k: (False, "recusou_mensagens"),
    )
    sessao = _sessao(db)

    resultado = asyncio.run(
        sender_module.send_whatsapp_template(db, TENANT, sessao.id, "x", "utility")
    )

    linha = db.query(WhatsAppLedger).one()
    assert resultado is None and cliente.chamadas == []
    assert linha.estado == "falhou" and "recusou_mensagens" in linha.erro_mensagem
    assert db.query(WhatsAppMessage).count() == 0


def test_categoria_de_modelo_invalida_e_recusada(db):
    with pytest.raises(ValueError, match="Categoria"):
        asyncio.run(
            sender_module.send_whatsapp_template(db, TENANT, "s", "x", "promocao")
        )
