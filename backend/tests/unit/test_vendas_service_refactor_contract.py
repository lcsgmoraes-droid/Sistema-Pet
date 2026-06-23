import importlib
from pathlib import Path

from app.vendas.service import VendaService


REPO_ROOT = Path(__file__).resolve().parents[3]


def _source(path: str) -> str:
    return (REPO_ROOT / path).read_text(encoding="utf-8")


def test_venda_service_criacao_foi_extraida_para_modulo_dedicado():
    criacao = importlib.import_module("app.vendas.criacao")
    service_source = _source("backend/app/vendas/service.py")
    criacao_source = _source("backend/app/vendas/criacao.py")

    assert criacao.criar_venda is not None
    assert "from app.vendas.criacao import criar_venda" in service_source
    assert len(service_source.splitlines()) < 2100
    assert len(criacao_source.splitlines()) > 450


def test_venda_service_preserva_api_publica_da_criacao():
    assert callable(VendaService.criar_venda)
    assert callable(VendaService._gerar_numero_venda)
    assert callable(VendaService._processar_baixa_estoque_item)
