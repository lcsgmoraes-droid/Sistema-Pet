"""Serviço central de sincronização de estoque com o Bling."""

from __future__ import annotations

import logging
import threading
from datetime import UTC, datetime, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.bling_integration import BlingAPI
from app.db import SessionLocal
from app.produtos_models import Produto, ProdutoBlingSync, ProdutoBlingSyncQueue

logger = logging.getLogger(__name__)

MAX_RETRIES = 5
RETRY_BACKOFF_MINUTES = [1, 5, 15, 30, 60]
DIVERGENCIA_MINIMA = 0.01


def utc_now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class BlingSyncService:
    """Centraliza fila, retry e reconciliação de estoque com o Bling."""

    @staticmethod
    def _retry_delay_minutes(tentativas: int) -> int:
        index = min(max(tentativas - 1, 0), len(RETRY_BACKOFF_MINUTES) - 1)
        return RETRY_BACKOFF_MINUTES[index]

    @staticmethod
    def _load_produto_sync(db: Session, produto_id: int) -> tuple[Optional[Produto], Optional[ProdutoBlingSync]]:
        produto = db.query(Produto).filter(Produto.id == produto_id).first()
        if not produto:
            return None, None

        sync = db.query(ProdutoBlingSync).filter(
            ProdutoBlingSync.produto_id == produto_id
        ).first()
        return produto, sync

    @staticmethod
    def queue_product_sync(
        db: Session,
        produto_id: int,
        estoque_novo: Optional[float] = None,
        motivo: str = "",
        origem: str = "evento",
        force: bool = False,
    ) -> Dict[str, Any]:
        produto, sync = BlingSyncService._load_produto_sync(db, produto_id)

        if not produto:
            return {"ok": False, "detail": "Produto não encontrado"}

        if not sync or not sync.sincronizar or not sync.bling_produto_id:
            return {
                "ok": False,
                "detail": "Produto não configurado para sincronização com Bling",
                "produto_id": produto_id,
            }

        estoque_destino = float(produto.estoque_atual or 0) if estoque_novo is None else float(estoque_novo)
        now = utc_now()

        fila = db.query(ProdutoBlingSyncQueue).filter(
            ProdutoBlingSyncQueue.produto_id == produto_id,
            ProdutoBlingSyncQueue.status.in_(["pendente", "processando", "erro"]),
        ).order_by(ProdutoBlingSyncQueue.updated_at.desc()).first()

        if not fila:
            fila = ProdutoBlingSyncQueue(
                tenant_id=produto.tenant_id,
                produto_id=produto.id,
                sync_id=sync.id,
                estoque_novo=estoque_destino,
                motivo=motivo,
                origem=origem,
                status="pendente",
                forcar_sync=force,
                tentativas=0,
                proxima_tentativa_em=now,
            )
            db.add(fila)
        else:
            fila.estoque_novo = estoque_destino
            fila.motivo = motivo
            fila.origem = origem
            fila.status = "pendente"
            fila.forcar_sync = force or fila.forcar_sync
            fila.tentativas = 0
            fila.ultima_tentativa_em = None
            fila.proxima_tentativa_em = now
            fila.processado_em = None
            fila.ultimo_erro = None

        sync.status = "pendente"
        sync.ultima_tentativa_sync = now
        sync.proxima_tentativa_sync = now
        sync.erro_mensagem = None

        db.flush()
        return {
            "ok": True,
            "produto_id": produto.id,
            "queue_id": fila.id,
            "estoque_enfileirado": estoque_destino,
            "motivo": motivo,
            "origem": origem,
        }

    @staticmethod
    def _mark_success(db: Session, fila: ProdutoBlingSyncQueue, sync: ProdutoBlingSync) -> Dict[str, Any]:
        now = utc_now()
        fila.status = "sucesso"
        fila.processado_em = now
        fila.proxima_tentativa_em = None
        fila.ultimo_erro = None

        sync.status = "ativo"
        sync.erro_mensagem = None
        sync.ultima_sincronizacao = now
        sync.ultima_sincronizacao_sucesso = now
        sync.ultima_tentativa_sync = now
        sync.proxima_tentativa_sync = None
        sync.tentativas_sync = 0

        return {
            "ok": True,
            "queue_id": fila.id,
            "produto_id": fila.produto_id,
            "bling_produto_id": sync.bling_produto_id,
            "estoque_enviado": fila.estoque_novo,
            "status": fila.status,
        }

    @staticmethod
    def _mark_error(db: Session, fila: ProdutoBlingSyncQueue, sync: ProdutoBlingSync, error: Exception) -> Dict[str, Any]:
        now = utc_now()
        message = str(error)[:500]
        delay_minutes = BlingSyncService._retry_delay_minutes(fila.tentativas)
        retry_allowed = fila.tentativas < MAX_RETRIES
        next_retry = now + timedelta(minutes=delay_minutes) if retry_allowed else None

        fila.status = "erro" if retry_allowed else "falha_final"
        fila.ultimo_erro = message
        fila.proxima_tentativa_em = next_retry

        sync.status = "erro"
        sync.erro_mensagem = message
        sync.ultima_tentativa_sync = now
        sync.proxima_tentativa_sync = next_retry
        sync.tentativas_sync = fila.tentativas

        logger.warning(
            "[BLING SYNC] Falha produto=%s tentativa=%s proxima=%s erro=%s",
            fila.produto_id,
            fila.tentativas,
            next_retry,
            message,
        )

        return {
            "ok": False,
            "queue_id": fila.id,
            "produto_id": fila.produto_id,
            "status": fila.status,
            "tentativas": fila.tentativas,
            "proxima_tentativa_em": next_retry,
            "erro": message,
        }

    @staticmethod
    def process_queue_item(db: Session, fila: ProdutoBlingSyncQueue) -> Dict[str, Any]:
        sync = db.query(ProdutoBlingSync).filter(ProdutoBlingSync.id == fila.sync_id).first()
        produto = db.query(Produto).filter(Produto.id == fila.produto_id).first()

        if not sync or not produto or not sync.sincronizar or not sync.bling_produto_id:
            fila.status = "falha_final"
            fila.ultimo_erro = "Produto sem vínculo ativo com o Bling"
            fila.processado_em = utc_now()
            return {
                "ok": False,
                "queue_id": fila.id,
                "produto_id": fila.produto_id,
                "status": fila.status,
                "erro": fila.ultimo_erro,
            }

        now = utc_now()
        fila.status = "processando"
        fila.ultima_tentativa_em = now
        fila.tentativas += 1
        sync.ultima_tentativa_sync = now
        sync.tentativas_sync = fila.tentativas
        db.flush()

        try:
            BlingAPI().atualizar_estoque_produto(
                produto_id=sync.bling_produto_id,
                estoque_novo=float(fila.estoque_novo),
                observacao=f"Sync {fila.origem or 'manual'} - {fila.motivo or 'Sistema Pet'}",
            )
            return BlingSyncService._mark_success(db, fila, sync)
        except Exception as error:
            return BlingSyncService._mark_error(db, fila, sync, error)

    @staticmethod
    def process_queue_item_by_id(db: Session, queue_id: int) -> Dict[str, Any]:
        fila = db.query(ProdutoBlingSyncQueue).filter(
            ProdutoBlingSyncQueue.id == queue_id
        ).first()
        if not fila:
            return {"ok": False, "detail": "Item da fila não encontrado"}
        return BlingSyncService.process_queue_item(db, fila)

    @staticmethod
    def queue_product_sync_background(
        produto_id: int,
        estoque_novo: Optional[float] = None,
        motivo: str = "",
        origem: str = "evento",
        force: bool = False,
    ) -> None:
        def _run() -> None:
            db = SessionLocal()
            try:
                resultado = BlingSyncService.queue_product_sync(
                    db,
                    produto_id=produto_id,
                    estoque_novo=estoque_novo,
                    motivo=motivo,
                    origem=origem,
                    force=force,
                )
                if not resultado.get("ok"):
                    db.rollback()
                    return

                BlingSyncService.process_queue_item_by_id(db, resultado["queue_id"])
                db.commit()
            except Exception as error:
                db.rollback()
                logger.warning("[BLING SYNC] Falha ao disparar sync em background: %s", error)
            finally:
                db.close()

        threading.Thread(
            target=_run,
            daemon=True,
            name=f"bling-queue-{produto_id}",
        ).start()

    @staticmethod
    def force_sync_now(produto_id: int, motivo: str = "forcar_manual") -> Dict[str, Any]:
        db = SessionLocal()
        try:
            queue_result = BlingSyncService.queue_product_sync(
                db,
                produto_id=produto_id,
                motivo=motivo,
                origem="manual",
                force=True,
            )
            if not queue_result.get("ok"):
                db.rollback()
                return queue_result

            result = BlingSyncService.process_queue_item_by_id(db, queue_result["queue_id"])
            db.commit()
            return result
        except Exception as error:
            db.rollback()
            return {"ok": False, "detail": str(error)}
        finally:
            db.close()

    @staticmethod
    def process_pending_queue(limit: int = 20) -> Dict[str, Any]:
        db = SessionLocal()
        now = utc_now()
        try:
            filas = db.query(ProdutoBlingSyncQueue).filter(
                ProdutoBlingSyncQueue.status.in_(["pendente", "erro"]),
                ProdutoBlingSyncQueue.proxima_tentativa_em.isnot(None),
                ProdutoBlingSyncQueue.proxima_tentativa_em <= now,
            ).order_by(
                ProdutoBlingSyncQueue.forcar_sync.desc(),
                ProdutoBlingSyncQueue.proxima_tentativa_em.asc(),
                ProdutoBlingSyncQueue.updated_at.asc(),
            ).limit(limit).all()

            processados = 0
            sucessos = 0
            erros = 0

            for fila in filas:
                result = BlingSyncService.process_queue_item(db, fila)
                processados += 1
                if result.get("ok"):
                    sucessos += 1
                else:
                    erros += 1

            db.commit()
            return {
                "processados": processados,
                "sucessos": sucessos,
                "erros": erros,
            }
        except Exception:
            db.rollback()
            logger.exception("[BLING SYNC] Erro ao processar fila pendente")
            return {"processados": 0, "sucessos": 0, "erros": 1}
        finally:
            db.close()

    @staticmethod
    def reprocess_failed_syncs(limit: int = 100) -> Dict[str, Any]:
        db = SessionLocal()
        now = utc_now()
        try:
            filas = db.query(ProdutoBlingSyncQueue).filter(
                ProdutoBlingSyncQueue.status.in_(["erro", "falha_final"]),
            ).order_by(ProdutoBlingSyncQueue.updated_at.asc()).limit(limit).all()

            total = 0
            for fila in filas:
                fila.status = "pendente"
                fila.proxima_tentativa_em = now
                fila.ultimo_erro = None
                fila.processado_em = None
                fila.forcar_sync = True

                sync = db.query(ProdutoBlingSync).filter(ProdutoBlingSync.id == fila.sync_id).first()
                if sync:
                    sync.status = "pendente"
                    sync.proxima_tentativa_sync = now
                    sync.erro_mensagem = None
                total += 1

            db.commit()
            if total:
                BlingSyncService.process_pending_queue(limit=limit)
            return {"reprocessados": total}
        except Exception:
            db.rollback()
            logger.exception("[BLING SYNC] Erro ao reprocessar falhas")
            return {"reprocessados": 0}
        finally:
            db.close()

    @staticmethod
    def reconcile_product(produto_id: int, force_sync: bool = False) -> Dict[str, Any]:
        db = SessionLocal()
        try:
            produto, sync = BlingSyncService._load_produto_sync(db, produto_id)
            if not produto:
                return {"ok": False, "detail": "Produto não encontrado"}
            if not sync or not sync.sincronizar or not sync.bling_produto_id:
                return {"ok": False, "detail": "Produto sem vínculo ativo com o Bling"}

            saldo = BlingAPI().consultar_saldo_estoque(sync.bling_produto_id)
            estoque_bling = float(saldo.get("saldoFisicoTotal", 0) or 0)
            estoque_sistema = float(produto.estoque_atual or 0)
            divergencia = estoque_sistema - estoque_bling
            now = utc_now()

            sync.ultima_conferencia_bling = now
            sync.ultimo_estoque_bling = estoque_bling
            sync.ultima_divergencia = divergencia

            result = {
                "ok": True,
                "produto_id": produto.id,
                "estoque_sistema": estoque_sistema,
                "estoque_bling": estoque_bling,
                "divergencia": divergencia,
                "acao": "sem_acao",
            }

            if abs(divergencia) >= DIVERGENCIA_MINIMA or force_sync:
                queue_result = BlingSyncService.queue_product_sync(
                    db,
                    produto_id=produto.id,
                    estoque_novo=estoque_sistema,
                    motivo="reconciliacao",
                    origem="reconciliacao",
                    force=force_sync,
                )
                if queue_result.get("ok"):
                    result["acao"] = "sync_enfileirada"
                    result["queue_id"] = queue_result["queue_id"]

            db.commit()
            return result
        except Exception as error:
            db.rollback()
            return {"ok": False, "detail": str(error)}
        finally:
            db.close()

    @staticmethod
    def reconcile_recent_products(minutes: int = 30, limit: int = 100) -> Dict[str, Any]:
        db = SessionLocal()
        cutoff = utc_now() - timedelta(minutes=minutes)
        try:
            syncs = db.query(ProdutoBlingSync).filter(
                ProdutoBlingSync.sincronizar == True,
                ProdutoBlingSync.bling_produto_id.isnot(None),
                (
                    (ProdutoBlingSync.updated_at >= cutoff)
                    | (ProdutoBlingSync.status.in_(["erro", "pendente"]))
                )
            ).order_by(ProdutoBlingSync.updated_at.desc()).limit(limit).all()

            produto_ids = [sync.produto_id for sync in syncs]
        finally:
            db.close()

        divergencias = 0
        for produto_id in produto_ids:
            result = BlingSyncService.reconcile_product(produto_id)
            if result.get("ok") and abs(result.get("divergencia", 0)) >= DIVERGENCIA_MINIMA:
                divergencias += 1

        return {"avaliados": len(produto_ids), "divergencias": divergencias}

    @staticmethod
    def reconcile_all_products(limit: Optional[int] = None) -> Dict[str, Any]:
        db = SessionLocal()
        try:
            query = db.query(ProdutoBlingSync).filter(
                ProdutoBlingSync.sincronizar == True,
                ProdutoBlingSync.bling_produto_id.isnot(None),
            ).order_by(ProdutoBlingSync.produto_id.asc())
            if limit:
                query = query.limit(limit)
            produto_ids = [sync.produto_id for sync in query.all()]
        finally:
            db.close()

        divergencias = 0
        for produto_id in produto_ids:
            result = BlingSyncService.reconcile_product(produto_id)
            if result.get("ok") and abs(result.get("divergencia", 0)) >= DIVERGENCIA_MINIMA:
                divergencias += 1

        return {"avaliados": len(produto_ids), "divergencias": divergencias}

    @staticmethod
    def get_health_snapshot(db: Session) -> Dict[str, Any]:
        pendentes = db.query(ProdutoBlingSyncQueue).filter(
            ProdutoBlingSyncQueue.status.in_(["pendente", "erro", "processando"])
        ).count()
        com_erro = db.query(ProdutoBlingSync).filter(ProdutoBlingSync.status == "erro").count()
        ativos = db.query(ProdutoBlingSync).filter(ProdutoBlingSync.sincronizar == True).count()
        divergentes = db.query(ProdutoBlingSync).filter(
            ProdutoBlingSync.ultima_divergencia.isnot(None)
        ).filter(
            (ProdutoBlingSync.ultima_divergencia > DIVERGENCIA_MINIMA)
            | (ProdutoBlingSync.ultima_divergencia < -DIVERGENCIA_MINIMA)
        ).count()
        return {
            "ativos": ativos,
            "pendentes": pendentes,
            "erros": com_erro,
            "divergentes": divergentes,
        }