"""
Coordenador central de sincronizações SEFAZ.

Garante que apenas UMA sincronização por tenant aconteça por vez,
entre todos os 4 workers uvicorn.

Responsabilidades:
  - Lock in-process — impede operações simultâneas no mesmo worker
  - Lock cross-process — serializa sync e alterações de config entre workers
  - Executa os lotes via SefazService.sincronizar_nsu
  - Persiste todos os documentos recebidos antes de avançar o NSU
  - Aplica espera mínima após maxNSU/137 e bloqueio após 656
  - Grava config.json atomicamente

NÃO decide QUANDO sincronizar — isso é do scheduler (main.py)
e do endpoint manual (sefaz_routes.py).
"""

from __future__ import annotations

import json
import logging
import os
import threading
import tempfile
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_LOCK_FILE = Path(tempfile.gettempdir()) / "sefaz_sync.lock"

# Ao atingir maxNSU ou receber cStat 137, aguarda mais que a hora mínima
# exigida pelo serviço. Quando há backlog, busca só mais um lote no próximo
# ciclo do scheduler (que roda a cada 10 minutos).
INTERVALO_SEM_NOVIDADES_MINUTOS = 65
INTERVALO_BACKLOG_MINUTOS = 10
PENALIDADE_656_MINUTOS = 300


def _nsu_15(valor: Any) -> str | None:
    texto = str(valor or "").strip()
    return texto if len(texto) == 15 and texto.isdigit() else None


def _data_utc(valor: Any) -> datetime | None:
    if not valor:
        return None
    try:
        data = datetime.fromisoformat(str(valor))
    except ValueError:
        return None
    return data.replace(tzinfo=timezone.utc) if data.tzinfo is None else data


def bloqueio_656_ate(cfg: dict[str, Any]) -> datetime | None:
    bloqueio = _data_utc(cfg.get("dfe_656_bloqueado_ate"))
    if cfg.get("_sync_bloqueado_656"):
        ultimo = _data_utc(cfg.get("ultimo_sync_at"))
        legado = _data_utc(cfg.get("_proximo_sync_permitido_at"))
        if ultimo is not None:
            legado = (
                max(legado, ultimo + timedelta(minutes=PENALIDADE_656_MINUTOS))
                if legado is not None
                else ultimo + timedelta(minutes=PENALIDADE_656_MINUTOS)
            )
        if legado is not None:
            bloqueio = max(bloqueio, legado) if bloqueio is not None else legado
    return bloqueio


def proximo_sync_permitido(cfg: dict[str, Any]) -> datetime | None:
    """Aplica a espera oficial mesmo a configurações legadas com prazo curto."""
    proximo = _data_utc(cfg.get("_proximo_sync_permitido_at"))
    bloqueio = bloqueio_656_ate(cfg)
    if bloqueio is not None:
        proximo = max(proximo, bloqueio) if proximo is not None else bloqueio
    ultimo = _data_utc(cfg.get("ultimo_sync_at"))
    if ultimo is None:
        return proximo

    cstat = str(cfg.get("ultimo_sync_cstat") or "")
    ult_retorno = _nsu_15(cfg.get("ultimo_sync_ult_nsu_retorno"))
    max_retorno = _nsu_15(cfg.get("ultimo_sync_max_nsu_retorno"))
    if cstat == "656":
        minimo = ultimo + timedelta(minutes=PENALIDADE_656_MINUTOS)
    elif cstat == "137" or (
        cfg.get("ultimo_sync_status") == "ok"
        and ult_retorno is not None
        and ult_retorno == max_retorno
    ):
        minimo = ultimo + timedelta(minutes=INTERVALO_SEM_NOVIDADES_MINUTOS)
    elif proximo is None:
        minimo = ultimo + timedelta(
            minutes=max(60, int(cfg.get("importacao_intervalo_min", 60)))
        )
    else:
        return proximo
    return max(proximo, minimo) if proximo is not None else minimo


class SefazLockBusy(Exception):
    """Outra operação de sync ou configuração SEFAZ detém o lock."""


class SefazSyncCoordinator:
    """
    Coordenador singleton de sincronizações SEFAZ.
    Uma instância por worker uvicorn (processos independentes).
    Coordenação cross-worker via arquivo de lock temporário.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._operation_lock = threading.Lock()
        self._running: set[str] = set()

    def is_syncing(self, tenant_id_str: str) -> bool:
        """Retorna True se este worker já está sincronizando o tenant."""
        with self._lock:
            return tenant_id_str in self._running

    @contextmanager
    def config_guard(self):
        """Serializa sync e escrita da configuração dentro e entre workers."""
        if not self._operation_lock.acquire(blocking=False):
            raise SefazLockBusy()
        lock_f = None
        unlock = None
        try:
            lock_f = open(_LOCK_FILE, "a+b")
            if os.name == "nt":
                import msvcrt

                if lock_f.seek(0, os.SEEK_END) == 0:
                    lock_f.write(b"0")
                    lock_f.flush()
                lock_f.seek(0)
                try:
                    msvcrt.locking(lock_f.fileno(), msvcrt.LK_NBLCK, 1)
                except OSError as exc:
                    raise SefazLockBusy() from exc

                def unlock():
                    msvcrt.locking(lock_f.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl

                try:
                    fcntl.flock(lock_f, fcntl.LOCK_EX | fcntl.LOCK_NB)
                except OSError as exc:
                    raise SefazLockBusy() from exc

                def unlock():
                    fcntl.flock(lock_f, fcntl.LOCK_UN)

            yield
        finally:
            try:
                if unlock is not None:
                    unlock()
            finally:
                if lock_f is not None:
                    lock_f.close()
                self._operation_lock.release()

    def try_reprocess_local(
        self, tenant_id_str: str, config_path: Path
    ) -> dict[str, Any]:
        """Tenta importar XML já salvo, sem consulta ou alteração do NSU."""
        from app.db import SessionLocal
        from app.notas_entrada.sefaz_importer import (
            reprocessar_documentos_sefaz_pendentes,
        )

        try:
            with self.config_guard():
                if not config_path.exists():
                    return {"status": "disabled"}
                cfg = json.loads(config_path.read_text(encoding="utf-8"))
                if not (
                    cfg.get("enabled")
                    and cfg.get("modo") == "real"
                    and cfg.get("importacao_automatica")
                ):
                    return {"status": "disabled"}
                db = SessionLocal()
                try:
                    resultado = reprocessar_documentos_sefaz_pendentes(
                        db, tenant_id_str
                    )
                    return {"status": "ok", **resultado}
                finally:
                    db.close()
        except SefazLockBusy:
            return {"status": "lock_busy"}
        except Exception as exc:
            logger.warning(
                "[SEFAZ] Reprocessamento local falhou para tenant %s: %s",
                tenant_id_str,
                exc,
            )
            return {"status": "error"}

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

        try:
            with self.config_guard():
                # A configuração recebida pelo scheduler ou rota pode estar velha.
                # Recarregar só após o lock impede repetir um distNSU já executado.
                if not config_path.exists():
                    return {
                        "status": "disabled",
                        "mensagem": "Configuração SEFAZ ausente.",
                    }
                from app.services.sefaz_tenant_config_service import (
                    SefazTenantConfigService,
                )

                cfg_atual = {
                    **SefazTenantConfigService.build_default_config(None),
                    **json.loads(config_path.read_text(encoding="utf-8")),
                }
                if not cfg_atual.get("enabled") or cfg_atual.get("modo") != "real":
                    return {"status": "disabled", "mensagem": "SEFAZ não habilitada."}
                if reason == "scheduler" and not cfg_atual.get("importacao_automatica"):
                    return {
                        "status": "disabled",
                        "mensagem": "Importação automática desativada.",
                    }
                if (
                    not cfg_atual.get("cert_path")
                    or not Path(cfg_atual["cert_path"]).exists()
                ):
                    return {
                        "status": "disabled",
                        "mensagem": "Certificado SEFAZ indisponível.",
                    }
                proximo = proximo_sync_permitido(cfg_atual)
                if proximo is not None and proximo > datetime.now(timezone.utc):
                    return {
                        "status": "cooldown",
                        "mensagem": "Aguarde o próximo horário de consulta SEFAZ.",
                        "proximo_permitido_at": proximo.isoformat(),
                    }
                logger.info(
                    f"[SEFAZ] [{reason}] Iniciando sync — tenant {tenant_id_str}"
                )
                return self._execute(tenant_id_str, config_path, cfg_atual, reason)

        except SefazLockBusy:
            logger.info(
                f"[SEFAZ] [{reason}] Sync ignorada (lock_busy) — tenant {tenant_id_str}"
            )
            return {
                "status": "lock_busy",
                "mensagem": "Outro processo já está sincronizando com a SEFAZ. Aguarde instantes.",
            }

        except Exception as exc:
            logger.warning(
                f"[SEFAZ] [{reason}] Erro inesperado no coordinator "
                f"(tenant {tenant_id_str}): {exc}"
            )
            return {"status": "error", "mensagem": str(exc)}
        finally:
            with self._lock:
                self._running.discard(tenant_id_str)

    def _execute(
        self,
        tenant_id_str: str,
        config_path: Path,
        cfg: dict[str, Any],
        reason: str,
    ) -> dict[str, Any]:
        from app.db import SessionLocal
        from app.notas_entrada.sefaz_importer import (
            importar_documentos_distribuicao,
            reprocessar_documentos_sefaz_pendentes,
        )
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
        ultimo_nsu_retorno: str | None = None
        max_nsu_retorno: str | None = None
        total_erros_processamento = 0
        MAX_LOTES = 1  # Uma chamada por ciclo — evita cStat 656 por consumo excessivo

        # Uma flag antiga nao deve mais descartar documentos ou mover o cursor.
        if cfg.pop("comecar_do_hoje", False):
            logger.warning(
                f"[SEFAZ] [{reason}] Pedido antigo de pular NSU ignorado "
                f"para tenant {tenant_id_str}; checkpoint preservado."
            )

        # Reprocessamento local vem antes da rede: notas completas já salvas
        # podem sair da pendência mesmo se a SEFAZ estiver indisponível.
        db_retry = None
        try:
            db_retry = SessionLocal()
            retry = reprocessar_documentos_sefaz_pendentes(db_retry, tenant_id_str)
            total_importadas += retry.get("importadas", 0)
            total_duplicadas += retry.get("duplicadas", 0)
            total_erros_processamento += retry.get("erros", 0)
        except Exception as exc:
            erro_generico = True
            mensagem_erro_generico = f"Falha ao reprocessar documentos locais: {exc}"
            logger.warning(
                f"[SEFAZ] [{reason}] Reprocessamento local falhou "
                f"(tenant {tenant_id_str}): {exc}"
            )
        finally:
            if db_retry is not None:
                db_retry.close()

        for lote_idx in range(MAX_LOTES if not erro_generico else 0):
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
            ultimo_nsu_retorno = novo_nsu
            max_nsu_retorno = max_nsu

            nsu_atual_valido = _nsu_15(nsu_loop)
            novo_nsu_valido = _nsu_15(novo_nsu)
            max_nsu_valido = _nsu_15(max_nsu)
            c_stat_lote = str(resultado.get("c_stat") or "")
            nsus_docs = [_nsu_15(doc.get("nsu")) for doc in docs]
            nsus_ordenados = sorted(nsu for nsu in nsus_docs if nsu is not None)
            if (
                not nsu_atual_valido
                or not novo_nsu_valido
                or not max_nsu_valido
                or novo_nsu_valido < nsu_atual_valido
                or novo_nsu_valido > max_nsu_valido
                or any(
                    nsu is None or nsu <= nsu_atual_valido or nsu > novo_nsu_valido
                    for nsu in nsus_docs
                )
                or len(set(nsus_docs)) != len(nsus_docs)
                or any(
                    int(atual) != int(anterior) + 1
                    for anterior, atual in zip(nsus_ordenados, nsus_ordenados[1:])
                )
                or (
                    c_stat_lote == "138"
                    and (not nsus_docs or max(nsus_docs) != novo_nsu_valido)
                )
                or (
                    c_stat_lote == "137"
                    and (nsus_docs or novo_nsu_valido != nsu_atual_valido)
                )
            ):
                erro_generico = True
                mensagem_erro_generico = "Resposta SEFAZ com sequência NSU inconsistente; checkpoint preservado"
                logger.warning(
                    f"[SEFAZ] [{reason}] NSU inconsistente no lote "
                    f"(tenant {tenant_id_str}); checkpoint {nsu_loop} preservado."
                )
                break

            if docs:
                db = SessionLocal()
                try:
                    # O staging grava todos os docZip antes de qualquer avanço
                    # de NSU. Falhas posteriores de parse ficam para retry local.
                    r = importar_documentos_distribuicao(db, tenant_id_str, docs)
                    if not r.get("staging_salvo") or r.get("documentos_salvos") != len(
                        docs
                    ):
                        raise RuntimeError(
                            "Lote SEFAZ nao foi integralmente salvo no staging"
                        )
                    total_importadas += r.get("importadas", 0)
                    total_duplicadas += r.get("duplicadas", 0)
                    total_erros_processamento += r.get("erros", 0)
                    if r.get("importadas", 0) > 0 or r.get("erros", 0) > 0:
                        logger.info(
                            f"[SEFAZ] [{reason}] Lote {lote_idx + 1}: "
                            f"{r.get('importadas', 0)} salvas, "
                            f"{r.get('duplicadas', 0)} duplicadas, "
                            f"{r.get('erros', 0)} erros, "
                            f"{r.get('saidas_descartadas', 0)} saídas. NSU: {novo_nsu}"
                        )
                except Exception as exc:
                    erro_generico = True
                    mensagem_erro_generico = f"Falha ao salvar lote recebido: {exc}"
                    logger.warning(
                        f"[SEFAZ] [{reason}] Checkpoint {nsu_loop} preservado "
                        f"apos falha de staging (tenant {tenant_id_str}): {exc}"
                    )
                    break
                finally:
                    db.close()

            total_docs += len(docs)
            nsu_loop = novo_nsu

            if novo_nsu >= max_nsu or not docs:
                break

        now = datetime.now(timezone.utc)
        now_iso = now.isoformat()

        # ── Erro 656 — aplicar cooldown sem mover o checkpoint ───────────────
        if erro_656:
            penalidade_min = PENALIDADE_656_MINUTOS
            proximo = now + timedelta(minutes=penalidade_min)
            nsu_ult_retorno = (
                str(nsu_sugerido_656 or cfg.get("ultimo_nsu", "000000000000000"))
                .strip()
                .zfill(15)
            )
            nsu_max_retorno = (
                str(
                    max_nsu_sugerido_656
                    or nsu_sugerido_656
                    or cfg.get("ultimo_nsu", "000000000000000")
                )
                .strip()
                .zfill(15)
            )
            detalhe_656 = mensagem_erro_656 or "SEFAZ bloqueou por consumo indevido."
            cfg.update(
                {
                    "ultimo_sync_at": now_iso,
                    "_proximo_sync_permitido_at": proximo.isoformat(),
                    "_sync_bloqueado_656": True,
                    "ultimo_sync_status": "erro_656",
                    "ultimo_sync_mensagem": (
                        f"{detalhe_656} "
                        f"Checkpoint preservado em {cfg.get('ultimo_nsu', nsu_loop)}. "
                        f"SEFAZ informou ultNSU={nsu_ult_retorno}, maxNSU={nsu_max_retorno}. "
                        f"Próxima tentativa em {penalidade_min} min."
                    ),
                    "ultimo_sync_cstat": "656",
                    "ultimo_sync_xmotivo": detalhe_656,
                    "ultimo_sync_ult_nsu_retorno": nsu_ult_retorno,
                    "ultimo_sync_max_nsu_retorno": nsu_max_retorno,
                    "ultimo_sync_documentos": 0,
                }
            )
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
            intervalo_erro_min = max(60, int(cfg.get("importacao_intervalo_min", 60)))
            proximo_erro = now + timedelta(minutes=intervalo_erro_min)
            detalhe = (
                mensagem_erro_generico or "Falha desconhecida na sincronização SEFAZ."
            )
            cfg.update(
                {
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
                    "ultimo_sync_ult_nsu_retorno": str(ultimo_nsu_retorno or nsu_loop)
                    .strip()
                    .zfill(15),
                    "ultimo_sync_max_nsu_retorno": str(max_nsu_retorno or nsu_loop)
                    .strip()
                    .zfill(15),
                    "ultimo_sync_documentos": 0,
                }
            )
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

        # ── Sucesso — uma hora sem novidades, próximo ciclo se há backlog ──
        ha_backlog = (
            total_docs > 0
            and str(resultado.get("c_stat", "")) != "137"
            and str(nsu_loop) < str(max_nsu_retorno or nsu_loop)
        )
        intervalo_min = (
            INTERVALO_BACKLOG_MINUTOS if ha_backlog else INTERVALO_SEM_NOVIDADES_MINUTOS
        )
        proximo = now + timedelta(minutes=intervalo_min)

        msg = (
            f"Sincronização concluída. {total_docs} documento(s) recebido(s), "
            f"{total_importadas} NF-e(s) importada(s), "
            f"{total_erros_processamento} pendente(s) de reprocessamento local."
            if total_docs
            else f"Nenhum documento novo. Próxima verificação em {intervalo_min} min."
        )

        max_confirmado = (
            max_nsu_retorno
            if _nsu_15(max_nsu_retorno) and int(max_nsu_retorno) > 0
            else cfg.get("ultimo_max_nsu_confirmado")
        )
        cfg.update(
            {
                "ultimo_sync_at": now_iso,
                "_proximo_sync_permitido_at": proximo.isoformat(),
                "_sync_bloqueado_656": False,
                "backoff_index": 0,
                "ultimo_sync_status": "ok",
                "ultimo_nsu": nsu_loop,
                "ultimo_sync_cstat": str(resultado.get("c_stat", "ok")),
                "ultimo_sync_xmotivo": str(resultado.get("x_motivo", "")),
                "ultimo_sync_ult_nsu_retorno": str(
                    resultado.get("ultimo_nsu", nsu_loop)
                )
                .strip()
                .zfill(15),
                "ultimo_sync_max_nsu_retorno": str(resultado.get("max_nsu", nsu_loop))
                .strip()
                .zfill(15),
                "ultimo_max_nsu_confirmado": max_confirmado,
                "ultimo_sync_documentos": total_docs,
                "ultimo_sync_mensagem": msg,
            }
        )
        self._atomic_save(config_path, cfg)
        logger.info(
            f"[SEFAZ] [{reason}] ✅ Tenant {tenant_id_str}: "
            f"{total_docs} doc(s), {total_importadas} importada(s). "
            f"NSU: {nsu_loop}. "
            f"Próxima: {intervalo_min}min (backlog={ha_backlog})"
        )
        return {
            "status": "ok",
            "documentos": total_docs,
            "importadas": total_importadas,
            "duplicadas": total_duplicadas,
            "ultimo_nsu": nsu_loop,
            "max_nsu": max_nsu_retorno or nsu_loop,
            "c_stat": str(resultado.get("c_stat", "ok")),
            "x_motivo": str(resultado.get("x_motivo", "")),
            "mensagem": msg,
            "proximo_permitido_at": proximo.isoformat(),
        }

    @staticmethod
    def _atomic_save(path: Path, data: dict[str, Any]) -> None:
        """Gravação atômica: escreve em .tmp e faz rename (os.replace)."""
        from app.services.sefaz_tenant_config_service import SefazTenantConfigService

        SefazTenantConfigService._secure_write(
            path, json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
        )


# Singleton global — uma instância por worker uvicorn
sefaz_coordinator = SefazSyncCoordinator()
