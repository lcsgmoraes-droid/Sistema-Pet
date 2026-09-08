"""Pausa operacional por produto; preserva identidade e politica de estoque."""

import logging

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, ConfigDict, StrictBool
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user_and_tenant
from app.db import get_session
from app.produtos.validators import _validar_tenant_e_obter_usuario
from app.produtos_models import Produto, ProdutoBlingSync
from app.security.permissions_decorator import require_permission
from app.services.produto_bling_identity_service import (
    produto_arquivado,
    vinculo_retirado,
)
from app.bling_sync.routes_common import utc_now

router = APIRouter()
logger = logging.getLogger(__name__)


class HabilitacaoSyncRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    sincronizar: StrictBool


def _carregar(db, tenant_id, produto_id, *, lock=False):
    products = db.query(Produto).filter(
        Produto.id == produto_id, Produto.tenant_id == tenant_id
    )
    if lock:
        products = products.populate_existing().with_for_update(of=Produto)
    produto = products.first()
    if produto is None:
        raise HTTPException(
            status_code=404, detail="Produto nao encontrado neste tenant."
        )
    links = db.query(ProdutoBlingSync).filter(
        ProdutoBlingSync.produto_id == produto_id,
        ProdutoBlingSync.tenant_id == tenant_id,
    )
    if lock:
        links = links.populate_existing().with_for_update(of=ProdutoBlingSync)
    return produto, links.first()


def _resposta(produto, sync):
    return {
        "produto_id": produto.id,
        "produto_nome": produto.nome,
        "sku": produto.codigo,
        "vinculado": bool(sync and str(sync.bling_produto_id or "").strip()),
        "sincronizar": bool(sync and sync.sincronizar),
        "bling_produto_id": sync.bling_produto_id if sync else None,
        "estoque_compartilhado": sync.estoque_compartilhado if sync else None,
        "status": sync.status if sync else "sem_vinculo",
        "retirado": produto_arquivado(produto) or vinculo_retirado(sync),
    }


@router.get("/habilitacao/{produto_id}")
@require_permission("produtos.editar")
def obter_habilitacao_bling(
    produto_id: int,
    response: Response,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    _, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)
    response.headers["Cache-Control"] = "no-store"
    produto, sync = _carregar(db, tenant_id, produto_id)
    return _resposta(produto, sync)


@router.patch("/habilitacao/{produto_id}")
@require_permission("produtos.editar")
def alterar_habilitacao_bling(
    produto_id: int,
    payload: HabilitacaoSyncRequest,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)
    produto, sync = _carregar(db, tenant_id, produto_id, lock=True)
    if produto_arquivado(produto) or vinculo_retirado(sync):
        raise HTTPException(
            status_code=409, detail="Origem retirada por fusao; nao pode ser reativada."
        )
    if sync is None or not str(sync.bling_produto_id or "").strip():
        raise HTTPException(
            status_code=409, detail="Produto sem vinculo Bling para pausar ou retomar."
        )
    if bool(sync.sincronizar) != payload.sincronizar:
        sync.sincronizar = payload.sincronizar
        sync.status = "ativo" if payload.sincronizar else "pausado"
        sync.updated_at = utc_now()
        logger.info(
            "Habilitacao Bling alterada tenant=%s produto=%s operador=%s sincronizar=%s",
            tenant_id,
            produto_id,
            user.id,
            payload.sincronizar,
        )
    db.commit()
    return _resposta(produto, sync)
