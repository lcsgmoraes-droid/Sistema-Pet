"""Etapa 2 do CRM (regras): colunas, movimentacao, ciclos e oportunidades."""

from uuid import uuid4

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from app.crm import funil_service as svc
from app.crm.leads_service import garantir_funil_padrao, identificar_ou_criar_lead
from app.crm.models import CrmColuna, CrmMovimentacao, CrmOportunidade
from app.db import Base
from app.tenancy.context import clear_current_tenant, set_current_tenant
from app.whatsapp.customer_lookup import SITUACAO_NENHUM, ResolucaoTutor

TENANT = uuid4()


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
        "clientes",
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


def _colunas(db):
    return {c.nome: c for c in db.query(CrmColuna).order_by(CrmColuna.ordem)}


@pytest.fixture()
def lead(db):
    return identificar_ou_criar_lead(db, TENANT, "5511999998888")


# --- colunas -----------------------------------------------------------------


def _spec(*pares):
    return [{"nome": nome, "tipo": tipo} for nome, tipo in pares]


def test_regras_de_colunas():
    ok = _spec(("Novo", "entrada"), ("Feito", "concluido"))
    svc.validar_colunas(ok)

    invalidos = [
        [],
        _spec(("Novo", "entrada")),  # sem concluido
        _spec(("Feito", "concluido")),  # sem entrada
        _spec(*[(f"C{i}", "andamento") for i in range(9)]),  # mais de 8
        _spec(("A", "entrada"), ("a", "concluido")),  # nome repetido
        _spec(("", "entrada"), ("B", "concluido")),
        _spec(("A", "entrada"), ("B", "estranho")),
    ]
    for colunas in invalidos:
        with pytest.raises(svc.RegraDoCrm):
            svc.validar_colunas(colunas)


def test_salvar_colunas_reordena_renomeia_e_protege_coluna_com_cards(db, lead):
    funil, _ = garantir_funil_padrao(db, TENANT)
    atuais = _colunas(db)
    nova = [
        {"id": atuais["Novo"].id, "nome": "Entrada", "tipo": "entrada"},
        {"id": atuais["Resolvido"].id, "nome": "Resolvido", "tipo": "concluido"},
        {"nome": "Perdido", "tipo": "encerrado", "janela_dias": 30},
    ]
    # "Novo" (entrada) tem o card; a coluna "Em contato" sem cards pode sair.
    svc.salvar_colunas(db, TENANT, funil.id, nova)
    depois = _colunas(db)
    assert list(depois) == ["Entrada", "Resolvido", "Perdido"]
    assert depois["Perdido"].janela_dias == 30

    sem_a_do_card = [
        {"id": depois["Resolvido"].id, "nome": "Resolvido", "tipo": "concluido"},
        {"nome": "Início", "tipo": "entrada"},
    ]
    with pytest.raises(svc.RegraDoCrm, match="ainda tem cards"):
        svc.salvar_colunas(db, TENANT, funil.id, sem_a_do_card)


# --- oportunidades e ciclo ---------------------------------------------------


def test_sinal_repetido_nao_duplica_e_generica_fica_por_ultimo(db, lead):
    svc.registrar_sinal(db, lead, tipo="sem_comprar", generica=True)
    vacina = svc.registrar_sinal(db, lead, tipo="vacina", detalhe="V10 do Rex")
    de_novo = svc.registrar_sinal(db, lead, tipo="vacina", detalhe="V10 do Rex")

    assert de_novo.id == vacina.id
    ordem = [o.tipo for o in svc.oportunidades_abertas(db, lead)]
    assert ordem == ["vacina", "sem_comprar"]


def test_concluir_exige_resultado_de_cada_oportunidade(db, lead):
    vacina = svc.registrar_sinal(db, lead, tipo="vacina")
    resolvido = _colunas(db)["Resolvido"]

    with pytest.raises(svc.RegraDoCrm, match="resultado de cada"):
        svc.mover_lead(db, lead, resolvido.id)

    with pytest.raises(svc.RegraDoCrm, match="motivo"):
        svc.mover_lead(
            db, lead, resolvido.id, resultados={vacina.id: {"estado": "descartada"}}
        )

    svc.mover_lead(
        db,
        lead,
        resolvido.id,
        user_id=3,
        resultados={vacina.id: {"estado": "resolvida"}},
    )
    assert lead.coluna_id == resolvido.id
    assert vacina.estado == "resolvida" and vacina.resolvida_em is not None


def test_encerrar_sem_resultado_exige_motivo_da_perda(db, lead):
    encerrado = _colunas(db)["Sem interesse"]

    with pytest.raises(svc.RegraDoCrm, match="motivo"):
        svc.mover_lead(db, lead, encerrado.id)

    svc.mover_lead(db, lead, encerrado.id, motivo_perda="Mudou de cidade")
    assert lead.motivo_perda == "Mudou de cidade"


def test_novo_sinal_em_card_concluido_abre_novo_ciclo_na_entrada(db, lead):
    vacina = svc.registrar_sinal(db, lead, tipo="vacina")
    colunas = _colunas(db)
    svc.mover_lead(
        db,
        lead,
        colunas["Resolvido"].id,
        resultados={vacina.id: {"estado": "resolvida"}},
    )

    nova = svc.registrar_sinal(db, lead, tipo="racao", detalhe="Acabando")

    assert lead.ciclo_atual == 2 and nova.ciclo == 2
    assert lead.coluna_id == colunas["Novo"].id
    assert [o.tipo for o in svc.oportunidades_abertas(db, lead)] == ["racao"]
    assert vacina.estado == "resolvida"  # o ciclo antigo fica como estava
    ciclos = {m.ciclo for m in db.query(CrmMovimentacao)}
    assert ciclos == {1, 2}


def test_reabrir_devolve_as_oportunidades_do_ciclo_a_aberta(db, lead):
    vacina = svc.registrar_sinal(db, lead, tipo="vacina")
    colunas = _colunas(db)
    svc.mover_lead(
        db,
        lead,
        colunas["Resolvido"].id,
        resultados={vacina.id: {"estado": "descartada", "motivo": "Já vacinou"}},
    )

    svc.mover_lead(db, lead, colunas["Em contato"].id, nota="Reaberto")

    db.refresh(vacina)
    assert vacina.estado == "aberta" and vacina.motivo is None
    assert lead.ciclo_atual == 1


def test_mover_para_a_mesma_coluna_nao_grava_nada(db, lead):
    antes = db.query(CrmMovimentacao).count()

    svc.mover_lead(db, lead, lead.coluna_id)

    assert db.query(CrmMovimentacao).count() == antes


def test_nao_move_para_coluna_de_outro_funil_ou_inexistente(db, lead):
    with pytest.raises(svc.RegraDoCrm, match="não encontrada"):
        svc.mover_lead(db, lead, 99999)


def test_movimentacao_guarda_origem_destino_autor_e_nota(db, lead):
    colunas = _colunas(db)

    svc.mover_lead(db, lead, colunas["Em contato"].id, user_id=5, nota="Liguei")

    ultima = db.query(CrmMovimentacao).order_by(CrmMovimentacao.id.desc()).first()
    assert ultima.coluna_origem_id == colunas["Novo"].id
    assert ultima.coluna_destino_id == colunas["Em contato"].id
    assert ultima.user_id == 5 and ultima.nota == "Liguei"
    assert db.query(CrmOportunidade).count() == 0
