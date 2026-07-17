from collections import defaultdict
from datetime import datetime, timedelta, timezone
import importlib
import importlib.util
from math import inf, nan
from types import SimpleNamespace

from sqlalchemy import Boolean, Column, Integer, MetaData, Table, create_engine, select

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

    assert (
        tuple(int(chave) for chave in stats["janelas"].keys()) == JANELAS_GIRO_SUGESTAO
    )
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


def test_montar_resultado_vendas_sugestao_arredonda_ordena_e_filtra_granel():
    stats_por_produto = defaultdict(_nova_stats_venda_sugestao)
    stats = stats_por_produto[10]
    stats["vendas_periodo"] = 3.4567
    stats["janelas"]["7"] = 1.2345
    stats["origens"]["Loja"] = 2.2222
    stats["origens"]["Bling/online"] = 3.3333
    stats["origens"]["Sem venda"] = 0
    stats["fontes"].update({"vendas", "estoque_externo"})
    stats["granel_kg_periodo"] = 7.8912
    stats["granel_pacotes_periodo"] = 2.3456
    stats["granel_janelas_kg"]["7"] = 4.4444
    stats["granel_janelas_pacotes"]["7"] = 1.1111
    stats["granel_itens"][99].update(
        {
            "produto_id": 99,
            "produto_nome": "Racao granel menor",
            "peso_pacote_kg": 1.2345,
            "kg": 3.4567,
            "pacotes": 2.2222,
        }
    )
    stats["granel_itens"][77].update(
        {
            "produto_id": 77,
            "produto_nome": "Racao granel maior",
            "peso_pacote_kg": 2,
            "kg": 5.1111,
            "pacotes": 1,
        }
    )
    stats["granel_itens"][88].update(
        {
            "produto_id": 88,
            "produto_nome": "Sem consumo",
            "kg": 0,
            "pacotes": 0,
        }
    )

    assert hasattr(sugestao_helpers, "_montar_resultado_vendas_sugestao")

    resultado = sugestao_helpers._montar_resultado_vendas_sugestao(stats_por_produto)

    assert resultado[10]["vendas_periodo"] == 3.457
    assert resultado[10]["janelas"] == {
        "7": 1.234,
        "15": 0.0,
        "30": 0.0,
        "60": 0.0,
        "90": 0.0,
    }
    assert resultado[10]["origens"] == [
        {"canal": "Bling/online", "quantidade": 3.333},
        {"canal": "Loja", "quantidade": 2.222},
    ]
    assert resultado[10]["fontes"] == ["estoque_externo", "vendas"]
    granel = resultado[10]["granel_consumo"]
    assert granel["kg_periodo"] == 7.891
    assert granel["pacotes_equivalentes_periodo"] == 2.346
    assert granel["janelas_kg"]["7"] == 4.444
    assert granel["janelas_pacotes"]["7"] == 1.111
    assert granel["itens"] == [
        {
            "produto_id": 77,
            "produto_nome": "Racao granel maior",
            "peso_pacote_kg": 2.0,
            "kg": 5.111,
            "pacotes_equivalentes": 1.0,
        },
        {
            "produto_id": 99,
            "produto_nome": "Racao granel menor",
            "peso_pacote_kg": 1.234,
            "kg": 3.457,
            "pacotes_equivalentes": 2.222,
        },
    ]


def test_calcular_dias_com_estoque_conta_intervalos_com_ruptura():
    data_inicio = datetime(2026, 6, 1)
    data_fim = datetime(2026, 6, 11)

    assert hasattr(sugestao_helpers, "_calcular_dias_com_estoque")

    resultado = sugestao_helpers._calcular_dias_com_estoque(
        movimentacoes=[
            SimpleNamespace(
                created_at=datetime(2026, 6, 3),
                tipo="saida",
                quantidade=2,
                quantidade_anterior=2,
                quantidade_nova=0,
            ),
            SimpleNamespace(
                created_at=datetime(2026, 6, 6),
                tipo="entrada",
                quantidade=5,
                quantidade_anterior=0,
                quantidade_nova=5,
            ),
            SimpleNamespace(
                created_at=datetime(2026, 6, 8),
                tipo="saida",
                quantidade=5,
                quantidade_anterior=5,
                quantidade_nova=0,
            ),
        ],
        estoque_atual=0,
        data_inicio=data_inicio,
        data_fim=data_fim,
    )

    assert resultado == {
        "dias_com_estoque": 4.0,
        "dias_sem_estoque": 6.0,
        "teve_ruptura": True,
        "ruptura_ativa": True,
    }


def test_gerar_observacao_combina_ruptura_tendencia_e_fallback():
    assert hasattr(sugestao_helpers, "_gerar_observacao")

    observacao = sugestao_helpers._gerar_observacao(
        prioridade="NORMAL",
        dias_estoque=0,
        tendencia="CRESCIMENTO",
        consumo_diario=0,
        ruptura_ativa=True,
    )

    assert observacao == (
        "Ruptura ativa: estoque zerado/negativo | "
        "Vendas em crescimento | "
        "Sem vendas no periodo analisado"
    )
    assert (
        sugestao_helpers._gerar_observacao(
            prioridade="NORMAL",
            dias_estoque=30,
            tendencia="ESTAVEL",
            consumo_diario=1,
        )
        == "Estoque adequado"
    )


def test_calcular_planejamento_compra_sugestao_aplica_ruptura_e_prioridade():
    assert hasattr(sugestao_helpers, "_calcular_planejamento_compra_sugestao")

    resultado = sugestao_helpers._calcular_planejamento_compra_sugestao(
        vendas_periodo=20,
        vendas_30=0,
        periodo_dias=30,
        estoque_atual=0,
        estoque_minimo=1,
        dias_com_estoque=10,
        dias_cobertura=30,
        lead_time=7,
        ruptura_ativa=True,
        teve_ruptura=True,
    )

    assert round(resultado["consumo_observado"], 3) == 0.667
    assert round(resultado["consumo_ajustado"], 3) == 1.333
    assert resultado["ajuste_ruptura_aplicado"] is True
    assert (
        resultado["motivo_ajuste_ruptura"]
        == "Media ajustada por ruptura, limitada a 2x o giro observado."
    )
    assert round(resultado["consumo_diario"], 3) == 1.333
    assert resultado["dias_estoque"] == 0
    assert resultado["dias_reposicao"] == 14.0
    assert resultado["lead_time_incluido_no_alvo"] is True
    assert resultado["dias_total_cobertura"] == 44.0
    assert round(resultado["quantidade_sugerida"], 3) == 58.667
    assert resultado["prioridade"] == "CR\u00cdTICO"


def test_montar_item_sugestao_compra_preserva_payload_operacional():
    assert hasattr(sugestao_helpers, "_montar_item_sugestao_compra")

    produto = SimpleNamespace(
        id=10,
        nome="Racao Premium",
        codigo="SKU-10",
        codigo_barras="789",
        marca_id=5,
        itens_por_caixa=None,
        peso_embalagem=None,
        peso_bruto=12.5,
        peso_liquido=11.0,
    )
    produto_fornecedor = SimpleNamespace(fornecedor_id=20)
    marca = SimpleNamespace(nome="Marca Boa")
    fornecedor_grupo = SimpleNamespace(id=30, nome="Grupo Fornecedor")
    vendas_janelas = {"7": 1.2345, "15": 2, "30": 3, "60": 4, "90": 5}
    vendas_stats = {
        "origens": [{"canal": "Loja", "quantidade": 3}],
        "fontes": ["vendas"],
        "granel_consumo": {"kg_periodo": 2.5},
    }
    planejamento = {
        "consumo_observado": 1.2345,
        "consumo_ajustado": 1.9876,
        "consumo_base": 1.4567,
        "consumo_diario": 1.9876,
        "dias_estoque": 2.26,
        "ajuste_ruptura_aplicado": True,
        "motivo_ajuste_ruptura": "Media ajustada pelos dias em que havia estoque.",
        "margem_seguranca_dias": 7,
        "dias_reposicao": 14.25,
        "lead_time_incluido_no_alvo": True,
        "dias_total_cobertura": 44.25,
        "estoque_para_calculo": 2.3456,
        "quantidade_sugerida": 9.8765,
        "prioridade": "CR\u00cdTICO",
    }

    item = sugestao_helpers._montar_item_sugestao_compra(
        produto=produto,
        produto_fornecedor=produto_fornecedor,
        marca=marca,
        fornecedor_grupo=fornecedor_grupo,
        fornecedores_por_id={20: "Fornecedor A"},
        estoque_info={
            "estoque_derivado": True,
            "tipo_produto": "kit",
            "tipo_kit": "virtual",
        },
        vendas_stats=vendas_stats,
        vendas_janelas=vendas_janelas,
        vendas_periodo=12.5,
        estoque_atual=2.3456,
        estoque_minimo=4,
        dias_com_estoque=10.5,
        dias_sem_estoque=3.5,
        teve_ruptura=True,
        ruptura_ativa=False,
        lead_time=7.25,
        dias_cobertura=30,
        planejamento=planejamento,
        tendencia="CRESCIMENTO",
        preco_unitario=12.345,
        valor_sugestao=121.9253925,
    )

    assert item["produto_id"] == 10
    assert item["fornecedor_nome"] == "Fornecedor A"
    assert item["fornecedor_grupo_nome"] == "Grupo Fornecedor"
    assert item["marca_nome"] == "Marca Boa"
    assert item["consumo_diario"] == 1.99
    assert item["consumo_diario_observado"] == 1.234
    assert item["consumo_diario_ajustado"] == 1.988
    assert item["consumo_diario_base"] == 1.457
    assert item["vendas_7d"] == 1.2345
    assert item["dias_estoque"] == 2.3
    assert item["ruptura_ajuste_aplicado"] is True
    assert item["lead_time"] == 7.25
    assert item["dias_planejamento"] == 30.0
    assert item["dias_reposicao"] == 14.2
    assert item["estoque_para_calculo"] == 2.346
    assert item["quantidade_sugerida"] == 9.88
    assert item["preco_unitario"] == 12.345
    assert item["valor_total"] == 121.93
    assert item["peso_bruto"] == 12.5
    assert item["estoque_derivado"] is True
    assert item["prioridade"] == "CR\u00cdTICO"
    assert item["observacao"].startswith("Urgente: estoque cobre menos de 3 dias")


def test_montar_item_sugestao_compra_converte_quantidade_por_embalagem_historica():
    produto = SimpleNamespace(
        id=11,
        nome="Sache Frango",
        codigo="SKU-11",
        codigo_barras="78911",
        marca_id=None,
        itens_por_caixa=12,
        peso_embalagem=None,
        peso_bruto=None,
        peso_liquido=None,
    )
    produto_fornecedor = SimpleNamespace(fornecedor_id=20)
    planejamento = {
        "consumo_observado": 4,
        "consumo_ajustado": 4,
        "consumo_base": 4,
        "consumo_diario": 4,
        "dias_estoque": 1,
        "ajuste_ruptura_aplicado": False,
        "motivo_ajuste_ruptura": None,
        "margem_seguranca_dias": 7,
        "dias_reposicao": 7,
        "lead_time_incluido_no_alvo": True,
        "dias_total_cobertura": 42,
        "estoque_para_calculo": 0,
        "quantidade_sugerida": 168,
        "prioridade": "CR\u00cdTICO",
    }

    item = sugestao_helpers._montar_item_sugestao_compra(
        produto=produto,
        produto_fornecedor=produto_fornecedor,
        marca=None,
        fornecedor_grupo=None,
        fornecedores_por_id={20: "Fornecedor A"},
        estoque_info={},
        vendas_stats={},
        vendas_janelas={},
        vendas_periodo=168,
        estoque_atual=0,
        estoque_minimo=0,
        dias_com_estoque=90,
        dias_sem_estoque=0,
        teve_ruptura=False,
        ruptura_ativa=True,
        lead_time=7,
        dias_cobertura=30,
        planejamento=planejamento,
        tendencia="EST\u00c1VEL",
        preco_unitario=3,
        valor_sugestao=504,
        embalagem_historica={"unidade_compra": "CX", "quantidade_por_embalagem": 12},
    )

    assert item["unidade_compra_sugerida"] == "CX"
    assert item["quantidade_por_embalagem_sugerida"] == 12
    assert item["quantidade_compra_sugerida"] == 14
    assert item["quantidade_total_unidades_sugerida"] == 168
    assert item["embalagem_sugestao_origem"] == "historico"


def test_selecionar_produtos_fornecedor_sugestao_deduplica_por_prioridade():
    assert hasattr(sugestao_helpers, "_selecionar_produtos_fornecedor_sugestao")

    produto_10 = SimpleNamespace(id=10, fornecedor_id=99)
    produto_11 = SimpleNamespace(id=11, fornecedor_id=31)
    marca_a = SimpleNamespace(nome="Marca A")
    marca_b = SimpleNamespace(nome="Marca B")
    linha_selecionada = (
        produto_10,
        SimpleNamespace(
            id=3,
            fornecedor_id=20,
            e_principal=False,
            preco_custo=50,
        ),
        marca_a,
    )
    linha_principal = (
        produto_10,
        SimpleNamespace(
            id=2,
            fornecedor_id=21,
            e_principal=True,
            preco_custo=10,
        ),
        marca_b,
    )
    linha_produto_11_principal = (
        produto_11,
        SimpleNamespace(
            id=4,
            fornecedor_id=30,
            e_principal=True,
            preco_custo=80,
        ),
        marca_a,
    )
    linha_produto_11_fornecedor_produto = (
        produto_11,
        SimpleNamespace(
            id=5,
            fornecedor_id=31,
            e_principal=False,
            preco_custo=20,
        ),
        marca_b,
    )

    selecionados = sugestao_helpers._selecionar_produtos_fornecedor_sugestao(
        [
            linha_principal,
            linha_selecionada,
            linha_produto_11_fornecedor_produto,
            linha_produto_11_principal,
        ],
        fornecedor_id=20,
    )

    por_produto = {
        produto.id: (produto_fornecedor, marca)
        for produto, produto_fornecedor, marca in selecionados
    }
    assert len(selecionados) == 2
    assert por_produto[10][0].fornecedor_id == 20
    assert por_produto[10][1].nome == "Marca A"
    assert por_produto[11][0].fornecedor_id == 30
    assert por_produto[11][1].nome == "Marca A"


def test_montar_resposta_sugestao_compra_ordena_resume_e_sanitiza():
    assert hasattr(sugestao_helpers, "_montar_resposta_sugestao_compra")

    fornecedor = SimpleNamespace(id=20, nome="Fornecedor A")
    fornecedor_grupo = SimpleNamespace(id=30, nome="Grupo A")
    data_inicio = datetime(2026, 6, 1, 8, 30)
    data_fim = datetime(2026, 6, 23, 9, 45)
    sugestoes = [
        {"produto_id": 1, "prioridade": "NORMAL", "valor_total": 100.0},
        {"produto_id": 2, "prioridade": "ATEN\u00c7\u00c3O", "valor_total": 200.0},
        {"produto_id": 3, "prioridade": "CR\u00cdTICO", "valor_total": 50.0},
        {"produto_id": 4, "prioridade": "CR\u00cdTICO", "valor_total": 150.0},
        {"produto_id": 5, "prioridade": "ALERTA", "valor_total": inf},
    ]

    resposta = sugestao_helpers._montar_resposta_sugestao_compra(
        fornecedor=fornecedor,
        fornecedor_ids=[20, 21],
        fornecedor_grupo=fornecedor_grupo,
        periodo_dias=90,
        dias_cobertura=30,
        apenas_fornecedor_principal=True,
        data_inicio=data_inicio,
        data_fim=data_fim,
        sugestoes=sugestoes,
        total_criticos=2,
        total_alerta=1,
        valor_total=500.555,
    )

    assert resposta["fornecedor"] == {
        "id": 20,
        "nome": "Fornecedor A",
        "ids_considerados": [20, 21],
        "grupo": {"id": 30, "nome": "Grupo A"},
    }
    assert resposta["periodo_dias"] == 90
    assert resposta["dias_cobertura"] == 30
    assert resposta["apenas_fornecedor_principal"] is True
    assert resposta["data_analise_inicio"] == "2026-06-01T08:30:00"
    assert resposta["data_analise_fim"] == "2026-06-23T09:45:00"
    assert [item["produto_id"] for item in resposta["sugestoes"]] == [4, 3, 5, 2, 1]
    assert resposta["sugestoes"][2]["valor_total"] == 0.0
    assert resposta["resumo"] == {
        "total_produtos": 5,
        "produtos_criticos": 2,
        "produtos_alerta": 1,
        "produtos_atencao": 1,
        "valor_total_estimado": 500.56,
    }


def test_sugestao_queries_basicas_sem_consulta_ao_banco():
    spec = importlib.util.find_spec("app.pedidos_compra.sugestao_queries")
    assert spec is not None
    sugestao_queries = importlib.import_module("app.pedidos_compra.sugestao_queries")

    class DbBloqueado:
        def query(self, *_args, **_kwargs):
            raise AssertionError("nao deveria consultar o banco")

    db = DbBloqueado()
    fornecedor = SimpleNamespace(id=20, fornecedor_grupo_id=None)
    data_ref = datetime(2026, 6, 23, 12, 0)
    produto = SimpleNamespace(
        id=10,
        estoque_atual="3.5",
        tipo_produto="PRODUTO",
        tipo_kit=None,
    )

    assert sugestao_queries._resolver_fornecedores_compra(
        db,
        tenant_id=1,
        fornecedor=fornecedor,
    ) == ([20], None)
    assert (
        sugestao_queries._carregar_vendas_sugestao(
            db,
            tenant_id=1,
            produto_ids=[],
            periodo_dias=30,
            data_fim=data_ref,
        )
        == {}
    )
    assert (
        sugestao_queries._agrupar_movimentacoes_estoque_periodo(
            db,
            tenant_id=1,
            produto_ids=[],
            data_inicio=data_ref - timedelta(days=30),
            data_fim=data_ref,
        )
        == {}
    )
    assert sugestao_queries._obter_estoque_atual_sugestao(db, produto, 1) == (
        3.5,
        {
            "estoque_derivado": False,
            "tipo_produto": "PRODUTO",
            "tipo_kit": None,
        },
    )


def test_filtro_ativo_sugestao_inclui_cadastro_legado_sem_flag():
    sugestao_queries = importlib.import_module("app.pedidos_compra.sugestao_queries")
    metadata = MetaData()
    produtos = Table(
        "produtos_teste_sugestao",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("ativo", Boolean, nullable=True),
    )
    engine = create_engine("sqlite:///:memory:")
    metadata.create_all(engine)

    with engine.begin() as conn:
        conn.execute(
            produtos.insert(),
            [
                {"id": 1, "ativo": True},
                {"id": 2, "ativo": None},
                {"id": 3, "ativo": False},
            ],
        )
        ids = (
            conn.execute(
                select(produtos.c.id)
                .where(
                    sugestao_queries._filtro_ativo_ou_legado_sugestao(produtos.c.ativo)
                )
                .order_by(produtos.c.id)
            )
            .scalars()
            .all()
        )

    assert ids == [1, 2]


def test_expandir_fornecedores_do_grupo_inclui_alias_legado_sem_cnpj():
    sugestao_queries = importlib.import_module("app.pedidos_compra.sugestao_queries")
    special_dog = SimpleNamespace(
        id=10149,
        nome="SPECIAL DOG PET FOOD LTDA",
        razao_social="SPECIAL DOG PET FOOD LTDA",
        cnpj="63.287.129/0004-95",
    )
    manfrim = SimpleNamespace(
        id=10013,
        nome="MANFRIM INDUSTRIAL E COMERCIAL LTDA",
        razao_social="MANFRIM INDUSTRIAL E COMERCIAL LTDA",
        cnpj="56.813.280/0002-92",
    )
    alias_legado = SimpleNamespace(
        id=10091,
        nome="Special Dog Pet Food Ltda.",
        razao_social="SPECIAL DOG PET FOOD LTDA",
        cnpj=None,
    )
    homonimo_outro_cnpj = SimpleNamespace(
        id=10200,
        nome="SPECIAL DOG PET FOOD LTDA",
        razao_social="SPECIAL DOG PET FOOD LTDA",
        cnpj="11.111.111/0001-11",
    )

    ids = sugestao_queries._expandir_ids_fornecedores_equivalentes(
        [special_dog, manfrim],
        [special_dog, manfrim, alias_legado, homonimo_outro_cnpj],
    )

    assert ids == {10013, 10091, 10149}


def test_calcular_tendencia_vendas_sugestao_respeita_periodo_e_limiares():
    assert hasattr(sugestao_helpers, "_calcular_tendencia_vendas_sugestao")

    assert (
        sugestao_helpers._calcular_tendencia_vendas_sugestao(
            periodo_dias=30,
            consumo_observado=2,
            consumo_recente=5,
        )
        == "N/A"
    )
    assert (
        sugestao_helpers._calcular_tendencia_vendas_sugestao(
            periodo_dias=60,
            consumo_observado=10,
            consumo_recente=13,
        )
        == "CRESCIMENTO"
    )
    assert (
        sugestao_helpers._calcular_tendencia_vendas_sugestao(
            periodo_dias=60,
            consumo_observado=10,
            consumo_recente=7,
        )
        == "QUEDA"
    )
    assert (
        sugestao_helpers._calcular_tendencia_vendas_sugestao(
            periodo_dias=60,
            consumo_observado=10,
            consumo_recente=10,
        )
        == "EST\u00c1VEL"
    )
