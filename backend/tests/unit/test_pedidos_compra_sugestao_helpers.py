from collections import defaultdict
from datetime import datetime, timedelta, timezone
from math import inf, nan
from types import SimpleNamespace

from app.pedidos_compra import sugestao as sugestao_helpers
from app.pedidos_compra.sugestao import (
    JANELAS_GIRO_SUGESTAO,
    _somar_conversao_granel_sugestao,
    _somar_venda_sugestao,
    _datetime_naive_utc_sugestao,
    _float_seguro_sugestao,
    _formatar_origem_venda,
    _nova_stats_venda_sugestao,
    _round_seguro_sugestao,
    _sanitizar_json_sugestao,
)


def test_float_seguro_sugestao_rejeita_valores_invalidos_e_infinitos():
    assert _float_seguro_sugestao("12.5") == 12.5
    assert _float_seguro_sugestao(None, padrao=7.0) == 7.0
    assert _float_seguro_sugestao(inf, padrao=3.0) == 3.0
    assert _float_seguro_sugestao(nan, padrao=2.0) == 2.0


def test_round_seguro_sugestao_usa_float_seguro():
    assert _round_seguro_sugestao("12.345", casas=2) == 12.35
    assert _round_seguro_sugestao("abc", padrao=4.321) == 4.32


def test_sanitizar_json_sugestao_limpa_float_em_estrutura_aninhada():
    payload = {
        "valor": inf,
        "itens": [{"ok": 1.5}, {"ruim": nan}],
    }

    assert _sanitizar_json_sugestao(payload) == {
        "valor": 0.0,
        "itens": [{"ok": 1.5}, {"ruim": 0.0}],
    }


def test_datetime_naive_utc_sugestao_remove_timezone_convertendo_para_utc():
    data = datetime(2026, 6, 23, 12, 30, tzinfo=timezone.utc)

    resultado = _datetime_naive_utc_sugestao(data)

    assert resultado == datetime(2026, 6, 23, 12, 30)
    assert resultado.tzinfo is None


def test_formatar_origem_venda_preserva_nomes_operacionais():
    assert _formatar_origem_venda(None) == "Loja"
    assert _formatar_origem_venda("venda_bling") == "Bling/online"
    assert _formatar_origem_venda("kit_virtual") == "Granel/kit"
    assert _formatar_origem_venda("marketplace_especial") == "Marketplace Especial"


def test_nova_stats_venda_sugestao_monta_janelas_e_colecoes_mutaveis():
    stats = _nova_stats_venda_sugestao()

    assert tuple(int(chave) for chave in stats["janelas"].keys()) == JANELAS_GIRO_SUGESTAO
    assert stats["origens"]["Loja"] == 0.0
    assert stats["granel_itens"][10] == {"kg": 0.0, "pacotes": 0.0}
    assert stats["fontes"] == set()


def test_somar_venda_sugestao_acumula_periodo_janelas_origem_e_fonte():
    stats_por_produto = defaultdict(_nova_stats_venda_sugestao)
    data_fim = datetime(2026, 6, 23, 12, 0)
    data_ref = data_fim - timedelta(days=5)

    _somar_venda_sugestao(
        stats_por_produto,
        produto_id=10,
        quantidade="3.5",
        data_ref=data_ref,
        data_inicio_periodo=data_fim - timedelta(days=30),
        data_fim=data_fim,
        origem="venda_bling",
        fonte="venda_interna",
    )

    stats = stats_por_produto[10]
    assert stats["vendas_periodo"] == 3.5
    assert stats["janelas"]["7"] == 3.5
    assert stats["janelas"]["15"] == 3.5
    assert stats["janelas"]["30"] == 3.5
    assert stats["janelas"]["60"] == 3.5
    assert stats["janelas"]["90"] == 3.5
    assert stats["origens"]["Bling/online"] == 3.5
    assert stats["fontes"] == {"venda_interna"}


def test_somar_conversao_granel_sugestao_acumula_pacotes_e_quilos():
    stats_por_produto = defaultdict(_nova_stats_venda_sugestao)
    data_fim = datetime(2026, 6, 23, 12, 0)
    data_ref = data_fim - timedelta(days=10)

    _somar_conversao_granel_sugestao(
        stats_por_produto,
        produto_pai_id=20,
        produto_granel_id=99,
        produto_granel_nome="Racao granel",
        quantidade_kg=4.5,
        quantidade_pacotes=3,
        peso_pacote_kg=1.5,
        data_ref=data_ref,
        data_inicio_periodo=data_fim - timedelta(days=30),
        data_fim=data_fim,
    )

    stats = stats_por_produto[20]
    assert stats["vendas_periodo"] == 3.0
    assert stats["janelas"]["7"] == 0.0
    assert stats["janelas"]["15"] == 3.0
    assert stats["granel_kg_periodo"] == 4.5
    assert stats["granel_pacotes_periodo"] == 3.0
    assert stats["granel_janelas_kg"]["15"] == 4.5
    assert stats["granel_janelas_pacotes"]["15"] == 3.0
    assert stats["origens"]["Granel"] == 3.0
    assert stats["fontes"] == {"conversao_granel"}
    assert stats["granel_itens"][99] == {
        "kg": 4.5,
        "pacotes": 3.0,
        "produto_id": 99,
        "produto_nome": "Racao granel",
        "peso_pacote_kg": 1.5,
    }


def test_somar_vendas_rows_sugestao_acumula_vendas_e_retorna_pares():
    stats_por_produto = defaultdict(_nova_stats_venda_sugestao)
    data_fim = datetime(2026, 6, 23, 12, 0)
    data_inicio_periodo = data_fim - timedelta(days=30)
    data_ref = data_fim - timedelta(days=2)

    assert hasattr(sugestao_helpers, "_somar_vendas_rows_sugestao")

    pares = sugestao_helpers._somar_vendas_rows_sugestao(
        stats_por_produto,
        produto_ids=[10],
        vendas_rows=[
            (10, 1001, "pdv", data_ref, 2),
            (10, 1002, "venda_bling", data_ref, "1.5"),
            (99, 1003, "pdv", data_ref, 8),
        ],
        data_inicio_periodo=data_inicio_periodo,
        data_fim=data_fim,
    )

    assert pares == {(1001, 10), (1002, 10), (1003, 99)}
    assert stats_por_produto[10]["pares_venda_produto"] == {(1001, 10), (1002, 10)}
    assert stats_por_produto[10]["vendas_periodo"] == 3.5
    assert stats_por_produto[10]["janelas"]["7"] == 3.5
    assert stats_por_produto[10]["origens"]["Loja"] == 2.0
    assert stats_por_produto[10]["origens"]["Bling/online"] == 1.5
    assert stats_por_produto[10]["fontes"] == {"vendas"}
    assert 99 not in stats_por_produto


def test_somar_conversoes_granel_rows_sugestao_acumula_rows_carregados():
    stats_por_produto = defaultdict(_nova_stats_venda_sugestao)
    data_fim = datetime(2026, 6, 23, 12, 0)
    data_inicio_periodo = data_fim - timedelta(days=30)
    data_ref = data_fim - timedelta(days=3)
    conversao = SimpleNamespace(
        produto_origem_id=20,
        produto_granel_id=99,
        quantidade_granel_kg=6,
        quantidade_origem=2,
        peso_por_unidade_kg=3,
        created_at=data_ref,
    )
    produto_granel = SimpleNamespace(nome="Racao a granel")

    assert hasattr(sugestao_helpers, "_somar_conversoes_granel_rows_sugestao")

    sugestao_helpers._somar_conversoes_granel_rows_sugestao(
        stats_por_produto,
        conversoes_rows=[(conversao, produto_granel)],
        data_inicio_periodo=data_inicio_periodo,
        data_fim=data_fim,
    )

    stats = stats_por_produto[20]
    assert stats["vendas_periodo"] == 2.0
    assert stats["janelas"]["7"] == 2.0
    assert stats["granel_kg_periodo"] == 6.0
    assert stats["granel_pacotes_periodo"] == 2.0
    assert stats["granel_itens"][99]["produto_nome"] == "Racao a granel"
    assert stats["granel_itens"][99]["peso_pacote_kg"] == 3.0
    assert stats["origens"]["Granel"] == 2.0
    assert stats["fontes"] == {"conversao_granel"}


def test_somar_movimentacoes_complementares_sugestao_deduplica_e_classifica_origem():
    stats_por_produto = defaultdict(_nova_stats_venda_sugestao)
    data_fim = datetime(2026, 6, 23, 12, 0)
    data_inicio_periodo = data_fim - timedelta(days=30)
    data_ref = data_fim - timedelta(days=4)

    assert hasattr(sugestao_helpers, "_somar_movimentacoes_complementares_sugestao")

    sugestao_helpers._somar_movimentacoes_complementares_sugestao(
        stats_por_produto,
        movimentos_rows=[
            SimpleNamespace(
                produto_id=10,
                referencia_id=1001,
                referencia_tipo="venda",
                motivo="venda loja",
                quantidade=2,
                created_at=data_ref,
            ),
            SimpleNamespace(
                produto_id=20,
                referencia_id=2001,
                referencia_tipo="venda",
                motivo="venda kit",
                quantidade=3,
                created_at=data_ref,
            ),
            SimpleNamespace(
                produto_id=30,
                referencia_id=3001,
                referencia_tipo="venda_bling",
                motivo="saida online",
                quantidade=4,
                created_at=data_ref,
            ),
            SimpleNamespace(
                produto_id=40,
                referencia_id=None,
                referencia_tipo="ajuste",
                motivo="inventario",
                quantidade=5,
                created_at=data_ref,
            ),
        ],
        pares_venda_produto={(1001, 10)},
        vendas_referenciadas_validas={1001, 2001},
        data_inicio_periodo=data_inicio_periodo,
        data_fim=data_fim,
    )

    assert 10 not in stats_por_produto
    assert 40 not in stats_por_produto
    assert stats_por_produto[20]["vendas_periodo"] == 3.0
    assert stats_por_produto[20]["origens"]["Granel/kit"] == 3.0
    assert stats_por_produto[20]["fontes"] == {"estoque_componentes"}
    assert stats_por_produto[30]["vendas_periodo"] == 4.0
    assert stats_por_produto[30]["origens"]["Bling/online"] == 4.0
    assert stats_por_produto[30]["fontes"] == {"estoque_externo"}
