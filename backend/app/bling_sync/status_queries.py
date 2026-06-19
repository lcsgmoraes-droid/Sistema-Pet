"""Queries compartilhadas para status da sincronizacao Bling."""

from datetime import UTC, datetime, timedelta
from typing import Any, Optional

from sqlalchemy import and_, desc, func, or_
from sqlalchemy.orm import Session, aliased

from ..produtos_models import Produto, ProdutoBlingSync, ProdutoBlingSyncQueue
from ..services.bling_sync_service import DIVERGENCIA_MINIMA

_SYNC_PROBLEMS_FRESHNESS_HOURS = 24


def utc_now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _latest_queue_ids_subquery(db: Session, tenant_id) -> Any:
    referencia_recente = func.coalesce(
        ProdutoBlingSyncQueue.proxima_tentativa_em,
        ProdutoBlingSyncQueue.processado_em,
        ProdutoBlingSyncQueue.ultima_tentativa_em,
        ProdutoBlingSyncQueue.updated_at,
        ProdutoBlingSyncQueue.created_at,
    )
    ranked = (
        db.query(
            ProdutoBlingSyncQueue.produto_id.label("produto_id"),
            ProdutoBlingSyncQueue.id.label("queue_id"),
            func.row_number()
            .over(
                partition_by=ProdutoBlingSyncQueue.produto_id,
                order_by=(
                    desc(referencia_recente),
                    desc(ProdutoBlingSyncQueue.updated_at),
                    desc(ProdutoBlingSyncQueue.id),
                ),
            )
            .label("rn"),
        )
        .filter(ProdutoBlingSyncQueue.tenant_id == tenant_id)
        .subquery()
    )
    return (
        db.query(
            ranked.c.produto_id.label("produto_id"),
            ranked.c.queue_id.label("queue_id"),
        )
        .filter(ranked.c.rn == 1)
        .subquery()
    )


def _sync_problem_freshness_cutoff() -> datetime:
    return utc_now() - timedelta(hours=_SYNC_PROBLEMS_FRESHNESS_HOURS)


def _build_sync_problem_query(
    db: Session,
    tenant_id: int,
    busca: Optional[str] = None,
):
    fila_atual_ids = _latest_queue_ids_subquery(db, tenant_id)
    fila_atual = aliased(ProdutoBlingSyncQueue)
    cutoff = _sync_problem_freshness_cutoff()

    erro_sync_aberto = and_(
        ProdutoBlingSync.status == "erro",
        ProdutoBlingSync.erro_mensagem.isnot(None),
        ProdutoBlingSync.erro_mensagem != "",
        or_(
            fila_atual.id.is_(None),
            fila_atual.status.in_(["erro", "falha_final", "pendente", "processando"]),
        ),
    )
    fila_falhou = fila_atual.status.in_(["erro", "falha_final"])
    pendencia_sem_fila = and_(
        ProdutoBlingSync.status == "pendente",
        fila_atual.id.is_(None),
    )
    divergencia_atual = and_(
        ProdutoBlingSync.ultima_divergencia.isnot(None),
        func.abs(ProdutoBlingSync.ultima_divergencia) >= DIVERGENCIA_MINIMA,
        ProdutoBlingSync.ultima_conferencia_bling.isnot(None),
        ProdutoBlingSync.ultima_conferencia_bling >= cutoff,
        or_(
            ProdutoBlingSync.ultima_sincronizacao_sucesso.is_(None),
            ProdutoBlingSync.ultima_conferencia_bling
            >= ProdutoBlingSync.ultima_sincronizacao_sucesso,
        ),
    )

    query = (
        db.query(Produto, ProdutoBlingSync, fila_atual)
        .join(
            ProdutoBlingSync,
            Produto.id == ProdutoBlingSync.produto_id,
        )
        .outerjoin(
            fila_atual_ids,
            fila_atual_ids.c.produto_id == Produto.id,
        )
        .outerjoin(
            fila_atual,
            fila_atual.id == fila_atual_ids.c.queue_id,
        )
        .filter(
            Produto.tenant_id == tenant_id,
            ProdutoBlingSync.tenant_id == tenant_id,
            ProdutoBlingSync.sincronizar.is_(True),
        )
        .filter(
            or_(
                erro_sync_aberto,
                fila_falhou,
                pendencia_sem_fila,
                divergencia_atual,
            )
        )
    )

    if busca:
        termo = f"%{busca}%"
        query = query.filter(
            or_(
                Produto.nome.ilike(termo),
                Produto.codigo.ilike(termo),
                ProdutoBlingSync.bling_produto_id.ilike(termo),
                ProdutoBlingSync.erro_mensagem.ilike(termo),
                fila_atual.ultimo_erro.ilike(termo),
            )
        )

    return query, fila_atual


def _count_sync_problems_abertos(db: Session, tenant_id: int) -> int:
    query, _fila_atual = _build_sync_problem_query(db, tenant_id=tenant_id, busca=None)
    return int(query.order_by(None).count())
