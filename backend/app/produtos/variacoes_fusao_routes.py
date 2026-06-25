"""Rotas de variacoes e fusao de produtos."""

import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.auth.dependencies import get_current_user_and_tenant
from app.db import get_session
from app.produtos.core import _aplicar_status_ativo_produto
from app.produtos.schemas import (
    ProdutoFusaoExecutarRequest,
    ProdutoFusaoPreviewRequest,
    ProdutoResponse,
)
from app.produtos.validators import _validar_tenant_e_obter_usuario
from app.produtos_models import Produto
from app.security.permissions_decorator import require_permission
from app.services.produto_merge_service import (
    executar_fusao_produtos,
    montar_preview_fusao_produtos,
)

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/{produto_id}/variacoes", response_model=List[ProdutoResponse])
def listar_variacoes_produto(
    produto_id: int,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    Lista todas as variaÃ§Ãµes de um produto PAI

    Sprint 2: Lazy load de variaÃ§Ãµes
    - Usado para expandir produto PAI na listagem
    - Retorna apenas produtos filhos (tipo_produto = 'VARIACAO')
    - Ordenado por nome
    """

    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)

    # Verificar se produto existe e Ã© PAI
    produto_pai = (
        db.query(Produto)
        .filter(Produto.id == produto_id, Produto.tenant_id == tenant_id)
        .first()
    )

    if not produto_pai:
        raise HTTPException(status_code=404, detail="Produto nÃ£o encontrado")

    if produto_pai.tipo_produto != "PAI":
        raise HTTPException(
            status_code=400,
            detail="Produto nÃ£o Ã© do tipo PAI (nÃ£o possui variaÃ§Ãµes)",
        )

    # Buscar variaÃ§Ãµes
    variacoes = (
        db.query(Produto)
        .filter(
            Produto.produto_pai_id == produto_id,
            Produto.tipo_produto == "VARIACAO",
            Produto.ativo.is_(True),  # Filtrar apenas variaÃ§Ãµes ativas
            Produto.tenant_id == tenant_id,
        )
        .options(joinedload(Produto.imagens), joinedload(Produto.lotes))
        .order_by(Produto.nome)
        .all()
    )

    logger.info(
        f"ðŸ“¦ Produto PAI #{produto_id} possui {len(variacoes)} variaÃ§Ãµes ativas"
    )

    return variacoes


@router.get("/{produto_id}/variacoes/excluidas", response_model=List[ProdutoResponse])
def listar_variacoes_excluidas(
    produto_id: int,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    Lista variaÃ§Ãµes excluÃ­das (soft-deleted) de um produto PAI
    Permite visualizar, restaurar ou excluir definitivamente
    """

    _, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)

    # Verificar se produto existe e Ã© PAI
    produto_pai = (
        db.query(Produto)
        .filter(Produto.id == produto_id, Produto.tenant_id == tenant_id)
        .first()
    )

    if not produto_pai:
        raise HTTPException(status_code=404, detail="Produto nÃ£o encontrado")

    if produto_pai.tipo_produto != "PAI":
        raise HTTPException(
            status_code=400,
            detail="Produto nÃ£o Ã© do tipo PAI (nÃ£o possui variaÃ§Ãµes)",
        )

    # Buscar variaÃ§Ãµes excluÃ­das
    variacoes_excluidas = (
        db.query(Produto)
        .filter(
            Produto.produto_pai_id == produto_id,
            Produto.tipo_produto == "VARIACAO",
            Produto.ativo.is_(False),  # Apenas inativas (excluÃ­das)
            Produto.tenant_id == tenant_id,
        )
        .options(joinedload(Produto.imagens), joinedload(Produto.lotes))
        .order_by(Produto.updated_at.desc())
        .all()
    )

    logger.info(
        f"ðŸ—‘ï¸ Produto PAI #{produto_id} possui {len(variacoes_excluidas)} variaÃ§Ãµes excluÃ­das"
    )

    return variacoes_excluidas


@router.patch("/{produto_id}/restaurar", response_model=ProdutoResponse)
def restaurar_variacao(
    produto_id: int,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    Restaura uma variaÃ§Ã£o excluÃ­da (reativa)
    """

    _, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)

    produto = (
        db.query(Produto)
        .filter(
            Produto.id == produto_id,
            Produto.tenant_id == tenant_id,
            Produto.tipo_produto == "VARIACAO",
        )
        .first()
    )

    if not produto:
        raise HTTPException(status_code=404, detail="VariaÃ§Ã£o nÃ£o encontrada")

    if produto.ativo:
        raise HTTPException(status_code=400, detail="VariaÃ§Ã£o jÃ¡ estÃ¡ ativa")

    # Restaurar
    _aplicar_status_ativo_produto(produto, True)

    db.commit()
    db.refresh(produto)

    logger.info(f"â™»ï¸ VariaÃ§Ã£o #{produto_id} restaurada com sucesso")

    return produto


@router.post("/fusao/preview")
@require_permission("produtos.editar")
def preview_fusao_produtos(
    payload: ProdutoFusaoPreviewRequest,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Mostra conflitos de cadastro e impacto antes de fundir dois produtos."""
    _, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)
    try:
        return montar_preview_fusao_produtos(
            db,
            tenant_id=tenant_id,
            principal_id=payload.produto_principal_id,
            duplicado_id=payload.produto_duplicado_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/fusao/executar")
@require_permission("produtos.editar")
def executar_fusao_produtos_endpoint(
    payload: ProdutoFusaoExecutarRequest,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Funde dois produtos transferindo historico e inativando o duplicado."""
    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)
    try:
        return executar_fusao_produtos(
            db,
            tenant_id=tenant_id,
            principal_id=payload.produto_principal_id,
            duplicado_id=payload.produto_duplicado_id,
            decisoes_campos=payload.decisoes_campos,
            user_id=current_user.id,
            observacao=payload.observacao,
        )
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        db.rollback()
        logger.error("Erro ao fundir produtos: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Erro ao fundir produtos: {exc}")


@router.delete("/{produto_id}/permanente", status_code=status.HTTP_204_NO_CONTENT)
def excluir_variacao_permanentemente(
    produto_id: int,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    Exclui DEFINITIVAMENTE uma variaÃ§Ã£o do banco de dados
    ATENÃ‡ÃƒO: Esta aÃ§Ã£o Ã© irreversÃ­vel!
    """

    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)

    produto = (
        db.query(Produto)
        .filter(
            Produto.id == produto_id,
            Produto.tenant_id == tenant_id,
            Produto.tipo_produto == "VARIACAO",
        )
        .first()
    )

    if not produto:
        raise HTTPException(status_code=404, detail="VariaÃ§Ã£o nÃ£o encontrada")

    if produto.ativo:
        raise HTTPException(
            status_code=400,
            detail="NÃ£o Ã© possÃ­vel excluir permanentemente uma variaÃ§Ã£o ativa. Exclua-a primeiro (soft delete).",
        )

    # Excluir DEFINITIVAMENTE
    db.delete(produto)
    db.commit()

    logger.warning(
        f"âš ï¸ VariaÃ§Ã£o #{produto_id} EXCLUÃDA PERMANENTEMENTE do banco de dados"
    )

    return None
