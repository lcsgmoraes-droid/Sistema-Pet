from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.nfe_cache_models import BlingNotaFiscalCache
from app.utils.logger import logger


_NFE_STATUSS_PENDENTES = ("pendente", "emitida danfe")


def _utc_now() -> datetime:
    return datetime.utcnow()


def _limite_data_recentes(dias: int) -> datetime:
    dias_ref = max(int(dias or 1), 1)
    return _utc_now() - timedelta(days=dias_ref)


def _buscar_nfes_pendentes_recentes(
    db: Session,
    tenant_id,
    *,
    dias: int,
    limite_notas: int,
) -> list[BlingNotaFiscalCache]:
    return (
        db.query(BlingNotaFiscalCache)
        .filter(
            BlingNotaFiscalCache.tenant_id == tenant_id,
            BlingNotaFiscalCache.data_emissao.isnot(None),
            BlingNotaFiscalCache.data_emissao >= _limite_data_recentes(dias),
            func.lower(BlingNotaFiscalCache.status).in_(_NFE_STATUSS_PENDENTES),
        )
        .order_by(BlingNotaFiscalCache.data_emissao.desc(), BlingNotaFiscalCache.id.desc())
        .limit(max(int(limite_notas or 0), 1))
        .all()
    )


def _contar_nfes_pendentes_recentes(db: Session, tenant_id, *, dias: int) -> int:
    total = (
        db.query(func.count(BlingNotaFiscalCache.id))
        .filter(
            BlingNotaFiscalCache.tenant_id == tenant_id,
            BlingNotaFiscalCache.data_emissao.isnot(None),
            BlingNotaFiscalCache.data_emissao >= _limite_data_recentes(dias),
            func.lower(BlingNotaFiscalCache.status).in_(_NFE_STATUSS_PENDENTES),
        )
        .scalar()
    )
    return int(total or 0)


def _planejar_janela_reconciliacao(registros: list[BlingNotaFiscalCache]) -> tuple[str, str]:
    datas = [registro.data_emissao for registro in registros if registro.data_emissao]
    if not datas:
        hoje = _utc_now().date().isoformat()
        return hoje, hoje

    return min(datas).date().isoformat(), max(datas).date().isoformat()


def _executar_sync_incremental(
    db: Session,
    tenant_id,
    *,
    data_inicial: str,
    data_final: str,
):
    from app.nfe_routes import _sincronizar_cache_nfes_com_bling

    return _sincronizar_cache_nfes_com_bling(
        db,
        tenant_id,
        data_inicial=data_inicial,
        data_final=data_final,
        situacao=None,
    )


def listar_tenants_com_nfes_pendentes_recentes(db: Session, *, dias: int) -> list:
    return [
        tenant_id
        for (tenant_id,) in (
            db.query(BlingNotaFiscalCache.tenant_id)
            .filter(
                BlingNotaFiscalCache.data_emissao.isnot(None),
                BlingNotaFiscalCache.data_emissao >= _limite_data_recentes(dias),
                func.lower(BlingNotaFiscalCache.status).in_(_NFE_STATUSS_PENDENTES),
            )
            .distinct()
            .all()
        )
    ]


def reconciliar_nfes_pendentes_recentes(
    db: Session,
    tenant_id,
    *,
    dias: int = 3,
    limite_notas: int = 200,
) -> dict:
    pendentes_antes = _contar_nfes_pendentes_recentes(db, tenant_id, dias=dias)
    registros = _buscar_nfes_pendentes_recentes(
        db,
        tenant_id,
        dias=dias,
        limite_notas=limite_notas,
    )

    if not registros:
        return {
            "tenant_id": str(tenant_id),
            "executada": False,
            "motivo": "sem_nfs_pendentes_recentes",
            "dias": dias,
            "limite_notas": limite_notas,
            "pendentes_antes": pendentes_antes,
            "pendentes_depois": pendentes_antes,
            "janela": None,
        }

    data_inicial, data_final = _planejar_janela_reconciliacao(registros)
    bling_ok, notas_sincronizadas = _executar_sync_incremental(
        db,
        tenant_id,
        data_inicial=data_inicial,
        data_final=data_final,
    )
    pendentes_depois = _contar_nfes_pendentes_recentes(db, tenant_id, dias=dias)

    return {
        "tenant_id": str(tenant_id),
        "executada": True,
        "bling_ok": bool(bling_ok),
        "dias": dias,
        "limite_notas": limite_notas,
        "pendentes_antes": pendentes_antes,
        "pendentes_depois": pendentes_depois,
        "pendentes_atualizadas": max(pendentes_antes - pendentes_depois, 0),
        "notas_sincronizadas": len(notas_sincronizadas or []),
        "janela": {
            "data_inicial": data_inicial,
            "data_final": data_final,
        },
    }


def executar_reconciliacao_automatica_nfes_pendentes(
    db: Session,
    *,
    dias: int = 3,
    limite_notas_por_tenant: int = 200,
) -> dict:
    tenant_ids = listar_tenants_com_nfes_pendentes_recentes(db, dias=dias)
    resultados: list[dict] = []

    for tenant_id in tenant_ids:
        try:
            resultados.append(
                reconciliar_nfes_pendentes_recentes(
                    db,
                    tenant_id,
                    dias=dias,
                    limite_notas=limite_notas_por_tenant,
                )
            )
        except Exception as exc:
            logger.warning(
                "nfe_pendentes_reconciliacao",
                f"Falha ao reconciliar tenant {tenant_id}: {exc}",
            )
            db.rollback()
            resultados.append(
                {
                    "tenant_id": str(tenant_id),
                    "executada": False,
                    "erro": str(exc),
                    "dias": dias,
                    "limite_notas": limite_notas_por_tenant,
                }
            )

    return {
        "tenants_processados": len(resultados),
        "tenants_com_pendencias": len(tenant_ids),
        "pendentes_antes_total": sum(int(item.get("pendentes_antes") or 0) for item in resultados),
        "pendentes_depois_total": sum(int(item.get("pendentes_depois") or 0) for item in resultados),
        "pendentes_atualizadas_total": sum(int(item.get("pendentes_atualizadas") or 0) for item in resultados),
        "resultados": resultados,
    }
