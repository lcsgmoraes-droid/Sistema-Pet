"""Rotas operacionais de envio, status e reconciliacao do sync Bling."""

from __future__ import annotations

import logging
import threading
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user_and_tenant
from app.bling_integration import BlingAPI
from app.bling_sync.product_matching import _coerce_float
from app.bling_sync.routes_common import PRODUTO_NAO_ENCONTRADO, utc_now
from app.bling_sync.schemas import ReconciliarBatchRequest, SyncStatusResponse
from app.bling_sync.status_queries import _build_sync_problem_query
from app.db import get_session
from app.produtos_models import (
    EstoqueMovimentacao,
    Produto,
    ProdutoBlingSync,
    ProdutoBlingSyncQueue,
)
from app.services.bling_sync_service import BlingSyncService

logger = logging.getLogger(__name__)
router = APIRouter()

_reconciliacao_geral_lock = threading.Lock()
_reconciliacao_geral_estado = {
    "running": False,
    "started_at": None,
    "finished_at": None,
    "result": None,
}


def _executar_reconciliacao_geral_em_background(
    limit: Optional[int], tenant_id
) -> None:
    try:
        resultado = BlingSyncService.reconcile_all_products(
            limit=limit, tenant_id=tenant_id
        )
        with _reconciliacao_geral_lock:
            _reconciliacao_geral_estado["result"] = {
                "ok": True,
                **resultado,
            }
    except Exception as error:
        logger.exception("❌ Erro na reconciliação geral em background")
        with _reconciliacao_geral_lock:
            _reconciliacao_geral_estado["result"] = {
                "ok": False,
                "erro": str(error),
            }
    finally:
        with _reconciliacao_geral_lock:
            _reconciliacao_geral_estado["running"] = False
            _reconciliacao_geral_estado["finished_at"] = utc_now()


@router.post("/enviar/{produto_id}")
def enviar_estoque_para_bling(
    produto_id: int,
    force: bool = Query(default=False),
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    Envia estoque atual do produto para o Bling
    Usado após vendas na loja física
    """
    logger.info(
        f"📤 Enviando estoque para Bling - Produto {produto_id} (force={force})"
    )

    resultado = BlingSyncService.force_sync_now(
        produto_id=produto_id,
        motivo="forcar_manual" if force else "envio_manual",
    )
    if not resultado.get("ok"):
        if resultado.get("auth_invalid"):
            raise HTTPException(
                status_code=409,
                detail=resultado.get("detail")
                or "Reconecte o Bling antes de tentar novo envio.",
            )
        if resultado.get("rate_limited"):
            return {
                "message": resultado.get("erro")
                or "Bling limitou as requisicoes agora. O item foi reagendado automaticamente.",
                **resultado,
            }
        raise HTTPException(
            status_code=400,
            detail=resultado.get("detail")
            or resultado.get("erro")
            or "Falha ao sincronizar",
        )

    return {
        "message": "Estoque enviado para Bling com sucesso",
        "produto_id": produto_id,
        "bling_produto_id": resultado.get("bling_produto_id"),
        "estoque_enviado": resultado.get("estoque_enviado"),
        "queue_id": resultado.get("queue_id"),
    }


@router.post("/forcar/{produto_id}")
def forcar_sincronizacao_produto(
    produto_id: int,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Força o envio imediato do estoque de um único produto."""
    resultado = BlingSyncService.force_sync_now(
        produto_id=produto_id, motivo="botao_forcar_sync"
    )
    if not resultado.get("ok"):
        if resultado.get("auth_invalid"):
            raise HTTPException(
                status_code=409,
                detail=resultado.get("detail")
                or "Reconecte o Bling antes de tentar novo envio.",
            )
        if resultado.get("rate_limited"):
            return {
                "message": resultado.get("erro")
                or "Bling limitou as requisicoes agora. O item foi reagendado automaticamente.",
                **resultado,
            }
        raise HTTPException(
            status_code=400,
            detail=resultado.get("detail")
            or resultado.get("erro")
            or "Falha ao forçar sincronização",
        )
    return {
        "message": "Sincronização forçada concluída",
        **resultado,
    }


# ============================================================================
# STATUS DE SINCRONIZAÇÃO
# ============================================================================


@router.get("/status", response_model=List[SyncStatusResponse])
def status_sincronizacao(
    apenas_divergencias: bool = False,
    busca: Optional[str] = Query(default=None),
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    Lista status de sincronização de todos os produtos

    - apenas_divergencias: Se TRUE, mostra apenas produtos com divergência de estoque
    """
    logger.info("📊 Consultando status de sincronização")
    _current_user, tenant_id = user_and_tenant

    # Buscar produtos com sincronização configurada
    query = (
        db.query(Produto, ProdutoBlingSync)
        .join(ProdutoBlingSync, Produto.id == ProdutoBlingSync.produto_id)
        .filter(
            Produto.tenant_id == tenant_id,
            ProdutoBlingSync.tenant_id == tenant_id,
            ProdutoBlingSync.sincronizar.is_(True),
        )
    )

    if busca:
        termo = f"%{busca}%"
        query = query.filter(
            or_(
                Produto.nome.ilike(termo),
                Produto.codigo.ilike(termo),
                ProdutoBlingSync.bling_produto_id.ilike(termo),
            )
        )

    resultados = []

    for produto, sync in query.all():
        fila = (
            db.query(ProdutoBlingSyncQueue)
            .filter(
                ProdutoBlingSyncQueue.produto_id == produto.id,
                ProdutoBlingSyncQueue.tenant_id == tenant_id,
            )
            .order_by(ProdutoBlingSyncQueue.updated_at.desc())
            .first()
        )

        # Usar dados cacheados para manter endpoint rápido e evitar rate-limit/timeout.
        estoque_bling = sync.ultimo_estoque_bling
        divergencia = sync.ultima_divergencia

        # Filtrar divergências se solicitado
        if apenas_divergencias and divergencia is not None and abs(divergencia) < 0.01:
            continue

        resultados.append(
            SyncStatusResponse(
                produto_id=produto.id,
                produto_nome=produto.nome,
                sku=produto.codigo,
                estoque_sistema=produto.estoque_atual or 0,
                estoque_bling=estoque_bling,
                divergencia=divergencia,
                sincronizado=sync.sincronizar,
                bling_produto_id=sync.bling_produto_id,
                ultima_sincronizacao=sync.ultima_sincronizacao,
                status=sync.status,
                ultima_tentativa_sync=sync.ultima_tentativa_sync,
                proxima_tentativa_sync=sync.proxima_tentativa_sync,
                ultima_conferencia_bling=sync.ultima_conferencia_bling,
                ultima_sincronizacao_sucesso=sync.ultima_sincronizacao_sucesso,
                ultimo_estoque_bling=sync.ultimo_estoque_bling,
                tentativas_sync=sync.tentativas_sync or 0,
                ultimo_erro=sync.erro_mensagem or (fila.ultimo_erro if fila else None),
                queue_id=fila.id if fila else None,
                queue_status=fila.status if fila else None,
            )
        )

    logger.info(f"✅ {len(resultados)} produtos em sincronização")
    return resultados


@router.get("/status-problemas", response_model=List[SyncStatusResponse])
def status_sincronizacao_problemas(
    busca: Optional[str] = Query(default=None),
    limit: int = Query(default=300, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Retorna apenas itens com pendencias de sincronizacao, sem N+1 de fila."""
    logger.info("Consultando status de sincronizacao com filtro de problemas")
    _current_user, tenant_id = user_and_tenant

    normalizados = BlingSyncService.normalize_sync_states_from_latest_queue(
        db, tenant_id=tenant_id
    )
    if (normalizados.get("repaired_active") or 0) > 0 or (
        normalizados.get("repaired_error") or 0
    ) > 0:
        db.commit()

    query, fila_atual = _build_sync_problem_query(
        db,
        tenant_id=tenant_id,
        busca=busca,
    )

    resultados = []
    for produto, sync, fila in (
        query.order_by(ProdutoBlingSync.updated_at.desc(), Produto.id.asc())
        .offset(offset)
        .limit(limit)
        .all()
    ):
        resultados.append(
            SyncStatusResponse(
                produto_id=produto.id,
                produto_nome=produto.nome,
                sku=produto.codigo,
                estoque_sistema=produto.estoque_atual or 0,
                estoque_bling=sync.ultimo_estoque_bling,
                divergencia=sync.ultima_divergencia,
                sincronizado=sync.sincronizar,
                bling_produto_id=sync.bling_produto_id,
                ultima_sincronizacao=sync.ultima_sincronizacao,
                status=sync.status,
                ultima_tentativa_sync=sync.ultima_tentativa_sync,
                proxima_tentativa_sync=sync.proxima_tentativa_sync,
                ultima_conferencia_bling=sync.ultima_conferencia_bling,
                ultima_sincronizacao_sucesso=sync.ultima_sincronizacao_sucesso,
                ultimo_estoque_bling=sync.ultimo_estoque_bling,
                tentativas_sync=sync.tentativas_sync or 0,
                ultimo_erro=sync.erro_mensagem or (fila.ultimo_erro if fila else None),
                queue_id=fila.id if fila else None,
                queue_status=fila.status if fila else None,
            )
        )

    logger.info("Status de problemas retornado com %s item(ns)", len(resultados))
    return resultados


@router.post("/reprocessar-falhas")
def reprocessar_falhas(
    body: Optional[ReconciliarBatchRequest] = None,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Reagenda imediatamente os itens com erro para nova tentativa."""
    limite = body.limit if body else 100
    _current_user, tenant_id = user_and_tenant
    resultado = BlingSyncService.reprocess_failed_syncs(
        limit=limite, tenant_id=tenant_id
    )
    if resultado.get("auth_invalid"):
        raise HTTPException(
            status_code=409,
            detail=resultado.get("detail")
            or "Reconecte o Bling antes de reprocessar as falhas.",
        )
    return resultado


@router.post("/reconciliar-recentes")
def reconciliar_recentes(
    body: ReconciliarBatchRequest,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Confere novamente produtos alterados recentemente ou com erro."""
    _current_user, tenant_id = user_and_tenant
    return BlingSyncService.reconcile_recent_products(
        minutes=body.minutes,
        limit=body.limit,
        tenant_id=tenant_id,
    )


@router.post("/reconciliar-geral")
def reconciliar_geral(
    body: Optional[ReconciliarBatchRequest] = None,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Inicia auditoria ampla em segundo plano para evitar travamento por timeout."""
    limite = body.limit if body else None
    _current_user, tenant_id = user_and_tenant

    with _reconciliacao_geral_lock:
        if _reconciliacao_geral_estado["running"]:
            return {
                "status": "running",
                "message": "Auditoria geral já está em execução",
                "started_at": _reconciliacao_geral_estado["started_at"],
            }

        _reconciliacao_geral_estado["running"] = True
        _reconciliacao_geral_estado["started_at"] = utc_now()
        _reconciliacao_geral_estado["finished_at"] = None
        _reconciliacao_geral_estado["result"] = None

    worker = threading.Thread(
        target=_executar_reconciliacao_geral_em_background,
        args=(limite, tenant_id),
        daemon=True,
    )
    worker.start()

    return {
        "status": "started",
        "message": "Auditoria geral iniciada em segundo plano",
        "limit": limite,
        "started_at": _reconciliacao_geral_estado["started_at"],
    }


@router.get("/reconciliar-geral/status")
def status_reconciliar_geral(
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Retorna status da auditoria geral em background."""
    with _reconciliacao_geral_lock:
        return {
            "running": _reconciliacao_geral_estado["running"],
            "started_at": _reconciliacao_geral_estado["started_at"],
            "finished_at": _reconciliacao_geral_estado["finished_at"],
            "result": _reconciliacao_geral_estado["result"],
        }


# ============================================================================
# RECONCILIAR DIVERGÊNCIAS
# ============================================================================


@router.post("/reconciliar/{produto_id}")
def reconciliar_estoque(
    produto_id: int,
    origem: str = Query(
        default="sistema", description="Origem: sistema, bling ou manual"
    ),
    valor_manual: Optional[float] = Query(
        default=None, description="Valor manual para ajuste"
    ),
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    Reconciliar divergência de estoque

    Opções:
    - origem=sistema: Usa valor do sistema → envia para Bling
    - origem=bling: Busca valor do Bling → atualiza sistema
    - origem=manual: Usa valor_manual → atualiza ambos
    """
    logger.info("Reconciliando estoque manual")

    current_user, _tenant = user_and_tenant

    if origem == "sistema":
        resultado = BlingSyncService.reconcile_product(
            produto_id=produto_id, force_sync=True
        )
        if not resultado.get("ok"):
            raise HTTPException(
                status_code=400, detail=resultado.get("detail") or "Erro ao reconciliar"
            )
        return {
            "message": "Reconciliação executada com sucesso",
            **resultado,
        }

    # Buscar produto e sync
    produto = db.query(Produto).filter(Produto.id == produto_id).first()
    if not produto:
        raise HTTPException(status_code=404, detail=PRODUTO_NAO_ENCONTRADO)

    sync = (
        db.query(ProdutoBlingSync)
        .filter(ProdutoBlingSync.produto_id == produto_id)
        .first()
    )

    if not sync or not sync.bling_produto_id:
        raise HTTPException(
            status_code=400, detail="Produto não configurado para sincronização"
        )

    try:
        bling = BlingAPI()
        estoque_anterior = produto.estoque_atual or 0
        estoque_novo = None

        if origem == "sistema":
            # Usa valor do sistema
            estoque_novo = estoque_anterior
            bling.atualizar_estoque_produto(sync.bling_produto_id, estoque_novo)
            logger.info(f"✅ Sistema → Bling: {estoque_novo}")

        elif origem == "bling":
            # Busca valor do Bling (saldo físico real)
            saldo = bling.consultar_saldo_estoque(sync.bling_produto_id)
            estoque_novo = _coerce_float(saldo.get("saldoFisicoTotal", 0))
            produto.estoque_atual = estoque_novo
            logger.info(f"✅ Bling → Sistema: {estoque_novo}")

        elif origem == "manual":
            if valor_manual is None:
                raise HTTPException(
                    status_code=400,
                    detail="valor_manual é obrigatório para origem=manual",
                )
            estoque_novo = valor_manual
            produto.estoque_atual = estoque_novo
            bling.atualizar_estoque_produto(sync.bling_produto_id, estoque_novo)
            logger.info(f"✅ Manual → Ambos: {estoque_novo}")

        else:
            raise HTTPException(
                status_code=400, detail="origem deve ser: sistema, bling ou manual"
            )

        # Registrar movimentação de ajuste
        if origem in ["bling", "manual"] and estoque_novo != estoque_anterior:
            diferenca = estoque_novo - estoque_anterior
            movimentacao = EstoqueMovimentacao(
                produto_id=produto.id,
                tipo="entrada" if diferenca > 0 else "saida",
                motivo="ajuste_reconciliacao",
                quantidade=abs(diferenca),
                quantidade_anterior=estoque_anterior,
                quantidade_nova=estoque_novo,
                observacao=f"Reconciliação Bling - Origem: {origem}",
                user_id=current_user.id,
            )
            db.add(movimentacao)

        # Atualizar sync
        sync.ultima_sincronizacao = utc_now()
        sync.status = "ativo"
        sync.erro_mensagem = None

        db.commit()

        return {
            "message": "Estoque reconciliado com sucesso",
            "produto_id": produto_id,
            "estoque_anterior": estoque_anterior,
            "estoque_novo": estoque_novo,
            "diferenca": estoque_novo - estoque_anterior,
            "origem": origem,
        }

    except Exception as e:
        logger.error(f"❌ Erro ao reconciliar: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Erro ao reconciliar: {str(e)}")
