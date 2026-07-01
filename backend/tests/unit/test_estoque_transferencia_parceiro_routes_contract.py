from pathlib import Path
import os

os.environ["DATABASE_URL"] = os.environ.get("DATABASE_URL") or "sqlite:///./test.db"
os.environ["DEBUG"] = "false"

from app import estoque_transferencia_parceiro_routes
from app.estoque import (
    transferencia_parceiro_documents,
    transferencia_parceiro_schemas,
    transferencia_parceiro_support,
)


ROOT = Path(__file__).resolve().parents[2]


def _source(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def test_transferencia_parceiro_routes_ficam_em_router_dedicado():
    routes = {
        (route.path, ",".join(sorted(route.methods)))
        for route in estoque_transferencia_parceiro_routes.router.routes
    }

    assert ("/estoque/transferencia-parceiro", "POST") in routes
    assert ("/estoque/transferencia-parceiro/{conta_receber_id}", "PUT") in routes
    assert ("/estoque/transferencia-parceiro/historico", "GET") in routes
    assert ("/estoque/transferencia-parceiro/{conta_receber_id}/pdf", "GET") in routes
    assert ("/estoque/transferencia-parceiro/pdf-consolidado", "POST") in routes
    assert (
        "/estoque/transferencia-parceiro/{conta_receber_id}/enviar-email",
        "POST",
    ) in routes
    assert (
        "/estoque/transferencia-parceiro/{conta_receber_id}/contas-pagar-compensacao",
        "GET",
    ) in routes
    assert (
        "/estoque/transferencia-parceiro/{conta_receber_id}/receber",
        "POST",
    ) in routes
    assert (
        "/estoque/transferencia-parceiro/baixa-lote/preview",
        "POST",
    ) in routes
    assert (
        "/estoque/transferencia-parceiro/baixa-lote",
        "POST",
    ) in routes
    assert ("/estoque/transferencia-parceiro/{conta_receber_id}", "DELETE") in routes


def test_estoque_routes_nao_expõe_mais_decorators_de_transferencia_parceiro():
    source = _source("app/estoque_routes.py")

    assert '"/transferencia-parceiro' not in source
    assert "class TransferenciaParceiroRequest" not in source
    assert "def transferir_estoque_para_parceiro(" not in source
    assert "def editar_transferencia_parceiro(" not in source
    assert "def excluir_transferencia_parceiro(" not in source


def test_main_registra_router_de_transferencia_parceiro():
    main_source = _source("app/main_routers.py")

    assert "from app.estoque_transferencia_parceiro_routes import" in main_source
    assert "router as estoque_transferencia_parceiro_router" in main_source
    assert "app.include_router(" in main_source
    assert "estoque_transferencia_parceiro_router" in main_source
    assert 'tags=["Estoque - Transferencia Parceiro"]' in main_source


def test_documentos_transferencia_parceiro_ficam_em_modulo_dedicado():
    assert (
        estoque_transferencia_parceiro_routes._gerar_pdf_transferencia_parceiro_bytes
        is transferencia_parceiro_documents._gerar_pdf_transferencia_parceiro_bytes
    )
    assert (
        estoque_transferencia_parceiro_routes._gerar_pdf_transferencias_parceiro_consolidado_bytes
        is transferencia_parceiro_documents._gerar_pdf_transferencias_parceiro_consolidado_bytes
    )
    assert (
        estoque_transferencia_parceiro_routes._montar_email_transferencia_parceiro
        is transferencia_parceiro_documents._montar_email_transferencia_parceiro
    )
    assert (
        estoque_transferencia_parceiro_routes._status_transferencia_parceiro
        is transferencia_parceiro_documents._status_transferencia_parceiro
    )


def test_schemas_transferencia_parceiro_ficam_em_modulo_dedicado():
    assert (
        estoque_transferencia_parceiro_routes.TransferenciaParceiroRequest
        is transferencia_parceiro_schemas.TransferenciaParceiroRequest
    )
    assert (
        estoque_transferencia_parceiro_routes.TransferenciaParceiroRecebimentoRequest
        is transferencia_parceiro_schemas.TransferenciaParceiroRecebimentoRequest
    )
    assert (
        estoque_transferencia_parceiro_routes.TransferenciaParceiroHistoricoResponse
        is transferencia_parceiro_schemas.TransferenciaParceiroHistoricoResponse
    )


def test_suporte_transferencia_parceiro_fica_em_modulo_dedicado():
    assert (
        estoque_transferencia_parceiro_routes._buscar_conta_transferencia_parceiro
        is transferencia_parceiro_support._buscar_conta_transferencia_parceiro
    )
    assert (
        estoque_transferencia_parceiro_routes._preparar_itens_transferencia_parceiro
        is transferencia_parceiro_support._preparar_itens_transferencia_parceiro
    )
    assert (
        estoque_transferencia_parceiro_routes._listar_itens_transferencia_parceiro
        is transferencia_parceiro_support._listar_itens_transferencia_parceiro
    )


def test_refatoracao_mantem_transferencia_parceiro_sem_arquivo_gigante():
    assert (
        len(_source("app/estoque_transferencia_parceiro_routes.py").splitlines()) < 1400
    )
    assert (
        len(_source("app/estoque/transferencia_parceiro_support.py").splitlines()) < 900
    )
    assert (
        len(_source("app/estoque/transferencia_parceiro_schemas.py").splitlines()) < 220
    )
