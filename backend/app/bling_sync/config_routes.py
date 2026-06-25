"""Rotas de configuracao e vinculo unitario do sync Bling."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user_and_tenant
from app.bling_integration import BlingAPI
from app.bling_sync.catalog_snapshots import _invalidate_bling_snapshots
from app.bling_sync.product_matching import _produto_eh_pai, _produto_sincroniza_estoque
from app.bling_sync.routes_common import (
    PRODUTO_NAO_ENCONTRADO,
    _buscar_item_bling_para_vinculo,
    _upsert_sync_vinculo,
    utc_now,
)
from app.bling_sync.schemas import ConfigSyncRequest, VincularProdutoRequest
from app.db import get_session
from app.produtos_models import Produto, ProdutoBlingSync

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/config")
def configurar_sincronizacao(
    config: ConfigSyncRequest,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    Configurar sincronização de produto com Bling

    - bling_produto_id: ID do produto no Bling (ou None para buscar automaticamente)
    - sincronizar: Se TRUE, sincroniza estoque automaticamente
    - estoque_compartilhado: Se TRUE, estoque é único (loja + online)
    """
    logger.info(f"⚙️ Configurando sync - Produto {config.produto_id}")

    _current_user, tenant_id = user_and_tenant

    # Verificar se produto existe
    produto = (
        db.query(Produto)
        .filter(
            Produto.id == config.produto_id,
            Produto.tenant_id == tenant_id,
        )
        .first()
    )
    if not produto:
        raise HTTPException(status_code=404, detail=PRODUTO_NAO_ENCONTRADO)

    # Buscar ou criar configuração
    sync = (
        db.query(ProdutoBlingSync)
        .filter(
            ProdutoBlingSync.produto_id == config.produto_id,
            ProdutoBlingSync.tenant_id == tenant_id,
        )
        .first()
    )

    if not sync:
        sync = ProdutoBlingSync(
            tenant_id=produto.tenant_id, produto_id=config.produto_id
        )
        db.add(sync)

    # Atualizar configuração
    sync.bling_produto_id = config.bling_produto_id
    sync.sincronizar = config.sincronizar
    sync.estoque_compartilhado = config.estoque_compartilhado
    sync.status = "ativo" if config.sincronizar else "pausado"
    sync.updated_at = utc_now()

    # Se não tem bling_produto_id, tentar buscar automaticamente
    if not sync.bling_produto_id and config.sincronizar:
        try:
            # Buscar no Bling por SKU ou código de barras
            bling = BlingAPI()
            resultado = bling.listar_produtos(
                codigo=produto.codigo_barras, sku=produto.codigo
            )

            produtos_bling = resultado.get("data", [])
            if produtos_bling and len(produtos_bling) > 0:
                sync.bling_produto_id = str(produtos_bling[0].get("id"))
                logger.info(
                    f"✅ Produto vinculado automaticamente: Bling ID {sync.bling_produto_id}"
                )
            else:
                sync.status = "erro"
                sync.erro_mensagem = "Produto não encontrado no Bling"
                logger.warning("⚠️ Produto não encontrado no Bling")
        except Exception as e:
            logger.error(f"❌ Erro ao buscar produto no Bling: {e}")
            sync.status = "erro"
            sync.erro_mensagem = str(e)

    db.commit()
    _invalidate_bling_snapshots(tenant_id)
    db.refresh(sync)

    return {
        "message": "Sincronização configurada com sucesso",
        "produto_id": sync.produto_id,
        "bling_produto_id": sync.bling_produto_id,
        "sincronizar": sync.sincronizar,
        "status": sync.status,
    }


@router.post("/vincular")
def vincular_produto_bling(
    body: VincularProdutoRequest,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Vincula manualmente um produto local a um produto do Bling."""
    _current_user, tenant_id = user_and_tenant

    produto = (
        db.query(Produto)
        .filter(
            Produto.id == body.produto_id,
            Produto.tenant_id == tenant_id,
        )
        .first()
    )
    if not produto:
        raise HTTPException(status_code=404, detail=PRODUTO_NAO_ENCONTRADO)

    sync = (
        db.query(ProdutoBlingSync)
        .filter(
            ProdutoBlingSync.produto_id == body.produto_id,
            ProdutoBlingSync.tenant_id == tenant_id,
        )
        .first()
    )

    if not sync:
        sync = ProdutoBlingSync(
            tenant_id=produto.tenant_id,
            produto_id=produto.id,
        )
        db.add(sync)

    _upsert_sync_vinculo(db, tenant_id, produto, str(body.bling_id))

    db.commit()
    _invalidate_bling_snapshots(tenant_id)
    return {
        "message": (
            "Produto PAI vinculado para catalogo. O estoque ficara sem sincronizacao automatica."
            if _produto_eh_pai(produto)
            else "Produto vinculado com sucesso"
        ),
        "produto_id": produto.id,
        "bling_produto_id": str(body.bling_id),
        "sincronizar_estoque": _produto_sincroniza_estoque(produto),
    }


@router.post("/vincular-automatico/{produto_id}")
def vincular_produto_bling_automatico(
    produto_id: int,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Tenta vincular automaticamente um produto local ao Bling pelo código/SKU."""
    _current_user, tenant_id = user_and_tenant

    produto = (
        db.query(Produto)
        .filter(Produto.id == produto_id, Produto.tenant_id == tenant_id)
        .first()
    )
    if not produto:
        raise HTTPException(status_code=404, detail=PRODUTO_NAO_ENCONTRADO)

    bling = BlingAPI()

    codigo_busca = (produto.codigo or "").strip()
    nome_busca = (produto.nome or "").strip()
    codigos_extras = [
        (produto.codigo_barras or "").strip(),
        (produto.gtin_ean or "").strip(),
        (produto.gtin_ean_tributario or "").strip(),
    ]

    item_escolhido = _buscar_item_bling_para_vinculo(
        bling,
        codigo_busca,
        nome_busca,
        codigos_extras=codigos_extras,
    )

    if not item_escolhido:
        raise HTTPException(
            status_code=404,
            detail="Produto não encontrado no Bling para vínculo automático",
        )

    bling_id = str(item_escolhido.get("id") or "").strip()
    if not bling_id:
        raise HTTPException(
            status_code=400, detail="Resposta do Bling sem ID de produto"
        )

    _upsert_sync_vinculo(db, tenant_id, produto, bling_id)

    db.commit()
    _invalidate_bling_snapshots(tenant_id)

    return {
        "message": (
            "Produto PAI vinculado para catalogo. O estoque ficara sem sincronizacao automatica."
            if _produto_eh_pai(produto)
            else "Produto vinculado automaticamente com sucesso"
        ),
        "produto_id": produto.id,
        "bling_produto_id": bling_id,
        "sincronizar_estoque": _produto_sincroniza_estoque(produto),
    }
