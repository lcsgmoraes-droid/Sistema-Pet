"""Reprocessamento de falhas da fila Bling."""

from __future__ import annotations

from datetime import timedelta
import logging
from typing import Any, Dict, Optional

from sqlalchemy.orm import aliased

from app.bling_integration import BlingAPI
from app.db import SessionLocal
from app.produtos_models import ProdutoBlingSync, ProdutoBlingSyncQueue

from .bling_sync_shared import (
    BLING_REPROCESS_IMMEDIATE_LIMIT,
    BLING_STOCK_MIN_INTERVAL_SECONDS,
    _detalhe_autenticacao_bling,
    _erro_autenticacao_bling,
    _latest_queue_ids_subquery,
    _mensagem_autenticacao_bling,
    utc_now,
)

logger = logging.getLogger(__name__)


class BlingSyncReprocessMixin:
    """Reagenda falhas e coordena execucao imediata controlada."""

    @classmethod
    def reprocess_failed_syncs(
        cls, limit: int = 100, tenant_id: Optional[int] = None
    ) -> Dict[str, Any]:
        db = SessionLocal()
        now = utc_now()
        try:
            try:
                BlingAPI().listar_naturezas_operacoes()
            except Exception as error:
                if _erro_autenticacao_bling(error):
                    detail = _mensagem_autenticacao_bling(error)
                    logger.warning(
                        "[BLING SYNC] Reprocessamento bloqueado por autenticacao invalida do Bling: %s",
                        detail,
                    )
                    return {
                        "reprocessados": 0,
                        "agendados_para_fila": 0,
                        "processados_agora": 0,
                        "normalizados_antes": 0,
                        "restantes_para_scheduler": 0,
                        "auth_invalid": True,
                        "detail": detail,
                        "technical_error": _detalhe_autenticacao_bling(error),
                    }
                raise

            normalizados = cls.normalize_sync_states_from_latest_queue(
                db, tenant_id=tenant_id
            )
            latest_ids = _latest_queue_ids_subquery(db, tenant_id=tenant_id)
            query = (
                db.query(ProdutoBlingSyncQueue)
                .join(latest_ids, latest_ids.c.queue_id == ProdutoBlingSyncQueue.id)
                .filter(ProdutoBlingSyncQueue.status.in_(["erro", "falha_final"]))
            )
            if tenant_id is not None:
                query = query.filter(ProdutoBlingSyncQueue.tenant_id == tenant_id)
            filas = (
                query.order_by(ProdutoBlingSyncQueue.updated_at.asc())
                .limit(limit)
                .all()
            )

            total = 0
            sem_fila_reenfileirados = 0
            produtos_reenfileirados: set[int] = set()
            for index, fila in enumerate(filas):
                if index < BLING_REPROCESS_IMMEDIATE_LIMIT:
                    proxima_tentativa = now
                else:
                    atraso = (
                        index - BLING_REPROCESS_IMMEDIATE_LIMIT + 1
                    ) * BLING_STOCK_MIN_INTERVAL_SECONDS
                    proxima_tentativa = now + timedelta(seconds=atraso)
                fila.status = "pendente"
                fila.proxima_tentativa_em = proxima_tentativa
                fila.ultimo_erro = None
                fila.processado_em = None
                fila.forcar_sync = True

                sync = (
                    db.query(ProdutoBlingSync)
                    .filter(ProdutoBlingSync.id == fila.sync_id)
                    .first()
                )
                if sync:
                    sync.status = "pendente"
                    sync.proxima_tentativa_sync = proxima_tentativa
                    sync.erro_mensagem = None
                total += 1
                produtos_reenfileirados.add(int(fila.produto_id))

            if total < limit:
                fila_atual = aliased(ProdutoBlingSyncQueue)
                syncs_sem_fila_query = (
                    db.query(ProdutoBlingSync)
                    .outerjoin(
                        latest_ids,
                        latest_ids.c.produto_id == ProdutoBlingSync.produto_id,
                    )
                    .outerjoin(fila_atual, fila_atual.id == latest_ids.c.queue_id)
                    .filter(
                        ProdutoBlingSync.sincronizar.is_(True),
                        ProdutoBlingSync.status == "erro",
                        ProdutoBlingSync.erro_mensagem.isnot(None),
                        ProdutoBlingSync.erro_mensagem != "",
                        ProdutoBlingSync.bling_produto_id.isnot(None),
                        ProdutoBlingSync.bling_produto_id != "",
                        fila_atual.id.is_(None),
                    )
                )
                if tenant_id is not None:
                    syncs_sem_fila_query = syncs_sem_fila_query.filter(
                        ProdutoBlingSync.tenant_id == tenant_id
                    )
                if produtos_reenfileirados:
                    syncs_sem_fila_query = syncs_sem_fila_query.filter(
                        ~ProdutoBlingSync.produto_id.in_(produtos_reenfileirados)
                    )

                syncs_sem_fila = (
                    syncs_sem_fila_query.order_by(
                        ProdutoBlingSync.updated_at.asc(), ProdutoBlingSync.id.asc()
                    )
                    .limit(max(limit - total, 0))
                    .all()
                )

                for sync in syncs_sem_fila:
                    queue_result = cls.queue_product_sync(
                        db,
                        produto_id=int(sync.produto_id),
                        motivo="reprocessar_falha_sem_fila",
                        origem="reprocessamento",
                        force=True,
                    )
                    if not queue_result.get("ok"):
                        logger.warning(
                            "[BLING SYNC] Nao foi possivel reenfileirar produto com erro sem fila atual: produto=%s detalhe=%s",
                            sync.produto_id,
                            queue_result.get("detail"),
                        )
                        continue

                    fila = (
                        db.query(ProdutoBlingSyncQueue)
                        .filter(ProdutoBlingSyncQueue.id == queue_result["queue_id"])
                        .first()
                    )
                    if not fila:
                        continue

                    if total < BLING_REPROCESS_IMMEDIATE_LIMIT:
                        proxima_tentativa = now
                    else:
                        atraso = (
                            total - BLING_REPROCESS_IMMEDIATE_LIMIT + 1
                        ) * BLING_STOCK_MIN_INTERVAL_SECONDS
                        proxima_tentativa = now + timedelta(seconds=atraso)

                    fila.status = "pendente"
                    fila.proxima_tentativa_em = proxima_tentativa
                    fila.ultimo_erro = None
                    fila.processado_em = None
                    fila.forcar_sync = True

                    sync.status = "pendente"
                    sync.proxima_tentativa_sync = proxima_tentativa
                    sync.erro_mensagem = None

                    total += 1
                    sem_fila_reenfileirados += 1
                    produtos_reenfileirados.add(int(sync.produto_id))

            db.commit()
            process_now_limit = min(total, BLING_REPROCESS_IMMEDIATE_LIMIT)
            immediate_result = (
                cls.process_pending_queue(limit=process_now_limit)
                if process_now_limit > 0
                else {"processados": 0, "sucessos": 0, "erros": 0}
            )
            return {
                "reprocessados": total,
                "agendados_para_fila": total,
                "normalizados_antes": int(normalizados.get("repaired_active") or 0)
                + int(normalizados.get("repaired_error") or 0),
                "sem_fila_reenfileirados": sem_fila_reenfileirados,
                "limite_execucao_imediata": process_now_limit,
                "processados_agora": int(immediate_result.get("processados") or 0),
                "sucessos_agora": int(immediate_result.get("sucessos") or 0),
                "erros_agora": int(immediate_result.get("erros") or 0),
                "rate_limited": bool(immediate_result.get("rate_limited")),
                "cooldown_seconds": float(
                    immediate_result.get("cooldown_seconds") or 0.0
                ),
                "restantes_para_scheduler": max(
                    total - int(immediate_result.get("processados") or 0), 0
                ),
                "auth_invalid": bool(immediate_result.get("auth_invalid")),
                "detail": immediate_result.get("detail"),
            }
        except Exception:
            db.rollback()
            logger.exception("[BLING SYNC] Erro ao reprocessar falhas")
            return {
                "reprocessados": 0,
                "agendados_para_fila": 0,
                "processados_agora": 0,
            }
        finally:
            db.close()
