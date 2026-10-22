"""Etapa 1.6 do CRM: identificacao do tutor e card para numero desconhecido."""

from uuid import uuid4

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from app.crm import leads_service as svc
from app.crm.models import CrmColuna, CrmInteracao, CrmLead, CrmMovimentacao
from app.db import Base
from app.models import Cliente
from app.tenancy.context import clear_current_tenant, set_current_tenant
from app.whatsapp.customer_lookup import (
    SITUACAO_AMBIGUO,
    SITUACAO_INVALIDO,
    SITUACAO_NENHUM,
    SITUACAO_UNICO,
    ResolucaoTutor,
)

TENANT = uuid4()


@pytest.fixture()
def db():
    engine = create_engine("sqlite:///:memory:")

    @event.listens_for(engine, "connect")
    def _now(conexao, _registro):  # o banco real (Postgres) tem now()
        conexao.create_function("now", 0, lambda: "2026-10-22 09:00:00")

    tabelas = [
        Base.metadata.tables[nome]
        for nome in (
            "crm_funis",
            "crm_colunas",
            "crm_leads",
            "crm_oportunidades",
            "crm_movimentacoes",
            "crm_interacoes",
            "crm_acoes",
            "crm_proximos_passos",
            "clientes",
        )
    ]
    Base.metadata.create_all(engine, tables=tabelas)
    sessao = sessionmaker(bind=engine)()
    set_current_tenant(TENANT)  # como a rota faz: toda consulta e de uma loja
    yield sessao
    clear_current_tenant()
    sessao.close()


def _resolver(monkeypatch, resolucao):
    monkeypatch.setattr(svc, "resolver_tutor_por_telefone", lambda *_a, **_k: resolucao)


def test_funil_padrao_nasce_com_colunas_validas_e_so_uma_vez(db):
    funil, entrada = svc.garantir_funil_padrao(db, TENANT)
    outro, _ = svc.garantir_funil_padrao(db, TENANT)

    colunas = db.query(CrmColuna).order_by(CrmColuna.ordem).all()
    tipos = [c.tipo for c in colunas]
    assert outro.id == funil.id
    assert entrada.nome == "Novo" and entrada.tipo == "entrada"
    assert len(colunas) == 6
    assert "entrada" in tipos and "concluido" in tipos


def test_numero_desconhecido_vira_card_sem_cadastro(db, monkeypatch):
    _resolver(monkeypatch, ResolucaoTutor(SITUACAO_NENHUM))

    lead = svc.identificar_ou_criar_lead(db, TENANT, "+55 (11) 99999-8888")

    assert lead.cliente_id is None
    assert lead.telefone == "5511999998888"
    assert lead.nome_exibicao == svc.SEM_NOME
    assert lead.origem == "whatsapp"
    assert db.query(CrmMovimentacao).count() == 1
    assert db.query(CrmInteracao).filter_by(tipo="lead_criado").count() == 1


def test_mesmo_numero_nao_duplica_o_card(db, monkeypatch):
    _resolver(monkeypatch, ResolucaoTutor(SITUACAO_NENHUM))

    primeiro = svc.identificar_ou_criar_lead(db, TENANT, "5511999998888", nome="Ana")
    segundo = svc.identificar_ou_criar_lead(db, TENANT, "5511999998888")

    assert primeiro.id == segundo.id
    assert primeiro.nome_exibicao == "Ana"
    assert db.query(CrmLead).count() == 1


def test_numero_ambiguo_nunca_vincula_a_um_cadastro(db, monkeypatch):
    _resolver(monkeypatch, ResolucaoTutor(SITUACAO_AMBIGUO, None, (1, 2)))

    lead = svc.identificar_ou_criar_lead(db, TENANT, "5511999998888")

    assert lead.cliente_id is None


def test_identificador_interno_do_whatsapp_nao_vira_card(db, monkeypatch):
    _resolver(monkeypatch, ResolucaoTutor(SITUACAO_INVALIDO))

    assert svc.identificar_ou_criar_lead(db, TENANT, "123@lid") is None
    assert db.query(CrmLead).count() == 0


def test_tutor_cadastrado_usa_o_cadastro_e_reaproveita_o_card(db, monkeypatch):
    db.add(
        Cliente(tenant_id=TENANT, user_id=1, nome="Maria Souza", celular="11999998888")
    )
    db.flush()
    cliente_id = db.query(Cliente.id).scalar()
    _resolver(monkeypatch, ResolucaoTutor(SITUACAO_UNICO, cliente_id, (cliente_id,)))

    lead = svc.identificar_ou_criar_lead(db, TENANT, "5511999998888")
    de_novo = svc.identificar_ou_criar_lead(db, TENANT, "5511999998888")

    assert lead.cliente_id == cliente_id and lead.nome_exibicao == "Maria Souza"
    assert de_novo.id == lead.id


def test_card_sem_cadastro_e_vinculado_quando_o_numero_ganha_dono(db, monkeypatch):
    _resolver(monkeypatch, ResolucaoTutor(SITUACAO_NENHUM))
    antigo = svc.identificar_ou_criar_lead(db, TENANT, "5511999998888")
    db.add(
        Cliente(tenant_id=TENANT, user_id=1, nome="Maria Souza", celular="11999998888")
    )
    db.flush()
    cliente_id = db.query(Cliente.id).scalar()
    _resolver(monkeypatch, ResolucaoTutor(SITUACAO_UNICO, cliente_id, (cliente_id,)))

    vinculado = svc.identificar_ou_criar_lead(db, TENANT, "5511999998888")

    assert vinculado.id == antigo.id and vinculado.cliente_id == cliente_id
    assert db.query(CrmLead).count() == 1


def test_sessao_nova_do_whatsapp_registra_o_card_so_com_crm_ativo():
    from pathlib import Path

    fonte = (Path(__file__).resolve().parents[2] / "app/whatsapp/webhook.py").read_text(
        encoding="utf-8"
    )
    assert "_registrar_lead_no_crm(db, tenant_id, phone)" in fonte
    assert 'tenant_has_active_module(db, str(tenant_id), "crm")' in fonte
    assert "db.begin_nested()" in fonte
