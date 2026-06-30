from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[2]

SUGESTAO_FILES = [
    "app/pedidos_compra/sugestao.py",
    "app/pedidos_compra/sugestao_parts/__init__.py",
    "app/pedidos_compra/sugestao_parts/base.py",
    "app/pedidos_compra/sugestao_parts/itens.py",
    "app/pedidos_compra/sugestao_parts/planejamento.py",
    "app/pedidos_compra/sugestao_parts/vendas.py",
]


def _non_empty_line_count(relative_path: str) -> int:
    source = (BACKEND_ROOT / relative_path).read_text(encoding="utf-8")
    return sum(1 for line in source.splitlines() if line.strip())


def test_sugestao_compra_fachada_preserva_helpers_extraidos():
    from app.pedidos_compra import sugestao
    from app.pedidos_compra.sugestao_parts import base, itens, planejamento, vendas

    assert sugestao._float_seguro_sugestao is base._float_seguro_sugestao
    assert sugestao._nova_stats_venda_sugestao is base._nova_stats_venda_sugestao
    assert sugestao._somar_venda_sugestao is vendas._somar_venda_sugestao
    assert (
        sugestao._somar_conversao_granel_sugestao
        is vendas._somar_conversao_granel_sugestao
    )
    assert (
        sugestao._calcular_planejamento_compra_sugestao
        is planejamento._calcular_planejamento_compra_sugestao
    )
    assert sugestao._montar_item_sugestao_compra is itens._montar_item_sugestao_compra


def test_sugestao_compra_fatia_27_fica_abaixo_de_700_linhas_nao_vazias():
    oversized = {
        relative_path: _non_empty_line_count(relative_path)
        for relative_path in SUGESTAO_FILES
        if _non_empty_line_count(relative_path) > 700
    }

    assert oversized == {}
