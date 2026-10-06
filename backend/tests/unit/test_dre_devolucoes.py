from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from contextlib import nullcontext
from unittest.mock import MagicMock

from app.dre_canais import agregacao, detalhes
from app.dre_canais.base import _novo_canal
from app.dre_canais.linhas import montar_linhas_dre_competencia
from app.dre_canais.routes import _montar_alertas_devolucoes
from app.vendas import devolucao_dre
from app.vendas.devolucao_dre import _custo_snapshot


def _evento(evento_id, valor, custo, *, pendente=False, canal="loja_fisica"):
    return SimpleNamespace(
        id=evento_id,
        venda_id=123,
        data_competencia=date(2026, 10, 5),
        canal=canal,
        forma_estorno="credito" if evento_id == 2 else "dinheiro",
        motivo="Teste",
        valor_devolvido=Decimal(valor),
        custo_produtos_estornado=Decimal(custo),
        custo_servicos_estornado=Decimal("0"),
        custo_pendente=pendente,
        itens=[{"custo_pendente": pendente}],
    )


def test_duas_devolucoes_parciais_zeram_receita_e_cmv_da_venda(monkeypatch):
    eventos = [_evento(1, "25.00", "15.00"), _evento(2, "75.00", "45.00")]
    monkeypatch.setattr(
        agregacao,
        "_devolucoes_periodo_query",
        lambda *_args: SimpleNamespace(all=lambda: eventos),
    )
    canal = _novo_canal()
    canal["receita_produtos"] = Decimal("100.00")
    canal["cmv"] = Decimal("60.00")
    dados = {"loja_fisica": canal}

    agregacao.agregar_devolucoes_por_canal(object(), 10, 2026, "tenant", dados)
    linhas, totais = montar_linhas_dre_competencia(dados)

    assert totais["devolucoes"] == 100
    assert totais["cmv"] == 0
    assert totais["receita_liquida"] == 0
    assert totais["lucro_bruto"] == 0
    assert next(linha for linha in linhas if linha.campo == "devolucoes").detalhavel


def test_devolucao_no_mes_seguinte_reverte_custo_original_sem_venda_no_mes(monkeypatch):
    monkeypatch.setattr(
        agregacao,
        "_devolucoes_periodo_query",
        lambda *_args: SimpleNamespace(all=lambda: [_evento(1, "30.00", "18.00")]),
    )
    dados = {}
    agregacao.agregar_devolucoes_por_canal(object(), 10, 2026, "tenant", dados)
    _, totais = montar_linhas_dre_competencia(dados)

    assert totais["devolucoes"] == 30
    assert totais["cmv"] == -18
    assert totais["lucro_bruto"] == -12


def test_custo_original_usa_snapshot_por_item_e_nao_cadastro_atual():
    item = SimpleNamespace(
        id=7,
        tipo="produto",
        produto_id=11,
        quantidade=Decimal("2"),
        preco_unitario=Decimal("50"),
    )
    venda = SimpleNamespace(
        itens=[item],
        rentabilidade_snapshot={
            "snapshot_version": 5,
            "itens": [
                {
                    "produto_id": 11,
                    "quantidade": 2,
                    "preco_unitario": 50,
                    "custo_total": 60,
                }
            ],
        },
    )
    assert _custo_snapshot(venda, item, Decimal("1")) == Decimal("30.00")


def test_custo_snapshot_parcial_preserva_centavos_ate_ultima_devolucao():
    item = SimpleNamespace(id=7, produto_id=11, quantidade=3, preco_unitario=10)
    venda = SimpleNamespace(
        itens=[item],
        rentabilidade_snapshot={
            "snapshot_version": 5,
            "itens": [
                {
                    "produto_id": 11,
                    "quantidade": 3,
                    "preco_unitario": 10,
                    "custo_total": "0.02",
                }
            ],
        },
    )

    parcelas = [
        _custo_snapshot(venda, item, Decimal("1"), Decimal(anterior))
        for anterior in range(3)
    ]

    assert parcelas == [Decimal("0.01"), Decimal("0.00"), Decimal("0.01")]
    assert sum(parcelas) == Decimal("0.02")


def test_snapshot_nao_depende_da_ordem_da_relacao_de_itens():
    primeiro = SimpleNamespace(id=7, produto_id=11, quantidade=2, preco_unitario=50)
    segundo = SimpleNamespace(id=8, produto_id=12, quantidade=1, preco_unitario=80)
    venda = SimpleNamespace(
        itens=[segundo, primeiro],
        rentabilidade_snapshot={
            "snapshot_version": 5,
            "itens": [
                {
                    "produto_id": 11,
                    "quantidade": 2,
                    "preco_unitario": 50,
                    "custo_total": 60,
                },
                {
                    "produto_id": 12,
                    "quantidade": 1,
                    "preco_unitario": 80,
                    "custo_total": 25,
                },
            ],
        },
    )

    assert _custo_snapshot(venda, primeiro, Decimal("1")) == Decimal("30.00")
    assert _custo_snapshot(venda, segundo, Decimal("1")) == Decimal("25.00")


def test_snapshot_duplicado_com_custos_diferentes_fica_pendente_sem_saida_rastreavel():
    item = SimpleNamespace(
        id=7, tipo="produto", produto_id=11, quantidade=1, preco_unitario=50
    )
    repetido = SimpleNamespace(
        id=8, tipo="produto", produto_id=11, quantidade=1, preco_unitario=50
    )
    venda = SimpleNamespace(
        id=123,
        itens=[repetido, item],
        rentabilidade_snapshot={
            "snapshot_version": 5,
            "itens": [
                {
                    "produto_id": 11,
                    "quantidade": 1,
                    "preco_unitario": 50,
                    "custo_total": 30,
                },
                {
                    "produto_id": 11,
                    "quantidade": 1,
                    "preco_unitario": 50,
                    "custo_total": 40,
                },
            ],
        },
    )
    db = MagicMock()

    assert _custo_snapshot(venda, item, Decimal("1")) is None
    custo, origem, pendente = devolucao_dre.custo_original_item_devolvido(
        db, venda, item, Decimal("1"), "tenant"
    )

    assert (custo, origem, pendente) == (Decimal("0"), "sem_custo_original", True)
    db.query.assert_not_called()


def test_sem_snapshot_usa_saida_historica_do_estoque(monkeypatch):
    item = SimpleNamespace(id=7, tipo="produto", produto_id=11, quantidade=2)
    venda = SimpleNamespace(id=123, rentabilidade_snapshot=None, itens=[item])
    db = MagicMock()
    db.query.return_value.filter.return_value.one.return_value = (2, 40)
    monkeypatch.setattr(
        devolucao_dre, "resolver_tenant_estoque_item", lambda *_args: ("tenant", False)
    )
    monkeypatch.setattr(
        devolucao_dre, "contexto_tenant_estoque", lambda *_args: nullcontext("tenant")
    )

    custo, origem, pendente = devolucao_dre.custo_original_item_devolvido(
        db, venda, item, Decimal("1"), "tenant"
    )

    assert custo == Decimal("20.00")
    assert origem == "saida_estoque_venda"
    assert pendente is False


def test_saida_estoque_parcial_preserva_centavos_ate_ultima_devolucao(monkeypatch):
    item = SimpleNamespace(id=7, tipo="produto", produto_id=11, quantidade=3)
    venda = SimpleNamespace(id=123, rentabilidade_snapshot=None, itens=[item])
    db = MagicMock()
    db.query.return_value.filter.return_value.one.return_value = (3, Decimal("0.02"))
    monkeypatch.setattr(
        devolucao_dre, "resolver_tenant_estoque_item", lambda *_args: ("tenant", False)
    )
    monkeypatch.setattr(
        devolucao_dre, "contexto_tenant_estoque", lambda *_args: nullcontext("tenant")
    )

    parcelas = [
        devolucao_dre.custo_original_item_devolvido(
            db, venda, item, Decimal("1"), "tenant", Decimal(anterior)
        )[0]
        for anterior in range(3)
    ]

    assert parcelas == [Decimal("0.01"), Decimal("0.00"), Decimal("0.01")]
    assert sum(parcelas) == Decimal("0.02")


def test_saida_estoque_com_quantidade_extra_nao_prova_custo_da_linha(monkeypatch):
    item = SimpleNamespace(id=7, tipo="produto", produto_id=11, quantidade=2)
    venda = SimpleNamespace(id=123, rentabilidade_snapshot=None, itens=[item])
    db = MagicMock()
    db.query.return_value.filter.return_value.one.return_value = (3, 60)
    monkeypatch.setattr(
        devolucao_dre, "resolver_tenant_estoque_item", lambda *_args: ("tenant", False)
    )
    monkeypatch.setattr(
        devolucao_dre, "contexto_tenant_estoque", lambda *_args: nullcontext("tenant")
    )

    custo, origem, pendente = devolucao_dre.custo_original_item_devolvido(
        db, venda, item, Decimal("1"), "tenant"
    )

    assert (custo, origem, pendente) == (Decimal("0"), "sem_custo_original", True)


def test_custo_pendente_fica_explicito_sem_estorno_inventado(monkeypatch):
    evento = _evento(1, "20.00", "0.00", pendente=True)
    monkeypatch.setattr(
        agregacao,
        "_devolucoes_periodo_query",
        lambda *_args: SimpleNamespace(all=lambda: [evento]),
    )
    dados = {}
    agregacao.agregar_devolucoes_por_canal(object(), 10, 2026, "tenant", dados)
    alertas = _montar_alertas_devolucoes(dados)

    assert dados["loja_fisica"]["devolucoes"] == Decimal("20.00")
    assert dados["loja_fisica"]["cmv"] == 0
    assert alertas[0]["codigo"] == "devolucao_custo_original_pendente"
    assert alertas[0]["quantidade_itens"] == 1
    assert "provisorio zero" in alertas[0]["mensagem"]
    assert "ajuste manualmente" in alertas[0]["mensagem"]


def test_detalhe_da_devolucao_exibe_deducao_e_estorno_cmv(monkeypatch):
    evento = _evento(1, "30.00", "18.00")
    monkeypatch.setattr(
        detalhes,
        "_devolucoes_periodo_query",
        lambda *_args: SimpleNamespace(all=lambda: [evento]),
    )
    args = (object(), 10, 2026, "tenant", "loja_fisica")
    deducao = detalhes._detalhes_devolucoes_campo(*args, "devolucoes")
    custo = detalhes._detalhes_devolucoes_campo(*args, "cmv")

    assert deducao[0].valor == 30
    assert custo[0].valor == -18
    assert deducao[0].meta["devolucao_id"] == 1
