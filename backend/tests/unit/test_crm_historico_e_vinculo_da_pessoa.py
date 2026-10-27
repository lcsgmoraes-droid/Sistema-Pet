"""CRM: conversas viram historico do card, gasto por pessoa e vinculo automatico."""

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from app.crm import mensagens_service as svc
from app.crm.models import CrmInteracao, CrmLead
from app.db import Base
from app.models import Cliente
from app.tenancy.context import clear_current_tenant, set_current_tenant
from app.whatsapp import consumo_models  # noqa: F401
from app.whatsapp import ledger_service as ledger
from app.whatsapp import models_handoff  # noqa: F401  (mapeia WhatsAppHandoff)
from app.whatsapp.ledger_models import WhatsAppLedger
from app.whatsapp.models import WhatsAppSession

TENANT = uuid4()
OUTRA_LOJA = uuid4()


@pytest.fixture()
def db():
    engine = create_engine("sqlite:///:memory:")

    @event.listens_for(engine, "connect")
    def _now(conexao, _registro):
        conexao.create_function("now", 0, lambda: "2026-10-27 09:00:00")

    nomes = (
        "crm_funis",
        "crm_colunas",
        "crm_leads",
        "crm_oportunidades",
        "crm_movimentacoes",
        "crm_interacoes",
        "clientes",
        "whatsapp_ledger",
        "whatsapp_tarifas",
        "whatsapp_ia_sessions",
        "whatsapp_ia_messages",
    )
    Base.metadata.create_all(
        engine, tables=[Base.metadata.tables[nome] for nome in nomes]
    )
    sessao = sessionmaker(bind=engine)()
    set_current_tenant(TENANT)
    yield sessao
    clear_current_tenant()
    sessao.close()


def _cliente(db, nome="Maria Souza", celular="11999998888"):
    db.add(
        Cliente(
            tenant_id=TENANT, user_id=1, nome=nome, celular=celular, is_cliente=True
        )
    )
    db.flush()
    return db.query(Cliente).filter_by(nome=nome).one()


def _conversa(db, telefone="5511999998888", cliente_id=None, ha=timedelta(days=2)):
    sessao = WhatsAppSession(
        tenant_id=TENANT,
        phone_number=telefone,
        status="bot",
        cliente_id=cliente_id,
        last_message_at=(datetime.now(UTC) - ha).replace(tzinfo=None),
    )
    db.add(sessao)
    db.commit()
    return sessao


def _card(db, telefone="5511999998888", cliente_id=None, nome="Contato"):
    lead = CrmLead(
        tenant_id=TENANT,
        funil_id=1,
        coluna_id=1,
        cliente_id=cliente_id,
        telefone=telefone,
        nome_exibicao=nome,
    )
    db.add(lead)
    db.commit()
    return lead


# --- linha do tempo e ultimo contato -----------------------------------------------


def test_mensagem_entra_na_linha_do_tempo_e_atualiza_o_ultimo_contato(db):
    lead = _card(db)
    sessao = _conversa(db)

    assert svc.anotar_mensagem_no_crm(
        db,
        tenant_id=TENANT,
        session=sessao,
        direcao="recebida",
        texto="Oi,   quero  ração",
        origem="tutor",
    )
    assert svc.anotar_mensagem_no_crm(
        db,
        tenant_id=TENANT,
        session=sessao,
        direcao="enviada",
        texto="Claro! Qual marca?",
        origem="ia",
    )

    tipos = [i.tipo for i in db.query(CrmInteracao).order_by(CrmInteracao.id)]
    assert tipos == ["mensagem_recebida", "mensagem_enviada"]
    primeira = db.query(CrmInteracao).first()
    assert primeira.resumo == "Oi, quero ração" and primeira.origem == "tutor"
    db.refresh(lead)
    assert lead.ultimo_contato_em is not None


def test_resumo_da_mensagem_e_cortado(db):
    _card(db)
    sessao = _conversa(db)

    svc.anotar_mensagem_no_crm(
        db,
        tenant_id=TENANT,
        session=sessao,
        direcao="recebida",
        texto="a" * 500,
        origem="tutor",
    )

    resumo = db.query(CrmInteracao).one().resumo
    assert len(resumo) == svc.TAMANHO_DO_RESUMO + 1 and resumo.endswith("…")


def test_conversa_sem_card_nao_cria_nada_nem_quebra(db):
    sessao = _conversa(db, telefone="5511900000000")

    assert (
        svc.anotar_mensagem_no_crm(
            db,
            tenant_id=TENANT,
            session=sessao,
            direcao="recebida",
            texto="oi",
            origem="tutor",
        )
        is False
    )
    assert db.query(CrmInteracao).count() == 0


def test_card_e_achado_pelo_cadastro_mesmo_com_outro_telefone(db):
    maria = _cliente(db)
    lead = _card(db, telefone="5511911112222", cliente_id=maria.id, nome="Maria")
    sessao = _conversa(db, telefone="5511999998888", cliente_id=maria.id)

    assert svc.lead_da_sessao(db, TENANT, sessao).id == lead.id


def test_card_de_outra_loja_nao_e_usado(db):
    set_current_tenant(
        OUTRA_LOJA
    )  # o guarda do ORM exige gravar no contexto da propria loja
    db.add(
        CrmLead(
            tenant_id=OUTRA_LOJA,
            funil_id=1,
            coluna_id=1,
            telefone="5511999998888",
            nome_exibicao="X",
        )
    )
    db.commit()
    set_current_tenant(TENANT)
    sessao = _conversa(db)

    assert svc.lead_da_sessao(db, TENANT, sessao) is None


# --- gasto por pessoa ------------------------------------------------------------


def test_livro_razao_guarda_o_card_e_a_ficha_soma_o_gasto_da_pessoa(db):
    lead = _card(db)
    sessao = _conversa(db)
    for numero in range(2):
        ledger.anotar_envio(
            db,
            tenant_id=TENANT,
            provedor="meta_cloud",
            session=sessao,
            message_row=SimpleNamespace(id=f"m{numero}"),
            wa_message_id=f"wamid.{numero}",
            origem="automacao",
        )
        linha = (
            db.query(WhatsAppLedger).filter_by(wa_message_id=f"wamid.{numero}").one()
        )
        linha.cobravel = True
        linha.custo_estimado = 0.36
    ledger.anotar_recebimento(
        db,
        tenant_id=TENANT,
        provedor="meta_cloud",
        session=sessao,
        message_row=SimpleNamespace(id="in"),
        wa_message_id="wamid.in",
    )
    db.commit()

    consumo = svc.consumo_do_lead(db, TENANT, lead.id)

    assert {l.lead_id for l in db.query(WhatsAppLedger)} == {lead.id}
    assert consumo == {
        "enviadas": 2,
        "recebidas": 1,
        "cobraveis": 2,
        "custo_estimado": 0.72,
    }


def test_mensagem_de_conversa_sem_card_fica_sem_card_no_livro_razao(db):
    sessao = _conversa(db, telefone="5511900000001")

    ledger.anotar_envio(
        db,
        tenant_id=TENANT,
        provedor="meta_cloud",
        session=sessao,
        message_row=SimpleNamespace(id="m"),
        wa_message_id="wamid.x",
        origem="ia",
    )

    assert db.query(WhatsAppLedger).one().lead_id is None


# --- vinculo automatico ao cadastrar a pessoa ----------------------------------------


def test_cadastrar_a_pessoa_liga_o_card_sem_cadastro_do_mesmo_telefone(db):
    lead = _card(db, telefone="5511999998888", nome="Sem nome no WhatsApp")
    maria = _cliente(db, celular="11999998888")

    assert svc.vincular_leads_ao_cliente(db, TENANT, maria) == 1
    db.commit()

    db.refresh(lead)
    assert lead.cliente_id == maria.id and lead.nome_exibicao == "Maria Souza"
    assert db.query(CrmInteracao).filter_by(tipo="vinculo").count() == 1


def test_telefone_com_dois_donos_nao_e_ligado(db):
    lead = _card(db, telefone="5511999998888")
    _cliente(db, "Maria", "11999998888")
    ana = _cliente(db, "Ana", "11999998888")  # mesmo numero em dois cadastros

    assert svc.vincular_leads_ao_cliente(db, TENANT, ana) == 0
    db.refresh(lead)
    assert lead.cliente_id is None


def test_pessoa_que_ja_tem_card_nao_ganha_um_segundo(db):
    maria = _cliente(db)
    _card(db, telefone="5511911112222", cliente_id=maria.id, nome="Maria")
    solto = _card(db, telefone="5511999998888", nome="Contato")

    assert svc.vincular_leads_ao_cliente(db, TENANT, maria) == 0
    db.refresh(solto)
    assert solto.cliente_id is None


def test_vinculo_com_seguranca_nunca_levanta_erro(db):
    class _Quebrado:
        def begin_nested(self):
            raise RuntimeError("banco fora")

        def rollback(self):
            pass

    cliente = SimpleNamespace(id=1, celular="11999998888", telefone=None, nome="X")

    assert (
        svc.vincular_leads_ao_cliente_com_seguranca(_Quebrado(), TENANT, cliente) == 0
    )


# --- conversas que ja existiam -----------------------------------------------------


def test_ativar_o_crm_cria_card_das_conversas_antigas_sem_duplicar(db):
    _conversa(db, telefone="5511999998888", ha=timedelta(days=5))
    _conversa(db, telefone="5511988887777", ha=timedelta(days=1))
    _conversa(
        db, telefone="5511999998888", ha=timedelta(days=10)
    )  # mesmo numero, outra sessao

    primeira = svc.criar_cards_das_conversas(db, TENANT)
    db.commit()
    segunda = svc.criar_cards_das_conversas(db, TENANT)
    db.commit()

    assert primeira["criados"] == 2 and primeira["ha_mais"] is False
    assert segunda["criados"] == 0 and segunda["ja_existiam"] == 2
    assert db.query(CrmLead).count() == 2
    assert all(lead.ultimo_contato_em is not None for lead in db.query(CrmLead))


def test_importacao_respeita_o_limite_por_rodada(db):
    for numero in range(3):
        _conversa(db, telefone=f"551190000000{numero}")

    rodada = svc.criar_cards_das_conversas(db, TENANT, limite=2)
    db.commit()

    assert rodada["criados"] == 2 and rodada["ha_mais"] is True
    final = svc.criar_cards_das_conversas(db, TENANT, limite=2)
    assert final["criados"] == 1 and final["ha_mais"] is False


def test_ligacoes_estao_no_cadastro_no_envio_no_webhook_e_na_ativacao():
    from pathlib import Path

    raiz = Path(__file__).resolve().parents[2] / "app"
    assert "vincular_leads_ao_cliente_com_seguranca(" in (
        raiz / "clientes/crud_routes.py"
    ).read_text(encoding="utf-8")
    assert "anotar_mensagem_no_crm(" in (raiz / "whatsapp/sender.py").read_text(
        encoding="utf-8"
    )
    assert "anotar_mensagem_no_crm(" in (raiz / "whatsapp/webhook.py").read_text(
        encoding="utf-8"
    )
    assert "_criar_cards_das_conversas(" in (
        raiz / "services/ops_lojas_modulos_service.py"
    ).read_text(encoding="utf-8")
