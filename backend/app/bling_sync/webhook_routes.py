"""Webhook e vinculo em massa do sync Bling."""

from __future__ import annotations

import logging
import time

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user_and_tenant
from app.bling_sync.catalog_snapshots import (
    _get_snapshot_sem_vinculo_com_match_bling,
    _remover_ids_do_snapshot_sem_vinculo_cache,
)
from app.bling_sync.product_matching import (
    _produto_sincroniza_estoque,
    _tipo_produto_local,
)
from app.bling_sync.routes_common import _upsert_sync_vinculo, utc_now
from app.db import get_session
from app.produtos_models import EstoqueMovimentacao, Produto, ProdutoBlingSync
from app.services.bling_sync_service import BlingSyncService

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/webhook/bling")
async def webhook_bling(request: Request, db: Session = Depends(get_session)):
    """
    Webhook para receber notificações do Bling

    Eventos suportados:
    - Venda criada: Baixa estoque no sistema
    - Venda cancelada: Retorna estoque ao sistema
    """
    try:
        body = await request.json()
        logger.info(f"📥 Webhook Bling recebido: {body}")

        evento = body.get("topic")
        dados = body.get("data", {})

        if evento == "vendas.created":
            # Venda online criada - baixar estoque
            venda_id = dados.get("id")
            itens = dados.get("itens", [])

            for item in itens:
                produto_bling_id = str(item.get("produtoId"))
                quantidade = float(item.get("quantidade", 0))

                # Buscar produto no sistema
                sync = (
                    db.query(ProdutoBlingSync)
                    .filter(ProdutoBlingSync.bling_produto_id == produto_bling_id)
                    .first()
                )

                if sync and sync.sincronizar:
                    produto = (
                        db.query(Produto).filter(Produto.id == sync.produto_id).first()
                    )

                    if produto:
                        estoque_anterior = produto.estoque_atual or 0
                        produto.estoque_atual = max(0, estoque_anterior - quantidade)

                        # Registrar movimentação com status 'reservado' (pendente de NF confirmada)
                        movimentacao = EstoqueMovimentacao(
                            produto_id=produto.id,
                            tipo="saida",
                            motivo="venda_online",
                            quantidade=quantidade,
                            quantidade_anterior=estoque_anterior,
                            quantidade_nova=produto.estoque_atual,
                            documento=f"BLING-{venda_id}",
                            referencia_id=venda_id,
                            referencia_tipo="venda_bling",
                            status="reservado",  # ← NOVO: Estoque reservado até NF ser autorizada
                            observacao="Venda online via Bling - Pendente de NF autorizada",
                            user_id=1,  # Sistema
                        )
                        db.add(movimentacao)

                        # Atualizar sync
                        sync.ultima_sincronizacao = utc_now()

                        logger.info(
                            f"✅ Estoque baixado - Produto {produto.id}: {estoque_anterior} → {produto.estoque_atual}"
                        )

            db.commit()
            return {"status": "success", "message": "Estoque atualizado"}

        elif evento == "vendas.deleted":
            # Venda cancelada - retornar estoque
            # Implementar lógica similar...
            pass

        return {"status": "ignored", "message": f"Evento {evento} não processado"}

    except Exception as e:
        logger.error(f"❌ Erro no webhook: {e}")
        return {"status": "error", "message": str(e)}


logger.info("✅ Módulo de sincronização Bling carregado")


# ============================================================================
# VINCULAR TODOS POR SKU
# ============================================================================


@router.post("/vincular-todos")
def vincular_todos_por_sku(
    limite: int = Query(default=20, ge=1, le=200),
    timeout_seconds: int = Query(default=15, ge=5, le=55),
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    Vincula automaticamente produtos do sistema com o Bling pelo código (SKU).

    Para cada produto faltante no recorte Bling-centric (existe no Bling e ainda sem vínculo local):
    - Busca no Bling pelo campo `codigo`
    - Se encontrar, cria ou atualiza ProdutoBlingSync com o ID do Bling
    - Produtos do tipo PAI são ignorados

    Retorna resumo com vinculados, não encontrados e erros.
    """
    logger.info("🔗 Iniciando vinculação em massa por SKU")
    _current_user, tenant_id = user_and_tenant

    snapshot = _get_snapshot_sem_vinculo_com_match_bling(
        db,
        tenant_id=tenant_id,
        force_refresh=False,
    )

    itens_match = [
        item
        for item in list(snapshot.get("items", []) or [])
        if item.get("match_origem") == "sku"
    ]
    total_sem_vinculo = len(itens_match)
    total_universo_sem_vinculo = int(
        snapshot.get("total_sem_vinculo_universo_local", total_sem_vinculo) or 0
    )
    coleta_bling_completa = bool(snapshot.get("coleta_bling_completa", True))
    total_bling = int(snapshot.get("total_bling", 0) or 0)

    itens_lote = itens_match[:limite]
    ids_lote = [
        int(item.get("id")) for item in itens_lote if item.get("id") is not None
    ]
    produtos_lote = (
        db.query(Produto)
        .filter(
            Produto.tenant_id == tenant_id,
            Produto.id.in_(ids_lote),
        )
        .all()
        if ids_lote
        else []
    )
    produtos_por_id = {produto.id: produto for produto in produtos_lote}

    vinculados = []
    nao_encontrados = []
    erros = []
    sincronizados_sucesso = 0
    sincronizados_erro = 0
    interrompido_por_tempo = False
    total_processados = 0
    inicio_execucao = time.monotonic()

    logger.info(
        "Processando lote por snapshot: %s de %s pendencias com match (universo local sem vinculo: %s)",
        len(itens_lote),
        total_sem_vinculo,
        total_universo_sem_vinculo,
    )

    for item in itens_lote:
        if (time.monotonic() - inicio_execucao) >= timeout_seconds:
            interrompido_por_tempo = True
            logger.warning(
                "Vinculo em massa interrompido por limite de tempo (%ss)",
                timeout_seconds,
            )
            break

        total_processados += 1
        produto_id = int(item.get("id") or 0)
        produto = produtos_por_id.get(produto_id)

        if not produto:
            erros.append(
                {
                    "produto_id": produto_id or None,
                    "codigo": item.get("codigo"),
                    "erro": "Produto local nao encontrado para o item do snapshot.",
                }
            )
            continue

        bling_produto_id = str(item.get("bling_id") or "").strip()
        if not bling_produto_id:
            nao_encontrados.append(
                {
                    "produto_id": produto.id,
                    "codigo": produto.codigo,
                    "nome": produto.nome,
                    "motivo": "Snapshot sem bling_id para esse item.",
                }
            )
            continue

        try:
            _upsert_sync_vinculo(db, tenant_id, produto, bling_produto_id)
            db.flush()

            if _produto_sincroniza_estoque(produto):
                resultado_sync = BlingSyncService.queue_product_sync(
                    db,
                    produto_id=produto.id,
                    estoque_novo=float(produto.estoque_atual or 0),
                    motivo="vinculo_massa_forcar_sync",
                    origem="manual",
                    force=True,
                )

                sync_ok = bool(resultado_sync.get("ok"))
                if sync_ok:
                    sincronizados_sucesso += 1
                else:
                    sincronizados_erro += 1
            else:
                sync_ok = None
                resultado_sync = {
                    "detail": "Produto PAI vinculado so para catalogo. O estoque segue nas variacoes.",
                }

            vinculados.append(
                {
                    "produto_id": produto.id,
                    "codigo": produto.codigo,
                    "nome": produto.nome,
                    "bling_produto_id": bling_produto_id,
                    "bling_nome": item.get("bling_nome"),
                    "match_origem": item.get("match_origem"),
                    "tipo_produto": _tipo_produto_local(produto),
                    "sync_ok": sync_ok,
                    "sync_detail": resultado_sync.get("detail")
                    or resultado_sync.get("erro"),
                }
            )

            logger.info(
                "Vinculado via snapshot: %s -> Bling ID %s",
                produto.codigo,
                bling_produto_id,
            )

        except Exception as e:
            logger.error("Erro ao vincular produto %s: %s", produto.codigo, e)
            erros.append(
                {"produto_id": produto.id, "codigo": produto.codigo, "erro": str(e)}
            )

    db.commit()
    _remover_ids_do_snapshot_sem_vinculo_cache(
        tenant_id,
        [item.get("produto_id") for item in vinculados],
    )

    logger.info(
        "Vinculacao concluida: %s vinculados, %s nao encontrados, %s erros",
        len(vinculados),
        len(nao_encontrados),
        len(erros),
    )

    return {
        "limite_lote": limite,
        "timeout_seconds": timeout_seconds,
        "interrompido_por_tempo": interrompido_por_tempo,
        "total_universo_local_sem_vinculo": total_universo_sem_vinculo,
        "total_bling_analisado": total_bling,
        "coleta_bling_completa": coleta_bling_completa,
        "total_sem_vinculo": total_sem_vinculo,
        "total_planejado_no_lote": len(itens_lote),
        "total_processados": total_processados,
        "restantes_para_proximo_lote": max(total_sem_vinculo - len(vinculados), 0),
        "vinculados": len(vinculados),
        "sincronizados_com_sucesso": sincronizados_sucesso,
        "sincronizados_com_erro": sincronizados_erro,
        "nao_encontrados_no_bling": len(nao_encontrados),
        "erros": len(erros),
        "tempo_execucao_ms": int((time.monotonic() - inicio_execucao) * 1000),
        "detalhes_vinculados": vinculados,
        "detalhes_nao_encontrados": nao_encontrados,
        "detalhes_erros": erros,
    }
