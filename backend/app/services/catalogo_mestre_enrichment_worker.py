"""Worker seguro e idempotente de enriquecimento do catalogo mestre.

Este modulo grava exclusivamente tabelas ``catalogo_mestre_*``. A primeira fase
gera somente rascunhos de descricao para racoes, petiscos e areias sanitarias.
"""

from __future__ import annotations

import logging
import os
import socket
import uuid
from dataclasses import dataclass
from datetime import datetime, time, timedelta, timezone
from typing import Any, Callable

from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from app.catalogo_mestre_models import (
    CatalogoMestreEnriquecimentoExecucao,
    CatalogoMestrePendencia,
    CatalogoMestreProduto,
)
from app.services.catalogo_mestre_core import quality_and_gaps
from app.services.catalogo_mestre_enrichment_provider import (
    CatalogDescriptionProvider,
    OpenAICatalogDescriptionProvider,
    build_product_context,
)


logger = logging.getLogger(__name__)
ELIGIBLE_PRODUCT_TYPES = frozenset({"racao", "petisco", "areia_sanitaria"})
SUPPORTED_TASK_TYPE = "descricao_completa"


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().casefold() in {"1", "true", "yes", "sim", "on"}


def _env_int(name: str, default: int, minimum: int, maximum: int) -> int:
    try:
        value = int(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        value = default
    return max(minimum, min(value, maximum))


@dataclass(frozen=True)
class CatalogEnrichmentConfig:
    enabled: bool = False
    apply_enabled: bool = False
    batch_size: int = 1
    daily_limit: int = 25
    max_attempts: int = 5
    lease_seconds: int = 900

    @classmethod
    def from_env(cls) -> "CatalogEnrichmentConfig":
        return cls(
            enabled=_env_bool("CATALOGO_MESTRE_WORKER_ENABLED"),
            apply_enabled=_env_bool("CATALOGO_MESTRE_WORKER_APPLY_ENABLED"),
            batch_size=_env_int("CATALOGO_MESTRE_WORKER_BATCH_SIZE", 1, 1, 10),
            daily_limit=_env_int("CATALOGO_MESTRE_WORKER_DAILY_LIMIT", 25, 1, 500),
            max_attempts=_env_int("CATALOGO_MESTRE_WORKER_MAX_ATTEMPTS", 5, 1, 10),
            lease_seconds=_env_int(
                "CATALOGO_MESTRE_WORKER_LEASE_SECONDS", 900, 60, 3600
            ),
        )


@dataclass
class CatalogEnrichmentStats:
    claimed: int = 0
    succeeded: int = 0
    failed: int = 0
    skipped: int = 0
    daily_remaining: int = 0
    reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "claimed": self.claimed,
            "succeeded": self.succeeded,
            "failed": self.failed,
            "skipped": self.skipped,
            "daily_remaining": self.daily_remaining,
            "reason": self.reason,
        }


@dataclass(frozen=True)
class ClaimedDescriptionTask:
    task_id: int
    product_id: int
    execution_id: int
    context: dict[str, Any]


class CatalogMasterEnrichmentWorker:
    """Reserva uma lacuna, chama o provedor fora da transacao e salva o rascunho."""

    def __init__(
        self,
        *,
        session_factory: Callable[[], Session],
        config: CatalogEnrichmentConfig | None = None,
        provider: CatalogDescriptionProvider | None = None,
        worker_id: str | None = None,
        now_factory: Callable[[], datetime] = utcnow,
    ):
        self.session_factory = session_factory
        self.config = config or CatalogEnrichmentConfig.from_env()
        self.provider = provider
        self.worker_id = worker_id or (
            f"{socket.gethostname()}-{os.getpid()}-{uuid.uuid4().hex[:8]}"
        )
        self.now_factory = now_factory

    def run_batch(self) -> CatalogEnrichmentStats:
        stats = CatalogEnrichmentStats()
        if not self.config.enabled:
            stats.reason = "worker_desativado"
            return stats
        if not self.config.apply_enabled:
            stats.reason = "gravacao_desativada"
            return stats

        try:
            if self.provider is None:
                self.provider = OpenAICatalogDescriptionProvider()
            provider = self.provider
        except Exception as exc:
            stats.reason = f"provedor_indisponivel:{type(exc).__name__}"
            logger.error(
                "[CATALOGO MESTRE] Provedor indisponivel: %s", type(exc).__name__
            )
            return stats

        remaining = self._remaining_today()
        stats.daily_remaining = remaining
        if remaining <= 0:
            stats.reason = "limite_diario_atingido"
            return stats

        batch_limit = min(self.config.batch_size, remaining)
        for _index in range(batch_limit):
            claimed = self._claim_next(provider)
            if claimed is None:
                stats.reason = "fila_elegivel_vazia"
                break
            stats.claimed += 1
            try:
                result = provider.generate(claimed.context)
                if self._finish_success(claimed, result):
                    stats.succeeded += 1
                else:
                    stats.skipped += 1
            except Exception as exc:
                self._finish_failure(claimed, exc)
                stats.failed += 1

        stats.daily_remaining = max(0, remaining - stats.claimed)
        return stats

    def _remaining_today(self) -> int:
        now = self.now_factory()
        day_start = datetime.combine(now.date(), time.min, tzinfo=timezone.utc)
        with self.session_factory() as db:
            used = int(
                db.scalar(
                    select(func.count(CatalogoMestreEnriquecimentoExecucao.id)).where(
                        CatalogoMestreEnriquecimentoExecucao.tipo
                        == SUPPORTED_TASK_TYPE,
                        CatalogoMestreEnriquecimentoExecucao.iniciada_em >= day_start,
                    )
                )
                or 0
            )
        return max(0, self.config.daily_limit - used)

    def _claim_next(
        self, provider: CatalogDescriptionProvider
    ) -> ClaimedDescriptionTask | None:
        now = self.now_factory()
        lease_until = now + timedelta(seconds=self.config.lease_seconds)
        with self.session_factory() as db:
            eligible_status = or_(
                CatalogoMestrePendencia.status == "pendente",
                and_(
                    CatalogoMestrePendencia.status == "processando",
                    CatalogoMestrePendencia.reserva_expira_em.is_not(None),
                    CatalogoMestrePendencia.reserva_expira_em <= now,
                ),
            )
            due = or_(
                CatalogoMestrePendencia.proxima_tentativa_em.is_(None),
                CatalogoMestrePendencia.proxima_tentativa_em <= now,
            )
            description_empty = or_(
                CatalogoMestreProduto.descricao_completa.is_(None),
                func.length(func.trim(CatalogoMestreProduto.descricao_completa)) == 0,
            )
            row = db.execute(
                select(CatalogoMestrePendencia, CatalogoMestreProduto)
                .join(
                    CatalogoMestreProduto,
                    CatalogoMestreProduto.id == CatalogoMestrePendencia.produto_id,
                )
                .where(
                    CatalogoMestrePendencia.tipo == SUPPORTED_TASK_TYPE,
                    eligible_status,
                    due,
                    CatalogoMestrePendencia.tentativas < self.config.max_attempts,
                    CatalogoMestreProduto.ativo.is_(True),
                    CatalogoMestreProduto.tipo_catalogo.in_(ELIGIBLE_PRODUCT_TYPES),
                    description_empty,
                )
                .order_by(
                    CatalogoMestrePendencia.prioridade.asc(),
                    CatalogoMestrePendencia.id.asc(),
                )
                .limit(1)
                .with_for_update(skip_locked=True)
            ).first()
            if row is None:
                return None

            task, product = row
            task.status = "processando"
            task.reservada_por = self.worker_id
            task.reserva_expira_em = lease_until
            task.ultima_execucao_em = now
            task.proxima_tentativa_em = None

            execution = CatalogoMestreEnriquecimentoExecucao(
                pendencia_id=task.id,
                produto_id=product.id,
                tipo=SUPPORTED_TASK_TYPE,
                provedor=provider.provider_name,
                modelo=provider.model,
                versao_prompt=provider.prompt_version,
                worker_id=self.worker_id,
                status="processando",
                iniciada_em=now,
                metadados={"tipo_catalogo": product.tipo_catalogo},
            )
            db.add(execution)
            db.flush()
            details = dict(task.detalhes or {})
            details["execucao_atual_id"] = execution.id
            task.detalhes = details
            claimed = ClaimedDescriptionTask(
                task_id=int(task.id),
                product_id=int(product.id),
                execution_id=int(execution.id),
                context=build_product_context(product),
            )
            db.commit()
            return claimed

    def _finish_success(self, claimed: ClaimedDescriptionTask, result: Any) -> bool:
        now = self.now_factory()
        with self.session_factory() as db:
            execution = db.get(
                CatalogoMestreEnriquecimentoExecucao, claimed.execution_id
            )
            row = db.execute(
                select(CatalogoMestrePendencia, CatalogoMestreProduto)
                .join(
                    CatalogoMestreProduto,
                    CatalogoMestreProduto.id == CatalogoMestrePendencia.produto_id,
                )
                .where(
                    CatalogoMestrePendencia.id == claimed.task_id,
                    CatalogoMestrePendencia.status == "processando",
                    CatalogoMestrePendencia.reservada_por == self.worker_id,
                )
                .with_for_update()
            ).first()
            if row is None:
                if execution is not None:
                    execution.status = "descartada_reserva_perdida"
                    execution.concluida_em = now
                db.commit()
                return False

            task, product = row
            if str(product.descricao_completa or "").strip():
                task.status = "resolvida"
                task.resolvida_em = now
                self._clear_reservation(task)
                if execution is not None:
                    execution.status = "descartada_campo_preenchido"
                    execution.concluida_em = now
                db.commit()
                return False

            draft = result.draft
            product.descricao_completa = draft.descricao_completa
            product.tags = self._merge_tags(product.tags, draft.tags)

            provenance = dict(product.proveniencia or {})
            field_owners = dict(provenance.get("campos") or {})
            owner = {
                "tipo": "openai_rascunho",
                "provedor": result.provider,
                "modelo": result.model,
                "versao_prompt": result.prompt_version,
                "status_revisao": "pendente",
                "gerado_em": now.isoformat(),
                "pendencia_id": task.id,
                "execucao_id": claimed.execution_id,
                "confianca": draft.confianca,
            }
            field_owners["descricao_completa"] = owner
            if draft.tags:
                field_owners["tags"] = owner
            provenance["campos"] = field_owners
            product.proveniencia = provenance

            product_payload = {
                column.name: getattr(product, column.name)
                for column in CatalogoMestreProduto.__table__.columns
            }
            product_payload["descricao_completa"] = product.descricao_completa
            product_payload["tags"] = product.tags
            quality, gaps = quality_and_gaps(
                product_payload,
                product.imagem_quantidade,
                product.imagem_meta_quantidade,
            )
            product.qualidade_percentual = quality
            product.lacunas = gaps

            details = dict(task.detalhes or {})
            details["ultimo_enriquecimento"] = {
                "execucao_id": claimed.execution_id,
                "provedor": result.provider,
                "modelo": result.model,
                "versao_prompt": result.prompt_version,
                "confianca": draft.confianca,
                "alertas_revisao": draft.alertas_revisao,
                "gerado_em": now.isoformat(),
            }
            details.pop("execucao_atual_id", None)
            task.detalhes = details
            task.status = "aguardando_revisao"
            task.tentativas = int(task.tentativas or 0) + 1
            task.ultimo_erro = None
            task.proxima_tentativa_em = None
            self._clear_reservation(task)

            if execution is not None:
                execution.status = "rascunho_gerado"
                execution.concluida_em = now
                execution.metadados = {
                    "tipo_catalogo": product.tipo_catalogo,
                    "confianca": draft.confianca,
                    "alertas_revisao": draft.alertas_revisao,
                }
            db.commit()
            return True

    def _finish_failure(
        self, claimed: ClaimedDescriptionTask, error: Exception
    ) -> None:
        now = self.now_factory()
        error_message = self._safe_error(error)
        with self.session_factory() as db:
            execution = db.get(
                CatalogoMestreEnriquecimentoExecucao, claimed.execution_id
            )
            if execution is not None:
                execution.status = "falha"
                execution.erro = error_message
                execution.concluida_em = now

            task = db.scalar(
                select(CatalogoMestrePendencia)
                .where(
                    CatalogoMestrePendencia.id == claimed.task_id,
                    CatalogoMestrePendencia.status == "processando",
                    CatalogoMestrePendencia.reservada_por == self.worker_id,
                )
                .with_for_update()
            )
            if task is not None:
                attempts = int(task.tentativas or 0) + 1
                task.tentativas = attempts
                task.ultimo_erro = error_message
                task.status = (
                    "falha_permanente"
                    if attempts >= self.config.max_attempts
                    else "pendente"
                )
                if task.status == "pendente":
                    delay_minutes = min(360, 5 * (2 ** max(0, attempts - 1)))
                    task.proxima_tentativa_em = now + timedelta(minutes=delay_minutes)
                else:
                    task.proxima_tentativa_em = None
                details = dict(task.detalhes or {})
                details.pop("execucao_atual_id", None)
                task.detalhes = details
                self._clear_reservation(task)
            db.commit()
        logger.warning(
            "[CATALOGO MESTRE] Falha na pendencia %s: %s",
            claimed.task_id,
            error_message,
        )

    @staticmethod
    def _clear_reservation(task: CatalogoMestrePendencia) -> None:
        task.reservada_por = None
        task.reserva_expira_em = None

    @staticmethod
    def _merge_tags(existing: Any, generated: list[str]) -> list[str] | None:
        values = existing if isinstance(existing, list) else []
        merged: list[str] = []
        for raw in [*values, *generated]:
            value = " ".join(str(raw).strip().lower().split())[:80]
            if value and value not in merged:
                merged.append(value)
        return merged[:20] or None

    @staticmethod
    def _safe_error(error: Exception) -> str:
        message = " ".join(str(error).replace("\x00", " ").split())
        return f"{type(error).__name__}: {message}"[:1000]
