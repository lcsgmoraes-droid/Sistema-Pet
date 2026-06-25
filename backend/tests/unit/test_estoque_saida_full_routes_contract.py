from pathlib import Path
import os

os.environ["DATABASE_URL"] = os.environ.get("DATABASE_URL") or "sqlite:///./test.db"
os.environ["DEBUG"] = "false"

from app import estoque_saida_full_routes


ROOT = Path(__file__).resolve().parents[2]


def _source(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def test_saida_full_routes_ficam_em_router_dedicado():
    routes = {
        (route.path, ",".join(sorted(route.methods)))
        for route in estoque_saida_full_routes.router.routes
    }

    assert ("/estoque/saida-full-nf/historico", "GET") in routes
    assert ("/estoque/saida-full-nf/{numero_nf}/canal", "PUT") in routes
    assert ("/estoque/saida-full-nf/validar-estoque", "POST") in routes
    assert ("/estoque/saida-full-nf", "POST") in routes
    assert ("/estoque/saida-full-pdf/parse", "POST") in routes
    assert ("/estoque/saida-full-xml/parse", "POST") in routes


def test_estoque_routes_nao_expõe_mais_rotas_saida_full():
    source = _source("app/estoque_routes.py")

    assert '"/saida-full-nf' not in source
    assert '"/saida-full-pdf/parse"' not in source
    assert '"/saida-full-xml/parse"' not in source
    assert "class SaidaFullNFRequest" not in source
    assert "def saida_full_por_nf(" not in source


def test_main_registra_router_de_saida_full():
    main_source = _source("app/main_routers.py")

    assert (
        "from app.estoque_saida_full_routes import router as estoque_saida_full_router"
        in main_source
    )
    assert (
        'app.include_router(estoque_saida_full_router, tags=["Estoque - Saida FULL"])'
        in main_source
    )


def test_parser_pdf_saida_full_nao_usa_regex_de_sku_e_quantidade():
    source = _source("app/estoque_saida_full_routes.py")

    assert "SKU_EXPLICITO_REGEX" not in source
    assert "QTD_EXPLICITA_REGEX" not in source
    assert "SKU_QTD_LINHA_REGEX" not in source


def test_parser_pdf_saida_full_extrai_sku_quantidade_explicitos_e_em_linha():
    itens = estoque_saida_full_routes._extrair_itens_full_pdf(
        "\n".join(
            [
                "Produto A SKU: ABC-123 QTD: 2",
                "codigo # ABC-123 quantidade 1,5",
                "XYZ_999 3",
                "Linha sem item",
            ]
        )
    )

    assert itens == [
        {"sku": "ABC-123", "quantidade": 3.5},
        {"sku": "XYZ_999", "quantidade": 3.0},
    ]


def test_saida_full_routes_vira_fachada_com_modulos_dedicados():
    fachada = _source("app/estoque_saida_full_routes.py")

    assert len(fachada.splitlines()) <= 140
    assert "from .estoque_saida_full.routes import router" in fachada
    assert "def saida_full_por_nf(" not in fachada
    assert "def parse_saida_full_pdf(" not in fachada
    assert "def _criar_conta_pagar_tarifa_full_nf(" not in fachada

    modulos = [
        "app/estoque_saida_full/nf_routes.py",
        "app/estoque_saida_full/parser_routes.py",
        "app/estoque_saida_full/parsers.py",
        "app/estoque_saida_full/financeiro.py",
    ]
    for modulo in modulos:
        source = _source(modulo)
        assert len(source.splitlines()) <= 700

    assert "_parse_saida_full_xml" in _source("app/estoque_saida_full/parsers.py")
    assert "_criar_conta_pagar_tarifa_full_nf" in _source(
        "app/estoque_saida_full/financeiro.py"
    )
    assert '@router.post("/saida-full-pdf/parse")' in _source(
        "app/estoque_saida_full/parser_routes.py"
    )
