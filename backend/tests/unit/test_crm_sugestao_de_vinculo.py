"""CRM: ao abrir um card sem cadastro, sugerir a pessoa que surgiu com o mesmo telefone."""

from uuid import uuid4

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from app.crm import acoes_service as svc
from app.crm.funil_service import RegraDoCrm
from app.crm.models import CrmLead, CrmVinculoIgnorado
from app.db import Base
from app.models import Cliente
from app.tenancy.context import clear_current_tenant, set_current_tenant

TENANT = uuid4()


@pytest.fixture()
def db():
    engine = create_engine("sqlite:///:memory:")

    @event.listens_for(engine, "connect")
    def _now(conexao, _registro):
        conexao.create_function("now", 0, lambda: "2026-10-30 09:00:00")

    nomes = (
        "crm_funis",
        "crm_colunas",
        "crm_leads",
        "crm_oportunidades",
        "crm_movimentacoes",
        "crm_interacoes",
        "crm_vinculos_ignorados",
        "clientes",
    )
    Base.metadata.create_all(
        engine, tables=[Base.metadata.tables[nome] for nome in nomes]
    )
    sessao = sessionmaker(bind=engine)()
    set_current_tenant(TENANT)
    yield sessao
    clear_current_tenant()
    sessao.close()


def _cliente(db, nome="Maria Souza", celular="(11) 99999-8888"):
    cliente = Cliente(
        tenant_id=TENANT, user_id=1, nome=nome, celular=celular, is_cliente=True
    )
    db.add(cliente)
    db.flush()
    return cliente


def _card(db, telefone="5511999998888", cliente_id=None):
    lead = CrmLead(
        tenant_id=TENANT,
        funil_id=1,
        coluna_id=1,
        cliente_id=cliente_id,
        telefone=telefone,
        nome_exibicao="Contato",
    )
    db.add(lead)
    db.flush()
    return lead


def test_sugere_a_pessoa_que_surgiu_com_o_mesmo_telefone(db):
    lead = _card(db)
    maria = _cliente(db)

    sugestao = svc.sugerir_vinculo(db, lead)

    assert sugestao == {
        "cliente_id": maria.id,
        "nome": "Maria Souza",
        "telefone": "(11) 99999-8888",
    }


def test_nao_sugere_nada_sem_pessoa_com_o_telefone(db):
    lead = _card(db)
    _cliente(db, nome="Outra", celular="(21) 98888-7777")

    assert svc.sugerir_vinculo(db, lead) is None


def test_card_ja_ligado_a_um_cadastro_nao_recebe_sugestao(db):
    maria = _cliente(db)
    lead = _card(db, cliente_id=maria.id)

    assert svc.sugerir_vinculo(db, lead) is None


def test_sim_vincula_e_a_sugestao_some(db):
    lead = _card(db)
    maria = _cliente(db)

    svc.vincular_a_cadastro(db, lead, maria.id, user_id=1)

    assert lead.cliente_id == maria.id
    assert svc.sugerir_vinculo(db, lead) is None


def test_nao_perguntar_novamente_vale_so_para_aquela_pessoa_e_aquele_card(db):
    lead = _card(db)
    outro_card = _card(db, telefone="5511977776666")
    maria = _cliente(db)
    _cliente(db, nome="Outra Maria", celular="(11) 97777-6666")

    svc.ignorar_sugestao_de_vinculo(db, lead, maria.id, user_id=1)

    assert svc.sugerir_vinculo(db, lead) is None  # Maria nao e mais sugerida ao card
    assert svc.sugerir_vinculo(db, outro_card)["nome"] == "Outra Maria"
    # Registrar de novo nao duplica.
    svc.ignorar_sugestao_de_vinculo(db, lead, maria.id, user_id=1)
    assert db.query(CrmVinculoIgnorado).count() == 1


def test_com_duas_pessoas_no_mesmo_telefone_pula_a_recusada_e_sugere_a_outra(db):
    lead = _card(db)
    primeira = _cliente(db, nome="Ana")
    segunda = _cliente(db, nome="Bia")

    svc.ignorar_sugestao_de_vinculo(db, lead, primeira.id)

    assert svc.sugerir_vinculo(db, lead)["cliente_id"] == segunda.id


def test_nao_sugere_pessoa_que_ja_tem_outro_card(db):
    maria = _cliente(db)
    _card(db, telefone=None, cliente_id=maria.id)
    lead = _card(db)

    assert svc.sugerir_vinculo(db, lead) is None


def test_ignorar_exige_pessoa_da_mesma_loja_e_card_sem_cadastro(db):
    lead = _card(db)
    with pytest.raises(RegraDoCrm):
        svc.ignorar_sugestao_de_vinculo(db, lead, 9999)

    maria = _cliente(db)
    ligado = _card(db, telefone="5511911112222", cliente_id=maria.id)
    with pytest.raises(RegraDoCrm):
        svc.ignorar_sugestao_de_vinculo(db, ligado, maria.id)
