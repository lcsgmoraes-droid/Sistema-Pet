from datetime import date, datetime
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from app.dre_canais import agregacao, detalhes
from app.dre_canais.base import _novo_canal
from app.dre_canais.linhas import montar_linhas_dre_competencia
from app.dre_canais.routes import _montar_alertas_devolucoes
from app.vendas import devolucao_dre


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


def test_snapshot_v5_legado_nao_comprova_custo_original():
    item = SimpleNamespace(id=7, tipo="produto", produto_id=11, quantidade=2)
    venda = SimpleNamespace(
        id=123,
        itens=[item],
        rentabilidade_snapshot={
            "snapshot_version": 5,
            "itens": [{"produto_id": 11, "quantidade": 2, "custo_total": 60}],
        },
    )
    db = MagicMock()

    custo, origem, pendente = devolucao_dre.custo_original_item_devolvido(
        db, venda, item, Decimal("1"), "tenant"
    )

    assert (custo, origem, pendente) == (Decimal("0"), "sem_custo_original", True)
    db.query.assert_not_called()


def test_saida_de_estoque_legada_pode_ter_sido_reprocessada():
    item = SimpleNamespace(id=7, tipo="produto", produto_id=11, quantidade=2)
    venda = SimpleNamespace(id=123, itens=[item], rentabilidade_snapshot=None)
    db = MagicMock()
    db.query.return_value.filter.return_value.one.return_value = (2, 60)

    custo, origem, pendente = devolucao_dre.custo_original_item_devolvido(
        db, venda, item, Decimal("1"), "tenant"
    )

    assert (custo, origem, pendente) == (Decimal("0"), "sem_custo_original", True)
    db.query.assert_not_called()


def test_reembolso_de_servico_mantem_custo_incurrido():
    item = SimpleNamespace(id=7, tipo="servico", produto_id=11, quantidade=1)
    venda = SimpleNamespace(id=123, itens=[item])

    custo, origem, pendente = devolucao_dre.custo_original_item_devolvido(
        MagicMock(), venda, item, Decimal("1"), "tenant"
    )

    assert (custo, origem, pendente) == (
        Decimal("0"),
        "servico_custo_mantido",
        False,
    )


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
    assert alertas[1]["codigo"] == "devolucao_imposto_a_conciliar"
    assert "nao estorna automaticamente" in alertas[1]["mensagem"]


def _dados_venda_com_cmv_estimado(valor: str, quantidade: int):
    canal = _novo_canal()
    canal["receita_produtos"] = Decimal("30.00")
    canal["cmv_estimado"] = Decimal(valor)
    canal["itens_cmv_estimado"] = [
        {
            "venda_id": 123,
            "venda_item_id": 7,
            "numero_venda": "TESTE-123",
            "produto_id": 11,
            "produto_nome": "Produto sem custo",
            "quantidade": quantidade,
            "valor_venda": 30.0,
            "valor_estimado": float(Decimal(valor)),
            "percentual_custo": 40.0,
        }
    ]
    return {"loja_fisica": canal}


def _evento_sem_custo_original(evento_id: int, quantidade: int):
    evento = _evento(evento_id, "10.00", "0.00", pendente=True)
    evento.itens = [
        {
            "venda_item_id": 7,
            "tipo": "produto",
            "quantidade": str(quantidade),
            "valor_devolvido": "10.00",
            "custo_pendente": True,
        }
    ]
    return evento


def test_cmv_estimado_reverte_tres_parciais_e_fecha_centavos(monkeypatch):
    eventos = [_evento_sem_custo_original(indice, 1) for indice in (1, 2, 3)]
    venda = SimpleNamespace(id=123, data_venda=datetime(2026, 10, 1))
    db = MagicMock()
    db.query.return_value.filter.return_value.all.side_effect = [[venda], eventos]
    monkeypatch.setattr(
        agregacao,
        "_devolucoes_periodo_query",
        lambda *_args: SimpleNamespace(all=lambda: eventos),
    )
    dados = _dados_venda_com_cmv_estimado("0.02", 3)

    agregacao.agregar_devolucoes_por_canal(db, 10, 2026, "tenant", dados)
    _, totais = montar_linhas_dre_competencia(dados)

    assert dados["loja_fisica"]["cmv_estimado"] == Decimal("0.00")
    assert [
        item["valor_estimado"] for item in dados["loja_fisica"]["itens_cmv_estornado"]
    ] == [-0.01, -0.01]
    assert totais["devolucoes"] == 30
    assert totais["cmv"] == 0
    assert totais["lucro_bruto"] == 0


def test_cmv_estimado_de_venda_anterior_reverte_no_mes_da_devolucao(monkeypatch):
    evento = _evento_sem_custo_original(1, 3)
    venda = SimpleNamespace(id=123, data_venda=datetime(2026, 9, 1))
    db = MagicMock()
    db.query.return_value.filter.return_value.all.side_effect = [[venda], [evento]]
    monkeypatch.setattr(
        agregacao,
        "_devolucoes_periodo_query",
        lambda *_args: SimpleNamespace(all=lambda: [evento]),
    )
    monkeypatch.setattr(
        agregacao,
        "obter_vendas_por_canal",
        lambda *_args: _dados_venda_com_cmv_estimado("12.00", 3),
    )
    dados = {}

    agregacao.agregar_devolucoes_por_canal(db, 10, 2026, "tenant", dados)

    assert dados["loja_fisica"]["cmv_estimado"] == Decimal("-12.00")
    assert dados["loja_fisica"]["itens_cmv_estornado"][0]["devolucao_id"] == 1


def test_cmv_atribuido_sem_comprovante_reverte_provisoriamente(monkeypatch):
    evento = _evento_sem_custo_original(1, 3)
    evento.valor_devolvido = Decimal("30.00")
    venda = SimpleNamespace(id=123, data_venda=datetime(2026, 10, 1))
    db = MagicMock()
    db.query.return_value.filter.return_value.all.side_effect = [[venda], [evento]]
    monkeypatch.setattr(
        agregacao,
        "_devolucoes_periodo_query",
        lambda *_args: SimpleNamespace(all=lambda: [evento]),
    )
    dados = _dados_venda_com_cmv_estimado("0.00", 3)
    canal = dados["loja_fisica"]
    canal["cmv"] = Decimal("12.00")
    canal["itens_cmv_estimado"] = []
    canal["itens_cmv_atribuido"] = [
        {
            "venda_id": 123,
            "venda_item_id": 7,
            "numero_venda": "TESTE-123",
            "produto_id": 11,
            "produto_nome": "Produto sem custo comprovado",
            "quantidade": 3,
            "valor_venda": 30.0,
            "valor_cmv_atribuido": 12.0,
        }
    ]

    agregacao.agregar_devolucoes_por_canal(db, 10, 2026, "tenant", dados)
    _, totais = montar_linhas_dre_competencia(dados)

    assert canal["cmv"] == Decimal("12.00")
    assert canal["cmv_estimado"] == Decimal("-12.00")
    assert totais["cmv"] == 0
    assert totais["receita_liquida"] == 0
    assert canal["itens_cmv_estornado"][0]["origem_cmv_estornado"] == (
        "custo_atribuido_sem_comprovante"
    )
    assert _montar_alertas_devolucoes(dados)[0]["codigo"] == (
        "devolucao_custo_original_pendente"
    )


@pytest.mark.parametrize("mes_venda", [9, 10])
def test_cmv_agregado_legado_sem_custo_por_item_fecha_apos_devolucao(
    monkeypatch, mes_venda
):
    item = SimpleNamespace(
        id=7,
        tipo="produto",
        produto_id=11,
        quantidade=Decimal("1"),
        preco_unitario=Decimal("100"),
        subtotal=Decimal("100"),
        produto=SimpleNamespace(nome="Produto 11", codigo="11"),
    )
    venda = SimpleNamespace(
        id=123,
        itens=[item],
        data_venda=datetime(2026, mes_venda, 1),
        numero_venda="TESTE-123",
    )
    snapshot = {
        "custo_produtos": 40,
        "itens": [
            {
                "produto_id": 11,
                "quantidade": 1,
                "preco_unitario": 100,
                "venda_bruta": 100,
                "custo_total": 0,
            }
        ],
    }
    canal_venda = _novo_canal()
    canal_venda["receita_produtos"] = Decimal("100")
    canal_venda["cmv"] = Decimal("40")
    agregacao._registrar_base_estimativa_cmv(
        venda,
        "loja_fisica",
        snapshot,
        {},
        {},
        canal_venda["itens_cmv_atribuido"],
    )
    evento = _evento_sem_custo_original(1, 1)
    evento.valor_devolvido = Decimal("100")
    evento.itens[0]["valor_devolvido"] = "100"
    db = MagicMock()
    db.query.return_value.filter.return_value.all.side_effect = [[venda], [evento]]
    monkeypatch.setattr(
        agregacao,
        "_devolucoes_periodo_query",
        lambda *_args: SimpleNamespace(all=lambda: [evento]),
    )
    dados = {"loja_fisica": canal_venda} if mes_venda == 10 else {}
    if mes_venda == 9:
        monkeypatch.setattr(
            agregacao,
            "obter_vendas_por_canal",
            lambda *_args: {"loja_fisica": canal_venda},
        )

    agregacao.agregar_devolucoes_por_canal(db, 10, 2026, "tenant", dados)
    _, totais = montar_linhas_dre_competencia(dados)

    assert dados["loja_fisica"]["cmv_estimado"] == Decimal("-40")
    assert totais["cmv"] == (0 if mes_venda == 10 else -40)
    assert totais["receita_liquida"] == (0 if mes_venda == 10 else -100)


def test_cmv_legado_sem_vinculo_inequivoco_nao_recebe_estorno_inventado(monkeypatch):
    evento = _evento_sem_custo_original(1, 3)
    monkeypatch.setattr(
        agregacao,
        "_devolucoes_periodo_query",
        lambda *_args: SimpleNamespace(all=lambda: [evento]),
    )
    venda = SimpleNamespace(id=123, data_venda=datetime(2026, 10, 1))
    db = MagicMock()
    db.query.return_value.filter.return_value.all.side_effect = [[venda], [evento]]
    dados = _dados_venda_com_cmv_estimado("0.00", 3)
    canal = dados["loja_fisica"]
    canal["cmv"] = Decimal("12.00")
    canal["itens_cmv_estimado"] = []

    agregacao.agregar_devolucoes_por_canal(db, 10, 2026, "tenant", dados)
    _, totais = montar_linhas_dre_competencia(dados)

    assert totais["cmv"] == 12
    assert not canal.get("itens_cmv_estornado")
    assert _montar_alertas_devolucoes(dados)[0]["codigo"] == (
        "devolucao_custo_original_pendente"
    )


def test_linhas_identicas_legadas_rateiam_estorno_provisorio_sem_custo_estoque(
    monkeypatch,
):
    primeiro = _evento_sem_custo_original(1, 1)
    primeiro.valor_devolvido = Decimal("50.00")
    primeiro.itens[0].update({"venda_item_id": 7, "valor_devolvido": "50.00"})
    segundo = _evento_sem_custo_original(2, 1)
    segundo.valor_devolvido = Decimal("50.00")
    segundo.itens[0].update({"venda_item_id": 8, "valor_devolvido": "50.00"})
    eventos = [primeiro, segundo]
    venda = SimpleNamespace(id=123, data_venda=datetime(2026, 10, 1))
    db = MagicMock()
    db.query.return_value.filter.return_value.all.side_effect = [[venda], eventos]
    monkeypatch.setattr(
        agregacao,
        "_devolucoes_periodo_query",
        lambda *_args: SimpleNamespace(all=lambda: eventos),
    )
    canal = _novo_canal()
    canal["receita_produtos"] = Decimal("100.00")
    canal["cmv"] = Decimal("70.00")
    canal["itens_cmv_atribuido"] = [
        {
            "venda_id": 123,
            "venda_item_id": item_id,
            "quantidade": 1,
            "valor_cmv_atribuido": 35.0,
            "rateio_ambiguo": True,
        }
        for item_id in (7, 8)
    ]
    dados = {"loja_fisica": canal}

    agregacao.agregar_devolucoes_por_canal(db, 10, 2026, "tenant", dados)
    _, totais = montar_linhas_dre_competencia(dados)

    assert canal["cmv_estimado"] == Decimal("-70.00")
    assert totais["cmv"] == 0
    assert totais["receita_liquida"] == 0
    assert all(item["custo_pendente"] for evento in eventos for item in evento.itens)


def test_detalhe_cmv_estimado_inclui_estorno_da_devolucao(monkeypatch):
    evento = _evento_sem_custo_original(1, 3)
    evento.valor_devolvido = Decimal("30.00")
    evento.itens[0]["valor_devolvido"] = "30.00"
    venda = SimpleNamespace(id=123, data_venda=datetime(2026, 10, 1))
    db = MagicMock()
    db.query.return_value.filter.return_value.all.side_effect = [[venda], [evento]]
    monkeypatch.setattr(
        agregacao,
        "_devolucoes_periodo_query",
        lambda *_args: SimpleNamespace(all=lambda: [evento]),
    )
    monkeypatch.setattr(
        detalhes,
        "obter_vendas_por_canal",
        lambda *_args, **_kwargs: _dados_venda_com_cmv_estimado("12.00", 3),
    )

    linhas = detalhes._detalhes_cmv_estimado(db, 10, 2026, "tenant", "loja_fisica")

    assert sorted(item.valor for item in linhas) == [-12.0, 12.0]
    assert sum(item.valor for item in linhas) == 0
    assert any(item.origem_tipo == "estorno_estimativa_cmv" for item in linhas)


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
