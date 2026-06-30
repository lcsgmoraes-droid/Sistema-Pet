from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[2]

UPLOAD_FILES = [
    "app/notas_entrada/upload_routes.py",
    "app/notas_entrada/upload_routes_parts/__init__.py",
    "app/notas_entrada/upload_routes_parts/common.py",
    "app/notas_entrada/upload_routes_parts/lote_xml_route.py",
    "app/notas_entrada/upload_routes_parts/pdf_route.py",
    "app/notas_entrada/upload_routes_parts/xml_route.py",
]


def _non_empty_line_count(relative_path: str) -> int:
    source = (BACKEND_ROOT / relative_path).read_text(encoding="utf-8")
    return sum(1 for line in source.splitlines() if line.strip())


def test_upload_notas_fachada_preserva_rotas_extraidas():
    from app.notas_entrada import upload_routes
    from app.notas_entrada.upload_routes_parts import (
        lote_xml_route,
        pdf_route,
        xml_route,
    )

    assert upload_routes.upload_xml is xml_route.upload_xml
    assert upload_routes.upload_pdf is pdf_route.upload_pdf
    assert upload_routes.upload_lote_xml is lote_xml_route.upload_lote_xml

    route_names = [
        route.name
        for route in upload_routes.router.routes
        if "POST" in getattr(route, "methods", set())
    ]
    assert route_names == ["upload_xml", "upload_pdf", "upload_lote_xml"]

    route_paths = [
        route.path
        for route in upload_routes.router.routes
        if "POST" in getattr(route, "methods", set())
    ]
    assert route_paths == ["/upload", "/upload-pdf", "/upload-lote"]


def test_upload_notas_fachada_preserva_reexports_legados():
    from app.notas_entrada import upload_routes
    from app.notas_entrada.produtos import _montar_sugestao_sku_produto
    from app.notas_entrada.xml_parser import parse_nfe_xml

    assert upload_routes._montar_sugestao_sku_produto is _montar_sugestao_sku_produto
    assert upload_routes.parse_nfe_xml is parse_nfe_xml


def test_upload_notas_fatia_30_fica_abaixo_de_700_linhas_nao_vazias():
    oversized = {
        relative_path: _non_empty_line_count(relative_path)
        for relative_path in UPLOAD_FILES
        if _non_empty_line_count(relative_path) > 700
    }

    assert oversized == {}


def test_upload_notas_rotas_usam_processamento_compartilhado():
    from app.notas_entrada.upload_routes_parts import common

    assert callable(common.salvar_entrada_com_itens)
    assert callable(common.buscar_ou_criar_fornecedor_nfe)

    route_files = [
        "app/notas_entrada/upload_routes_parts/lote_xml_route.py",
        "app/notas_entrada/upload_routes_parts/pdf_route.py",
        "app/notas_entrada/upload_routes_parts/xml_route.py",
    ]
    route_sources = "\n".join(
        (BACKEND_ROOT / relative_path).read_text(encoding="utf-8")
        for relative_path in route_files
    )

    assert "NotaEntradaItem(" not in route_sources
    assert "datetime.utcnow" not in route_sources
