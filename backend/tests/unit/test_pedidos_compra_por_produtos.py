from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.pedidos_compra import exportacao
from app.pedidos_compra.schemas import PedidoCompraRequest, PedidoCompraResponse
from app.pedidos_compra.validacoes import garantir_fornecedor_operacional
from app.produtos_compras_models import PedidoCompra

ROOT = Path(__file__).resolve().parents[3]


def test_schemas_e_modelo_aceitam_pedido_sem_fornecedor():
    request = PedidoCompraRequest(
        itens=[
            {
                "produto_id": 10,
                "quantidade_pedida": 2,
                "preco_unitario": 15,
            }
        ]
    )
    response_field = PedidoCompraResponse.model_fields["fornecedor_id"]

    assert request.fornecedor_id is None
    assert response_field.default is None
    assert PedidoCompra.__table__.c.fornecedor_id.nullable is True


def test_etapa_operacional_exige_fornecedor_identificado():
    with pytest.raises(HTTPException) as exc_info:
        garantir_fornecedor_operacional(SimpleNamespace(fornecedor_id=None))

    assert exc_info.value.status_code == 400
    assert "Selecione um fornecedor" in exc_info.value.detail


def test_nome_do_documento_e_arquivo_identificam_pedido_generico(monkeypatch):
    pedido = SimpleNamespace(id=8, numero_pedido="PC202600008", fornecedor_id=None)
    monkeypatch.setattr(exportacao, "_buscar_nome_marca_pedido", lambda *_args: None)

    assert exportacao._nome_fornecedor_documento(None, pedido) == "Não informado"
    assert (
        exportacao._montar_nome_arquivo_pedido(pedido, "Não informado", None, 1, "pdf")
        == "Pedido PC202600008 Sem Fornecedor.pdf"
    )


def test_frontend_oferece_montagem_por_produtos_e_vinculo_em_lote():
    modo = (
        ROOT
        / "frontend"
        / "src"
        / "components"
        / "compras"
        / "PedidoCompraModoMontagem.jsx"
    ).read_text(encoding="utf-8")
    hook = (
        ROOT
        / "frontend"
        / "src"
        / "components"
        / "compras"
        / "usePedidoCompraPorProdutos.js"
    ).read_text(encoding="utf-8")
    operacoes = (
        ROOT
        / "frontend"
        / "src"
        / "components"
        / "compras"
        / "pedidosCompraOperacoesController.js"
    ).read_text(encoding="utf-8")

    assert "Por produtos" in modo
    assert "Estoque baixo" in modo
    assert "Vincular selecionados" in modo
    assert 'api.patch("/produtos/atualizar-lote"' in hook
    assert (
        'fornecedor_operacao: vinculoComoPrincipal ? "definir_principal" : "adicionar"'
        in hook
    )
    assert (
        "return Number.isFinite(fornecedorId) && fornecedorId > 0 ? fornecedorId : null"
        in operacoes
    )


def test_migracao_torna_fornecedor_do_pedido_opcional():
    migration = (
        ROOT
        / "backend"
        / "alembic"
        / "versions"
        / "zzy20260921a1_pedido_compra_fornecedor_opcional.py"
    ).read_text(encoding="utf-8")

    assert (
        'down_revision: Union[str, Sequence[str], None] = "zzx20260919a1"' in migration
    )
    assert '"pedidos_compra"' in migration
    assert '"fornecedor_id"' in migration
    assert "nullable=True" in migration
