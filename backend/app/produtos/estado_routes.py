"""Rotas de atualizacao rapida, exclusao e ativacao de produtos."""

import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user_and_tenant
from app.db import get_session
from app.produtos.core import _aplicar_status_ativo_produto
from app.produtos.schemas import ProdutoAtivoUpdate, ProdutoResponse
from app.produtos.validators import (
    _obter_produto_ou_404,
    _validar_pode_inativar_produto,
    _validar_tenant_e_obter_usuario,
)
from app.produtos_models import Produto
from app.security.permissions_decorator import require_permission

router = APIRouter()
logger = logging.getLogger(__name__)


@router.patch("/{produto_id}")
def atualizar_preco_produto(
    produto_id: int,
    preco_venda: Optional[float] = None,
    preco_custo: Optional[float] = None,
    preco_promocional: Optional[float] = None,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Atualiza apenas o preÃ§o de um produto (ediÃ§Ã£o rÃ¡pida)"""

    current_user, tenant_id = user_and_tenant
    logger.info(f"ðŸ·ï¸ Atualizando preÃ§o do produto {produto_id}")

    produto = (
        db.query(Produto)
        .filter(Produto.id == produto_id, Produto.tenant_id == tenant_id)
        .first()
    )

    if not produto:
        raise HTTPException(status_code=404, detail="Produto nÃ£o encontrado")

    # Atualizar apenas os preÃ§os fornecidos
    if preco_venda is not None:
        produto.preco_venda = preco_venda
    if preco_custo is not None:
        produto.preco_custo = preco_custo
    if preco_promocional is not None:
        produto.preco_promocional = preco_promocional

    produto.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(produto)

    logger.info(f"âœ… PreÃ§o atualizado: PV={produto.preco_venda}")

    return {
        "id": produto.id,
        "preco_venda": produto.preco_venda,
        "preco_custo": produto.preco_custo,
        "preco_promocional": produto.preco_promocional,
    }


@router.delete("/{produto_id}", status_code=status.HTTP_204_NO_CONTENT)
def deletar_produto(
    produto_id: int,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Deleta (soft delete) um produto"""

    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)

    produto = (
        db.query(Produto)
        .filter(Produto.id == produto_id, Produto.tenant_id == tenant_id)
        .first()
    )

    if not produto:
        raise HTTPException(status_code=404, detail="Produto nÃ£o encontrado")

    _validar_pode_inativar_produto(db, produto, tenant_id)

    # Soft delete
    _aplicar_status_ativo_produto(produto, False)

    db.commit()

    return None


@router.patch("/{produto_id}/ativo", response_model=ProdutoResponse)
@require_permission("produtos.editar")
def atualizar_status_ativo_produto(
    produto_id: int,
    payload: ProdutoAtivoUpdate,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Ativa ou desativa produto sem removÃª-lo do sistema."""

    _, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)
    produto = _obter_produto_ou_404(db, produto_id, tenant_id)

    if payload.ativo == bool(produto.ativo):
        return produto

    if not payload.ativo:
        _validar_pode_inativar_produto(db, produto, tenant_id)

    _aplicar_status_ativo_produto(produto, payload.ativo)

    db.commit()
    db.refresh(produto)

    logger.info(
        "ðŸ” Produto %s #%s com status alterado para %s",
        produto.nome,
        produto.id,
        "ativo" if payload.ativo else "inativo",
    )

    return produto
