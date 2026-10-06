from datetime import datetime
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from app.dre_canais.agregacao import (
    _aplicar_estimativas_cmv,
    _bulk_cashback_por_venda,
    _bulk_cupons_por_venda,
    _complementar_snapshot_com_custos_reais,
    _conciliar_custo_campanha_snapshot,
    _registrar_base_estimativa_cmv,
)
from app.dre_canais.base import _novo_canal
from app.dre_canais.linhas import montar_linhas_dre_competencia
from app.dre_canais.routes import _montar_alertas_cmv_estimado
from app.dre_canais.schemas import DREAlerta
from app.vendas import devolucao_dre


def test_estima_cmv_pela_proporcao_ponderada_do_mesmo_canal():
    dados = {"loja_fisica": _novo_canal()}
    bases = {
        "loja_fisica": {
            "receita_confirmada": Decimal("1000"),
            "custo_confirmado": Decimal("600"),
        }
    }
    pendencias = {
        "loja_fisica": [
            {"produto_id": 1, "valor_venda": 100},
            {"produto_id": 2, "valor_venda": 50},
        ]
    }

    _aplicar_estimativas_cmv(dados, bases, pendencias)

    assert dados["loja_fisica"]["cmv_estimado"] == Decimal("90.00")
    assert dados["loja_fisica"]["percentual_cmv_estimado"] == Decimal("60.0")
    assert dados["loja_fisica"]["origem_percentual_cmv_estimado"] == "mesmo_canal"
    assert [
        item["valor_estimado"] for item in dados["loja_fisica"]["itens_cmv_estimado"]
    ] == [60.0, 30.0]


def test_estima_com_base_global_quando_canal_nao_tem_amostra_confiavel():
    dados = {"shopee": _novo_canal()}
    bases = {
        "loja_fisica": {
            "receita_confirmada": Decimal("200"),
            "custo_confirmado": Decimal("100"),
        },
        "shopee": {
            "receita_confirmada": Decimal("0"),
            "custo_confirmado": Decimal("0"),
        },
    }
    pendencias = {"shopee": [{"produto_id": 3, "valor_venda": 80}]}

    _aplicar_estimativas_cmv(dados, bases, pendencias)

    assert dados["shopee"]["cmv_estimado"] == Decimal("40.00")
    assert dados["shopee"]["origem_percentual_cmv_estimado"] == "todos_canais_periodo"


def _item_legado(item_id, produto_id, quantidade, preco, subtotal):
    return SimpleNamespace(
        id=item_id,
        tipo="produto",
        produto_id=produto_id,
        quantidade=Decimal(str(quantidade)),
        preco_unitario=Decimal(str(preco)),
        subtotal=Decimal(str(subtotal)),
        produto=SimpleNamespace(nome=f"Produto {produto_id}", codigo=str(produto_id)),
    )


def test_duas_linhas_identicas_sem_custo_recebem_cmv_provisorio():
    itens = [
        _item_legado(7, 11, 1, 50, 50),
        _item_legado(8, 11, 1, 50, 50),
        _item_legado(9, 12, 1, 100, 100),
    ]
    venda = SimpleNamespace(
        id=123,
        numero_venda="TESTE-123",
        data_venda=datetime(2026, 10, 1),
        itens=itens,
    )
    snapshot = {
        "itens": [
            {"produto_id": 11, "quantidade": 1, "preco_unitario": 50, "custo_total": 0},
            {"produto_id": 11, "quantidade": 1, "preco_unitario": 50, "custo_total": 0},
            {
                "produto_id": 12,
                "quantidade": 1,
                "preco_unitario": 100,
                "custo_total": 40,
                "venda_bruta": 100,
            },
        ]
    }
    dados = {"loja_fisica": _novo_canal()}
    bases, pendencias = {}, {}

    _registrar_base_estimativa_cmv(
        venda,
        "loja_fisica",
        snapshot,
        bases,
        pendencias,
        dados["loja_fisica"]["itens_cmv_atribuido"],
    )
    _aplicar_estimativas_cmv(dados, bases, pendencias)

    assert dados["loja_fisica"]["cmv_estimado"] == Decimal("40.00")
    assert {
        item["venda_item_id"]: item["valor_estimado"]
        for item in dados["loja_fisica"]["itens_cmv_estimado"]
    } == {7: 20.0, 8: 20.0}


def test_snapshot_legado_rateia_cmv_positivo_de_linhas_identicas_com_alerta():
    itens = [_item_legado(7, 11, 1, 50, 50), _item_legado(8, 11, 1, 50, 50)]
    venda = SimpleNamespace(id=123, itens=itens, data_venda=datetime(2026, 10, 1))
    snapshot = {
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
        ]
    }
    dados = {"loja_fisica": _novo_canal()}

    _registrar_base_estimativa_cmv(
        venda,
        "loja_fisica",
        snapshot,
        {},
        {},
        dados["loja_fisica"]["itens_cmv_atribuido"],
    )

    assert [
        item["valor_cmv_atribuido"]
        for item in dados["loja_fisica"]["itens_cmv_atribuido"]
    ] == [35.0, 35.0]
    assert _montar_alertas_cmv_estimado(dados)[0]["codigo"] == "cmv_rateio_ambiguo"


def test_quantidade_fracionaria_do_snapshot_arredondada_a_centavos_e_vinculada():
    item = _item_legado(7, 11, "0.005", 100, 0.5)
    conhecido = _item_legado(8, 12, 1, 100, 100)
    venda = SimpleNamespace(
        id=123, itens=[item, conhecido], data_venda=datetime(2026, 10, 1)
    )
    snapshot = {
        "itens": [
            {
                "produto_id": 12,
                "quantidade": 1,
                "preco_unitario": 100,
                "custo_total": 40,
            },
            {
                "produto_id": 11,
                "quantidade": 0.01,
                "preco_unitario": 100,
                "custo_total": 0,
            },
        ]
    }
    dados = {"loja_fisica": _novo_canal()}
    bases, pendencias = {}, {}

    _registrar_base_estimativa_cmv(
        venda,
        "loja_fisica",
        snapshot,
        bases,
        pendencias,
        dados["loja_fisica"]["itens_cmv_atribuido"],
    )
    _aplicar_estimativas_cmv(dados, bases, pendencias)

    assert [item["venda_item_id"] for item in pendencias["loja_fisica"]] == [7]
    assert dados["loja_fisica"]["cmv_estimado"] == Decimal("0.20")


def test_custo_real_cadastrado_depois_substitui_estimativa_sem_mudar_snapshot():
    produto = SimpleNamespace(preco_custo=Decimal("25"))
    item = SimpleNamespace(quantidade=Decimal("2"), produto_id=10, produto=produto)
    venda = SimpleNamespace(itens=[item])
    snapshot_original = {
        "custo_produtos": 0,
        "itens": [{"custo_total": 0, "custo_unitario": 0}],
    }

    ajustado = _complementar_snapshot_com_custos_reais(venda, snapshot_original, {})

    assert ajustado["custo_produtos"] == 50.0
    assert ajustado["itens"][0]["custo_total"] == 50.0
    assert ajustado["itens"][0]["custo_origem_complemento_dre"] == "cadastro_produto"
    assert snapshot_original["custo_produtos"] == 0
    assert snapshot_original["itens"][0]["custo_total"] == 0
    assert produto.preco_custo == Decimal("25")


def test_dre_prefere_comprovante_original_apos_reprocessamento_com_itens_invertidos(
    monkeypatch,
):
    monkeypatch.setattr(
        devolucao_dre,
        "resolver_tenant_estoque_item",
        lambda *_args: ("tenant", False),
    )

    def item(item_id, custo):
        return SimpleNamespace(
            id=item_id,
            venda_id=123,
            tipo="produto",
            produto_id=11,
            quantidade=1,
            preco_unitario=50,
            custo_original_saida={
                "versao": 1,
                "origem": "baixa_estoque_venda",
                "venda_id": 123,
                "venda_item_id": item_id,
                "produto_id": 11,
                "movimentacao_id": item_id + 100,
                "tenant_estoque_id": "tenant",
                "quantidade": "1",
                "custo_total": custo,
            },
        )

    venda = SimpleNamespace(id=123, itens=[item(7, "5.00"), item(8, "12.50")])
    snapshot = {
        "custo_produtos": 70.0,
        "itens": [
            {
                "venda_item_id": 8,
                "produto_id": 11,
                "quantidade": 1,
                "preco_unitario": 50,
                "custo_total": 40,
            },
            {
                "venda_item_id": 7,
                "produto_id": 11,
                "quantidade": 1,
                "preco_unitario": 50,
                "custo_total": 30,
            },
        ],
    }

    ajustado = _complementar_snapshot_com_custos_reais(venda, snapshot, {}, "tenant")

    assert ajustado["custo_produtos"] == 17.5
    assert [item["custo_total"] for item in ajustado["itens"]] == [12.5, 5.0]
    assert snapshot["custo_produtos"] == 70.0


def test_cmv_reconstroi_total_zerado_quando_itens_ja_tem_custo():
    item = SimpleNamespace(quantidade=Decimal("2"), produto_id=10, produto=None)
    venda = SimpleNamespace(itens=[item])
    snapshot_original = {
        "custo_produtos": 0,
        "itens": [{"custo_total": 145.98, "custo_unitario": 72.99}],
    }

    ajustado = _complementar_snapshot_com_custos_reais(venda, snapshot_original, {})

    assert ajustado["custo_produtos"] == 145.98
    assert snapshot_original["custo_produtos"] == 0


def test_cmv_preserva_total_quando_itens_antigos_nao_tem_custo():
    item = SimpleNamespace(quantidade=Decimal("1"), produto_id=10, produto=None)
    venda = SimpleNamespace(itens=[item])
    snapshot_original = {"custo_produtos": 72.99, "itens": [{"custo_total": 0}]}

    assert (
        _complementar_snapshot_com_custos_reais(venda, snapshot_original, {})
        is snapshot_original
    )


def test_total_legado_sem_custo_por_item_nao_soma_outra_estimativa():
    item = _item_legado(7, 11, 1, 100, 100)
    item.produto.preco_custo = Decimal("80")
    venda = SimpleNamespace(id=123, itens=[item], data_venda=datetime(2026, 10, 1))
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
    assert _complementar_snapshot_com_custos_reais(venda, snapshot, {}) is snapshot
    dados = {"loja_fisica": _novo_canal()}
    bases, pendencias = {}, {}

    _registrar_base_estimativa_cmv(
        venda,
        "loja_fisica",
        snapshot,
        bases,
        pendencias,
        dados["loja_fisica"]["itens_cmv_atribuido"],
    )
    _aplicar_estimativas_cmv(dados, bases, pendencias)

    assert pendencias["loja_fisica"] == []
    assert dados["loja_fisica"]["cmv_estimado"] == 0
    assert dados["loja_fisica"]["itens_cmv_atribuido"][0]["valor_cmv_atribuido"] == 40.0
    assert _montar_alertas_cmv_estimado(dados)[0]["codigo"] == "cmv_rateio_ambiguo"


def test_total_legado_rateia_centavos_entre_duas_linhas_sem_custo():
    itens = [_item_legado(7, 11, 1, 50, 50), _item_legado(8, 12, 1, 50, 50)]
    venda = SimpleNamespace(id=123, itens=itens, data_venda=datetime(2026, 10, 1))
    snapshot = {
        "custo_produtos": 0.03,
        "itens": [
            {"produto_id": 11, "quantidade": 1, "preco_unitario": 50, "custo_total": 0},
            {"produto_id": 12, "quantidade": 1, "preco_unitario": 50, "custo_total": 0},
        ],
    }
    dados = {"loja_fisica": _novo_canal()}

    _registrar_base_estimativa_cmv(
        venda,
        "loja_fisica",
        snapshot,
        {},
        {},
        dados["loja_fisica"]["itens_cmv_atribuido"],
    )

    assert [
        item["valor_cmv_atribuido"]
        for item in dados["loja_fisica"]["itens_cmv_atribuido"]
    ] == [0.02, 0.01]


def test_total_legado_misto_sem_vinculo_nao_duplica_cmv_e_exibe_alerta():
    produto = _item_legado(7, 11, 1, 100, 100)
    servico = _item_legado(8, 12, 1, 50, 50)
    servico.tipo = "servico"
    venda = SimpleNamespace(
        id=123, itens=[produto, servico], data_venda=datetime(2026, 10, 1)
    )
    snapshot = {
        "custo_produtos": 30,
        "itens": [
            {
                "produto_id": 11,
                "quantidade": 1,
                "preco_unitario": 100,
                "custo_total": 0,
            },
            {"produto_id": 12, "quantidade": 1, "preco_unitario": 50, "custo_total": 0},
        ],
    }
    dados = {"loja_fisica": _novo_canal()}
    bases, pendencias = {}, {}

    _registrar_base_estimativa_cmv(
        venda,
        "loja_fisica",
        snapshot,
        bases,
        pendencias,
        dados["loja_fisica"]["itens_cmv_atribuido"],
    )
    _aplicar_estimativas_cmv(dados, bases, pendencias)

    assert pendencias["loja_fisica"] == []
    assert dados["loja_fisica"]["cmv_estimado"] == 0
    alertas = _montar_alertas_cmv_estimado(dados)
    assert alertas[0]["codigo"] == "cmv_agregado_sem_rateio"
    assert alertas[0]["valor_sem_rateio"] == 30.0
    assert DREAlerta(**alertas[0]).valor_sem_rateio == 30.0


def test_custo_agregado_de_servico_nao_gera_alerta_de_cmv_produto():
    servico = _item_legado(7, 11, 1, 100, 100)
    servico.tipo = "servico"
    venda = SimpleNamespace(id=123, itens=[servico])
    snapshot = {
        "custo_produtos": 30,
        "itens": [
            {"produto_id": 11, "quantidade": 1, "preco_unitario": 100, "custo_total": 0}
        ],
    }
    dados = {"loja_fisica": _novo_canal()}

    _registrar_base_estimativa_cmv(
        venda,
        "loja_fisica",
        snapshot,
        {},
        {},
        dados["loja_fisica"]["itens_cmv_atribuido"],
    )

    assert dados["loja_fisica"]["itens_cmv_atribuido"] == []
    assert _montar_alertas_cmv_estimado(dados) == []


def test_cmv_preserva_total_quando_snapshot_tem_menos_itens():
    item = SimpleNamespace(quantidade=Decimal("1"), produto_id=10, produto=None)
    venda = SimpleNamespace(itens=[item, item])
    snapshot_original = {"custo_produtos": 72.99, "itens": [{"custo_total": 0}]}

    assert (
        _complementar_snapshot_com_custos_reais(venda, snapshot_original, {})
        is snapshot_original
    )


def test_cmv_total_inclui_parcela_provisoria_de_forma_transparente():
    canal = _novo_canal()
    canal["receita_produtos"] = Decimal("200")
    canal["cmv"] = Decimal("60")
    canal["cmv_estimado"] = Decimal("20")
    canal["fretes_compras"] = Decimal("10")

    linhas, totais = montar_linhas_dre_competencia({"loja_fisica": canal})

    assert totais["cmv"] == pytest.approx(90.0)
    linha_estimativa = next(linha for linha in linhas if linha.campo == "cmv_estimado")
    assert linha_estimativa.valor == pytest.approx(20.0)
    assert linha_estimativa.detalhavel is True


def test_snapshot_com_campanha_fantasma_usa_ledger_sem_recalcular_cmv():
    snapshot = {
        "custo_campanha": 4.0,
        "custo_produtos": 40.0,
        "imposto": 7.3,
        "itens": [{"custo_total": 40.0}],
    }

    ajustado = _conciliar_custo_campanha_snapshot(snapshot, 0, 0, 0)

    assert ajustado["custo_campanha"] == 0.0
    assert ajustado["custo_produtos"] == 40.0
    assert ajustado["imposto"] == 7.3
    assert ajustado["itens"] is snapshot["itens"]
    assert snapshot["custo_campanha"] == 4.0


def test_falha_na_consulta_de_campanha_interrompe_dre_sem_zerar_custo():
    db = MagicMock()
    db.query.side_effect = RuntimeError("ledger indisponivel")
    venda = SimpleNamespace(id=11, cupom_discount_applied=0)

    with pytest.raises(RuntimeError, match="ledger indisponivel"):
        _bulk_cashback_por_venda(db, "tenant", [11])
    with pytest.raises(RuntimeError, match="ledger indisponivel"):
        _bulk_cupons_por_venda(db, "tenant", [venda])


def test_cupom_legado_anulado_reclassifica_desconto_sem_gerar_lucro():
    snapshot = {
        "venda_bruta": 100.0,
        "desconto": 0.0,
        "cupom_desconto": 20.0,
        "custo_campanha": 20.0,
        "custo_produtos": 0.0,
        "imposto": 0.0,
    }

    ajustado = _conciliar_custo_campanha_snapshot(snapshot, 0, 0, 20)
    canal = _novo_canal()
    canal["receita_produtos"] = Decimal(str(ajustado["venda_bruta"]))
    canal["descontos"] = Decimal(str(ajustado["desconto"]))
    canal["campanhas"] = Decimal(str(ajustado["custo_campanha"]))
    canal["devolucoes"] = Decimal("80")
    _, totais = montar_linhas_dre_competencia({"loja_fisica": canal})

    assert ajustado["desconto"] == 20.0
    assert ajustado["custo_campanha"] == 0.0
    assert totais["lucro_bruto"] == 0.0
    assert snapshot["desconto"] == 0.0


def test_alerta_identifica_produtos_e_valores_afetados():
    canal = _novo_canal()
    canal["cmv_estimado"] = Decimal("45")
    canal["percentual_cmv_estimado"] = Decimal("60")
    canal["origem_percentual_cmv_estimado"] = "mesmo_canal"
    canal["itens_cmv_estimado"] = [
        {"produto_id": 1, "valor_venda": 50},
        {"produto_id": 1, "valor_venda": 25},
    ]

    alertas = _montar_alertas_cmv_estimado({"loja_fisica": canal})

    assert len(alertas) == 1
    assert alertas[0]["quantidade_produtos"] == 1
    assert alertas[0]["quantidade_itens"] == 2
    assert alertas[0]["valor_vendas"] == pytest.approx(75.0)
    assert alertas[0]["valor_estimado"] == pytest.approx(45.0)
    assert alertas[0]["sem_base_estimativa"] is False
