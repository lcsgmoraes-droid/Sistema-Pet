"""Rotinas de reconciliacao de estoque Bling."""

from __future__ import annotations

from datetime import timedelta
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from app.bling_integration import BlingAPI
from app.db import SessionLocal
from app.produtos_models import ProdutoBlingSync
from app.tenancy.context import tenant_context

from .bling_sync_shared import (
    DIVERGENCIA_MINIMA,
    _erro_rate_limit_bling,
    _mensagem_rate_limit_bling,
    _positive_limit,
    _registrar_cooldown_rate_limit,
    _remaining_limit,
    _tenant_scope_or_current,
    listar_tenants_com_produto_bling_sync_ativo,
    listar_tenants_com_produto_bling_sync_recentes,
    utc_now,
)


class BlingSyncReconciliationMixin:
    """Conferencia de saldos locais contra o Bling."""

    @classmethod
    def reconcile_product(
        cls, produto_id: int, force_sync: bool = False
    ) -> Dict[str, Any]:
        db = SessionLocal()
        try:
            produto, sync = cls._load_produto_sync(db, produto_id)
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
                queue_result = cls.queue_product_sync(
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
            if _erro_rate_limit_bling(error):
                cooldown_seconds = _registrar_cooldown_rate_limit(error)
                return {
                    "ok": False,
                    "detail": _mensagem_rate_limit_bling(error, cooldown_seconds),
                    "rate_limited": True,
                    "cooldown_seconds": cooldown_seconds,
                }
            return {"ok": False, "detail": str(error)}
        finally:
            db.close()

    @classmethod
    def _listar_produto_ids_reconciliacao_recente(
        cls,
        db: Session,
        tenant_id,
        *,
        minutes: int,
        limit: Optional[int],
    ) -> list[int]:
        cutoff = utc_now() - timedelta(minutes=max(int(minutes or 1), 1))
        query = (
            db.query(ProdutoBlingSync.produto_id)
            .filter(
                ProdutoBlingSync.tenant_id == tenant_id,
                ProdutoBlingSync.sincronizar.is_(True),
                ProdutoBlingSync.bling_produto_id.isnot(None),
                ProdutoBlingSync.bling_produto_id != "",
                (
                    (ProdutoBlingSync.updated_at >= cutoff)
                    | (ProdutoBlingSync.status.in_(["erro", "pendente"]))
                ),
            )
            .order_by(
                ProdutoBlingSync.updated_at.desc(), ProdutoBlingSync.produto_id.asc()
            )
        )
        positive_limit = _positive_limit(limit)
        if positive_limit is not None:
            query = query.limit(positive_limit)
        return [int(produto_id) for (produto_id,) in query.all()]

    @classmethod
    def _listar_produto_ids_reconciliacao_geral(
        cls,
        db: Session,
        tenant_id,
        *,
        limit: Optional[int],
    ) -> list[int]:
        query = (
            db.query(ProdutoBlingSync.produto_id)
            .filter(
                ProdutoBlingSync.tenant_id == tenant_id,
                ProdutoBlingSync.sincronizar.is_(True),
                ProdutoBlingSync.bling_produto_id.isnot(None),
                ProdutoBlingSync.bling_produto_id != "",
            )
            .order_by(ProdutoBlingSync.produto_id.asc())
        )
        positive_limit = _positive_limit(limit)
        if positive_limit is not None:
            query = query.limit(positive_limit)
        return [int(produto_id) for (produto_id,) in query.all()]

    @classmethod
    def reconcile_recent_products(
        cls,
        minutes: int = 30,
        limit: int = 100,
        tenant_id: Optional[Any] = None,
    ) -> Dict[str, Any]:
        db = SessionLocal()
        try:
            tenant_scope = _tenant_scope_or_current(tenant_id)
            tenant_ids = (
                [tenant_scope]
                if tenant_scope is not None
                else listar_tenants_com_produto_bling_sync_recentes(db, minutes=minutes)
            )
            avaliados = 0
            divergencias = 0
            tenants_processados = 0
            rate_limited = False
            cooldown_seconds = 0.0

            for tenant in tenant_ids:
                remaining = _remaining_limit(limit, avaliados)
                if remaining == 0:
                    break

                with tenant_context(tenant) as scoped_tenant:
                    produto_ids = cls._listar_produto_ids_reconciliacao_recente(
                        db,
                        scoped_tenant,
                        minutes=minutes,
                        limit=remaining,
                    )
                    if produto_ids:
                        tenants_processados += 1

                    for produto_id in produto_ids:
                        result = cls.reconcile_product(produto_id)
                        avaliados += 1
                        if result.get("rate_limited"):
                            rate_limited = True
                            cooldown_seconds = float(
                                result.get("cooldown_seconds") or 0.0
                            )
                            break
                        if (
                            result.get("ok")
                            and abs(result.get("divergencia", 0)) >= DIVERGENCIA_MINIMA
                        ):
                            divergencias += 1

                if rate_limited:
                    break

            return {
                "avaliados": avaliados,
                "divergencias": divergencias,
                "rate_limited": rate_limited,
                "cooldown_seconds": cooldown_seconds,
                "tenants_processados": tenants_processados,
            }
        finally:
            db.close()

    @classmethod
    def reconcile_all_products(
        cls,
        limit: Optional[int] = None,
        force_sync: bool = False,
        tenant_id: Optional[Any] = None,
    ) -> Dict[str, Any]:
        db = SessionLocal()
        try:
            tenant_scope = _tenant_scope_or_current(tenant_id)
            tenant_ids = (
                [tenant_scope]
                if tenant_scope is not None
                else listar_tenants_com_produto_bling_sync_ativo(db)
            )
            avaliados = 0
            divergencias = 0
            tenants_processados = 0
            rate_limited = False
            cooldown_seconds = 0.0

            for tenant in tenant_ids:
                remaining = _remaining_limit(limit, avaliados)
                if remaining == 0:
                    break

                with tenant_context(tenant) as scoped_tenant:
                    produto_ids = cls._listar_produto_ids_reconciliacao_geral(
                        db,
                        scoped_tenant,
                        limit=remaining,
                    )
                    if produto_ids:
                        tenants_processados += 1

                    for produto_id in produto_ids:
                        result = cls.reconcile_product(
                            produto_id, force_sync=force_sync
                        )
                        avaliados += 1
                        if result.get("rate_limited"):
                            rate_limited = True
                            cooldown_seconds = float(
                                result.get("cooldown_seconds") or 0.0
                            )
                            break
                        if (
                            result.get("ok")
                            and abs(result.get("divergencia", 0)) >= DIVERGENCIA_MINIMA
                        ):
                            divergencias += 1

                if rate_limited:
                    break

            return {
                "avaliados": avaliados,
                "divergencias": divergencias,
                "rate_limited": rate_limited,
                "cooldown_seconds": cooldown_seconds,
                "tenants_processados": tenants_processados,
            }
        finally:
            db.close()
