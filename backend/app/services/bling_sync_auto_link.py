"""Auto-vinculo por SKU e snapshots de saude do sync Bling."""

from __future__ import annotations

from typing import Any, Dict, Optional

from sqlalchemy import or_
from sqlalchemy.orm import Session, aliased

from app.bling_integration import BlingAPI
from app.db import SessionLocal
from app.produtos_models import Produto, ProdutoBlingSync, ProdutoBlingSyncQueue
from app.tenancy.context import tenant_context

from .bling_sync_shared import (
    DIVERGENCIA_MINIMA,
    _buscar_item_bling_para_produto,
    _erro_rate_limit_bling,
    _registrar_cooldown_rate_limit,
    _remaining_limit,
    _tenant_scope_or_current,
    listar_tenants_com_produtos_sem_vinculo_bling,
    utc_now,
)


class BlingSyncAutoLinkMixin:
    """Auto-link de produtos por SKU e visao operacional."""

    @staticmethod
    def _get_or_create_sync(db: Session, produto: Produto) -> ProdutoBlingSync:
        query = db.query(ProdutoBlingSync).filter(
            ProdutoBlingSync.produto_id == produto.id,
            ProdutoBlingSync.tenant_id == produto.tenant_id,
        )
        sync = query.first()
        if not sync:
            sync = ProdutoBlingSync(tenant_id=produto.tenant_id, produto_id=produto.id)
            db.add(sync)
        return sync

    @classmethod
    def _marcar_auto_link_sem_match(cls, db: Session, produto: Produto) -> None:
        sync = cls._get_or_create_sync(db, produto)
        sync.sincronizar = False
        sync.estoque_compartilhado = False
        sync.status = "sem_vinculo"
        sync.erro_mensagem = "Produto nao encontrado no Bling por SKU no auto-vinculo."
        sync.updated_at = utc_now()

    @classmethod
    def _auto_link_by_sku_for_tenant(cls, tenant_id, limit: int) -> Dict[str, Any]:
        db = SessionLocal()
        try:
            sync_candidato = aliased(ProdutoBlingSync)

            produtos = (
                db.query(Produto)
                .outerjoin(
                    sync_candidato,
                    (sync_candidato.produto_id == Produto.id)
                    & (sync_candidato.tenant_id == tenant_id),
                )
                .filter(
                    Produto.tenant_id == tenant_id,
                    Produto.codigo.isnot(None),
                    Produto.codigo != "",
                    Produto.tipo_produto != "PAI",
                )
                .filter(
                    or_(
                        sync_candidato.id.is_(None),
                        sync_candidato.bling_produto_id.is_(None),
                        sync_candidato.bling_produto_id == "",
                    )
                )
                .order_by(
                    sync_candidato.updated_at.asc().nullsfirst(),
                    Produto.updated_at.desc().nullslast(),
                    Produto.id.asc(),
                )
                .limit(limit)
                .all()
            )

            bling = BlingAPI()
            vinculados = 0
            nao_encontrados = 0
            erros = 0

            for produto in produtos:
                try:
                    item = _buscar_item_bling_para_produto(
                        bling,
                        codigo_busca=produto.codigo or "",
                        nome_busca=produto.nome or "",
                    )
                    if not item:
                        cls._marcar_auto_link_sem_match(db, produto)
                        nao_encontrados += 1
                        continue

                    bling_id = str(item.get("id") or "").strip()
                    if not bling_id:
                        cls._marcar_auto_link_sem_match(db, produto)
                        nao_encontrados += 1
                        continue

                    sync = cls._get_or_create_sync(db, produto)
                    sync.bling_produto_id = bling_id
                    sync.sincronizar = True
                    sync.estoque_compartilhado = True
                    sync.status = "ativo"
                    sync.erro_mensagem = None
                    sync.updated_at = utc_now()
                    vinculados += 1
                except Exception as error:
                    if _erro_rate_limit_bling(error):
                        _registrar_cooldown_rate_limit(error)
                        break
                    erros += 1

            db.commit()
            return {
                "processados": len(produtos),
                "vinculados": vinculados,
                "nao_encontrados": nao_encontrados,
                "erros": erros,
            }
        except Exception as error:
            db.rollback()
            return {
                "processados": 0,
                "vinculados": 0,
                "nao_encontrados": 0,
                "erros": 1,
                "detail": str(error),
            }
        finally:
            db.close()

    @classmethod
    def auto_link_by_sku(
        cls, limit: int = 500, tenant_id: Optional[Any] = None
    ) -> Dict[str, Any]:
        tenant_scope = _tenant_scope_or_current(tenant_id)
        if tenant_scope is not None:
            with tenant_context(tenant_scope) as scoped_tenant:
                return cls._auto_link_by_sku_for_tenant(scoped_tenant, limit)

        db = SessionLocal()
        try:
            tenant_ids = listar_tenants_com_produtos_sem_vinculo_bling(db)
        finally:
            db.close()

        total = {"processados": 0, "vinculados": 0, "nao_encontrados": 0, "erros": 0}
        for tenant in tenant_ids:
            remaining = _remaining_limit(limit, int(total["processados"]))
            if remaining == 0:
                break
            with tenant_context(tenant) as scoped_tenant:
                result = cls._auto_link_by_sku_for_tenant(
                    scoped_tenant, int(remaining or 0)
                )

            for key in total:
                total[key] += int(result.get(key) or 0)

            if int(result.get("erros") or 0):
                break

        return total

    @classmethod
    def run_nightly_forced_link_and_sync(
        cls, link_limit: int = 500, sync_limit: int = 1000
    ) -> Dict[str, Any]:
        link_result = cls.auto_link_by_sku(limit=link_limit)
        reconcile_result = cls.reconcile_all_products(limit=sync_limit, force_sync=True)
        queue_result = cls.process_pending_queue(limit=sync_limit)
        return {
            "link": link_result,
            "reconcile": reconcile_result,
            "queue": queue_result,
        }

    @classmethod
    def get_health_snapshot(
        cls, db: Session, tenant_id: Optional[str] = None
    ) -> Dict[str, Any]:
        queue_query = db.query(ProdutoBlingSyncQueue)
        sync_query = db.query(ProdutoBlingSync)

        if tenant_id is not None:
            queue_query = queue_query.filter(
                ProdutoBlingSyncQueue.tenant_id == tenant_id
            )
            sync_query = sync_query.filter(ProdutoBlingSync.tenant_id == tenant_id)

        pendentes = queue_query.filter(
            ProdutoBlingSyncQueue.status.in_(["pendente", "erro", "processando"])
        ).count()
        com_erro = sync_query.filter(ProdutoBlingSync.status == "erro").count()
        ativos = sync_query.filter(ProdutoBlingSync.sincronizar.is_(True)).count()
        divergentes = (
            sync_query.filter(ProdutoBlingSync.ultima_divergencia.isnot(None))
            .filter(
                (ProdutoBlingSync.ultima_divergencia > DIVERGENCIA_MINIMA)
                | (ProdutoBlingSync.ultima_divergencia < -DIVERGENCIA_MINIMA)
            )
            .count()
        )
        return {
            "ativos": ativos,
            "pendentes": pendentes,
            "erros": com_erro,
            "divergentes": divergentes,
        }
