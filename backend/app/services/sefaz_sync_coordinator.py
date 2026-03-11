"""
Coordenador central de sincronizações SEFAZ.

Garante que apenas UMA sincronização por tenant aconteça por vez,
entre todos os 4 workers uvicorn.

Responsabilidades:
  - Lock in-process (threading.Lock) — impede 2 threads do mesmo worker
  - Lock cross-process (fcntl.flock) — impede 2 workers diferentes
  - Executa os lotes via SefazService.sincronizar_nsu
  - Importa documentos para o banco via importar_docs_sefaz
  - Aplica backoff adaptativo (sem docs = espera aumenta progressivamente)
  - Grava config.json atomicamente (via arquivo .tmp + rename)

NÃO decide QUANDO sincronizar — isso é do scheduler (main.py)
e do endpoint manual (sefaz_routes.py).
"""
from __future__ import annotations

import json
import logging
import os
import threading
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_LOCK_FILE = "/tmp/sefaz_sync.lock"

# Intervalos de backoff quando não há documentos novos.
# Política conservadora para reduzir risco de consumo indevido:
# Índice 0 = 1ª vez sem documento → aguarda 120 min
# Índice 4 = 5ª+ vez sem documento → aguarda 1440 min (24h)
BACKOFF_MINUTES = [120, 240, 480, 720, 1440]


class SefazSyncCoordinator:
    """
    Coordenador singleton de sincronizações SEFAZ.
    Uma instância por worker uvicorn (processos independentes).
    Coordenação cross-worker via arquivo de lock em /tmp.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._running: set[str] = set()

    def is_syncing(self, tenant_id_str: str) -> bool:
        """Retorna True se este worker já está sincronizando o tenant."""
        with self._lock:
            return tenant_id_str in self._running

    def try_sync(
        self,
        tenant_id_str: str,
        config_path: Path,
        cfg: dict[str, Any],
        reason: str = "scheduler",
    ) -> dict[str, Any]:
        """
        Tenta adquirir os locks e executar sincronização para o tenant.

        O CHAMADOR decide se está na hora de rodar (timing/intervalo).
        Este método garante apenas EXCLUSIVIDADE na execução.

        Retorna dict com chave 'status':
          'ok'              → sincronizou com sucesso
          'erro_656'        → SEFAZ bloqueou (cStat 656)
          'already_running' → já rodando neste worker (mesmo processo)
          'lock_busy'       → outro worker está rodando (outro processo)
          'error'           → erro inesperado
        """
        # 1. Verificar execução in-process (thread-safe)
        with self._lock:
            if tenant_id_str in self._running:
                logger.info(
                    f"[SEFAZ] [{reason}] Sync ignorada (already_running) — tenant {tenant_id_str}"
                )
                return {
                    "status": "already_running",
                    "mensagem": "Sincronização SEFAZ já está em andamento. Aguarde.",
                }
            self._running.add(tenant_id_str)

        lock_f = None
        try:
            # 2. Adquirir lock de arquivo — coordenação cross-worker
            try:
                import fcntl
                lock_f = open(_LOCK_FILE, "w")
                try:
                    fcntl.flock(lock_f, fcntl.LOCK_EX | fcntl.LOCK_NB)
                except OSError:
                    lock_f.close()
                    lock_f = None
                    with self._lock:
                        self._running.discard(tenant_id_str)
                    logger.info(
                        f"[SEFAZ] [{reason}] Sync ignorada (lock_busy) — tenant {tenant_id_str}"
                    )
                    return {
                        "status": "lock_busy",
                        "mensagem": "Outro processo já está sincronizando com a SEFAZ. Aguarde instantes.",
                    }
            except ImportError:
                lock_f = None  # Windows — sem fcntl, aceita sem lock de arquivo

            # 3. Executar
            logger.info(f"[SEFAZ] [{reason}] Iniciando sync — tenant {tenant_id_str}")
            return self._execute(tenant_id_str, config_path, cfg, reason)

        except Exception as exc:
            logger.warning(
                f"[SEFAZ] [{reason}] Erro inesperado no coordinator "
                f"(tenant {tenant_id_str}): {exc}"
            )
            return {"status": "error", "mensagem": str(exc)}
        finally:
            with self._lock:
                self._running.discard(tenant_id_str)
            if lock_f:
                try:
                    lock_f.close()
                except Exception:
                    pass

    def _execute(
        self,
        tenant_id_str: str,
        config_path: Path,
        cfg: dict[str, Any],
        reason: str,
    ) -> dict[str, Any]:
        from app.db import SessionLocal
        from app.notas_entrada_routes import importar_docs_sefaz
        from app.services.sefaz_service import SefazService

        nsu_loop = cfg.get("ultimo_nsu", "000000000000000")
        total_docs = 0
        total_importadas = 0
        total_duplicadas = 0
        erro_656 = False
        MAX_LOTES = 3

        for lote_idx in range(MAX_LOTES):
            try:
                resultado = SefazService.sincronizar_nsu(
                    config=cfg,
                    ultimo_nsu=nsu_loop,
                )
            except Exception as exc:
                logger.warning(
                    f"[SEFAZ] [{reason}] Erro no lote {lote_idx + 1} "
                    f"(tenant {tenant_id_str}): {exc}"
                )
                if "656" in str(exc) or "Consumo Indevido" in str(exc):
                    erro_656 = True
                break

            docs = resultado.get("docs_list", [])
            total_docs += len(docs)
            novo_nsu = resultado.get("ultimo_nsu", nsu_loop)
            max_nsu = resultado.get("max_nsu", novo_nsu)

            if docs:
                db = SessionLocal()
                try:
                    r = importar_docs_sefaz(docs, tenant_id_str, db)
                    total_importadas += r.get("importadas", 0)
                    total_duplicadas += r.get("duplicadas", 0)
                    if r["importadas"] > 0 or r.get("erros", 0) > 0:
                        logger.info(
                            f"[SEFAZ] [{reason}] Lote {lote_idx + 1}: "
                            f"{r['importadas']} salvas, {r['duplicadas']} duplicadas, "
                            f"{r['erros']} erros, "
                            f"{r.get('saidas_descartadas', 0)} saídas. NSU: {novo_nsu}"
                        )
                finally:
                    db.close()

            nsu_loop = novo_nsu

            if novo_nsu >= max_nsu or not docs:
                break

            # Pausa entre lotes — reduz risco de cStat 656
            time.sleep(5)

        now = datetime.now(timezone.utc)
        now_iso = now.isoformat()

        # ── Erro 656 — penalidade de 90 minutos ─────────────────────────────
        if erro_656:
            penalidade_min = 180
            proximo = now + timedelta(minutes=penalidade_min)
            cfg.update({
                "ultimo_sync_at": now_iso,
                "_proximo_sync_permitido_at": proximo.isoformat(),
                "_sync_bloqueado_656": True,
                "ultimo_sync_status": "erro_656",
                "ultimo_sync_mensagem": (
                    f"SEFAZ bloqueou (cStat 656). "
                    f"Próxima tentativa em {penalidade_min} min."
                ),
                "ultimo_sync_documentos": 0,
            })
            self._atomic_save(config_path, cfg)
            logger.warning(
                f"[SEFAZ] [{reason}] ⏳ Tenant {tenant_id_str}: "
                f"penalidade {penalidade_min}min aplicada (cStat 656)"
            )
            return {
                "status": "erro_656",
                "mensagem": cfg["ultimo_sync_mensagem"],
                "documentos": 0,
                "importadas": 0,
                "duplicadas": 0,
                "proximo_permitido_at": proximo.isoformat(),
            }

        # ── Sucesso — backoff adaptativo ─────────────────────────────────────
        backoff_index = int(cfg.get("backoff_index", 0))
        if total_docs > 0:
            backoff_index = 0  # documentos encontrados: resetar backoff
        else:
            if backoff_index < len(BACKOFF_MINUTES) - 1:
                backoff_index += 1  # sem documentos: avançar backoff

        intervalo_min = BACKOFF_MINUTES[backoff_index]
        proximo = now + timedelta(minutes=intervalo_min)

        msg = (
            f"Sincronização concluída. {total_docs} documento(s) recebido(s), "
            f"{total_importadas} NF-e(s) importada(s)."
            if total_docs
            else f"Nenhum documento novo. Próxima verificação em {intervalo_min} min."
        )

        cfg.update({
            "ultimo_sync_at": now_iso,
            "_proximo_sync_permitido_at": proximo.isoformat(),
            "_sync_bloqueado_656": False,
            "backoff_index": backoff_index,
            "ultimo_sync_status": "ok",
            "ultimo_nsu": nsu_loop,
            "ultimo_sync_documentos": total_docs,
            "ultimo_sync_mensagem": msg,
        })
        self._atomic_save(config_path, cfg)
        logger.info(
            f"[SEFAZ] [{reason}] ✅ Tenant {tenant_id_str}: "
            f"{total_docs} doc(s), {total_importadas} importada(s). "
            f"NSU: {nsu_loop}. "
            f"Próxima: {intervalo_min}min (backoff_index={backoff_index})"
        )
        return {
            "status": "ok",
            "documentos": total_docs,
            "importadas": total_importadas,
            "duplicadas": total_duplicadas,
            "ultimo_nsu": nsu_loop,
            "mensagem": msg,
            "proximo_permitido_at": proximo.isoformat(),
        }

    @staticmethod
    def _atomic_save(path: Path, data: dict[str, Any]) -> None:
        """Gravação atômica: escreve em .tmp e faz rename (os.replace)."""
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(str(tmp), str(path))


# Singleton global — uma instância por worker uvicorn
sefaz_coordinator = SefazSyncCoordinator()
