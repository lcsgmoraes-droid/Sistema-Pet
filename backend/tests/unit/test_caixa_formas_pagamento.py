"""Fechamento preserva cada forma cadastrada, mesmo quando o tipo é igual."""

from datetime import datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy.schema import CreateTable

from app.caixa.formas_pagamento import (
    carregar_nomes_formas_pagamento,
    nome_forma_pagamento,
)
from app.caixa_routes import listar_vendas_caixa, obter_resumo_caixa
from app.financeiro_models import FormaPagamento
from app.vendas_models import VendaPagamento
from tests.unit.test_caixa_recebimentos_auditoria import (  # noqa: F401
    caixa_session,
    recebimentos,
)


@pytest.fixture
def formas_loja(recebimentos):  # noqa: F811 - fixture importada para reutilização
    caso = recebimentos
    # A tabela é criada somente no banco/schema descartável desta fixture.
    with caso.db.get_bind().begin() as connection:
        connection.execute(
            CreateTable(FormaPagamento.__table__, include_foreign_key_constraints=[])
        )
    formas = {}
    for nome, tipo, ativo in (
        ("PIX", "pix", True),
        ("Pix Stone", "pix", False),
        ("Pix Itaú", "pix", True),
        ("Crédito Stone", "cartao_credito", True),
        ("Crédito Itaú", "cartao_credito", True),
    ):
        forma = FormaPagamento(
            tenant_id=caso.auth[1],
            user_id=caso.auth[0].id,
            nome=nome,
            tipo=tipo,
            ativo=ativo,
        )
        caso.db.add(forma)
        formas[nome] = forma
    caso.db.flush()
    caso.formas = formas
    for pagamento in caso.pagamentos[:2]:
        pagamento.forma_pagamento_id = formas["PIX"].id
    caso.db.flush()
    return caso


def adicionar_pagamento(caso, forma, valor, *, tipo="PIX", forma_id=None):
    pagamento = VendaPagamento(
        tenant_id=caso.auth[1],
        venda_id=caso.venda.id,
        caixa_id=caso.atual.id,
        forma_pagamento=tipo,
        forma_pagamento_id=caso.formas[forma].id if forma else forma_id,
        valor=valor,
        status="confirmado",
        data_pagamento=datetime(2026, 10, 9, 13),
    )
    caso.db.add(pagamento)
    caso.db.flush()
    return pagamento


def consultar_resumo(caso, caixa=None):
    return obter_resumo_caixa(
        (caixa or caso.atual).id,
        db=caso.db,
        current_user_and_tenant=caso.auth,
    )


def consultar_forma(caso, forma):
    return listar_vendas_caixa(
        caso.atual.id,
        forma_pagamento=forma,
        db=caso.db,
        current_user_and_tenant=caso.auth,
    )


def test_pix_cadastrados_separados_com_estorno_e_forma_inativa(formas_loja):
    caso = formas_loja
    stone = adicionar_pagamento(caso, "Pix Stone", 80)
    itau = adicionar_pagamento(caso, "Pix Itaú", 60)
    estorno = adicionar_pagamento(caso, "Pix Stone", -10)
    legado = adicionar_pagamento(caso, None, 15)

    resumo = consultar_resumo(caso)
    composicao = resumo["composicao_recebimentos"]
    esperado = {"PIX": 55, "Pix Stone": 70, "Pix Itaú": 60, "Dinheiro": 20}
    assert {
        nome: dados["total"]
        for nome, dados in composicao["por_forma_pagamento"].items()
    } == esperado
    assert {
        nome: dados["total"]
        for nome, dados in resumo["recebimentos_por_forma_pagamento"].items()
    } == esperado
    assert composicao["total_recebido"] == sum(esperado.values()) == 205
    assert composicao["devolucoes"] == 10
    assert resumo["totais"]["saldo_atual"] == 120
    detalhes = {item["id"]: item for item in composicao["detalhes"]}
    assert detalhes[f"pagamento-{stone.id}"]["forma_pagamento"] == "Pix Stone"
    assert detalhes[f"pagamento-{itau.id}"]["forma_pagamento"] == "Pix Itaú"
    assert detalhes[f"pagamento-{estorno.id}"]["forma_pagamento"] == "Pix Stone"
    assert detalhes[f"pagamento-{estorno.id}"]["tipo"] == "estorno"
    assert detalhes[f"pagamento-{legado.id}"]["forma_pagamento"] == "PIX"
    assert not caso.formas["Pix Stone"].ativo

    original = consultar_resumo(caso, caso.original)
    formas_venda = original["pagamentos_vendas_por_forma_pagamento"]
    assert {nome: dados["total"] for nome, dados in formas_venda.items()} == {
        **esperado,
        "PIX": 85,
    }


def test_cartoes_do_mesmo_tipo_mantem_totais_separados(formas_loja):
    caso = formas_loja
    adicionar_pagamento(caso, "Crédito Stone", 90, tipo="cartao_credito")
    adicionar_pagamento(caso, "Crédito Itaú", 70, tipo="cartao_credito")

    composicao = consultar_resumo(caso)["composicao_recebimentos"]
    assert composicao["por_forma_pagamento"]["Crédito Stone"]["total"] == 90
    assert composicao["por_forma_pagamento"]["Crédito Itaú"]["total"] == 70
    assert "cartao_credito" not in composicao["por_forma_pagamento"]
    assert sum(
        dados["total"] for dados in composicao["por_forma_pagamento"].values()
    ) == composicao["total_recebido"] == 220


def test_detalhes_filtram_forma_cadastrada_sem_incluir_outros_pix(formas_loja):
    caso = formas_loja
    stone = adicionar_pagamento(caso, "Pix Stone", 80)
    estorno = adicionar_pagamento(caso, "Pix Stone", -10)
    itau = adicionar_pagamento(caso, "Pix Itaú", 60)
    legado = adicionar_pagamento(caso, None, 15)
    # Associação legada inconsistente não pode entrar no detalhe desta empresa.
    caso.db.execute(
        VendaPagamento.__table__.insert().values(
            tenant_id=uuid4(),
            venda_id=caso.venda.id,
            caixa_id=caso.atual.id,
            forma_pagamento="PIX",
            forma_pagamento_id=caso.formas["Pix Stone"].id,
            valor=999,
            data_pagamento=datetime(2026, 10, 9, 14),
        )
    )

    assert {item["pagamento_id"] for item in consultar_forma(caso, "Pix Stone")} == {
        stone.id,
        estorno.id,
    }
    assert {item["pagamento_id"] for item in consultar_forma(caso, "Pix Itaú")} == {
        itau.id
    }
    assert {item["pagamento_id"] for item in consultar_forma(caso, "PIX")} == {
        caso.pagamentos[1].id,
        legado.id,
    }
    vendas = consultar_forma(caso, None)
    pagamentos = {
        item["id"]: item
        for venda in vendas
        for item in venda["recebimentos"]
        if item["tipo"] == "pagamento"
    }
    assert pagamentos[stone.id]["forma_pagamento"] == "Pix Stone"
    assert pagamentos[stone.id]["forma_pagamento_tipo"] == "PIX"
    assert pagamentos[itau.id]["forma_pagamento"] == "Pix Itaú"
    historico = {item["id"]: item for item in vendas[0]["pagamentos"]}
    # O histórico preserva o tipo original usado pela conferência/assinatura.
    assert historico[stone.id]["forma_pagamento"] == "PIX"
    assert historico[itau.id]["forma_pagamento"] == "PIX"


def test_nome_por_id_respeita_tenant_e_preserva_fallback_legado(formas_loja):
    caso = formas_loja
    outro_tenant = uuid4()
    id_estrangeiro = 90001
    id_inexistente = 90002
    caso.db.execute(
        FormaPagamento.__table__.insert().values(
            id=id_estrangeiro,
            tenant_id=outro_tenant,
            user_id=caso.auth[0].id,
            nome="Nome privado de outra empresa",
            tipo="pix",
            ativo=True,
        )
    )
    nomes = carregar_nomes_formas_pagamento(
        caso.db,
        tenant_id=caso.auth[1],
        forma_ids=[
            caso.formas["Pix Stone"].id,
            id_estrangeiro,
            id_inexistente,
            None,
        ],
    )
    assert nomes == {caso.formas["Pix Stone"].id: "Pix Stone"}
    assert nome_forma_pagamento(
        SimpleNamespace(
            forma_pagamento_id=caso.formas["Pix Stone"].id,
            forma_pagamento="PIX",
        ),
        nomes,
    ) == "Pix Stone"
    for forma_id in (None, id_estrangeiro, id_inexistente):
        assert nome_forma_pagamento(
            SimpleNamespace(forma_pagamento_id=forma_id, forma_pagamento="PIX"),
            nomes,
        ) == "PIX"

    estrangeiro = adicionar_pagamento(caso, None, 11, forma_id=id_estrangeiro)
    inexistente = adicionar_pagamento(caso, None, 12, forma_id=id_inexistente)
    composicao = consultar_resumo(caso)["composicao_recebimentos"]
    assert composicao["por_forma_pagamento"]["PIX"]["total"] == 63
    assert set(composicao["por_forma_pagamento"]) == {"PIX", "Dinheiro"}
    detalhes = {item["id"]: item for item in composicao["detalhes"]}
    for pagamento in (estrangeiro, inexistente):
        assert detalhes[f"pagamento-{pagamento.id}"]["forma_pagamento"] == "PIX"


def test_nome_personalizado_nao_muda_natureza_do_recebimento(formas_loja):
    caso = formas_loja
    for nome, tipo in (
        ("Pix Cashback parceiro", "pix"),
        ("Benefício fidelidade", "cashback"),
    ):
        forma = FormaPagamento(
            tenant_id=caso.auth[1],
            user_id=caso.auth[0].id,
            nome=nome,
            tipo=tipo,
        )
        caso.db.add(forma)
        caso.formas[nome] = forma
    caso.db.flush()
    pix = adicionar_pagamento(caso, "Pix Cashback parceiro", 10)
    beneficio = adicionar_pagamento(
        caso, "Benefício fidelidade", 12, tipo="cashback"
    )

    composicao = consultar_resumo(caso)["composicao_recebimentos"]
    assert composicao["total_recebido"] == 70
    assert composicao["creditos_utilizados"] == 12
    assert composicao["por_forma_pagamento"]["Pix Cashback parceiro"]["total"] == 10
    assert "Benefício fidelidade" not in composicao["por_forma_pagamento"]
    assert any(item["id"] == f"pagamento-{pix.id}" for item in composicao["detalhes"])
    assert [item["id"] for item in composicao["detalhes_creditos"]] == [
        f"pagamento-{beneficio.id}"
    ]


def test_cadastros_com_mesmo_nome_tem_identidade_estavel_em_resumo_e_detalhe(
    formas_loja,
):
    caso = formas_loja
    duplicada = FormaPagamento(
        tenant_id=caso.auth[1],
        user_id=caso.auth[0].id,
        nome="Pix Stone",
        tipo="pix",
        ativo=True,
    )
    caso.db.add(duplicada)
    caso.db.flush()
    primeira = adicionar_pagamento(caso, "Pix Stone", 40)
    nome_primeira = f"Pix Stone (forma #{caso.formas['Pix Stone'].id})"
    nome_segunda = f"Pix Stone (forma #{duplicada.id})"

    # O cadastro sem recebimento já participa da desambiguação: o nome de um
    # mesmo cadastro não pode variar entre caixas conforme os pagamentos.
    composicao = consultar_resumo(caso)["composicao_recebimentos"]
    assert composicao["por_forma_pagamento"][nome_primeira]["total"] == 40
    assert "Pix Stone" not in composicao["por_forma_pagamento"]
    assert nome_segunda not in composicao["por_forma_pagamento"]
    assert {item["pagamento_id"] for item in consultar_forma(caso, nome_primeira)} == {
        primeira.id
    }

    segunda = adicionar_pagamento(caso, None, 25, forma_id=duplicada.id)
    composicao = consultar_resumo(caso)["composicao_recebimentos"]
    assert composicao["por_forma_pagamento"][nome_primeira]["total"] == 40
    assert composicao["por_forma_pagamento"][nome_segunda]["total"] == 25
    assert composicao["total_recebido"] == 125
    detalhes = {item["id"]: item for item in composicao["detalhes"]}
    assert detalhes[f"pagamento-{primeira.id}"]["forma_pagamento"] == nome_primeira
    assert detalhes[f"pagamento-{segunda.id}"]["forma_pagamento"] == nome_segunda
    assert {item["pagamento_id"] for item in consultar_forma(caso, nome_segunda)} == {
        segunda.id
    }
