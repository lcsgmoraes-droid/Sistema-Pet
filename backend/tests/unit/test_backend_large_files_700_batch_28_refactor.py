from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[2]

FLUXO_CAIXA_FILES = [
    "app/ia/aba5_fluxo_caixa.py",
    "app/ia/aba5_fluxo_caixa_parts/__init__.py",
    "app/ia/aba5_fluxo_caixa_parts/acoes.py",
    "app/ia/aba5_fluxo_caixa_parts/base.py",
    "app/ia/aba5_fluxo_caixa_parts/indices.py",
    "app/ia/aba5_fluxo_caixa_parts/projecoes.py",
]


def _non_empty_line_count(relative_path: str) -> int:
    source = (BACKEND_ROOT / relative_path).read_text(encoding="utf-8")
    return sum(1 for line in source.splitlines() if line.strip())


def test_fluxo_caixa_fachada_preserva_funcoes_extraidas():
    from app.ia import aba5_fluxo_caixa
    from app.ia.aba5_fluxo_caixa_parts import acoes, base, indices, projecoes

    assert aba5_fluxo_caixa._get_user_tenant_id is base._get_user_tenant_id
    assert aba5_fluxo_caixa._resolve_tenant_id is base._resolve_tenant_id
    assert aba5_fluxo_caixa._utcnow_naive is base._utcnow_naive
    assert aba5_fluxo_caixa._saldo_realizado_atual is base._saldo_realizado_atual
    assert (
        aba5_fluxo_caixa._montar_projecoes_estaticas
        is projecoes._montar_projecoes_estaticas
    )
    assert (
        aba5_fluxo_caixa._persistir_projecoes_estaticas
        is projecoes._persistir_projecoes_estaticas
    )
    assert (
        aba5_fluxo_caixa._gerar_projecoes_estaticas
        is projecoes._gerar_projecoes_estaticas
    )
    assert aba5_fluxo_caixa.calcular_indices_saude is indices.calcular_indices_saude
    assert aba5_fluxo_caixa.projetar_fluxo_15_dias is projecoes.projetar_fluxo_15_dias
    assert (
        aba5_fluxo_caixa.obter_projecoes_proximos_dias
        is projecoes.obter_projecoes_proximos_dias
    )
    assert aba5_fluxo_caixa.simular_cenario is acoes.simular_cenario
    assert aba5_fluxo_caixa.gerar_alertas_caixa is acoes.gerar_alertas_caixa
    assert aba5_fluxo_caixa.registrar_movimentacao is acoes.registrar_movimentacao


def test_fluxo_caixa_fatia_28_fica_abaixo_de_700_linhas_nao_vazias():
    oversized = {
        relative_path: _non_empty_line_count(relative_path)
        for relative_path in FLUXO_CAIXA_FILES
        if _non_empty_line_count(relative_path) > 700
    }

    assert oversized == {}
