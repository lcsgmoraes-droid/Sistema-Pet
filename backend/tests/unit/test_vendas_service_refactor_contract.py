import importlib
from pathlib import Path

from app.vendas import finalizacao
from app.vendas.cancelamento_service import cancelar_venda
from app.vendas.estoque_baixa import processar_baixa_estoque_item
from app.vendas.numeracao import gerar_numero_venda
from app.vendas.service import VendaService
from app.vendas.service import _calcular_pagamentos_finalizacao


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


def test_venda_service_finalizacao_foi_extraida_para_modulo_dedicado():
    service_source = _source("backend/app/vendas/service.py")
    finalizacao_source = _source("backend/app/vendas/finalizacao.py")
    finalizacao_eventos_source = _source("backend/app/vendas/finalizacao_eventos.py")
    finalizacao_pos_commit_source = _source(
        "backend/app/vendas/finalizacao_pos_commit.py"
    )

    assert callable(finalizacao.finalizar_venda)
    assert "from app.vendas.finalizacao import (" in service_source
    assert "finalizar_venda as finalizar_venda_impl" in service_source
    assert "consume_coupon_redemption" not in service_source
    assert "db.query(OperadoraCartao)" not in service_source
    assert len(service_source.splitlines()) < 1000
    assert len(finalizacao_source.splitlines()) < 1000
    assert len(finalizacao_eventos_source.splitlines()) < 300
    assert len(finalizacao_pos_commit_source.splitlines()) < 250
    assert "publicar_eventos_finalizacao(" in finalizacao_source
    assert "processar_pos_commit_finalizacao(" in finalizacao_source


def test_venda_service_cancelamento_estoque_e_numeracao_foram_extraidos():
    service_source = _source("backend/app/vendas/service.py")
    cancelamento_source = _source("backend/app/vendas/cancelamento_service.py")
    estoque_source = _source("backend/app/vendas/estoque_baixa.py")
    numeracao_source = _source("backend/app/vendas/numeracao.py")

    assert (
        "from app.vendas.cancelamento_service import cancelar_venda as cancelar_venda_impl"
        in service_source
    )
    assert "from app.vendas.estoque_baixa import (" in service_source
    assert (
        "from app.vendas.numeracao import gerar_numero_venda as gerar_numero_venda_impl"
        in service_source
    )

    assert callable(cancelar_venda)
    assert callable(processar_baixa_estoque_item)
    assert callable(gerar_numero_venda)

    for source in [
        service_source,
        cancelamento_source,
        estoque_source,
        numeracao_source,
    ]:
        assert len(source.splitlines()) < 700


def test_venda_service_preserva_api_publica():
    assert callable(VendaService.criar_venda)
    assert callable(VendaService._gerar_numero_venda)
    assert callable(VendaService._processar_baixa_estoque_item)
    assert callable(VendaService.cancelar_venda)
    assert callable(VendaService.finalizar_venda)
    assert VendaService._gerar_numero_venda is gerar_numero_venda
    assert VendaService._processar_baixa_estoque_item is processar_baixa_estoque_item
    assert VendaService.cancelar_venda is cancelar_venda
    assert (
        _calcular_pagamentos_finalizacao is finalizacao._calcular_pagamentos_finalizacao
    )
