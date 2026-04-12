"""Serviço central de sincronização de estoque com o Bling."""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
import json
import os
from pathlib import Path
import re
import tempfile
import threading
import time
from typing import Any, Dict, List, Optional

from sqlalchemy import desc, func
from sqlalchemy.orm import Session, aliased

from app.bling_integration import BlingAPI
from app.db import SessionLocal
from app.produtos_models import Produto, ProdutoBlingSync, ProdutoBlingSyncQueue

logger = logging.getLogger(__name__)

try:
    import fcntl
except ImportError:  # pragma: no cover - fallback para Windows/local
    fcntl = None

MAX_RETRIES = 5
RETRY_BACKOFF_MINUTES = [1, 5, 15, 30, 60]
DIVERGENCIA_MINIMA = 0.01
BLING_STOCK_MIN_INTERVAL_SECONDS = float(os.getenv("BLING_STOCK_MIN_INTERVAL_SECONDS", "0.45"))
BLING_RATE_LIMIT_COOLDOWN_SECONDS = float(os.getenv("BLING_RATE_LIMIT_COOLDOWN_SECONDS", "4"))
BLING_REPROCESS_IMMEDIATE_LIMIT = int(os.getenv("BLING_REPROCESS_IMMEDIATE_LIMIT", "8"))
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


def _cooldown_rate_limit_segundos(valor: Any, default: float = BLING_RATE_LIMIT_COOLDOWN_SECONDS) -> float:
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
        or "\"period\": \"day\"" in mensagem
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
        func.row_number().over(
            partition_by=ProdutoBlingSyncQueue.produto_id,
            order_by=(
                desc(referencia_recente),
                desc(ProdutoBlingSyncQueue.updated_at),
                desc(ProdutoBlingSyncQueue.id),
            ),
        ).label("rn"),
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
    codigo_local = _normalizar_texto(codigo_busca).lower()
    if not codigo_local:
        return itens[0] if itens else None

    for item in itens:
        codigo_item = str(item.get("codigo") or item.get("sku") or "").strip().lower()
        if codigo_item and codigo_item == codigo_local:
            return item

    return itens[0] if itens else None


def _buscar_item_bling_para_produto(bling: BlingAPI, codigo_busca: str, nome_busca: str) -> Optional[dict]:
    codigo_busca = _normalizar_texto(codigo_busca)
    nome_busca = _normalizar_texto(nome_busca)

    consultas = []
    if codigo_busca:
        consultas.append({"codigo": codigo_busca, "limite": 50})
        consultas.append({"sku": codigo_busca, "limite": 50})
    if nome_busca:
        consultas.append({"nome": nome_busca, "limite": 50})

    for params in consultas:
        itens = _buscar_produtos_bling(bling, **params)
        if not itens:
            continue

        return _escolher_item_por_codigo(itens, codigo_busca)

    return None


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
    def _mark_auth_invalid(
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

    @staticmethod
    def _mark_rate_limited(
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
            _reservar_janela_envio_bling()
            BlingAPI().atualizar_estoque_produto(
                produto_id=sync.bling_produto_id,
                estoque_novo=float(fila.estoque_novo),
                observacao=f"Sync {fila.origem or 'manual'} - {fila.motivo or 'Sistema Pet'}",
            )
            return BlingSyncService._mark_success(db, fila, sync)
        except Exception as error:
            if _erro_rate_limit_bling(error):
                cooldown_seconds = _registrar_cooldown_rate_limit(error)
                fila.tentativas = max(int(fila.tentativas or 0) - 1, 0)
                sync.tentativas_sync = fila.tentativas
                return BlingSyncService._mark_rate_limited(db, fila, sync, error, cooldown_seconds)
            if _erro_autenticacao_bling(error):
                return BlingSyncService._mark_auth_invalid(db, fila, sync, error)
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

            # A execução acontece no scheduler (fila persistente), sem thread local.
            db.commit()
        except Exception as error:
            db.rollback()
            logger.warning("[BLING SYNC] Falha ao enfileirar sync: %s", error)
        finally:
            db.close()

    @staticmethod
    def normalize_sync_states_from_latest_queue(db: Session, tenant_id: Optional[int] = None) -> Dict[str, int]:
        latest_ids = _latest_queue_ids_subquery(db, tenant_id=tenant_id)
        latest_queue = aliased(ProdutoBlingSyncQueue)

        query = (
            db.query(ProdutoBlingSync, latest_queue)
            .outerjoin(latest_ids, latest_ids.c.produto_id == ProdutoBlingSync.produto_id)
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
                sync.ultima_tentativa_sync = fila.ultima_tentativa_em or sync.ultima_tentativa_sync
                sync.tentativas_sync = max(int(sync.tentativas_sync or 0), int(fila.tentativas or 0))
                repaired_error += 1

        return {
            "repaired_active": repaired_active,
            "repaired_error": repaired_error,
        }

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
            rate_limited = False
            cooldown_seconds = 0.0
            auth_invalid = False
            auth_detail = None

            for fila in filas:
                result = BlingSyncService.process_queue_item(db, fila)
                processados += 1
                if result.get("ok"):
                    sucessos += 1
                else:
                    erros += 1
                    if result.get("rate_limited"):
                        rate_limited = True
                        cooldown_seconds = float(result.get("cooldown_seconds") or 0.0)
                        break
                    if result.get("auth_invalid"):
                        auth_invalid = True
                        auth_detail = result.get("detail")
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

    @staticmethod
    def reprocess_failed_syncs(limit: int = 100, tenant_id: Optional[int] = None) -> Dict[str, Any]:
        db = SessionLocal()
        now = utc_now()
        try:
            try:
                BlingAPI().listar_naturezas_operacoes()
            except Exception as error:
                if _erro_autenticacao_bling(error):
                    detail = _mensagem_autenticacao_bling(error)
                    logger.warning("[BLING SYNC] Reprocessamento bloqueado por autenticacao invalida do Bling: %s", detail)
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

            normalizados = BlingSyncService.normalize_sync_states_from_latest_queue(db, tenant_id=tenant_id)
            latest_ids = _latest_queue_ids_subquery(db, tenant_id=tenant_id)
            query = (
                db.query(ProdutoBlingSyncQueue)
                .join(latest_ids, latest_ids.c.queue_id == ProdutoBlingSyncQueue.id)
                .filter(ProdutoBlingSyncQueue.status.in_(["erro", "falha_final"]))
            )
            if tenant_id is not None:
                query = query.filter(ProdutoBlingSyncQueue.tenant_id == tenant_id)
            filas = query.order_by(ProdutoBlingSyncQueue.updated_at.asc()).limit(limit).all()

            total = 0
            sem_fila_reenfileirados = 0
            produtos_reenfileirados: set[int] = set()
            for index, fila in enumerate(filas):
                if index < BLING_REPROCESS_IMMEDIATE_LIMIT:
                    proxima_tentativa = now
                else:
                    atraso = (index - BLING_REPROCESS_IMMEDIATE_LIMIT + 1) * BLING_STOCK_MIN_INTERVAL_SECONDS
                    proxima_tentativa = now + timedelta(seconds=atraso)
                fila.status = "pendente"
                fila.proxima_tentativa_em = proxima_tentativa
                fila.ultimo_erro = None
                fila.processado_em = None
                fila.forcar_sync = True

                sync = db.query(ProdutoBlingSync).filter(ProdutoBlingSync.id == fila.sync_id).first()
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
                    .outerjoin(latest_ids, latest_ids.c.produto_id == ProdutoBlingSync.produto_id)
                    .outerjoin(fila_atual, fila_atual.id == latest_ids.c.queue_id)
                    .filter(
                        ProdutoBlingSync.sincronizar == True,
                        ProdutoBlingSync.status == "erro",
                        ProdutoBlingSync.erro_mensagem.isnot(None),
                        ProdutoBlingSync.erro_mensagem != "",
                        ProdutoBlingSync.bling_produto_id.isnot(None),
                        ProdutoBlingSync.bling_produto_id != "",
                        fila_atual.id.is_(None),
                    )
                )
                if tenant_id is not None:
                    syncs_sem_fila_query = syncs_sem_fila_query.filter(ProdutoBlingSync.tenant_id == tenant_id)
                if produtos_reenfileirados:
                    syncs_sem_fila_query = syncs_sem_fila_query.filter(~ProdutoBlingSync.produto_id.in_(produtos_reenfileirados))

                syncs_sem_fila = (
                    syncs_sem_fila_query
                    .order_by(ProdutoBlingSync.updated_at.asc(), ProdutoBlingSync.id.asc())
                    .limit(max(limit - total, 0))
                    .all()
                )

                for sync in syncs_sem_fila:
                    queue_result = BlingSyncService.queue_product_sync(
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

                    fila = db.query(ProdutoBlingSyncQueue).filter(
                        ProdutoBlingSyncQueue.id == queue_result["queue_id"]
                    ).first()
                    if not fila:
                        continue

                    if total < BLING_REPROCESS_IMMEDIATE_LIMIT:
                        proxima_tentativa = now
                    else:
                        atraso = (total - BLING_REPROCESS_IMMEDIATE_LIMIT + 1) * BLING_STOCK_MIN_INTERVAL_SECONDS
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
                BlingSyncService.process_pending_queue(limit=process_now_limit)
                if process_now_limit > 0
                else {"processados": 0, "sucessos": 0, "erros": 0}
            )
            return {
                "reprocessados": total,
                "agendados_para_fila": total,
                "normalizados_antes": int(normalizados.get("repaired_active") or 0) + int(normalizados.get("repaired_error") or 0),
                "sem_fila_reenfileirados": sem_fila_reenfileirados,
                "limite_execucao_imediata": process_now_limit,
                "processados_agora": int(immediate_result.get("processados") or 0),
                "sucessos_agora": int(immediate_result.get("sucessos") or 0),
                "erros_agora": int(immediate_result.get("erros") or 0),
                "rate_limited": bool(immediate_result.get("rate_limited")),
                "cooldown_seconds": float(immediate_result.get("cooldown_seconds") or 0.0),
                "restantes_para_scheduler": max(total - int(immediate_result.get("processados") or 0), 0),
                "auth_invalid": bool(immediate_result.get("auth_invalid")),
                "detail": immediate_result.get("detail"),
            }
        except Exception:
            db.rollback()
            logger.exception("[BLING SYNC] Erro ao reprocessar falhas")
            return {"reprocessados": 0, "agendados_para_fila": 0, "processados_agora": 0}
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
    def reconcile_all_products(limit: Optional[int] = None, force_sync: bool = False) -> Dict[str, Any]:
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
            result = BlingSyncService.reconcile_product(produto_id, force_sync=force_sync)
            if result.get("ok") and abs(result.get("divergencia", 0)) >= DIVERGENCIA_MINIMA:
                divergencias += 1

        return {"avaliados": len(produto_ids), "divergencias": divergencias}

    @staticmethod
    def auto_link_by_sku(limit: int = 500) -> Dict[str, Any]:
        db = SessionLocal()
        try:
            subq_vinculados = (
                db.query(ProdutoBlingSync.produto_id)
                .filter(
                    ProdutoBlingSync.bling_produto_id.isnot(None),
                    ProdutoBlingSync.bling_produto_id != "",
                )
                .subquery()
            )

            produtos = (
                db.query(Produto)
                .filter(
                    Produto.codigo.isnot(None),
                    Produto.codigo != "",
                    Produto.tipo_produto != "PAI",
                )
                .filter(Produto.id.notin_(subq_vinculados))
                .order_by(Produto.id.asc())
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
                        nao_encontrados += 1
                        continue

                    bling_id = str(item.get("id") or "").strip()
                    if not bling_id:
                        nao_encontrados += 1
                        continue

                    sync = db.query(ProdutoBlingSync).filter(
                        ProdutoBlingSync.produto_id == produto.id,
                        ProdutoBlingSync.tenant_id == produto.tenant_id,
                    ).first()
                    if not sync:
                        sync = ProdutoBlingSync(tenant_id=produto.tenant_id, produto_id=produto.id)
                        db.add(sync)

                    sync.bling_produto_id = bling_id
                    sync.sincronizar = True
                    sync.status = "ativo"
                    sync.erro_mensagem = None
                    sync.updated_at = utc_now()
                    vinculados += 1
                except Exception:
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
            return {"processados": 0, "vinculados": 0, "nao_encontrados": 0, "erros": 1, "detail": str(error)}
        finally:
            db.close()

    @staticmethod
    def run_nightly_forced_link_and_sync(link_limit: int = 500, sync_limit: int = 1000) -> Dict[str, Any]:
        link_result = BlingSyncService.auto_link_by_sku(limit=link_limit)
        reconcile_result = BlingSyncService.reconcile_all_products(limit=sync_limit, force_sync=True)
        queue_result = BlingSyncService.process_pending_queue(limit=sync_limit)
        return {
            "link": link_result,
            "reconcile": reconcile_result,
            "queue": queue_result,
        }

    @staticmethod
    def get_health_snapshot(db: Session, tenant_id: Optional[str] = None) -> Dict[str, Any]:
        queue_query = db.query(ProdutoBlingSyncQueue)
        sync_query = db.query(ProdutoBlingSync)

        if tenant_id is not None:
            queue_query = queue_query.filter(ProdutoBlingSyncQueue.tenant_id == tenant_id)
            sync_query = sync_query.filter(ProdutoBlingSync.tenant_id == tenant_id)

        pendentes = queue_query.filter(
            ProdutoBlingSyncQueue.status.in_(["pendente", "erro", "processando"])
        ).count()
        com_erro = sync_query.filter(ProdutoBlingSync.status == "erro").count()
        ativos = sync_query.filter(ProdutoBlingSync.sincronizar == True).count()
        divergentes = sync_query.filter(
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
