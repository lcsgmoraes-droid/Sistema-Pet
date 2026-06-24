from pathlib import Path

from app import relatorio_vendas_routes
from app import relatorio_vendas_builder, relatorio_vendas_pdf


BACKEND_ROOT = Path(__file__).resolve().parents[2]


def _route_signatures(router):
    return {
        (route.path, ",".join(sorted(route.methods)))
        for route in router.routes
        if hasattr(route, "methods")
    }


def test_relatorio_vendas_routes_preserva_paths_publicos_extraidos():
    paths = _route_signatures(relatorio_vendas_routes.router)

    assert ("/relatorios/vendas/relatorio", "GET") in paths
    assert ("/relatorios/vendas/export/pdf", "GET") in paths
    assert ("/relatorios/vendas/reprocessar-rentabilidade", "POST") in paths


def test_relatorio_vendas_routes_reexporta_pdf_extraido():
    assert relatorio_vendas_routes.exportar_vendas_pdf is (
        relatorio_vendas_pdf.exportar_vendas_pdf
    )
    assert callable(relatorio_vendas_builder.montar_relatorio_vendas)


def test_relatorio_vendas_routes_stays_below_large_file_threshold_after_extraction():
    app_root = BACKEND_ROOT / "app"
    extracted_files = [
        app_root / "relatorio_vendas_routes.py",
        app_root / "relatorio_vendas_common.py",
        app_root / "relatorio_vendas_builder.py",
        app_root / "relatorio_vendas_pdf.py",
    ]

    assert len(extracted_files[0].read_text(encoding="utf-8").splitlines()) < 150
    for source in extracted_files[1:]:
        assert len(source.read_text(encoding="utf-8").splitlines()) < 1000
