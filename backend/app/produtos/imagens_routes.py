"""Rotas de imagens de produtos."""

from __future__ import annotations

import logging
from typing import List

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user_and_tenant
from app.config import settings
from app.db import get_session
from app.produtos.schemas import ImagemUpdateRequest, ImagemUploadResponse
from app.produtos.validators import _validar_tenant_e_obter_usuario
from app.produtos_models import Produto, ProdutoImagem
from app.services.product_image_storage import (
    delete_product_image_assets,
    prepare_product_image_variants,
    save_product_image_variants,
)

logger = logging.getLogger(__name__)
router = APIRouter()


# ==========================================
# ENDPOINTS - IMAGENS
# ==========================================


@router.post("/{produto_id}/imagens", response_model=ImagemUploadResponse)
async def upload_imagem_produto(
    produto_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    Upload de imagem para um produto

    - Aceita JPG, PNG, WebP
    - Otimiza automaticamente para WebP
    - Gera miniatura para listagens
    - Salva em storage local ou S3-compatÃ­vel
    - Primeira imagem Ã© automaticamente marcada como principal
    """
    try:
        current_user, tenant_id = user_and_tenant
        logger.info(f"[UPLOAD] Iniciando upload para produto {produto_id}")

        # Imagens podem ser preparadas mesmo em produtos inativos/descontinuados.
        # O bloqueio deve ser apenas por tenant/existencia, igual a tela de edicao.
        produto = (
            db.query(Produto)
            .filter(Produto.id == produto_id, Produto.tenant_id == tenant_id)
            .first()
        )

        if not produto:
            logger.error("[UPLOAD] Produto nao encontrado para upload de imagem")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Produto nÃ£o encontrado"
            )

        logger.info(f"[UPLOAD] Produto encontrado: {produto.nome}")

        # Validar tipo de arquivo
        allowed_types = ["image/jpeg", "image/png", "image/webp"]
        if file.content_type not in allowed_types:
            logger.error("[UPLOAD] Tipo de imagem invalido")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Formato nÃ£o aceito. Use JPG, PNG ou WebP",
            )

        file_bytes = await file.read()
        file_size = len(file_bytes)

        max_size = int(settings.PRODUCT_IMAGE_UPLOAD_MAX_BYTES or 10 * 1024 * 1024)
        if file_size > max_size:
            logger.error(f"[UPLOAD] Arquivo muito grande: {file_size} bytes")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Arquivo muito grande. MÃ¡ximo: {max_size // (1024 * 1024)}MB",
            )

        logger.info(f"[UPLOAD] Arquivo validado: {file_size} bytes")

        try:
            imagem_preparada = prepare_product_image_variants(file_bytes)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(exc),
            ) from exc

        imagem_salva = save_product_image_variants(
            tenant_id=tenant_id,
            produto_id=produto_id,
            prepared_image=imagem_preparada,
        )

        # Verificar se jÃ¡ existe imagem principal
        tem_principal = (
            db.query(ProdutoImagem)
            .filter(
                ProdutoImagem.tenant_id == tenant_id,
                ProdutoImagem.produto_id == produto_id,
                ProdutoImagem.e_principal.is_(True),
            )
            .first()
        )

        # Primeira imagem Ã© principal automaticamente
        e_principal = not tem_principal
        logger.info(f"[UPLOAD] Ã‰ principal: {e_principal}")

        # Obter prÃ³xima ordem
        max_ordem = (
            db.query(func.max(ProdutoImagem.ordem))
            .filter(
                ProdutoImagem.tenant_id == tenant_id,
                ProdutoImagem.produto_id == produto_id,
            )
            .scalar()
            or 0
        )
        logger.info(f"[UPLOAD] PrÃ³xima ordem: {max_ordem + 1}")

        # Criar registro no banco
        nova_imagem = ProdutoImagem(
            tenant_id=tenant_id,
            produto_id=produto_id,
            url=imagem_salva.url,
            ordem=max_ordem + 1,
            e_principal=e_principal,
            tamanho=imagem_preparada.original_size_bytes,
            largura=imagem_preparada.width,
            altura=imagem_preparada.height,
        )

        db.add(nova_imagem)

        # Se é a imagem principal, atualizar também o campo imagem_principal do produto
        if e_principal:
            produto.imagem_principal = nova_imagem.url

        db.commit()
        db.refresh(nova_imagem)

        logger.info("[UPLOAD] Imagem adicionada ao produto")

        return nova_imagem

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[UPLOAD] âŒ ERRO: {str(e)}")
        logger.error(f"[UPLOAD] Traceback: {traceback.format_exc()}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao fazer upload: {str(e)}",
        )


@router.get("/{produto_id}/imagens", response_model=List[ImagemUploadResponse])
def listar_imagens_produto(
    produto_id: int,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    Listar todas as imagens de um produto
    Ordenadas por: principal DESC, ordem ASC
    """
    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)

    # Verificar se produto existe e pertence ao usuÃ¡rio
    produto = (
        db.query(Produto)
        .filter(Produto.id == produto_id, Produto.tenant_id == tenant_id)
        .first()
    )

    if not produto:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Produto nÃ£o encontrado"
        )

    imagens = (
        db.query(ProdutoImagem)
        .filter(
            ProdutoImagem.tenant_id == tenant_id, ProdutoImagem.produto_id == produto_id
        )
        .order_by(ProdutoImagem.e_principal.desc(), ProdutoImagem.ordem.asc())
        .all()
    )

    return imagens


@router.put("/imagens/{imagem_id}", response_model=ImagemUploadResponse)
def atualizar_imagem(
    imagem_id: int,
    dados: ImagemUpdateRequest,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    Atualizar dados da imagem (ordem, se é principal)
    """
    user, tenant_id = user_and_tenant

    # Buscar imagem e verificar permissão
    imagem = (
        db.query(ProdutoImagem)
        .join(Produto)
        .filter(
            ProdutoImagem.id == imagem_id,
            ProdutoImagem.tenant_id == tenant_id,
            Produto.tenant_id == tenant_id,
        )
        .first()
    )

    if not imagem:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Imagem nÃ£o encontrada"
        )

    # Se for marcar como principal, desmarcar outras
    if dados.principal and not imagem.e_principal:
        db.query(ProdutoImagem).filter(
            ProdutoImagem.tenant_id == tenant_id,
            ProdutoImagem.produto_id == imagem.produto_id,
            ProdutoImagem.e_principal.is_(True),
        ).update({"e_principal": False})
        imagem.produto.imagem_principal = imagem.url

    # Atualizar campos
    if dados.ordem is not None:
        imagem.ordem = dados.ordem
    if dados.principal is not None:
        imagem.e_principal = dados.principal
        if dados.principal is False and imagem.produto.imagem_principal == imagem.url:
            proxima_principal = (
                db.query(ProdutoImagem)
                .filter(
                    ProdutoImagem.tenant_id == tenant_id,
                    ProdutoImagem.produto_id == imagem.produto_id,
                    ProdutoImagem.id != imagem.id,
                )
                .order_by(
                    ProdutoImagem.ordem.asc(),
                    ProdutoImagem.id.asc(),
                )
                .first()
            )
            imagem.produto.imagem_principal = (
                proxima_principal.url if proxima_principal else None
            )
            if proxima_principal:
                proxima_principal.e_principal = True

    imagem.updated_at = datetime.now()

    db.commit()
    db.refresh(imagem)

    logger.info("Imagem de produto atualizada")

    return imagem


@router.delete("/imagens/{imagem_id}")
def deletar_imagem(
    imagem_id: int,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    Deletar imagem do produto
    Remove o arquivo fÃ­sico e o registro do banco
    """
    current_user, tenant_id = user_and_tenant

    # Buscar imagem e verificar permissÃ£o
    imagem = (
        db.query(ProdutoImagem)
        .join(Produto)
        .filter(
            ProdutoImagem.id == imagem_id,
            ProdutoImagem.tenant_id == tenant_id,
            Produto.tenant_id == tenant_id,
        )
        .first()
    )

    if not imagem:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Imagem nÃ£o encontrada"
        )

    url_removida = imagem.url
    era_principal = bool(imagem.e_principal)
    produto = imagem.produto

    try:
        delete_product_image_assets(url_removida)
    except Exception as e:
        logger.warning(f"Erro ao deletar assets da imagem {imagem_id}: {e}")

    # Deletar registro
    db.delete(imagem)

    proxima_imagem = (
        db.query(ProdutoImagem)
        .filter(
            ProdutoImagem.tenant_id == tenant_id,
            ProdutoImagem.produto_id == produto.id,
            ProdutoImagem.id != imagem_id,
        )
        .order_by(
            ProdutoImagem.e_principal.desc(),
            ProdutoImagem.ordem.asc(),
            ProdutoImagem.id.asc(),
        )
        .first()
    )

    if proxima_imagem:
        if era_principal or produto.imagem_principal == url_removida:
            db.query(ProdutoImagem).filter(
                ProdutoImagem.tenant_id == tenant_id,
                ProdutoImagem.produto_id == produto.id,
            ).update({"e_principal": False})
            proxima_imagem.e_principal = True
            produto.imagem_principal = proxima_imagem.url
    else:
        produto.imagem_principal = None

    db.commit()

    logger.info("Imagem de produto deletada")

    return {"message": "Imagem deletada com sucesso"}
