import importlib
from pathlib import Path

from app.nfe import listagem


REPO_ROOT = Path(__file__).resolve().parents[3]


def _source(path: str) -> str:
    return (REPO_ROOT / path).read_text(encoding="utf-8")


def test_nfe_listagem_foi_dividida_em_modulos_menores():
    modules = [
        "app.nfe.listagem_base",
        "app.nfe.listagem_cache",
        "app.nfe.listagem_xml",
        "app.nfe.listagem_normalizacao",
        "app.nfe.listagem_detalhes",
        "app.nfe.listagem_pedidos",
        "app.nfe.listagem_sync",
    ]

    for module_name in modules:
        module = importlib.import_module(module_name)
        assert module is not None


def test_nfe_listagem_permanece_fachada_pequena_com_aliases_legados():
    source = _source("backend/app/nfe/listagem.py")

    assert len(source.splitlines()) < 250
    assert listagem._normalizar_nota_bling is importlib.import_module(
        "app.nfe.listagem_normalizacao"
    )._normalizar_nota_bling
    assert listagem._sincronizar_cache_nfes_com_bling is importlib.import_module(
        "app.nfe.listagem_sync"
    )._sincronizar_cache_nfes_com_bling
