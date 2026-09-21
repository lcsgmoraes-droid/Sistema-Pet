"""Validacoes compartilhadas do fluxo de pedidos de compra."""

from typing import Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

from ..models import Cliente
from ..produtos_models import PedidoCompra, Produto


def validar_fornecedor_pedido(
    db: Session, tenant_id: int, fornecedor_id: Optional[int]
) -> Optional[Cliente]:
    """Aceita pedido generico ou garante que o fornecedor pertence ao tenant."""
    if fornecedor_id is None:
        return None

    fornecedor = (
        db.query(Cliente)
        .filter(
            Cliente.id == fornecedor_id,
            Cliente.tenant_id == tenant_id,
            Cliente.tipo_cadastro == "fornecedor",
        )
        .first()
    )
    if not fornecedor:
        raise HTTPException(status_code=404, detail="Fornecedor não encontrado")
    return fornecedor


def validar_itens_pedido(db: Session, tenant_id: int, itens) -> None:
    """Garante pedido com itens e produtos pertencentes ao tenant."""
    if not itens:
        raise HTTPException(status_code=400, detail="Pedido deve ter pelo menos 1 item")

    produto_ids = {item.produto_id for item in itens}
    encontrados = {
        produto_id
        for (produto_id,) in db.query(Produto.id)
        .filter(Produto.id.in_(produto_ids), Produto.tenant_id == tenant_id)
        .all()
    }
    ausente = next(
        (produto_id for produto_id in produto_ids if produto_id not in encontrados),
        None,
    )
    if ausente is not None:
        raise HTTPException(status_code=404, detail=f"Produto {ausente} não encontrado")


def garantir_fornecedor_operacional(pedido: PedidoCompra) -> None:
    """Bloqueia etapas fiscais/operacionais que exigem fornecedor identificado."""
    if pedido.fornecedor_id is None:
        raise HTTPException(
            status_code=400,
            detail="Selecione um fornecedor no pedido antes de continuar esta operação",
        )
