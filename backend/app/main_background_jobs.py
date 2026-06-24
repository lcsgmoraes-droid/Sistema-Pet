"""Background job loops used by the application lifecycle."""

import logging
import os
import threading
import time
from typing import Optional

logger = logging.getLogger(__name__)

BLING_TOKEN_RENOVACAO_INTERVALO_SEGUNDOS = 5 * 60 * 60  # 5 horas
_bling_token_stop_event = threading.Event()
_bling_token_thread: Optional[threading.Thread] = None

# Job de expiração de reservas de pedidos Bling vencidos
_expirar_reservas_stop_event = threading.Event()
_expirar_reservas_thread: Optional[threading.Thread] = None
EXPIRAR_RESERVAS_INTERVALO_SEGUNDOS = 30 * 60  # 30 minutos

_estoque_validade_stop_event = threading.Event()
_estoque_validade_thread: Optional[threading.Thread] = None
ESTOQUE_VALIDADE_INTERVALO_SEGUNDOS = 6 * 60 * 60  # 6 horas

# SEFAZ — sincronização automática de NF-e por NSU
_sefaz_sync_stop_event = threading.Event()
_sefaz_sync_thread: Optional[threading.Thread] = None

# Campaign Engine — scheduler APScheduler
_campaign_scheduler = None

# Bling Sync — scheduler APScheduler
_bling_sync_scheduler = None

# Arquivos usados para coordenar renovação entre os múltiplos workers uvicorn
_BLING_LOCK_FILE = "/tmp/bling_token_renewal.lock"
_BLING_LAST_RENEWAL_FILE = "/tmp/bling_token_last_renewal.txt"
# Janela de segurança: se outro worker renovou há menos de 60s, apenas recarrega do .env
_BLING_RENEWAL_COOLDOWN = 60

# File lock para coordenar sincronização SEFAZ entre workers uvicorn
_SEFAZ_LOCK_FILE = "/tmp/sefaz_sync.lock"

# Lock líder para garantir que apenas 1 worker rode jobs de background
_BACKGROUND_JOBS_LOCK_FILE = "/tmp/petshop_background_jobs.lock"
_background_jobs_lock_handle = None
_is_background_jobs_leader = False


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None or raw == "":
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _try_become_background_jobs_leader() -> bool:
    """
    Tenta eleger este processo como líder dos jobs de background.

    Em Linux (produção), usa fcntl+arquivo para garantir exclusividade entre
    processos uvicorn workers. Em ambientes sem fcntl (ex.: Windows), retorna
    True para facilitar desenvolvimento local.
    """
    global _background_jobs_lock_handle
    global _is_background_jobs_leader

    try:
        import fcntl  # Linux

        lock_handle = open(_BACKGROUND_JOBS_LOCK_FILE, "w")
        try:
            fcntl.flock(lock_handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
            _background_jobs_lock_handle = lock_handle
            _is_background_jobs_leader = True
            return True
        except OSError:
            lock_handle.close()
            _background_jobs_lock_handle = None
            _is_background_jobs_leader = False
            return False
    except ImportError:
        # Windows/dev: sem fcntl, mantém comportamento simples
        _is_background_jobs_leader = True
        return True


def _release_background_jobs_leader() -> None:
    """Libera lock de liderança dos jobs de background, quando existir."""
    global _background_jobs_lock_handle
    global _is_background_jobs_leader

    if _background_jobs_lock_handle is None:
        _is_background_jobs_leader = False
        return

    try:
        import fcntl

        fcntl.flock(_background_jobs_lock_handle, fcntl.LOCK_UN)
    except Exception:
        pass

    try:
        _background_jobs_lock_handle.close()
    except Exception:
        pass

    _background_jobs_lock_handle = None
    _is_background_jobs_leader = False


def _bling_recarregar_tokens_do_env():
    """Relê o access_token e refresh_token do .env e atualiza os.environ."""
    import os as _os

    try:
        from dotenv import dotenv_values

        env_path = "/opt/petshop/.env"
        if _os.path.exists(env_path):
            vals = dotenv_values(env_path)
            if vals.get("BLING_ACCESS_TOKEN"):
                _os.environ["BLING_ACCESS_TOKEN"] = vals["BLING_ACCESS_TOKEN"]
            if vals.get("BLING_REFRESH_TOKEN"):
                _os.environ["BLING_REFRESH_TOKEN"] = vals["BLING_REFRESH_TOKEN"]
    except Exception as e:
        logger.warning(f"[BLING] ⚠️ Erro ao recarregar tokens do .env: {e}")


def _loop_renovacao_token_bling():
    """
    Loop em background para renovar token Bling periodicamente.
    Usa um arquivo de lock para garantir que apenas um dos múltiplos
    workers uvicorn execute a renovação — os demais apenas recarregam
    o token atualizado do .env.
    """
    import os as _os

    worker_pid = _os.getpid()
    logger.info(
        f"[BLING] Job de renovação automática iniciado (PID {worker_pid}, intervalo: 5h)"
    )

    while not _bling_token_stop_event.is_set():
        try:
            # Tenta importar fcntl (disponível no Linux/servidor)
            try:
                import fcntl

                has_fcntl = True
            except ImportError:
                has_fcntl = False

            if has_fcntl:
                # Coordenação via file lock entre workers
                with open(_BLING_LOCK_FILE, "w") as lock_f:
                    fcntl.flock(lock_f, fcntl.LOCK_EX)
                    try:
                        now = time.time()
                        recently_renewed = False
                        if _os.path.exists(_BLING_LAST_RENEWAL_FILE):
                            try:
                                with open(_BLING_LAST_RENEWAL_FILE, "r") as tf:
                                    last_ts = float(tf.read().strip())
                                if now - last_ts < _BLING_RENEWAL_COOLDOWN:
                                    recently_renewed = True
                            except Exception:
                                pass

                        if recently_renewed:
                            logger.info(
                                f"[BLING] PID {worker_pid} — token já renovado por outro worker, recarregando do .env"
                            )
                            _bling_recarregar_tokens_do_env()
                        else:
                            from app.bling_integration import BlingAPI

                            bling = BlingAPI()
                            bling.renovar_access_token()
                            with open(_BLING_LAST_RENEWAL_FILE, "w") as tf:
                                tf.write(str(time.time()))
                            logger.info(
                                f"[BLING] ✅ PID {worker_pid} — Token renovado automaticamente"
                            )
                    finally:
                        fcntl.flock(lock_f, fcntl.LOCK_UN)
            else:
                # Ambiente de desenvolvimento (Windows) — renova diretamente
                from app.bling_integration import BlingAPI

                bling = BlingAPI()
                bling.renovar_access_token()
                logger.info("[BLING] ✅ Token renovado automaticamente")

        except Exception as e:
            logger.warning(
                f"[BLING] ⚠️ PID {worker_pid} — Falha na renovação automática do token: {e}"
            )

        _bling_token_stop_event.wait(BLING_TOKEN_RENOVACAO_INTERVALO_SEGUNDOS)

    logger.info(f"[BLING] Job de renovação automática finalizado (PID {worker_pid})")


def _loop_sefaz_sync():
    """
    Job em background para sincronizar NF-e automaticamente via SEFAZ.
    *** DESATIVADO TEMPORARIAMENTE — sincronização apenas via chamada manual. ***
    Para reativar: remover o return logo abaixo.
    """
    logger.info(
        "[SEFAZ] Sincronização automática DESATIVADA — usando apenas modo manual."
    )
    return

    # --- CÓDIGO ABAIXO PRESERVADO PARA REATIVAÇÃO FUTURA ---
    import os as _os
    from datetime import datetime as _dt, timezone as _tz
    from pathlib import Path as _Path

    worker_pid = _os.getpid()
    logger.info(f"[SEFAZ] Job de sincronizacao automatica iniciado (PID {worker_pid})")

    # Aguarda 90 segundos no startup para o backend estar totalmente pronto
    _sefaz_sync_stop_event.wait(90)

    while not _sefaz_sync_stop_event.is_set():
        try:
            import json as _json
            from app.services.sefaz_tenant_config_service import (
                SefazTenantConfigService,
            )
            from app.services.sefaz_sync_coordinator import sefaz_coordinator

            base_dir = SefazTenantConfigService.BASE_DIR
            if base_dir.exists():
                for tenant_dir in base_dir.iterdir():
                    if not tenant_dir.is_dir():
                        continue
                    config_path = tenant_dir / SefazTenantConfigService.CONFIG_FILE
                    if not config_path.exists():
                        continue
                    try:
                        cfg = _json.loads(config_path.read_text(encoding="utf-8"))

                        # Verificações básicas de habilitação
                        if not cfg.get("importacao_automatica"):
                            continue
                        if not cfg.get("enabled"):
                            continue
                        if cfg.get("modo") != "real":
                            continue
                        if (
                            not cfg.get("cert_path")
                            or not _Path(cfg["cert_path"]).exists()
                        ):
                            continue

                        # Verificação de timing:
                        # _proximo_sync_permitido_at controla tanto penalidade 656
                        # quanto o intervalo de backoff — setado pelo coordinator
                        # após cada sync (bem-sucedida ou não).
                        agora = _dt.now(_tz.utc)
                        proximo_str = cfg.get("_proximo_sync_permitido_at")
                        if proximo_str:
                            proximo_dt = _dt.fromisoformat(proximo_str)
                            if proximo_dt.tzinfo is None:
                                proximo_dt = proximo_dt.replace(tzinfo=_tz.utc)
                            if proximo_dt > agora:
                                continue  # em penalidade 656 ou backoff ainda ativo

                        # Fallback para configs antigas (só existia ultimo_sync_at)
                        else:
                            ultimo_str = cfg.get("ultimo_sync_at")
                            if ultimo_str:
                                ultimo_dt = _dt.fromisoformat(ultimo_str)
                                if ultimo_dt.tzinfo is None:
                                    ultimo_dt = ultimo_dt.replace(tzinfo=_tz.utc)
                                intervalo_min = int(
                                    cfg.get("importacao_intervalo_min", 60)
                                )
                                if (
                                    agora - ultimo_dt
                                ).total_seconds() / 60 < intervalo_min:
                                    continue

                        tenant_id_str = tenant_dir.name
                        result = sefaz_coordinator.try_sync(
                            tenant_id_str=tenant_id_str,
                            config_path=config_path,
                            cfg=cfg,
                            reason="scheduler",
                        )
                        r_status = result.get("status")
                        if r_status == "lock_busy":
                            logger.debug(
                                f"[SEFAZ] Scheduler: lock ocupado para {tenant_id_str} "
                                f"— outro worker já executou este ciclo."
                            )
                        elif r_status == "already_running":
                            logger.debug(
                                f"[SEFAZ] Scheduler: sync já em andamento para {tenant_id_str}."
                            )
                        elif r_status not in ("ok", "erro_656"):
                            logger.warning(
                                f"[SEFAZ] Scheduler: resultado inesperado para "
                                f"{tenant_id_str}: {result}"
                            )
                    except Exception as exc_tenant:
                        logger.warning(
                            f"[SEFAZ] ⚠️ Erro ao processar tenant {tenant_dir.name}: {exc_tenant}"
                        )
        except Exception as exc:
            logger.warning(f"[SEFAZ] ⚠️ Erro no loop de sincronizacao: {exc}")

        _sefaz_sync_stop_event.wait(600)  # verifica a cada 10 minutos

    logger.info(
        f"[SEFAZ] Job de sincronizacao automatica finalizado (PID {worker_pid})"
    )


def _loop_expirar_reservas():
    """
    Job em background para expirar reservas de pedidos Bling vencidos.
    Roda a cada 30 minutos e marca como 'expirado' todos os pedidos
    com status='aberto' cuja expira_em já passou, liberando o estoque reservado.
    """
    from datetime import datetime as _dt
    import os as _os

    worker_pid = _os.getpid()
    logger.info(
        f"[RESERVAS] Job de expiração de reservas iniciado (PID {worker_pid}, intervalo: 30min)"
    )

    # Aguarda 2 minutos no startup para o backend estar totalmente pronto
    _expirar_reservas_stop_event.wait(120)

    while not _expirar_reservas_stop_event.is_set():
        try:
            from app.db import SessionLocal
            from app.models import Tenant
            from app.pedido_integrado_models import PedidoIntegrado
            from app.pedido_integrado_item_models import PedidoIntegradoItem
            from app.tenancy.context import clear_current_tenant, set_current_tenant
            from uuid import UUID

            db = SessionLocal()
            try:
                agora = _dt.utcnow()
                tenants_ativos = (
                    db.query(Tenant.id).filter(Tenant.status == "active").all()
                )
                total_expirados = 0

                for (tenant_id_raw,) in tenants_ativos:
                    try:
                        tenant_id = UUID(str(tenant_id_raw))
                    except (TypeError, ValueError):
                        logger.warning(
                            "[RESERVAS] Tenant com ID invalido ignorado no job de expiracao"
                        )
                        continue

                    set_current_tenant(tenant_id)
                    pedidos_vencidos_tenant = (
                        db.query(PedidoIntegrado)
                        .filter(
                            PedidoIntegrado.tenant_id == tenant_id,
                            PedidoIntegrado.status == "aberto",
                            PedidoIntegrado.expira_em < agora,
                        )
                        .all()
                    )

                    if pedidos_vencidos_tenant:
                        logger.info(
                            "[RESERVAS] %s pedido(s) vencido(s) para expirar no tenant %s",
                            len(pedidos_vencidos_tenant),
                            str(tenant_id)[:8],
                        )

                    for pedido in pedidos_vencidos_tenant:
                        # Libera apenas os itens ainda reservados (sem liberado_em nem vendido_em)
                        itens = (
                            db.query(PedidoIntegradoItem)
                            .filter(
                                PedidoIntegradoItem.tenant_id == tenant_id,
                                PedidoIntegradoItem.pedido_integrado_id == pedido.id,
                                PedidoIntegradoItem.liberado_em.is_(None),
                                PedidoIntegradoItem.vendido_em.is_(None),
                            )
                            .all()
                        )
                        for item in itens:
                            item.liberado_em = agora
                            db.add(item)

                        pedido.status = "expirado"
                        db.add(pedido)

                    total_expirados += len(pedidos_vencidos_tenant)

                if total_expirados:
                    db.commit()
                    logger.info(
                        "[RESERVAS] %s pedido(s) expirado(s), reservas liberadas",
                        total_expirados,
                    )

            except Exception as e:
                db.rollback()
                logger.warning(f"[RESERVAS] ⚠️ Erro ao expirar reservas: {e}")
            finally:
                clear_current_tenant()
                db.close()

        except Exception as e:
            logger.warning(
                f"[RESERVAS] ⚠️ PID {worker_pid} — Falha geral no job de expiração: {e}"
            )

        _expirar_reservas_stop_event.wait(EXPIRAR_RESERVAS_INTERVALO_SEGUNDOS)

    logger.info(
        f"[RESERVAS] Job de expiração de reservas finalizado (PID {worker_pid})"
    )



def _loop_estoque_validade():
    """Job em background para retirar lotes em risco do estoque vendavel."""
    import os as _os
    from uuid import UUID

    worker_pid = _os.getpid()
    logger.info(
        "[VALIDADE] Job de protecao de estoque iniciado (PID %s, intervalo: 6h)",
        worker_pid,
    )

    _estoque_validade_stop_event.wait(180)

    while not _estoque_validade_stop_event.is_set():
        try:
            from app.db import SessionLocal
            from app.estoque_validade_service import EstoqueValidadeService
            from app.models import Tenant
            from app.tenancy.context import clear_current_tenant, set_current_tenant

            db = SessionLocal()
            try:
                tenants = (
                    db.query(Tenant)
                    .filter(
                        Tenant.status == "active",
                        Tenant.protecao_validade_ativa.is_(True),
                    )
                    .all()
                )
                total_bloqueios = 0

                for tenant in tenants:
                    try:
                        set_current_tenant(UUID(str(tenant.id)))
                    except (TypeError, ValueError):
                        clear_current_tenant()

                    try:
                        resultado = EstoqueValidadeService.processar_lotes_em_risco(
                            db=db,
                            tenant=tenant,
                            user_id=None,
                            origem="scheduler",
                        )
                        total_bloqueios += int(resultado.get("processados") or 0)
                        db.commit()
                    except Exception as exc_tenant:
                        db.rollback()
                        logger.warning(
                            "[VALIDADE] Erro ao processar tenant %s: %s",
                            str(getattr(tenant, "id", ""))[:8],
                            exc_tenant,
                        )
                    finally:
                        clear_current_tenant()

                if total_bloqueios:
                    logger.info(
                        "[VALIDADE] %s lote(s) retirado(s) do estoque vendavel",
                        total_bloqueios,
                    )
            finally:
                clear_current_tenant()
                db.close()
        except Exception as exc:
            logger.warning("[VALIDADE] Falha geral no job de validade: %s", exc)

        _estoque_validade_stop_event.wait(ESTOQUE_VALIDADE_INTERVALO_SEGUNDOS)

    logger.info("[VALIDADE] Job de protecao de estoque finalizado (PID %s)", worker_pid)


def start_background_jobs() -> None:
    """Start schedulers and background threads only on the elected leader worker."""
    became_leader = _try_become_background_jobs_leader()
    if became_leader:
        logger.info("[JOBS] Este worker e o lider de background jobs.")

        try:
            from app.campaigns.scheduler import CampaignScheduler

            global _campaign_scheduler
            _campaign_scheduler = CampaignScheduler()
            _campaign_scheduler.start()
            logger.info("[OK] Campaign Scheduler iniciado!")
        except Exception as e:
            logger.error(f"[ERROR] Erro ao iniciar Campaign Scheduler: {str(e)}")

        if _env_bool("BLING_SYNC_SCHEDULER_ENABLED", True):
            try:
                from app.schedulers.bling_sync_scheduler import BlingSyncScheduler

                global _bling_sync_scheduler
                _bling_sync_scheduler = BlingSyncScheduler()
                _bling_sync_scheduler.start()
                logger.info("[OK] Bling Sync Scheduler iniciado!")
            except Exception as e:
                logger.error(f"[ERROR] Erro ao iniciar Bling Sync Scheduler: {str(e)}")
        else:
            logger.info("[JOBS] Bling Sync Scheduler desativado neste processo.")

        global _bling_token_thread
        _bling_token_stop_event.clear()
        _bling_token_thread = threading.Thread(
            target=_loop_renovacao_token_bling,
            name="bling-token-renovacao",
            daemon=True,
        )
        _bling_token_thread.start()

        global _expirar_reservas_thread
        _expirar_reservas_stop_event.clear()
        _expirar_reservas_thread = threading.Thread(
            target=_loop_expirar_reservas,
            name="expirar-reservas",
            daemon=True,
        )
        _expirar_reservas_thread.start()

        if _env_bool("ESTOQUE_VALIDADE_SCHEDULER_ENABLED", True):
            global _estoque_validade_thread
            _estoque_validade_stop_event.clear()
            _estoque_validade_thread = threading.Thread(
                target=_loop_estoque_validade,
                name="estoque-validade",
                daemon=True,
            )
            _estoque_validade_thread.start()
        else:
            logger.info(
                "[JOBS] Protecao de estoque por validade desativada neste processo."
            )

        global _sefaz_sync_thread
        _sefaz_sync_stop_event.clear()
        _sefaz_sync_thread = threading.Thread(
            target=_loop_sefaz_sync,
            name="sefaz-sync-automatico",
            daemon=True,
        )
        _sefaz_sync_thread.start()
    else:
        logger.info(
            "[JOBS] Worker secundario: background jobs desativados neste processo."
        )


def stop_background_jobs() -> None:
    """Stop schedulers and background threads when this process owns the leader lock."""
    if not _is_background_jobs_leader:
        return

    try:
        global _campaign_scheduler
        if _campaign_scheduler:
            _campaign_scheduler.shutdown()
            logger.info("[STOP] Campaign Scheduler parado!")
    except Exception as e:
        logger.error(f"[ERROR] Erro ao parar Campaign Scheduler: {str(e)}")

    try:
        global _bling_sync_scheduler
        if _bling_sync_scheduler:
            _bling_sync_scheduler.shutdown()
            logger.info("[STOP] Bling Sync Scheduler parado!")
    except Exception as e:
        logger.error(f"[ERROR] Erro ao parar Bling Sync Scheduler: {str(e)}")

    global _sefaz_sync_thread
    _sefaz_sync_stop_event.set()

    global _bling_token_thread
    _bling_token_stop_event.set()
    if _bling_token_thread and _bling_token_thread.is_alive():
        _bling_token_thread.join(timeout=2)
    _bling_token_thread = None

    global _expirar_reservas_thread
    _expirar_reservas_stop_event.set()
    if _expirar_reservas_thread and _expirar_reservas_thread.is_alive():
        _expirar_reservas_thread.join(timeout=2)
    _expirar_reservas_thread = None

    global _estoque_validade_thread
    _estoque_validade_stop_event.set()
    if _estoque_validade_thread and _estoque_validade_thread.is_alive():
        _estoque_validade_thread.join(timeout=2)
    _estoque_validade_thread = None

    _release_background_jobs_leader()
