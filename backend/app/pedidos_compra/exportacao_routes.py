"""Rotas de exportacao de pedidos de compra."""

from io import BytesIO
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session, joinedload

from ..auth.dependencies import get_current_user_and_tenant
from ..db import get_session
from ..produtos_models import PedidoCompra
from .exportacao import (
    _buscar_fornecedor_pedido,
    _gerar_excel_pedido_bytes,
    _gerar_pdf_pedido_bytes,
    _montar_content_disposition_attachment,
    _montar_nome_arquivo_pedido,
    _normalizar_colunas_exportacao_pedido,
)

router = APIRouter()


# ============================================================================
# EXPORTAÇÃO PDF/EXCEL
# ============================================================================


@router.get("/{pedido_id}/export/excel")
def exportar_excel(
    pedido_id: int,
    colunas: Optional[str] = Query(
        None, description="Colunas do documento separadas por virgula"
    ),
    db: Session = Depends(get_session),
    current_user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Exporta pedido para Excel"""
    current_user, tenant_id = current_user_and_tenant
    pedido = (
        db.query(PedidoCompra)
        .filter(PedidoCompra.id == pedido_id, PedidoCompra.tenant_id == tenant_id)
        .options(joinedload(PedidoCompra.itens))
        .first()
    )

    if not pedido:
        raise HTTPException(status_code=404, detail="Pedido não encontrado")

    fornecedor = _buscar_fornecedor_pedido(db, tenant_id, pedido)
    fornecedor_nome = (
        fornecedor.nome if fornecedor else f"Fornecedor {pedido.fornecedor_id}"
    )
    colunas_exportacao = _normalizar_colunas_exportacao_pedido(colunas)
    output = BytesIO(
        _gerar_excel_pedido_bytes(
            pedido, fornecedor_nome, db, tenant_id, colunas_exportacao
        )
    )
    filename = _montar_nome_arquivo_pedido(
        pedido, fornecedor_nome, db, tenant_id, "xlsx"
    )

    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": _montar_content_disposition_attachment(filename)
        },
    )


@router.get("/{pedido_id}/export/pdf")
def exportar_pdf(
    pedido_id: int,
    colunas: Optional[str] = Query(
        None, description="Colunas do documento separadas por virgula"
    ),
    db: Session = Depends(get_session),
    current_user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Exporta pedido para PDF"""
    current_user, tenant_id = current_user_and_tenant
    pedido = (
        db.query(PedidoCompra)
        .filter(PedidoCompra.id == pedido_id, PedidoCompra.tenant_id == tenant_id)
        .options(joinedload(PedidoCompra.itens))
        .first()
    )

    if not pedido:
        raise HTTPException(status_code=404, detail="Pedido não encontrado")

    fornecedor = _buscar_fornecedor_pedido(db, tenant_id, pedido)
    fornecedor_nome = (
        fornecedor.nome if fornecedor else f"Fornecedor {pedido.fornecedor_id}"
    )
    colunas_exportacao = _normalizar_colunas_exportacao_pedido(colunas)
    buffer = BytesIO(
        _gerar_pdf_pedido_bytes(
            pedido, fornecedor_nome, db, tenant_id, colunas_exportacao
        )
    )
    filename = _montar_nome_arquivo_pedido(
        pedido, fornecedor_nome, db, tenant_id, "pdf"
    )

    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={
            "Content-Disposition": _montar_content_disposition_attachment(filename)
        },
    )
