"""Fotos do cadastro operacional: storage e galeria normais do ERP."""

import hashlib
import logging
import warnings
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from PIL import Image
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_session
from app.models import User
from app.produtos.schemas import ImagemUploadResponse
from app.produtos_models import Produto, ProdutoImagem
from app.routes.app_mobile_funcionario_pdv.auth import (
    _get_funcionario_operacional_or_403,
)
from app.routes.ecommerce_auth import _get_current_ecommerce_user
from app.services.product_image_storage import (
    delete_product_image_assets,
    prepare_product_image_variants,
    save_product_image_variants,
)

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/{produto_id}/imagens", response_model=ImagemUploadResponse)
def adicionar_imagem_produto_rapido(
    produto_id: int,
    file: UploadFile = File(...),
    current_user: User = Depends(_get_current_ecommerce_user),
    db: Session = Depends(get_session),
):
    _, tenant_id = _get_funcionario_operacional_or_403(db, current_user)
    tenant_uuid = UUID(tenant_id)
    produto = (
        db.query(Produto)
        .filter(
            Produto.id == produto_id,
            Produto.tenant_id == tenant_uuid,
        )
        .with_for_update()
        .first()
    )
    if not produto:
        raise HTTPException(status_code=404, detail="Produto nao encontrado.")
    if file.content_type not in {"image/jpeg", "image/png", "image/webp"}:
        raise HTTPException(status_code=400, detail="Use fotos JPG, PNG ou WebP.")
    limite = int(settings.PRODUCT_IMAGE_UPLOAD_MAX_BYTES or 10 * 1024 * 1024)
    conteudo = file.file.read(limite + 1)
    if not conteudo or len(conteudo) > limite:
        raise HTTPException(
            status_code=400,
            detail=f"Envie uma foto de ate {limite // (1024 * 1024)} MB.",
        )

    token = f"app-{hashlib.sha256(conteudo).hexdigest()}"
    imagens = (
        db.query(ProdutoImagem)
        .filter(
            ProdutoImagem.produto_id == produto_id,
            ProdutoImagem.tenant_id == tenant_uuid,
        )
        .all()
    )
    # Uma resposta perdida pode ser reenviada sem duplicar arquivo ou galeria.
    existente = next(
        (item for item in imagens if item.url.endswith(f"/{token}.webp")), None
    )
    if existente:
        return existente
    if len(imagens) >= 5:
        raise HTTPException(
            status_code=400,
            detail="O cadastro pelo app permite ate 5 fotos. Complete a galeria no ERP.",
        )
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            preparada = prepare_product_image_variants(conteudo)
    except (
        ValueError,
        OSError,
        Image.DecompressionBombError,
        Image.DecompressionBombWarning,
    ) as exc:
        raise HTTPException(
            status_code=400,
            detail="Nao foi possivel ler a foto. Tente outra imagem JPG, PNG ou WebP.",
        ) from exc

    salva = None
    try:
        salva = save_product_image_variants(
            tenant_id=tenant_id,
            produto_id=produto_id,
            prepared_image=preparada,
            image_token=token,
        )
        principal = not produto.imagem_principal and not any(
            item.e_principal for item in imagens
        )
        imagem = ProdutoImagem(
            tenant_id=tenant_uuid,
            produto_id=produto_id,
            url=salva.url,
            ordem=max((item.ordem or 0 for item in imagens), default=0) + 1,
            e_principal=principal,
            tamanho=preparada.original_size_bytes,
            largura=preparada.width,
            altura=preparada.height,
        )
        db.add(imagem)
        if principal:
            produto.imagem_principal = imagem.url
        db.flush()
        resposta = ImagemUploadResponse.model_validate(imagem)
        db.commit()
        return resposta
    except Exception as exc:
        db.rollback()
        if salva:
            try:
                delete_product_image_assets(salva.url)
            except Exception:
                logger.exception("Falha ao remover foto sem registro no banco")
        logger.exception("Falha ao salvar foto de produto pelo app")
        raise HTTPException(
            status_code=503,
            detail="O produto esta salvo, mas a foto nao foi enviada. Tente enviar a foto novamente.",
        ) from exc
