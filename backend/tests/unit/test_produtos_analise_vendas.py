from datetime import datetime

from app.produtos.relatorios_analise_routes import (
    _aplicar_curva_abc,
    _preencher_evolucao,
    _variacao_percentual,
)


def test_curva_abc_mantem_primeiro_item_na_classe_a_ao_cruzar_80_por_cento():
    produtos = [
        {"produto_id": 1, "faturamento": 900},
        {"produto_id": 2, "faturamento": 60},
        {"produto_id": 3, "faturamento": 40},
    ]

    _aplicar_curva_abc(produtos, "faturamento", "faturamento")

    assert produtos[0]["abc_faturamento"] == "A"
    assert produtos[0]["acumulado_faturamento_pct"] == 90
    assert produtos[1]["abc_faturamento"] == "B"
    assert produtos[2]["abc_faturamento"] == "C"


def test_curva_abc_sem_resultado_classifica_como_c():
    produtos = [{"produto_id": 1, "quantidade": 0}]

    _aplicar_curva_abc(produtos, "quantidade", "quantidade")

    assert produtos[0]["abc_quantidade"] == "C"
    assert produtos[0]["acumulado_quantidade_pct"] == 0


def test_evolucao_preenche_dias_sem_venda():
    inicio = datetime(2026, 9, 1)
    fim = datetime(2026, 9, 3, 23, 59, 59)

    resultado = _preencher_evolucao(
        inicio,
        fim,
        [{"data": "2026-09-02", "faturamento": 50, "quantidade": 2}],
    )

    assert [item["data"] for item in resultado] == [
        "2026-09-01",
        "2026-09-02",
        "2026-09-03",
    ]
    assert resultado[0]["faturamento"] == 0
    assert resultado[1]["faturamento"] == 50


def test_variacao_percentual_sinaliza_quando_nao_existe_base():
    assert _variacao_percentual(10, 0) is None
    assert _variacao_percentual(0, 0) == 0
    assert _variacao_percentual(120, 100) == 20
