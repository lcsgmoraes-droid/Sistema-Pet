"""Rotas de atualizacao rapida, exclusao e ativacao de produtos."""

import json
import logging
from datetime import datetime
from typing import Optional
from uuid import UUID
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user_and_tenant
from app.db import get_session
from app.audit_log import log_action
from app.produto_identity_models import ProdutoSkuAlias
from app.produtos.core import _aplicar_status_ativo_produto
from app.produtos.schemas import ProdutoAtivoUpdate, ProdutoResponse
from app.produtos.validators import (
    _obter_produto_ou_404,
    _validar_pode_inativar_produto,
    _validar_sku_unico,
    _validar_tenant_e_obter_usuario,
)
from app.produtos_models import Produto
from app.security.permissions_decorator import require_permission
from app.services.produto_alias_service import _lock_alias_namespace
from app.services.produto_sku_service import normalizar_sku
from app.services.kit_custo_service import KitCustoService
from app.grupo_comercial_estoque_compartilhado_service import (
    GrupoComercialEstoqueCompartilhadoService,
)
from app.tenancy.context import set_current_tenant

router = APIRouter()
logger = logging.getLogger(__name__)


def _liberar_sku_produto(db: Session, produto: Produto, tenant_id, user_id: int):
    """Desocupa a identidade comercial sem apagar o cadastro nem o historico por ID."""
    sku_antigo = str(produto.codigo or "").strip()
    if sku_antigo.startswith(f"__LIBERADO__{produto.id}__"):
        return None

    codigo_interno = f"__LIBERADO__{produto.id}__{uuid4().hex[:16]}"
    _validar_sku_unico(db, codigo_interno, tenant_id, produto_id=produto.id)
    chave_antiga = normalizar_sku(sku_antigo)
    codigos_alternativos = produto.codigos_barras_alternativos
    try:
        alternativos = json.loads(codigos_alternativos) if codigos_alternativos else []
    except (TypeError, ValueError):
        alternativos = [codigos_alternativos]
    if not isinstance(alternativos, list):
        alternativos = [alternativos]
    alternativos_filtrados = [
        codigo for codigo in alternativos if normalizar_sku(codigo) != chave_antiga
    ]
    if normalizar_sku(produto.codigo_barras) == chave_antiga:
        produto.codigo_barras = None
    if alternativos_filtrados != alternativos:
        produto.codigos_barras_alternativos = json.dumps(alternativos_filtrados)
    db.query(ProdutoSkuAlias).filter(
        ProdutoSkuAlias.tenant_id == tenant_id,
        ProdutoSkuAlias.produto_id == produto.id,
        ProdutoSkuAlias.sku_normalizado == chave_antiga,
    ).delete(synchronize_session=False)
    produto.codigo = codigo_interno
    produto.updated_at = datetime.utcnow()
    log_action(
        db,
        user_id,
        "release_product_sku",
        entity_type="product",
        entity_id=produto.id,
        old_value={"codigo": sku_antigo},
        new_value={"codigo": codigo_interno},
        tenant_id=tenant_id,
        commit=False,
    )
    return sku_antigo


@router.patch("/{produto_id}")
def atualizar_preco_produto(
    produto_id: int,
    preco_venda: Optional[float] = None,
    preco_custo: Optional[float] = None,
    preco_promocional: Optional[float] = None,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Atualiza apenas o preço de um produto (edição rápida)"""

    current_user, tenant_solicitante_id = user_and_tenant
    acesso_catalogo = GrupoComercialEstoqueCompartilhadoService.resolver_produto_catalogo(
        db, tenant_solicitante_id, produto_id
    )
    tenant_id = UUID(str(acesso_catalogo.tenant_origem_id))
    set_current_tenant(tenant_id)
    logger.info(f"🏷️ Atualizando preço do produto {produto_id}")

    produto = (
        db.query(Produto)
        .filter(Produto.id == produto_id, Produto.tenant_id == tenant_id)
        .first()
    )

    if not produto:
        raise HTTPException(status_code=404, detail="Produto não encontrado")

    # Atualizar apenas os preços fornecidos
    if preco_venda is not None:
        produto.preco_venda = preco_venda
    if preco_custo is not None:
        produto.preco_custo = preco_custo
        KitCustoService.recalcular_kits_que_usam_produto(db, produto.id)
    if preco_promocional is not None:
        produto.preco_promocional = preco_promocional

    produto.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(produto)

    logger.info(f"✅ Preço atualizado: PV={produto.preco_venda}")

    return {
        "id": produto.id,
        "preco_venda": produto.preco_venda,
        "preco_custo": produto.preco_custo,
        "preco_promocional": produto.preco_promocional,
    }


@router.delete("/{produto_id}", status_code=status.HTTP_204_NO_CONTENT)
def deletar_produto(
    produto_id: int,
    liberar_sku: bool = False,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Deleta (soft delete) um produto"""

    current_user, tenant_solicitante_id = _validar_tenant_e_obter_usuario(
        user_and_tenant
    )
    acesso_catalogo = GrupoComercialEstoqueCompartilhadoService.resolver_produto_catalogo(
        db, tenant_solicitante_id, produto_id
    )
    tenant_id = UUID(str(acesso_catalogo.tenant_origem_id))
    set_current_tenant(tenant_id)
    if liberar_sku:
        _lock_alias_namespace(db, tenant_id)

    query = db.query(Produto).filter(
        Produto.id == produto_id, Produto.tenant_id == tenant_id
    )
    produto = (
        query.with_for_update().populate_existing().first()
        if liberar_sku
        else query.first()
    )

    if not produto:
        raise HTTPException(status_code=404, detail="Produto não encontrado")

    _validar_pode_inativar_produto(db, produto, tenant_id)

    # Soft delete
    _aplicar_status_ativo_produto(produto, False)
    if liberar_sku:
        _liberar_sku_produto(db, produto, tenant_id, current_user.id)

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
    """Ativa ou desativa produto sem removê-lo do sistema."""

    current_user, tenant_solicitante_id = _validar_tenant_e_obter_usuario(
        user_and_tenant
    )
    if payload.ativo and payload.liberar_sku:
        raise HTTPException(
            status_code=400, detail="Para liberar o SKU, inative o produto."
        )
    acesso_catalogo = GrupoComercialEstoqueCompartilhadoService.resolver_produto_catalogo(
        db, tenant_solicitante_id, produto_id
    )
    tenant_id = UUID(str(acesso_catalogo.tenant_origem_id))
    set_current_tenant(tenant_id)
    if payload.liberar_sku:
        _lock_alias_namespace(db, tenant_id)
        produto = (
            db.query(Produto)
            .filter(Produto.id == produto_id, Produto.tenant_id == tenant_id)
            .with_for_update()
            .populate_existing()
            .first()
        )
        if not produto:
            raise HTTPException(status_code=404, detail="Produto nao encontrado")
    else:
        produto = _obter_produto_ou_404(db, produto_id, tenant_id)

    if payload.ativo == bool(produto.ativo) and not payload.liberar_sku:
        return produto

    if not payload.ativo:
        _validar_pode_inativar_produto(db, produto, tenant_id)

    _aplicar_status_ativo_produto(produto, payload.ativo)
    if payload.liberar_sku:
        _liberar_sku_produto(db, produto, tenant_id, current_user.id)

    db.commit()
    db.refresh(produto)

    logger.info(
        "🔁 Produto %s #%s com status alterado para %s",
        produto.nome,
        produto.id,
        "ativo" if payload.ativo else "inativo",
    )

    return produto
