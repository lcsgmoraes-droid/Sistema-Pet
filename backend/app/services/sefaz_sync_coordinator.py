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
# Política muito conservadora: mínimo 12h, máximo 24h.
# Índice 0 = 1ª vez sem documento → aguarda 720 min (12h)
# Índice 4 = 5ª+ vez sem documento → aguarda 1440 min (24h)
BACKOFF_MINUTES = [720, 720, 1440, 1440, 1440]
PENALIDADE_656_MINUTOS = 300


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
        from app.services.sefaz_service import SefazConsumoIndevidoError, SefazService

        nsu_loop = cfg.get("ultimo_nsu", "000000000000000")
        total_docs = 0
        total_importadas = 0
        total_duplicadas = 0
        erro_656 = False
        erro_generico = False
        mensagem_erro_generico: str | None = None
        mensagem_erro_656: str | None = None
        nsu_sugerido_656: str | None = None
        max_nsu_sugerido_656: str | None = None
        pulou_para_hoje = False
        MAX_LOTES = 1  # Uma chamada por ciclo — evita cStat 656 por consumo excessivo

        for lote_idx in range(MAX_LOTES):
            try:
                resultado = SefazService.sincronizar_nsu(
                    config=cfg,
                    ultimo_nsu=nsu_loop,
                )
            except Exception as exc:
                if isinstance(exc, SefazConsumoIndevidoError):
                    erro_656 = True
                    mensagem_erro_656 = exc.mensagem
                    nsu_sugerido_656 = exc.ult_nsu or exc.max_nsu
                    max_nsu_sugerido_656 = exc.max_nsu
                    logger.warning(
                        f"[SEFAZ] [{reason}] cStat 656 no lote {lote_idx + 1} "
                        f"(tenant {tenant_id_str}) — ultNSU sugerido={nsu_sugerido_656}"
                    )
                    break

                logger.warning(
                    f"[SEFAZ] [{reason}] Erro no lote {lote_idx + 1} "
                    f"(tenant {tenant_id_str}): {exc}"
                )
                if "656" in str(exc) or "Consumo Indevido" in str(exc):
                    erro_656 = True
                    mensagem_erro_656 = str(exc)
                    break

                erro_generico = True
                mensagem_erro_generico = str(exc)
                break

            docs = resultado.get("docs_list", [])
            novo_nsu = resultado.get("ultimo_nsu", nsu_loop)
            max_nsu = resultado.get("max_nsu", novo_nsu)

            # comecar_do_hoje: avança NSU para o ponto atual sem importar docs antigos
            if cfg.get("comecar_do_hoje"):
                nsu_loop = max_nsu
                pulou_para_hoje = True
                cfg["comecar_do_hoje"] = False
                logger.info(
                    f"[SEFAZ] [{reason}] comecar_do_hoje ativo — NSU avançado para {max_nsu} "
                    f"(tenant {tenant_id_str})"
                )
                break

            total_docs += len(docs)

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

        now = datetime.now(timezone.utc)
        now_iso = now.isoformat()

        # ── Erro 656 — aplicar cooldown e salvar ultNSU sugerido ────────────
        if erro_656:
            penalidade_min = PENALIDADE_656_MINUTOS
            proximo = now + timedelta(minutes=penalidade_min)
            nsu_ult_retorno = str(nsu_sugerido_656 or cfg.get("ultimo_nsu", "000000000000000")).strip().zfill(15)
            nsu_max_retorno = str(max_nsu_sugerido_656 or nsu_sugerido_656 or cfg.get("ultimo_nsu", "000000000000000")).strip().zfill(15)
            if nsu_sugerido_656:
                cfg["ultimo_nsu"] = nsu_ult_retorno
            detalhe_656 = mensagem_erro_656 or "SEFAZ bloqueou por consumo indevido."
            cfg.update({
                "ultimo_sync_at": now_iso,
                "_proximo_sync_permitido_at": proximo.isoformat(),
                "_sync_bloqueado_656": True,
                "ultimo_sync_status": "erro_656",
                "ultimo_sync_mensagem": (
                    f"{detalhe_656} "
                    f"ultNSU={nsu_ult_retorno}, maxNSU={nsu_max_retorno}. "
                    f"Próxima tentativa em {penalidade_min} min."
                ),
                "ultimo_sync_cstat": "656",
                "ultimo_sync_xmotivo": detalhe_656,
                "ultimo_sync_ult_nsu_retorno": nsu_ult_retorno,
                "ultimo_sync_max_nsu_retorno": nsu_max_retorno,
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

        # ── Erro genérico — registrar detalhe real e não mascarar como OK ───
        if erro_generico:
            intervalo_erro_min = max(5, int(cfg.get("importacao_intervalo_min", 15)))
            proximo_erro = now + timedelta(minutes=intervalo_erro_min)
            detalhe = mensagem_erro_generico or "Falha desconhecida na sincronização SEFAZ."
            cfg.update({
                "ultimo_sync_at": now_iso,
                "_proximo_sync_permitido_at": proximo_erro.isoformat(),
                "_sync_bloqueado_656": False,
                "ultimo_sync_status": "erro",
                "ultimo_sync_mensagem": (
                    f"Falha na sincronização SEFAZ: {detalhe}. "
                    f"Nova tentativa automática em {intervalo_erro_min} min."
                ),
                "ultimo_sync_cstat": None,
                "ultimo_sync_xmotivo": detalhe,
                "ultimo_sync_ult_nsu_retorno": str(cfg.get("ultimo_nsu", nsu_loop)).strip().zfill(15),
                "ultimo_sync_max_nsu_retorno": str(cfg.get("ultimo_nsu", nsu_loop)).strip().zfill(15),
                "ultimo_sync_documentos": 0,
            })
            self._atomic_save(config_path, cfg)
            logger.warning(
                f"[SEFAZ] [{reason}] ❌ Tenant {tenant_id_str}: erro real registrado. "
                f"Detalhe={detalhe}"
            )
            return {
                "status": "error",
                "mensagem": cfg["ultimo_sync_mensagem"],
                "documentos": 0,
                "importadas": 0,
                "duplicadas": 0,
                "proximo_permitido_at": proximo_erro.isoformat(),
            }

        # ── Sucesso — backoff adaptativo ─────────────────────────────────────
        backoff_index = int(cfg.get("backoff_index", 0))
        if total_docs > 0 or pulou_para_hoje:
            backoff_index = 0  # docs encontrados ou pulo intencional: resetar backoff
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
            "ultimo_sync_cstat": str(resultado.get("c_stat", "ok")),
            "ultimo_sync_xmotivo": str(resultado.get("x_motivo", "")),
            "ultimo_sync_ult_nsu_retorno": str(resultado.get("ultimo_nsu", nsu_loop)).strip().zfill(15),
            "ultimo_sync_max_nsu_retorno": str(resultado.get("max_nsu", nsu_loop)).strip().zfill(15),
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
