from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[2]
TARGETS = [
    "app/sugestoes_racoes_routes.py",
    "app/racoes_sugestoes_common.py",
    "app/racoes_sugestoes_schemas.py",
    "app/racoes_sugestoes_duplicatas_routes.py",
    "app/racoes_sugestoes_padronizacao_routes.py",
    "app/racoes_sugestoes_gaps_routes.py",
    "app/racoes_sugestoes_relatorio_routes.py",
]


def _line_count(relative: str) -> int:
    return len((BACKEND_ROOT / relative).read_text(encoding="utf-8").splitlines())


def test_sugestoes_racoes_batch_11_modulos_ficam_abaixo_de_700_linhas():
    assert {relative: _line_count(relative) for relative in TARGETS} == {
        relative: count
        for relative in TARGETS
        if (count := _line_count(relative)) <= 700
    }


def test_sugestoes_racoes_facade_preserva_imports_publicos():
    from app import sugestoes_racoes_routes
    from app import racoes_sugestoes_common
    from app import racoes_sugestoes_duplicatas_routes
    from app import racoes_sugestoes_gaps_routes
    from app import racoes_sugestoes_padronizacao_routes
    from app import racoes_sugestoes_relatorio_routes
    from app import racoes_sugestoes_schemas

    assert (
        sugestoes_racoes_routes.DuplicataDetectada
        is racoes_sugestoes_schemas.DuplicataDetectada
    )
    assert sugestoes_racoes_routes.GapEstoque is racoes_sugestoes_schemas.GapEstoque
    assert (
        sugestoes_racoes_routes.PadronizacaoNome
        is racoes_sugestoes_schemas.PadronizacaoNome
    )
    assert (
        sugestoes_racoes_routes._produto_eh_racao_expr
        is racoes_sugestoes_common._produto_eh_racao_expr
    )
    assert (
        sugestoes_racoes_routes.detectar_duplicatas
        is racoes_sugestoes_duplicatas_routes.detectar_duplicatas
    )
    assert (
        sugestoes_racoes_routes.sugerir_padronizacao_nomes
        is racoes_sugestoes_padronizacao_routes.sugerir_padronizacao_nomes
    )
    assert (
        sugestoes_racoes_routes.identificar_gaps_estoque
        is racoes_sugestoes_gaps_routes.identificar_gaps_estoque
    )
    assert (
        sugestoes_racoes_routes.obter_relatorio_completo
        is racoes_sugestoes_relatorio_routes.obter_relatorio_completo
    )


def test_sugestoes_racoes_rotas_publicas_permanecem_no_router():
    from app import sugestoes_racoes_routes

    routes = {
        (route.path, method)
        for route in sugestoes_racoes_routes.router.routes
        for method in getattr(route, "methods", set())
    }

    assert ("/racoes/sugestoes/duplicatas", "GET") in routes
    assert ("/racoes/sugestoes/duplicatas/ignorar", "POST") in routes
    assert ("/racoes/sugestoes/duplicatas/mesclar", "POST") in routes
    assert ("/racoes/sugestoes/padronizar-nomes", "GET") in routes
    assert ("/racoes/sugestoes/gaps-estoque", "GET") in routes
    assert ("/racoes/sugestoes/relatorio-completo", "GET") in routes
