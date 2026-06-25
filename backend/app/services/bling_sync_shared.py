"""Utilitarios compartilhados da sincronizacao de estoque Bling."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
import json
import os
from pathlib import Path
import re
import tempfile
import threading
import time
from typing import Any, Dict, Optional

from sqlalchemy import desc, func
from sqlalchemy.orm import Session

from app.bling_integration import BlingAPI
from app.bling_sync.product_matching import _item_bling_tem_sku_estrito
from app.produtos_models import ProdutoBlingSyncQueue
from app.tenancy.context import get_current_tenant
from app.utils.tenant_safe_sql import execute_tenant_safe_all

try:
    import fcntl
except ImportError:  # pragma: no cover - fallback para Windows/local
    fcntl = None

MAX_RETRIES = 5
RETRY_BACKOFF_MINUTES = [1, 5, 15, 30, 60]
DIVERGENCIA_MINIMA = 0.01
BLING_STOCK_MIN_INTERVAL_SECONDS = float(
    os.getenv("BLING_STOCK_MIN_INTERVAL_SECONDS", "0.45")
)
BLING_RATE_LIMIT_COOLDOWN_SECONDS = float(
    os.getenv("BLING_RATE_LIMIT_COOLDOWN_SECONDS", "4")
)
BLING_REPROCESS_IMMEDIATE_LIMIT = int(os.getenv("BLING_REPROCESS_IMMEDIATE_LIMIT", "8"))
BLING_SECONDARY_READY_DEFER_THRESHOLD = int(
    os.getenv("BLING_SECONDARY_READY_DEFER_THRESHOLD", "1")
)
BLING_SECONDARY_TOTAL_DEFER_THRESHOLD = int(
    os.getenv("BLING_SECONDARY_TOTAL_DEFER_THRESHOLD", "5")
)
BLING_RATE_LIMIT_STATE_FILE = Path(
    os.getenv("BLING_RATE_LIMIT_STATE_FILE")
    or (Path(tempfile.gettempdir()) / "petshop_bling_stock_rate_limit.json")
)
_RATE_LIMIT_FALLBACK_LOCK = threading.Lock()


def _normalizar_texto(valor: Optional[str]) -> str:
    return re.sub(r"\s+", " ", (valor or "").strip())


def _erro_rate_limit_bling(valor: Any) -> bool:
    mensagem = _normalizar_texto(str(valor or "")).lower()
    return (
        "too_many_requests" in mensagem
        or "too many requests" in mensagem
        or "429" in mensagem
        or "limite de requisi" in mensagem
    )


def _erro_autenticacao_bling(valor: Any) -> bool:
    mensagem = _normalizar_texto(str(valor or "")).lower()
    return (
        "invalid_token" in mensagem
        or "invalid token" in mensagem
        or "invalid_grant" in mensagem
        or "unauthorized" in mensagem
        or "401 client error" in mensagem
        or "token expirado" in mensagem
    )


def _detalhe_autenticacao_bling(valor: Any) -> str:
    mensagem = _normalizar_texto(str(valor or "")).lower()
    if "invalid_grant" in mensagem:
        return "400 INVALID_GRANT"
    if "invalid_token" in mensagem or "invalid token" in mensagem:
        return "401 INVALID_TOKEN"
    if "unauthorized" in mensagem or "401 client error" in mensagem:
        return "401 UNAUTHORIZED"
    return "BLING_AUTH_INVALID"


def _mensagem_autenticacao_bling(valor: Any) -> str:
    detalhe = _detalhe_autenticacao_bling(valor)
    if detalhe == "400 INVALID_GRANT":
        return (
            "A integracao com o Bling perdeu a autorizacao salva. "
            "Reconecte o Bling antes de reprocessar ou forcar novos envios."
        )
    return (
        "O token do Bling expirou e a renovacao automatica nao conseguiu concluir. "
        "Reconecte o Bling antes de reprocessar ou forcar novos envios."
    )


def _cooldown_rate_limit_segundos(
    valor: Any, default: float = BLING_RATE_LIMIT_COOLDOWN_SECONDS
) -> float:
    mensagem = _normalizar_texto(str(valor or "")).lower()
    cooldown = float(default)

    if "retry-after" in mensagem:
        match_retry = re.search(r"retry-after[^0-9]*(\d+)", mensagem)
        if match_retry:
            cooldown = max(cooldown, float(match_retry.group(1)))

    period_kind = None
    match_period = re.search(r"'period':\s*'([^']+)'", mensagem)
    if match_period:
        period_kind = match_period.group(1).strip().lower()
        if period_kind == "second":
            cooldown = max(cooldown, 2.0)
        elif period_kind == "minute":
            cooldown = max(cooldown, 60.0)
        elif period_kind == "hour":
            cooldown = max(cooldown, 3600.0)
        elif period_kind == "day":
            cooldown = max(cooldown, _cooldown_daily_limit_seconds())

    if "por segundo" in mensagem:
        cooldown = max(cooldown, 2.0)
    elif "por minuto" in mensagem:
        cooldown = max(cooldown, 60.0)
    elif "por hora" in mensagem:
        cooldown = max(cooldown, 3600.0)
    elif "por dia" in mensagem or "amanha" in mensagem or "amanhã" in mensagem:
        cooldown = max(cooldown, _cooldown_daily_limit_seconds())

    return cooldown


def _mensagem_rate_limit_bling(valor: Any, cooldown_seconds: float) -> str:
    mensagem = _normalizar_texto(str(valor or "")).lower()
    if (
        "'period': 'day'" in mensagem
        or '"period": "day"' in mensagem
        or "por dia" in mensagem
        or "amanha" in mensagem
        or "amanhã" in mensagem
    ):
        return (
            "Bling atingiu o limite diario de requisicoes. "
            f"Nova tentativa automatica amanha, por volta de {_format_retry_eta(cooldown_seconds)}. "
            f"Detalhe: {_normalizar_texto(str(valor or 'rate limit diario do Bling'))[:320]}"
        )

    return (
        "Bling limitou as requisicoes agora. "
        f"Nova tentativa automatica em cerca de {int(max(cooldown_seconds, 1))}s. "
        f"Detalhe: {_normalizar_texto(str(valor or 'rate limit do Bling'))[:320]}"
    )


def _cooldown_daily_limit_seconds() -> float:
    now = datetime.now().astimezone()
    retry_at = (now + timedelta(days=1)).replace(
        hour=0,
        minute=5,
        second=0,
        microsecond=0,
    )
    return max((retry_at - now).total_seconds(), 3600.0)


def _format_retry_eta(cooldown_seconds: float) -> str:
    retry_at = datetime.now().astimezone() + timedelta(seconds=max(cooldown_seconds, 0))
    return retry_at.strftime("%H:%M")


def _secondary_jobs_defer_reason(
    *,
    cooldown_active: bool,
    ready_queue: int,
    total_queue: int,
    forced_queue: int,
) -> str | None:
    if cooldown_active:
        return "bling_cooldown_active"
    if forced_queue > 0:
        return "manual_stock_sync_pending"
    if ready_queue >= max(BLING_SECONDARY_READY_DEFER_THRESHOLD, 1):
        return "stock_queue_ready"
    if total_queue >= max(BLING_SECONDARY_TOTAL_DEFER_THRESHOLD, 1):
        return "stock_queue_backlog"
    return None


def _rate_limit_state_path() -> Path:
    path = BLING_RATE_LIMIT_STATE_FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _latest_queue_ids_subquery(db: Session, tenant_id: Optional[int] = None):
    referencia_recente = func.coalesce(
        ProdutoBlingSyncQueue.proxima_tentativa_em,
        ProdutoBlingSyncQueue.processado_em,
        ProdutoBlingSyncQueue.ultima_tentativa_em,
        ProdutoBlingSyncQueue.updated_at,
        ProdutoBlingSyncQueue.created_at,
    )
    query = db.query(
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
    if tenant_id is not None:
        query = query.filter(ProdutoBlingSyncQueue.tenant_id == tenant_id)
    ranked = query.subquery()
    return (
        db.query(
            ranked.c.produto_id.label("produto_id"),
            ranked.c.queue_id.label("queue_id"),
        )
        .filter(ranked.c.rn == 1)
        .subquery()
    )


def _read_rate_limit_state(handle) -> Dict[str, Any]:
    handle.seek(0)
    raw = handle.read().strip()
    if not raw:
        return {}
    try:
        data = json.loads(raw)
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def _write_rate_limit_state(handle, state: Dict[str, Any]) -> None:
    handle.seek(0)
    handle.truncate()
    handle.write(json.dumps(state))
    handle.flush()
    try:
        os.fsync(handle.fileno())
    except OSError:
        pass


class _SharedRateLimitState:
    def __enter__(self):
        self._handle = open(_rate_limit_state_path(), "a+", encoding="utf-8")
        if fcntl:
            fcntl.flock(self._handle.fileno(), fcntl.LOCK_EX)
        else:  # pragma: no cover - usado apenas quando fcntl nao existe
            _RATE_LIMIT_FALLBACK_LOCK.acquire()
        self.state = _read_rate_limit_state(self._handle)
        return self

    def save(self) -> None:
        _write_rate_limit_state(self._handle, self.state)

    def __exit__(self, exc_type, exc, tb):
        try:
            if fcntl:
                try:
                    fcntl.flock(self._handle.fileno(), fcntl.LOCK_UN)
                except Exception:
                    pass
            else:  # pragma: no cover
                _RATE_LIMIT_FALLBACK_LOCK.release()
        finally:
            self._handle.close()


def _reservar_janela_envio_bling() -> float:
    while True:
        sleep_for = 0.0
        with _SharedRateLimitState() as shared:
            now = time.time()
            next_allowed_at = float(shared.state.get("next_allowed_at") or 0.0)
            cooldown_until = float(shared.state.get("cooldown_until") or 0.0)
            available_at = max(next_allowed_at, cooldown_until)

            if available_at <= now:
                shared.state["next_allowed_at"] = now + BLING_STOCK_MIN_INTERVAL_SECONDS
                shared.save()
                return 0.0

            sleep_for = max(available_at - now, 0.05)

        time.sleep(min(sleep_for, 5.0))


def _registrar_cooldown_rate_limit(valor: Any) -> float:
    cooldown = _cooldown_rate_limit_segundos(valor)
    with _SharedRateLimitState() as shared:
        now = time.time()
        shared.state["cooldown_until"] = max(
            float(shared.state.get("cooldown_until") or 0.0),
            now + cooldown,
        )
        shared.state["next_allowed_at"] = max(
            float(shared.state.get("next_allowed_at") or 0.0),
            now + cooldown,
        )
        shared.save()
    return cooldown


def _extrair_produtos_bling(resultado: Optional[dict]) -> list[dict]:
    itens = (resultado or {}).get("data", [])
    produtos: list[dict] = []
    for item in itens:
        if isinstance(item, dict) and isinstance(item.get("produto"), dict):
            produtos.append(item.get("produto") or {})
        elif isinstance(item, dict):
            produtos.append(item)
    return produtos


def _buscar_produtos_bling(bling: BlingAPI, **params) -> list[dict]:
    try:
        return _extrair_produtos_bling(bling.listar_produtos(**params))
    except Exception:
        return []


def _escolher_item_por_codigo(itens: list[dict], codigo_busca: str) -> Optional[dict]:
    codigo_local = _normalizar_texto(codigo_busca)
    if not codigo_local:
        return None

    for item in itens:
        if _item_bling_tem_sku_estrito(item, codigo_local):
            return item

    return None


def _buscar_item_bling_para_produto(
    bling: BlingAPI, codigo_busca: str, nome_busca: str
) -> Optional[dict]:
    codigo_busca = _normalizar_texto(codigo_busca)

    consultas = []
    if codigo_busca:
        consultas.append({"codigo": codigo_busca, "limite": 50})
        consultas.append({"sku": codigo_busca, "limite": 50})

    for params in consultas:
        itens = _buscar_produtos_bling(bling, **params)
        if not itens:
            continue

        return _escolher_item_por_codigo(itens, codigo_busca)

    return None


def utc_now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _first_column_values(rows) -> list[Any]:
    values: list[Any] = []
    for row in rows:
        if isinstance(row, (tuple, list)):
            values.append(row[0])
            continue
        mapping = getattr(row, "_mapping", None)
        if mapping:
            values.append(next(iter(mapping.values())))
            continue
        values.append(row)
    return values


def _positive_limit(limit: Optional[int]) -> Optional[int]:
    if limit is None:
        return None
    return max(int(limit or 0), 0)


def _remaining_limit(limit: Optional[int], processed: int) -> Optional[int]:
    total_limit = _positive_limit(limit)
    if total_limit is None:
        return None
    return max(total_limit - processed, 0)


def _tenant_scope_or_current(tenant_id=None):
    return tenant_id if tenant_id is not None else get_current_tenant()


def listar_tenants_com_produto_bling_sync_recentes(
    db: Session, *, minutes: int
) -> list[Any]:
    cutoff = utc_now() - timedelta(minutes=max(int(minutes or 1), 1))
    rows = execute_tenant_safe_all(
        db,
        """
        SELECT DISTINCT tenant_id
        FROM produto_bling_sync
        WHERE sincronizar IS TRUE
          AND bling_produto_id IS NOT NULL
          AND bling_produto_id <> ''
          AND (
                updated_at >= :cutoff
                OR status IN ('erro', 'pendente')
              )
        ORDER BY tenant_id
        """,
        {"cutoff": cutoff},
        require_tenant=False,
        allow_global=True,
        global_reason="Job global Bling produto recentes precisa descobrir tenants com produtos alterados ou pendentes.",
    )
    return _first_column_values(rows)


def listar_tenants_com_produto_bling_sync_ativo(db: Session) -> list[Any]:
    rows = execute_tenant_safe_all(
        db,
        """
        SELECT DISTINCT tenant_id
        FROM produto_bling_sync
        WHERE sincronizar IS TRUE
          AND bling_produto_id IS NOT NULL
          AND bling_produto_id <> ''
        ORDER BY tenant_id
        """,
        require_tenant=False,
        allow_global=True,
        global_reason="Job global Bling produto ativo precisa descobrir tenants com produtos vinculados.",
    )
    return _first_column_values(rows)


def listar_tenants_com_produtos_sem_vinculo_bling(db: Session) -> list[Any]:
    rows = execute_tenant_safe_all(
        db,
        """
        SELECT DISTINCT p.tenant_id
        FROM produtos p
        LEFT JOIN produto_bling_sync s
          ON s.produto_id = p.id
         AND s.tenant_id = p.tenant_id
        WHERE p.codigo IS NOT NULL
          AND p.codigo <> ''
          AND COALESCE(p.tipo_produto, '') <> 'PAI'
          AND (
                s.id IS NULL
                OR s.bling_produto_id IS NULL
                OR s.bling_produto_id = ''
              )
        ORDER BY p.tenant_id
        """,
        require_tenant=False,
        allow_global=True,
        global_reason="Job global Bling auto-link precisa descobrir tenants com produtos sem vinculo.",
    )
    return _first_column_values(rows)
