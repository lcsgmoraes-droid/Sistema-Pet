"""Fila persistente de sincronizacao de estoque com o Bling."""

from __future__ import annotations

from datetime import datetime, timedelta
import logging
import time
from typing import Any, Dict, Optional
from uuid import UUID

from sqlalchemy.orm import Session, aliased

from app.bling_integration import BlingAPI
from app.db import SessionLocal
from app.models import Tenant
from app.produtos_models import Produto, ProdutoBlingSync, ProdutoBlingSyncQueue
from app.tenancy.context import tenant_context
from app.utils.tenant_safe_sql import execute_tenant_safe_one

from .bling_sync_shared import (
    MAX_RETRIES,
    RETRY_BACKOFF_MINUTES,
    _SharedRateLimitState,
    _detalhe_autenticacao_bling,
    _erro_autenticacao_bling,
    _erro_rate_limit_bling,
    _latest_queue_ids_subquery,
    _mensagem_autenticacao_bling,
    _mensagem_rate_limit_bling,
    _normalizar_texto,
    _registrar_cooldown_rate_limit,
    _reservar_janela_envio_bling,
    _secondary_jobs_defer_reason,
    utc_now,
)

logger = logging.getLogger(__name__)


class BlingSyncQueueMixin:
    """Operacoes de fila, retry e protecao contra rate limit."""

    @classmethod
    def _retry_delay_minutes(cls, tentativas: int) -> int:
        index = min(max(tentativas - 1, 0), len(RETRY_BACKOFF_MINUTES) - 1)
        return RETRY_BACKOFF_MINUTES[index]

    @classmethod
    def register_rate_limit_cooldown(cls, error: Any) -> float:
        return _registrar_cooldown_rate_limit(error)

    @classmethod
    def get_rate_limit_snapshot(cls) -> Dict[str, Any]:
        with _SharedRateLimitState() as shared:
            now = time.time()
            cooldown_until = float(shared.state.get("cooldown_until") or 0.0)
            next_allowed_at = float(shared.state.get("next_allowed_at") or 0.0)

        cooldown_remaining = max(cooldown_until - now, 0.0)
        next_allowed_remaining = max(next_allowed_at - now, 0.0)

        return {
            "cooldown_active": cooldown_remaining > 0,
            "cooldown_seconds": cooldown_remaining,
            "cooldown_until": (
                datetime.fromtimestamp(cooldown_until).astimezone().isoformat()
                if cooldown_until > 0
                else None
            ),
            "next_allowed_in_seconds": next_allowed_remaining,
        }

    @classmethod
    def get_pending_queue_snapshot(cls, db: Optional[Session] = None) -> Dict[str, int]:
        own_session = db is None
        db_session = db or SessionLocal()
        now = utc_now()
        try:
            row = execute_tenant_safe_one(
                db_session,
                """
                SELECT
                    COALESCE(SUM(CASE WHEN status IN ('pendente', 'erro', 'processando') THEN 1 ELSE 0 END), 0) AS total_pending,
                    COALESCE(SUM(CASE WHEN status IN ('pendente', 'erro')
                        AND proxima_tentativa_em IS NOT NULL
                        AND proxima_tentativa_em <= :now THEN 1 ELSE 0 END), 0) AS ready_pending,
                    COALESCE(SUM(CASE WHEN status IN ('pendente', 'erro', 'processando')
                        AND forcar_sync IS TRUE THEN 1 ELSE 0 END), 0) AS forced_pending,
                    COALESCE(SUM(CASE WHEN status = 'processando' THEN 1 ELSE 0 END), 0) AS processing
                FROM produto_bling_sync_queue
                """,
                {"now": now},
                require_tenant=False,
                allow_global=True,
                global_reason="Guard global do worker Bling precisa medir backlog de sincronizacao de estoque.",
            )
            mapping = row if isinstance(row, dict) else getattr(row, "_mapping", {})
            return {
                "total_pending": int(mapping.get("total_pending", 0) or 0),
                "ready_pending": int(mapping.get("ready_pending", 0) or 0),
                "forced_pending": int(mapping.get("forced_pending", 0) or 0),
                "processing": int(mapping.get("processing", 0) or 0),
            }
        finally:
            if own_session:
                db_session.close()

    @classmethod
    def get_secondary_job_guard_snapshot(
        cls,
        db: Optional[Session] = None,
    ) -> Dict[str, Any]:
        rate_limit = cls.get_rate_limit_snapshot()
        queue = cls.get_pending_queue_snapshot(db=db)
        reason = _secondary_jobs_defer_reason(
            cooldown_active=bool(rate_limit["cooldown_active"]),
            ready_queue=int(queue["ready_pending"] or 0),
            total_queue=int(queue["total_pending"] or 0),
            forced_queue=int(queue["forced_pending"] or 0),
        )
        return {
            **rate_limit,
            **queue,
            "defer_secondary_jobs": bool(reason),
            "reason": reason,
        }

    @classmethod
    def _load_produto_sync(
        cls, db: Session, produto_id: int
    ) -> tuple[Optional[Produto], Optional[ProdutoBlingSync]]:
        produto = db.query(Produto).filter(Produto.id == produto_id).first()
        if not produto:
            return None, None

        sync = (
            db.query(ProdutoBlingSync)
            .filter(ProdutoBlingSync.produto_id == produto_id)
            .first()
        )
        return produto, sync

    @classmethod
    def queue_product_sync(
        cls,
        db: Session,
        produto_id: int,
        estoque_novo: Optional[float] = None,
        motivo: str = "",
        origem: str = "evento",
        force: bool = False,
    ) -> Dict[str, Any]:
        produto, sync = cls._load_produto_sync(db, produto_id)

        if not produto:
            return {"ok": False, "detail": "Produto não encontrado"}

        if not sync or not sync.sincronizar or not sync.bling_produto_id:
            return {
                "ok": False,
                "detail": "Produto não configurado para sincronização com Bling",
                "produto_id": produto_id,
            }

        estoque_destino = (
            float(produto.estoque_atual or 0)
            if estoque_novo is None
            else float(estoque_novo)
        )
        now = utc_now()

        fila = (
            db.query(ProdutoBlingSyncQueue)
            .filter(
                ProdutoBlingSyncQueue.produto_id == produto_id,
                ProdutoBlingSyncQueue.status.in_(["pendente", "processando", "erro"]),
            )
            .order_by(ProdutoBlingSyncQueue.updated_at.desc())
            .first()
        )

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

    @classmethod
    def _mark_success(
        cls, db: Session, fila: ProdutoBlingSyncQueue, sync: ProdutoBlingSync
    ) -> Dict[str, Any]:
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

    @classmethod
    def _mark_error(
        cls,
        db: Session,
        fila: ProdutoBlingSyncQueue,
        sync: ProdutoBlingSync,
        error: Exception,
    ) -> Dict[str, Any]:
        now = utc_now()
        message = str(error)[:500]
        delay_minutes = cls._retry_delay_minutes(fila.tentativas)
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

    @classmethod
    def _mark_auth_invalid(
        cls,
        db: Session,
        fila: ProdutoBlingSyncQueue,
        sync: ProdutoBlingSync,
        error: Exception,
    ) -> Dict[str, Any]:
        now = utc_now()
        technical_error = _detalhe_autenticacao_bling(error)
        message = f"{_mensagem_autenticacao_bling(error)} [{technical_error}]"

        fila.status = "falha_final"
        fila.ultimo_erro = message[:500]
        fila.proxima_tentativa_em = None
        fila.processado_em = now

        sync.status = "erro"
        sync.erro_mensagem = message[:500]
        sync.ultima_tentativa_sync = now
        sync.proxima_tentativa_sync = None
        sync.tentativas_sync = fila.tentativas

        logger.warning(
            "[BLING SYNC] Autenticacao invalida produto=%s detalhe=%s erro=%s",
            fila.produto_id,
            technical_error,
            _normalizar_texto(str(error))[:320],
        )

        return {
            "ok": False,
            "queue_id": fila.id,
            "produto_id": fila.produto_id,
            "status": fila.status,
            "tentativas": fila.tentativas,
            "proxima_tentativa_em": None,
            "erro": message[:500],
            "detail": _mensagem_autenticacao_bling(error),
            "auth_invalid": True,
            "technical_error": technical_error,
        }

    @classmethod
    def _mark_rate_limited(
        cls,
        db: Session,
        fila: ProdutoBlingSyncQueue,
        sync: ProdutoBlingSync,
        error: Exception,
        cooldown_seconds: float,
    ) -> Dict[str, Any]:
        now = utc_now()
        next_retry = now + timedelta(seconds=max(cooldown_seconds, 1))
        message = _mensagem_rate_limit_bling(error, cooldown_seconds)[:500]

        fila.status = "pendente"
        fila.ultimo_erro = message
        fila.proxima_tentativa_em = next_retry
        fila.processado_em = None

        sync.status = "pendente"
        sync.erro_mensagem = message
        sync.ultima_tentativa_sync = now
        sync.proxima_tentativa_sync = next_retry
        sync.tentativas_sync = fila.tentativas

        logger.warning(
            "[BLING SYNC] Rate limit produto=%s nova_tentativa=%s detalhe=%s",
            fila.produto_id,
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
            "rate_limited": True,
            "cooldown_seconds": cooldown_seconds,
        }

    @classmethod
    def process_queue_item(
        cls, db: Session, fila: ProdutoBlingSyncQueue
    ) -> Dict[str, Any]:
        sync = (
            db.query(ProdutoBlingSync)
            .filter(ProdutoBlingSync.id == fila.sync_id)
            .first()
        )
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
            _reservar_janela_envio_bling()
            BlingAPI().atualizar_estoque_produto(
                produto_id=sync.bling_produto_id,
                estoque_novo=float(fila.estoque_novo),
                observacao=f"Sync {fila.origem or 'manual'} - {fila.motivo or 'CorePet'}",
            )
            return cls._mark_success(db, fila, sync)
        except Exception as error:
            if _erro_rate_limit_bling(error):
                cooldown_seconds = _registrar_cooldown_rate_limit(error)
                fila.tentativas = max(int(fila.tentativas or 0) - 1, 0)
                sync.tentativas_sync = fila.tentativas
                return cls._mark_rate_limited(db, fila, sync, error, cooldown_seconds)
            if _erro_autenticacao_bling(error):
                return cls._mark_auth_invalid(db, fila, sync, error)
            return cls._mark_error(db, fila, sync, error)

    @classmethod
    def process_queue_item_by_id(cls, db: Session, queue_id: int) -> Dict[str, Any]:
        fila = (
            db.query(ProdutoBlingSyncQueue)
            .filter(ProdutoBlingSyncQueue.id == queue_id)
            .first()
        )
        if not fila:
            return {"ok": False, "detail": "Item da fila não encontrado"}
        return cls.process_queue_item(db, fila)

    @classmethod
    def queue_product_sync_background(
        cls,
        produto_id: int,
        estoque_novo: Optional[float] = None,
        motivo: str = "",
        origem: str = "evento",
        force: bool = False,
    ) -> None:
        db = SessionLocal()
        try:
            resultado = cls.queue_product_sync(
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

            # A execução acontece no scheduler (fila persistente), sem thread local.
            db.commit()
        except Exception as error:
            db.rollback()
            logger.warning("[BLING SYNC] Falha ao enfileirar sync: %s", error)
        finally:
            db.close()

    @classmethod
    def normalize_sync_states_from_latest_queue(
        cls, db: Session, tenant_id: Optional[int] = None
    ) -> Dict[str, int]:
        latest_ids = _latest_queue_ids_subquery(db, tenant_id=tenant_id)
        latest_queue = aliased(ProdutoBlingSyncQueue)

        query = (
            db.query(ProdutoBlingSync, latest_queue)
            .outerjoin(
                latest_ids, latest_ids.c.produto_id == ProdutoBlingSync.produto_id
            )
            .outerjoin(latest_queue, latest_queue.id == latest_ids.c.queue_id)
        )
        if tenant_id is not None:
            query = query.filter(ProdutoBlingSync.tenant_id == tenant_id)

        repaired_active = 0
        repaired_error = 0

        for sync, fila in query.all():
            if not fila:
                continue

            if fila.status == "sucesso" and sync.status != "ativo":
                processado_em = fila.processado_em or fila.updated_at or utc_now()
                sync.status = "ativo"
                sync.erro_mensagem = None
                sync.proxima_tentativa_sync = None
                sync.tentativas_sync = 0
                sync.ultima_tentativa_sync = processado_em
                sync.ultima_sincronizacao = processado_em
                sync.ultima_sincronizacao_sucesso = processado_em
                repaired_active += 1
                continue

            if fila.status in ("erro", "falha_final") and sync.status != "erro":
                sync.status = "erro"
                sync.erro_mensagem = fila.ultimo_erro
                sync.proxima_tentativa_sync = fila.proxima_tentativa_em
                sync.ultima_tentativa_sync = (
                    fila.ultima_tentativa_em or sync.ultima_tentativa_sync
                )
                sync.tentativas_sync = max(
                    int(sync.tentativas_sync or 0), int(fila.tentativas or 0)
                )
                repaired_error += 1

        return {
            "repaired_active": repaired_active,
            "repaired_error": repaired_error,
        }

    @classmethod
    def force_sync_now(
        cls, produto_id: int, motivo: str = "forcar_manual"
    ) -> Dict[str, Any]:
        db = SessionLocal()
        try:
            queue_result = cls.queue_product_sync(
                db,
                produto_id=produto_id,
                motivo=motivo,
                origem="manual",
                force=True,
            )
            if not queue_result.get("ok"):
                db.rollback()
                return queue_result

            result = cls.process_queue_item_by_id(db, queue_result["queue_id"])
            db.commit()
            return result
        except Exception as error:
            db.rollback()
            return {"ok": False, "detail": str(error)}
        finally:
            db.close()

    @classmethod
    def process_pending_queue(cls, limit: int = 20) -> Dict[str, Any]:
        db = SessionLocal()
        now = utc_now()
        try:
            processados = 0
            sucessos = 0
            erros = 0
            rate_limited = False
            cooldown_seconds = 0.0
            auth_invalid = False
            auth_detail = None

            tenant_rows = (
                db.query(Tenant.id)
                .filter(Tenant.status == "active")
                .order_by(Tenant.created_at.asc())
                .all()
            )

            for (tenant_id_raw,) in tenant_rows:
                if processados >= limit:
                    break

                try:
                    tenant_uuid = UUID(str(tenant_id_raw))
                except (TypeError, ValueError):
                    logger.warning(
                        "[BLING SYNC] Ignorando tenant_id invalido na fila: %s",
                        tenant_id_raw,
                    )
                    continue

                with tenant_context(tenant_uuid):
                    restante = max(0, limit - processados)
                    filas = (
                        db.query(ProdutoBlingSyncQueue)
                        .filter(
                            ProdutoBlingSyncQueue.tenant_id == tenant_uuid,
                            ProdutoBlingSyncQueue.status.in_(["pendente", "erro"]),
                            ProdutoBlingSyncQueue.proxima_tentativa_em.isnot(None),
                            ProdutoBlingSyncQueue.proxima_tentativa_em <= now,
                        )
                        .order_by(
                            ProdutoBlingSyncQueue.forcar_sync.desc(),
                            ProdutoBlingSyncQueue.proxima_tentativa_em.asc(),
                            ProdutoBlingSyncQueue.updated_at.asc(),
                        )
                        .limit(restante)
                        .all()
                    )

                    for fila in filas:
                        result = cls.process_queue_item(db, fila)
                        processados += 1
                        if result.get("ok"):
                            sucessos += 1
                        else:
                            erros += 1
                            if result.get("rate_limited"):
                                rate_limited = True
                                cooldown_seconds = float(
                                    result.get("cooldown_seconds") or 0.0
                                )
                                break
                            if result.get("auth_invalid"):
                                auth_invalid = True
                                auth_detail = result.get("detail")
                                break

                if rate_limited or auth_invalid:
                    break

            db.commit()
            return {
                "processados": processados,
                "sucessos": sucessos,
                "erros": erros,
                "rate_limited": rate_limited,
                "cooldown_seconds": cooldown_seconds,
                "auth_invalid": auth_invalid,
                "detail": auth_detail,
            }
        except Exception:
            db.rollback()
            logger.exception("[BLING SYNC] Erro ao processar fila pendente")
            return {"processados": 0, "sucessos": 0, "erros": 1}
        finally:
            db.close()
