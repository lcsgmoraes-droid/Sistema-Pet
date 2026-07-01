from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[2]

DRE_IA_FILES = [
    "app/dre_ia_routes.py",
    "app/dre_ia_routes_parts/__init__.py",
    "app/dre_ia_routes_parts/anomalias_export_routes.py",
    "app/dre_ia_routes_parts/base_routes.py",
    "app/dre_ia_routes_parts/canal_routes.py",
    "app/dre_ia_routes_parts/dependencies.py",
    "app/dre_ia_routes_parts/detalhada_routes.py",
    "app/dre_ia_routes_parts/schemas.py",
]


def _non_empty_line_count(relative_path: str) -> int:
    source = (BACKEND_ROOT / relative_path).read_text(encoding="utf-8")
    return sum(1 for line in source.splitlines() if line.strip())


def test_dre_ia_fachada_preserva_funcoes_e_schemas_extraidos():
    from app import dre_ia_routes
    from app.dre_ia_routes_parts import (
        anomalias_export_routes,
        base_routes,
        canal_routes,
        dependencies,
        detalhada_routes,
        schemas,
    )

    assert dre_ia_routes._usuario_dre is dependencies._usuario_dre
    assert dre_ia_routes.DREResumo is schemas.DREResumo
    assert dre_ia_routes.DRECompleto is schemas.DRECompleto
    assert dre_ia_routes.CalcularDRERequest is schemas.CalcularDRERequest
    assert dre_ia_routes.CalcularDRECanalRequest is schemas.CalcularDRECanalRequest
    assert (
        dre_ia_routes.CalcularDREConsolidadoRequest
        is schemas.CalcularDREConsolidadoRequest
    )
    assert (
        dre_ia_routes.CalcularDREDetalhadadRequest
        is schemas.CalcularDREDetalhadadRequest
    )
    assert dre_ia_routes.DREDetalheResponse is schemas.DREDetalheResponse
    assert dre_ia_routes.AlocarDespesaRequest is schemas.AlocarDespesaRequest

    assert dre_ia_routes.calcular_dre is base_routes.calcular_dre
    assert dre_ia_routes.listar_dres is base_routes.listar_dres
    assert dre_ia_routes.obter_indices_mercado is base_routes.obter_indices_mercado
    assert dre_ia_routes.exportar_dre_pdf is anomalias_export_routes.exportar_dre_pdf
    assert (
        dre_ia_routes.listar_canais_disponiveis
        is canal_routes.listar_canais_disponiveis
    )
    assert dre_ia_routes.calcular_dre_por_canal is canal_routes.calcular_dre_por_canal
    assert (
        dre_ia_routes.calcular_dre_detalhado is detalhada_routes.calcular_dre_detalhado
    )
    assert dre_ia_routes.alocar_despesa is detalhada_routes.alocar_despesa


def test_dre_ia_fachada_preserva_ordem_das_rotas_publicas():
    from app import dre_ia_routes

    route_names = [
        route.name
        for route in dre_ia_routes.router.routes
        if "GET" in getattr(route, "methods", set())
        or "POST" in getattr(route, "methods", set())
    ]

    assert route_names == [
        "calcular_dre",
        "listar_canais",
        "listar_dres",
        "obter_dre",
        "obter_produtos_rentabilidade",
        "obter_categorias_rentabilidade",
        "obter_insights",
        "comparar_periodos",
        "obter_indices_mercado",
        "listar_setores",
        "calcular_mes_atual",
        "calcular_mes_passado",
        "obter_anomalias_dre",
        "recalcular_anomalias",
        "exportar_dre_pdf",
        "exportar_dre_excel",
        "listar_canais_disponiveis",
        "calcular_dre_por_canal",
        "calcular_dre_consolidado_canais",
        "listar_dres_por_canal",
        "calcular_dre_detalhado",
        "calcular_dre_consolidado",
        "alocar_despesa",
    ]

    canais_routes = [
        route.name
        for route in dre_ia_routes.router.routes
        if route.path == "/ia/dre/canais" and "GET" in getattr(route, "methods", set())
    ]
    assert canais_routes == ["listar_canais", "listar_canais_disponiveis"]


def test_dre_ia_fatia_29_fica_abaixo_de_700_linhas_nao_vazias():
    oversized = {
        relative_path: _non_empty_line_count(relative_path)
        for relative_path in DRE_IA_FILES
        if _non_empty_line_count(relative_path) > 700
    }

    assert oversized == {}
