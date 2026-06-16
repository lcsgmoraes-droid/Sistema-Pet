"""Rotas de transferência simples de estoque."""

from datetime import datetime
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from .auth.dependencies import get_current_user_and_tenant
from .db import get_session
from .produtos_models import EstoqueMovimentacao, Produto


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/estoque", tags=["Estoque - Transferencia"])


class TransferenciaEstoqueRequest(BaseModel):
    """Transferência entre estoques."""

    produto_id: int
    quantidade: float = Field(gt=0)
    estoque_origem: str = Field(default="fisico")
    estoque_destino: str
    motivo: Optional[str] = "transferencia"
    observacao: Optional[str] = None


@router.post("/transferencia", status_code=status.HTTP_201_CREATED)
def transferencia_estoque(
    transf: TransferenciaEstoqueRequest,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    Transferência entre estoques.

    Tipos de estoque:
    - fisico: estoque físico da loja
    - ecommerce: estoque online
    - consignado: produtos em consignação
    """
    current_user, tenant_id = user_and_tenant
    logger.info(
        "Transferência - Produto %s: %s -> %s",
        transf.produto_id,
        transf.estoque_origem,
        transf.estoque_destino,
    )

    if transf.estoque_origem == transf.estoque_destino:
        raise HTTPException(
            status_code=400, detail="Origem e destino não podem ser iguais"
        )

    produto = (
        db.query(Produto)
        .filter(
            Produto.id == transf.produto_id,
            Produto.tenant_id == tenant_id,
        )
        .first()
    )
    if not produto:
        raise HTTPException(status_code=404, detail="Produto não encontrado")

    estoque_anterior = produto.estoque_atual or 0
    if estoque_anterior < transf.quantidade:
        raise HTTPException(
            status_code=400,
            detail=f"Estoque insuficiente em '{transf.estoque_origem}'",
        )

    codigo_transf = f"TRF-{datetime.now().strftime('%Y%m%d%H%M%S')}"

    mov_saida = EstoqueMovimentacao(
        produto_id=produto.id,
        tipo="transferencia",
        motivo="transferencia_enviada",
        quantidade=transf.quantidade,
        quantidade_anterior=estoque_anterior,
        quantidade_nova=estoque_anterior,
        estoque_origem=transf.estoque_origem,
        estoque_destino=transf.estoque_destino,
        documento=codigo_transf,
        observacao=transf.observacao,
        user_id=current_user.id,
        tenant_id=tenant_id,
    )
    db.add(mov_saida)

    mov_entrada = EstoqueMovimentacao(
        produto_id=produto.id,
        tipo="transferencia",
        motivo="transferencia_recebida",
        quantidade=transf.quantidade,
        quantidade_anterior=estoque_anterior,
        quantidade_nova=estoque_anterior,
        estoque_origem=transf.estoque_origem,
        estoque_destino=transf.estoque_destino,
        documento=codigo_transf,
        observacao=transf.observacao,
        user_id=current_user.id,
        tenant_id=tenant_id,
    )
    db.add(mov_entrada)
    db.commit()

    logger.info("Transferência registrada: %s", codigo_transf)

    return {
        "message": "Transferência registrada com sucesso",
        "codigo": codigo_transf,
        "movimentacoes": [mov_saida.id, mov_entrada.id],
    }
