import importlib
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]


def _source(path: str) -> str:
    return (REPO_ROOT / path).read_text(encoding="utf-8")


def test_dre_canais_rotas_foram_fatiadas_em_modulos_menores():
    modules = [
        "app.dre_canais.schemas",
        "app.dre_canais.base",
        "app.dre_canais.agregacao",
        "app.dre_canais.linhas",
        "app.dre_canais.detalhes",
        "app.dre_canais.routes",
    ]

    for module_name in modules:
        module = importlib.import_module(module_name)
        assert module is not None


def test_dre_canais_routes_permanece_fachada_pequena():
    source = _source("backend/app/dre_canais_routes.py")

    assert "router = APIRouter(" not in source
    assert len(source.splitlines()) < 200


def test_dre_canais_endpoint_principal_nao_mantem_codigo_morto_legacy():
    source = _source("backend/app/dre_canais/routes.py")

    assert "# Obter dados por canal" not in source
    assert "contas_antigas_comissao" not in source
