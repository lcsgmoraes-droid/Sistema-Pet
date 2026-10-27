"""Etapa 2 do CRM: quadro, criacao de card, acoes e proximo passo."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from app.crm import acoes_service as acoes
from app.crm import funil_service as funil
from app.crm.funil_service import RegraDoCrm
from app.crm.leads_service import identificar_ou_criar_lead
from app.crm.models import CrmColuna, CrmLead
from app.crm.quadro_service import montar_quadro
from app.db import Base
from app.models import Cliente, Pet
from app.whatsapp import consumo_models  # noqa: F401
from app.whatsapp import ledger_models  # noqa: F401
from app.tenancy.context import clear_current_tenant, set_current_tenant
from app.whatsapp.customer_lookup import SITUACAO_NENHUM, ResolucaoTutor

TENANT = uuid4()
OUTRA_LOJA = uuid4()


@pytest.fixture()
def db(monkeypatch):
    engine = create_engine("sqlite:///:memory:")

    @event.listens_for(engine, "connect")
    def _now(conexao, _registro):
        conexao.create_function("now", 0, lambda: "2026-10-22 09:00:00")

    nomes = (
        "crm_funis",
        "crm_colunas",
        "crm_leads",
        "crm_oportunidades",
        "crm_movimentacoes",
        "crm_interacoes",
        "crm_acoes",
        "crm_proximos_passos",
        "clientes",
        "pets",
        "users",
        "whatsapp_ledger",
    )
    Base.metadata.create_all(
        engine, tables=[Base.metadata.tables[nome] for nome in nomes]
    )
    sessao = sessionmaker(bind=engine)()
    set_current_tenant(TENANT)
    from app.crm import leads_service

    monkeypatch.setattr(
        leads_service,
        "resolver_tutor_por_telefone",
        lambda *_a, **_k: ResolucaoTutor(SITUACAO_NENHUM),
    )
    yield sessao
    clear_current_tenant()
    sessao.close()


def _coluna(db, nome):
    return db.query(CrmColuna).filter_by(nome=nome).one()


def _manual(db, nome="Ana", telefone="11911112222", **extra):
    return acoes.criar_lead_manual(db, TENANT, nome=nome, telefone=telefone, **extra)


def test_quadro_novo_cria_o_funil_padrao_e_vem_vazio(db):
    quadro = montar_quadro(db, TENANT)

    nomes = [c["nome"] for c in quadro["colunas"]]
    assert nomes[0] == "Novo" and len(nomes) == 6
    assert all(c["total"] == 0 and c["cards"] == [] for c in quadro["colunas"])


def test_card_nao_mostra_telefone_e_traz_oportunidades_e_dias(db):
    lead = identificar_ou_criar_lead(db, TENANT, "5511999998888", nome="Ana")
    funil.registrar_sinal(db, lead, tipo="vacina", detalhe="V10")
    funil.registrar_sinal(db, lead, tipo="sem_comprar", generica=True)
    lead.coluna_desde = datetime.now(UTC) - timedelta(days=6)
    db.flush()

    card = montar_quadro(db, TENANT)["colunas"][0]["cards"][0]

    assert card["nome"] == "Ana" and card["sem_cadastro"] is True
    assert "telefone" not in card and "5511999998888" not in str(card)
    assert [o["tipo"] for o in card["oportunidades"]] == ["vacina", "sem_comprar"]
    assert card["dias_na_coluna"] == 6


def test_totais_valor_e_filtros_do_quadro(db):
    _manual(db, "Ana", "11911112222", valor_estimado=100)
    bruno = _manual(db, "Bruno", "11933334444", valor_estimado=50)
    funil.mover_lead(db, bruno, _coluna(db, "Em contato").id)

    quadro = montar_quadro(db, TENANT)
    por_nome = {c["nome"]: c for c in quadro["colunas"]}
    assert por_nome["Novo"]["total"] == 1 and por_nome["Novo"]["valor_total"] == 100
    assert por_nome["Em contato"]["valor_total"] == 50

    achados = montar_quadro(db, TENANT, busca="bru")
    assert sum(c["total"] for c in achados["colunas"]) == 1


def test_pets_do_tutor_aparecem_no_card(db):
    db.add(Cliente(tenant_id=TENANT, user_id=1, nome="Maria", celular="11999998888"))
    db.flush()
    cliente_id = db.query(Cliente.id).scalar()
    db.add(
        Pet(
            tenant_id=TENANT,
            user_id=1,
            codigo="P1",
            especie="Cachorro",
            cliente_id=cliente_id,
            nome="Rex",
        )
    )
    db.flush()
    acoes.criar_lead_manual(db, TENANT, cliente_id=cliente_id)

    card = montar_quadro(db, TENANT)["colunas"][0]["cards"][0]

    assert card["pets"] == ["Rex"] and card["sem_cadastro"] is False


def test_coluna_final_so_mostra_os_ultimos_dias(db):
    lead = _manual(db)
    final = _coluna(db, "Resolvido")
    funil.mover_lead(db, lead, final.id)
    final.janela_dias = 7
    lead.coluna_desde = datetime.now(UTC) - timedelta(days=10)
    db.flush()

    colunas = {c["nome"]: c for c in montar_quadro(db, TENANT)["colunas"]}

    assert colunas["Resolvido"]["cards"] == []


def test_card_manual_valida_duplicidade_e_dados(db):
    _manual(db, "Ana", "(11) 91111-2222")

    with pytest.raises(RegraDoCrm, match="Já existe"):
        _manual(db, "Ana 2", "11911112222")
    with pytest.raises(RegraDoCrm, match="nome"):
        acoes.criar_lead_manual(db, TENANT, telefone="11900000000")
    with pytest.raises(RegraDoCrm, match="telefone"):
        acoes.criar_lead_manual(db, TENANT, nome="Sem fone")
    with pytest.raises(RegraDoCrm, match="não encontrada"):
        acoes.criar_lead_manual(db, TENANT, cliente_id=999)


def test_acao_atualiza_ultimo_contato_e_conclui_o_passo(db):
    lead = _manual(db)
    passo = acoes.agendar_passo(
        db, lead, tipo="ligar", agendado_para=datetime.now(UTC) + timedelta(days=1)
    )

    acoes.registrar_acao(db, lead, tipo="ligacao", observacao="Atendeu", user_id=4)

    assert lead.ultimo_contato_em is not None
    assert passo.concluido_em is not None


def test_observacao_nao_conta_como_contato_nem_conclui_passo(db):
    lead = _manual(db)
    passo = acoes.agendar_passo(
        db, lead, tipo="ligar", agendado_para=datetime.now(UTC) + timedelta(days=1)
    )

    acoes.registrar_acao(db, lead, tipo="observacao", observacao="Exigente", user_id=4)

    assert lead.ultimo_contato_em is None and passo.concluido_em is None


def test_novo_passo_substitui_o_pendente_e_aparece_no_card(db):
    lead = _manual(db)
    quando = datetime.now(UTC) + timedelta(days=2)
    acoes.agendar_passo(db, lead, tipo="ligar", agendado_para=datetime.now(UTC))
    acoes.agendar_passo(
        db, lead, tipo="visita", agendado_para=quando, descricao="Levar amostra"
    )

    card = montar_quadro(db, TENANT)["colunas"][0]["cards"][0]

    assert card["proximo_passo"]["tipo"] == "visita"
    with pytest.raises(RegraDoCrm):
        acoes.agendar_passo(db, lead, tipo="inexistente", agendado_para=quando)
    with pytest.raises(RegraDoCrm):
        acoes.registrar_acao(db, lead, tipo="inexistente", observacao=None, user_id=1)


def test_detalhe_traz_caminhada_oportunidades_e_linha_do_tempo(db):
    lead = _manual(db)
    funil.registrar_sinal(db, lead, tipo="vacina")
    funil.mover_lead(db, lead, _coluna(db, "Em contato").id, nota="Liguei")

    ficha = acoes.detalhe_do_lead(db, lead)

    assert [(c["de"], c["para"]) for c in ficha["caminhada"]] == [
        (None, "Novo"),
        ("Novo", "Em contato"),
    ]
    assert ficha["oportunidades"][0]["tipo"] == "vacina"
    assert {i["tipo"] for i in ficha["linha_do_tempo"]} >= {"lead_criado", "etapa"}


def test_card_de_outra_loja_nao_e_encontrado(db):
    lead = _manual(db)

    with pytest.raises(RegraDoCrm, match="não encontrado"):
        acoes.obter_lead(db, OUTRA_LOJA, lead.id)
    assert db.query(CrmLead).filter(CrmLead.tenant_id == OUTRA_LOJA).count() == 0


def _cliente(db, nome, celular, **extra):
    db.add(
        Cliente(
            tenant_id=TENANT,
            user_id=1,
            nome=nome,
            celular=celular,
            is_cliente=True,
            **extra,
        )
    )
    db.flush()
    return db.query(Cliente).filter_by(nome=nome).one()


def test_busca_de_tutores_por_nome_ou_telefone_e_marca_quem_ja_tem_card(db):
    maria = _cliente(db, "Maria Souza", "11999998888")
    _cliente(db, "Mario Lima", "11977776666")
    acoes.criar_lead_manual(db, TENANT, cliente_id=maria.id)

    por_nome = acoes.buscar_tutores(db, TENANT, "mari")
    por_fone = acoes.buscar_tutores(db, TENANT, "9999-8888".replace("-", ""))

    assert {t["nome"]: t["tem_card"] for t in por_nome} == {
        "Maria Souza": True,
        "Mario Lima": False,
    }
    assert [t["nome"] for t in por_fone] == ["Maria Souza"]
    assert acoes.buscar_tutores(db, TENANT, "m") == []


def test_vincular_card_sem_cadastro_a_uma_pessoa(db):
    lead = _manual(db)
    maria = _cliente(db, "Maria Souza", "11999998888")

    acoes.vincular_a_cadastro(db, lead, maria.id, user_id=2)

    assert lead.cliente_id == maria.id and lead.nome_exibicao == "Maria Souza"
    with pytest.raises(RegraDoCrm, match="já está ligado"):
        acoes.vincular_a_cadastro(db, lead, maria.id)


def test_vincular_nao_duplica_card_de_quem_ja_tem_um(db):
    maria = _cliente(db, "Maria Souza", "11999998888")
    acoes.criar_lead_manual(db, TENANT, cliente_id=maria.id)
    outro = _manual(db, "Contato", "11922223333")

    with pytest.raises(RegraDoCrm, match="outro card"):
        acoes.vincular_a_cadastro(db, outro, maria.id)
    with pytest.raises(RegraDoCrm, match="não encontrada"):
        acoes.vincular_a_cadastro(db, outro, 12345)
