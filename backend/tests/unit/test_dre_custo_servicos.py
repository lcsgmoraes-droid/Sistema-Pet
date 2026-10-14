from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.dre_canais import agregacao
from app.dre_canais.agregacao import (
    _separar_custo_produto_servico,
    _valor_snapshot_campo,
)
from app.dre_canais.base import _novo_canal, _separar_receita_produto_servico
from app.dre_canais.detalhes import CAMPOS_DETALHE_VENDAS
from app.dre_canais.linhas import montar_linhas_dre_competencia


def _item(tipo, produto_id, preco, custo):
    return (
        SimpleNamespace(
            tipo=tipo,
            produto_id=produto_id,
            quantidade=Decimal("1"),
            preco_unitario=Decimal(str(preco)),
            subtotal=Decimal(str(preco)),
        ),
        {"produto_id": produto_id, "custo_total": custo},
    )


def test_venda_somente_servico_tem_custo_proprio_sem_cmv():
    item, item_snapshot = _item("servico", 10, 130, 65)
    venda = SimpleNamespace(itens=[item])
    snapshot = {
        "venda_bruta": 130,
        "custo_produtos": 65,
        "itens": [item_snapshot],
    }

    assert _separar_receita_produto_servico(venda, Decimal("130")) == (
        Decimal("0"),
        Decimal("130"),
    )
    assert _separar_custo_produto_servico(venda, snapshot) == (
        Decimal("0"),
        Decimal("65.00"),
    )
    assert _valor_snapshot_campo("cmv", venda, snapshot) == 0
    assert _valor_snapshot_campo("custo_servicos", venda, snapshot) == 65

    canal = _novo_canal()
    canal["receita_servicos"] = Decimal("130")
    canal["custo_servicos"] = Decimal("65")
    linhas, totais = montar_linhas_dre_competencia({"loja_fisica": canal})

    assert totais["cmv"] == pytest.approx(0)
    assert totais["custo_servicos"] == pytest.approx(65)
    assert totais["custos_diretos"] == pytest.approx(65)
    assert totais["lucro_bruto"] == pytest.approx(65)
    assert "custo_servicos" in CAMPOS_DETALHE_VENDAS
    linha_servicos = next(linha for linha in linhas if linha.campo == "custo_servicos")
    assert linha_servicos.valor == pytest.approx(65)
    assert linha_servicos.detalhavel is True


def test_venda_mista_separa_cmv_e_servico_sem_alterar_lucro():
    produto, produto_snapshot = _item("produto", 11, 100, 45)
    servico, servico_snapshot = _item("servico", 12, 130, 65)
    venda = SimpleNamespace(itens=[produto, servico])
    snapshot = {
        "venda_bruta": 230,
        "custo_produtos": 110,
        "itens": [produto_snapshot, servico_snapshot],
    }

    assert _separar_receita_produto_servico(venda, Decimal("230")) == (
        Decimal("100"),
        Decimal("130"),
    )
    assert _separar_custo_produto_servico(venda, snapshot) == (
        Decimal("45.00"),
        Decimal("65.00"),
    )
    assert _valor_snapshot_campo("cmv", venda, snapshot) == 45
    assert _valor_snapshot_campo("custo_servicos", venda, snapshot) == 65

    canal = _novo_canal()
    canal["receita_produtos"] = Decimal("100")
    canal["receita_servicos"] = Decimal("130")
    canal["cmv"] = Decimal("45")
    canal["custo_servicos"] = Decimal("65")
    _, totais = montar_linhas_dre_competencia({"loja_fisica": canal})

    assert totais["cmv"] == pytest.approx(45)
    assert totais["custo_servicos"] == pytest.approx(65)
    assert totais["custos_diretos"] == pytest.approx(110)
    assert totais["lucro_bruto"] == pytest.approx(120)
    assert totais["lucro_liquido"] == pytest.approx(120)


def test_agregacao_venda_mista_alimenta_linhas_separadas(monkeypatch):
    produto, produto_snapshot = _item("produto", 11, 100, 45)
    servico, servico_snapshot = _item("servico", 12, 130, 65)
    venda = SimpleNamespace(
        id=7,
        canal="loja_fisica",
        itens=[produto, servico],
        rentabilidade_snapshot={
            "snapshot_version": 999,
            "venda_bruta": 230,
            "custo_produtos": 110,
            "itens": [produto_snapshot, servico_snapshot],
        },
    )

    class FakeQuery:
        def options(self, *args):
            return self

        def filter(self, *args):
            return self

        def all(self):
            return [venda]

    db = SimpleNamespace(query=lambda model: FakeQuery())
    for nome in (
        "_formas_pagamento_map",
        "_bulk_comissoes_por_venda",
        "_bulk_cupons_por_venda",
        "_bulk_cashback_por_venda",
        "_bulk_taxa_operacional_por_venda",
        "_bulk_estoque_custos_por_venda",
    ):
        monkeypatch.setattr(agregacao, nome, lambda *args: {})
    monkeypatch.setattr(agregacao, "_impostos_percentual", lambda *args: 0)

    dados = agregacao.obter_vendas_por_canal(db, 10, 2026, "tenant-teste")

    assert dados["loja_fisica"]["receita_produtos"] == Decimal("100")
    assert dados["loja_fisica"]["receita_servicos"] == Decimal("130")
    assert dados["loja_fisica"]["cmv"] == Decimal("45.00")
    assert dados["loja_fisica"]["custo_servicos"] == Decimal("65.00")


def test_fotografia_antiga_servico_unico_preserva_custo_e_produto_nao_muda():
    servico, _ = _item("servico", 12, 130, 65)
    produto, _ = _item("produto", 11, 100, 45)

    assert _separar_custo_produto_servico(
        SimpleNamespace(itens=[servico]), {"custo_produtos": 65}
    ) == (Decimal("0"), Decimal("65.00"))
    assert _separar_custo_produto_servico(
        SimpleNamespace(itens=[produto]), {"custo_produtos": 45}
    ) == (Decimal("45.00"), Decimal("0"))


def test_fotografia_mista_com_itens_em_ordem_diferente_reconcilia_por_produto():
    produto, produto_snapshot = _item("produto", 11, 100, 45)
    servico, servico_snapshot = _item("servico", 12, 130, 65)
    venda = SimpleNamespace(itens=[produto, servico])
    snapshot = {
        "custo_produtos": 110,
        "itens": [servico_snapshot, produto_snapshot],
    }

    assert _separar_custo_produto_servico(venda, snapshot) == (
        Decimal("45.00"),
        Decimal("65.00"),
    )
