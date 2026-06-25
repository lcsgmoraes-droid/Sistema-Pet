"""Rotas de cobertura, pendencias e criacao local a partir do Bling."""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user_and_tenant
from app.bling_integration import BlingAPI
from app.bling_sync.catalog_snapshots import (
    _get_resumo_cobertura_bling,
    _get_snapshot_faltantes_bling,
    _get_snapshot_sem_vinculo_com_match_bling,
    _invalidate_bling_snapshots,
)
from app.bling_sync.product_matching import (
    _barcode_bling,
    _produto_eh_pai,
    _produto_sincroniza_estoque,
    _sku_bling,
    _texto_limpo,
)
from app.bling_sync.routes_common import _upsert_sync_vinculo, utc_now
from app.bling_sync.schemas import CriarProdutoBlingFaltanteRequest
from app.db import get_session
from app.produtos_models import Produto, ProdutoBlingSync
from app.services.bling_nf_service import (
    buscar_produto_do_item,
    criar_produto_automatico_do_bling_por_item,
)
from app.services.bling_sync_service import BlingSyncService

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/health")
def health_sincronizacao(
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Resumo operacional da integração com o Bling."""
    _current_user, tenant_id = user_and_tenant
    return BlingSyncService.get_health_snapshot(db, tenant_id=tenant_id)


@router.get("/produtos-sem-vinculo")
def listar_produtos_sem_vinculo(
    busca: Optional[str] = Query(default=None),
    limit: int = Query(default=2000, ge=1, le=5000),
    offset: int = Query(default=0, ge=0),
    force_refresh: bool = Query(default=False),
    apenas_com_match_bling: bool = Query(default=True),
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Lista rápida de produtos sem vínculo, priorizando base Bling (com match no Bling)."""
    _current_user, tenant_id = user_and_tenant
    erro_coleta_bling = None
    fallback_local = False

    subq_vinculados = (
        db.query(ProdutoBlingSync.produto_id)
        .filter(
            ProdutoBlingSync.tenant_id == tenant_id,
            ProdutoBlingSync.bling_produto_id.isnot(None),
            ProdutoBlingSync.bling_produto_id != "",
        )
        .subquery()
    )

    query = (
        db.query(
            Produto.id,
            Produto.nome,
            Produto.codigo,
            Produto.estoque_atual,
        )
        .filter(
            Produto.tenant_id == tenant_id,
            Produto.tipo_produto != "PAI",
            Produto.codigo.isnot(None),
            Produto.codigo != "",
        )
        .filter(Produto.id.notin_(subq_vinculados))
    )

    termo = (busca or "").strip().lower()

    if apenas_com_match_bling:
        try:
            snapshot = _get_snapshot_sem_vinculo_com_match_bling(
                db,
                tenant_id=tenant_id,
                force_refresh=force_refresh,
            )
            itens_base = snapshot.get("items", [])

            if termo:
                itens_base = [
                    item
                    for item in itens_base
                    if termo in (item.get("nome") or "").lower()
                    or termo in (item.get("codigo") or "").lower()
                ]

            paginados = itens_base[offset : offset + limit]

            return {
                "items": paginados,
                "total": len(itens_base),
                "limit": limit,
                "offset": offset,
                "apenas_com_match_bling": True,
                "snapshot_disponivel": snapshot.get("snapshot_disponivel", True),
                "precisa_atualizar": snapshot.get("precisa_atualizar", False),
                "total_sem_vinculo_universo_local": snapshot.get(
                    "total_sem_vinculo_universo_local", 0
                ),
                "total_bling": snapshot.get("total_bling", 0),
                "coleta_bling_completa": snapshot.get("coleta_bling_completa", True),
                "cache_utilizado_por_falha": snapshot.get(
                    "cache_utilizado_por_falha", False
                ),
                "cache_idade_segundos": snapshot.get("cache_idade_segundos", 0),
                "atualizado_em": snapshot.get("atualizado_em"),
            }
        except Exception as e:
            fallback_local = True
            erro_coleta_bling = str(e)
            logger.warning(
                f"⚠️ Falha ao montar snapshot de produtos sem vínculo no Bling: {e}. Aplicando fallback local."
            )

    if termo:
        like = f"%{termo}%"
        query = query.filter(
            or_(
                Produto.nome.ilike(like),
                Produto.codigo.ilike(like),
            )
        )

    total = query.count()
    itens = query.order_by(Produto.id.asc()).offset(offset).limit(limit).all()

    return {
        "items": [
            {
                "id": item.id,
                "nome": item.nome,
                "codigo": item.codigo,
                "estoque_atual": float(item.estoque_atual or 0),
            }
            for item in itens
        ],
        "total": total,
        "limit": limit,
        "offset": offset,
        "apenas_com_match_bling": False,
        "fallback_local_por_erro_bling": fallback_local,
        "erro_coleta_bling": erro_coleta_bling,
        "snapshot_disponivel": False,
        "precisa_atualizar": True,
    }


@router.get("/resumo-cobertura")
def resumo_cobertura_bling(
    force_refresh: bool = Query(default=False),
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    Resumo de cobertura Bling -> CorePet.

    Regra de negócio: o universo principal é o Bling (online/marketplace).
    """
    _current_user, tenant_id = user_and_tenant
    try:
        normalizados = BlingSyncService.normalize_sync_states_from_latest_queue(
            db, tenant_id=tenant_id
        )
        if (normalizados.get("repaired_active") or 0) > 0 or (
            normalizados.get("repaired_error") or 0
        ) > 0:
            db.commit()
        return _get_resumo_cobertura_bling(
            db, tenant_id=tenant_id, force_refresh=force_refresh
        )
    except Exception as e:
        logger.error(f"❌ Erro ao gerar resumo de cobertura Bling: {e}")
        # Não quebrar a tela: retorna payload seguro quando falhar sem cache.
        return {
            "total_bling": 0,
            "bling_com_match_no_sistema": 0,
            "bling_sem_match_no_sistema": 0,
            "bling_sync_ok": 0,
            "bling_com_problema": 0,
            "sync_problemas_abertos": 0,
            "total_sistema": db.query(Produto)
            .filter(Produto.tenant_id == tenant_id, Produto.tipo_produto != "PAI")
            .count(),
            "somente_sistema": db.query(Produto)
            .filter(Produto.tenant_id == tenant_id, Produto.tipo_produto != "PAI")
            .count(),
            "coleta_bling_completa": False,
            "erro_coleta_bling": "Falha temporaria ao consultar Bling",
            "atualizado_em": utc_now(),
            "snapshot_disponivel": False,
            "precisa_atualizar": True,
        }


@router.get("/faltantes-bling")
def listar_faltantes_bling(
    force_refresh: bool = Query(default=False),
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    Retorna snapshot dos produtos existentes no Bling que não possuem match no CorePet.

    - Sem force_refresh: usa cache para responder rápido.
    - Com force_refresh: recalcula snapshot sob demanda.
    """
    _current_user, tenant_id = user_and_tenant

    try:
        snapshot = _get_snapshot_faltantes_bling(
            db, tenant_id=tenant_id, force_refresh=force_refresh
        )
    except Exception as e:
        logger.error(f"❌ Erro ao gerar snapshot de faltantes Bling: {e}")
        return {
            "items": [],
            "total": 0,
            "total_bling": 0,
            "snapshot_disponivel": False,
            "coleta_bling_completa": False,
            "precisa_atualizar": True,
            "erro_coleta_bling": "Falha temporária ao consultar o Bling",
            "atualizado_em": None,
            "limit": limit,
            "offset": offset,
        }

    itens = snapshot.get("items", [])
    paginados = itens[offset : offset + limit]

    return {
        "items": paginados,
        "total": snapshot.get("total", len(itens)),
        "total_bling": snapshot.get("total_bling", 0),
        "snapshot_disponivel": snapshot.get("snapshot_disponivel", True),
        "coleta_bling_completa": snapshot.get("coleta_bling_completa", True),
        "cache_utilizado_por_falha": snapshot.get("cache_utilizado_por_falha", False),
        "cache_idade_segundos": snapshot.get("cache_idade_segundos", 0),
        "atualizado_em": snapshot.get("atualizado_em"),
        "limit": limit,
        "offset": offset,
    }


@router.get("/dashboard")
def dashboard_pendencias_bling(
    force_refresh: bool = Query(default=False),
    limit: int = Query(default=200, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    Retorna os blocos principais da central do Bling em uma única resposta.

    Objetivo: evitar múltiplas requisições pesadas concorrendo entre si
    quando a tela abre ou quando o usuário pede atualização completa.
    """
    return {
        "resumo": resumo_cobertura_bling(
            force_refresh=force_refresh,
            db=db,
            user_and_tenant=user_and_tenant,
        ),
        "faltantes": listar_faltantes_bling(
            force_refresh=force_refresh,
            limit=limit,
            offset=offset,
            db=db,
            user_and_tenant=user_and_tenant,
        ),
        "vinculos": listar_produtos_sem_vinculo(
            busca=None,
            limit=limit,
            offset=offset,
            force_refresh=force_refresh,
            apenas_com_match_bling=True,
            db=db,
            user_and_tenant=user_and_tenant,
        ),
    }


@router.post("/faltantes-bling/criar")
def criar_produto_local_para_faltante_bling(
    body: CriarProdutoBlingFaltanteRequest,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    _current_user, tenant_id = user_and_tenant

    bling_id = _texto_limpo(body.bling_id)
    if not bling_id:
        raise HTTPException(status_code=400, detail="bling_id e obrigatorio")

    try:
        item_bling = BlingAPI().consultar_produto(bling_id)
    except Exception as e:
        raise HTTPException(
            status_code=400, detail=f"Erro ao consultar produto no Bling: {e}"
        ) from e

    if isinstance(item_bling, dict) and isinstance(item_bling.get("produto"), dict):
        item_bling = item_bling.get("produto") or {}

    if not isinstance(item_bling, dict) or not item_bling:
        raise HTTPException(status_code=404, detail="Produto do Bling nao encontrado")

    sku = _sku_bling(item_bling)
    codigo_barras = _barcode_bling(item_bling)

    produto = (
        buscar_produto_do_item(db=db, tenant_id=tenant_id, sku=sku) if sku else None
    )
    correspondencia_usada = "sku" if produto else None

    if not produto and codigo_barras:
        produto = buscar_produto_do_item(db=db, tenant_id=tenant_id, sku=codigo_barras)
        correspondencia_usada = "codigo_barras" if produto else None

    if not produto:
        produto = criar_produto_automatico_do_bling_por_item(
            db=db,
            tenant_id=tenant_id,
            item_bling=item_bling,
            sku_preferencial=sku or codigo_barras or bling_id,
        )
        correspondencia_usada = "autocadastro"

    if not produto:
        raise HTTPException(
            status_code=400,
            detail="Nao foi possivel criar o produto local a partir do Bling",
        )

    conflito_bling = (
        db.query(ProdutoBlingSync)
        .filter(
            ProdutoBlingSync.tenant_id == tenant_id,
            ProdutoBlingSync.bling_produto_id == bling_id,
            ProdutoBlingSync.produto_id != produto.id,
        )
        .first()
    )
    if conflito_bling:
        raise HTTPException(
            status_code=409,
            detail=f"Esse item do Bling ja esta vinculado ao produto local {conflito_bling.produto_id}.",
        )

    sync_existente = (
        db.query(ProdutoBlingSync)
        .filter(
            ProdutoBlingSync.tenant_id == tenant_id,
            ProdutoBlingSync.produto_id == produto.id,
        )
        .first()
    )
    if sync_existente and _texto_limpo(sync_existente.bling_produto_id) not in {
        "",
        bling_id,
    }:
        raise HTTPException(
            status_code=409,
            detail=(
                f"O produto local {produto.codigo} ja esta vinculado a outro item do Bling "
                f"({sync_existente.bling_produto_id})."
            ),
        )

    _upsert_sync_vinculo(db, tenant_id, produto, bling_id)
    db.commit()
    _invalidate_bling_snapshots(tenant_id)

    return {
        "message": (
            "Produto PAI vinculado para catalogo. O estoque ficara sem sincronizacao automatica."
            if _produto_eh_pai(produto)
            else "Produto preparado para sincronizacao com sucesso"
        ),
        "produto_id": produto.id,
        "produto_codigo": produto.codigo,
        "produto_nome": produto.nome,
        "bling_produto_id": bling_id,
        "acao": "vinculado_existente"
        if correspondencia_usada in {"sku", "codigo_barras"}
        else "criado_e_vinculado",
        "correspondencia_usada": correspondencia_usada,
        "sincronizar_estoque": _produto_sincroniza_estoque(produto),
    }
