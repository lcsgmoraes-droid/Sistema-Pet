from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.services.pedido_integrado_duplicate_review_service import (
    consolidar_duplicidades_seguras_pedido,
    listar_grupos_duplicados_pedido_loja,
)
from app.tenancy.context import tenant_context
from app.utils.tenant_safe_sql import execute_tenant_safe_all
from app.utils.correlation import current_correlation_id, operation_correlation_context
from app.utils.logger import logger


def _utc_now() -> datetime:
    return datetime.utcnow()


def _limite_data_recentes(dias: int) -> datetime:
    dias_ref = max(int(dias or 1), 1)
    return _utc_now() - timedelta(days=dias_ref)


def listar_tenants_com_duplicidades_recentes(db: Session, *, dias: int) -> list:
    cutoff = _limite_data_recentes(dias)
    rows = execute_tenant_safe_all(
        db,
        text(
            """
            SELECT DISTINCT tenant_id
            FROM pedidos_integrados
            WHERE status != 'mesclado'
              AND criado_em >= :cutoff
            """
        ),
        {"dias": dias, "cutoff": cutoff},
        require_tenant=False,
        allow_global=True,
        global_reason="Job global de duplicidades de pedidos integrados precisa descobrir tenants antes do contexto ativo.",
    )
    return [
        tenant_id
        for (tenant_id,) in rows
        if tenant_id is not None
    ]


def reconciliar_duplicidades_recentes_pedido_loja(
    db: Session,
    tenant_id,
    *,
    dias: int = 7,
    limite_grupos: int = 20,
) -> dict:
    limite_grupos = max(int(limite_grupos or 0), 1)
    grupos = listar_grupos_duplicados_pedido_loja(
        db,
        tenant_id=tenant_id,
        dias=dias,
        limite_scan=max(limite_grupos * 10, 400),
    )[:limite_grupos]

    if not grupos:
        return {
            "executada": False,
            "motivo": "sem_duplicidades_recentes",
            "tenant_id": tenant_id,
            "grupos_mapeados": 0,
            "grupos_consolidados": 0,
            "grupos_seguros": 0,
            "grupos_com_revisao_manual": 0,
            "pedidos_mesclados": 0,
            "erros": 0,
            "resultados": [],
        }

    grupos_seguros = 0
    grupos_com_revisao_manual = 0
    grupos_consolidados = 0
    pedidos_mesclados = 0
    erros = 0
    resultados: list[dict] = []

    for grupo in grupos:
        pedido_canonico = grupo.get("pedido_canonico") or {}
        pedido_canonico_id = pedido_canonico.get("id")
        if not pedido_canonico_id:
            continue

        if grupo.get("pode_consolidar_automaticamente"):
            grupos_seguros += 1
        if grupo.get("requer_revisao_manual"):
            grupos_com_revisao_manual += 1

        if not grupo.get("pedidos_seguro_ids"):
            resultados.append(
                {
                    "pedido_canonico_id": pedido_canonico_id,
                    "numero_pedido_loja": grupo.get("numero_pedido_loja"),
                    "acao": "sem_mescla_segura",
                    "success": False,
                    "motivo": "sem_duplicados_seguro_ids",
                }
            )
            continue

        try:
            resultado = consolidar_duplicidades_seguras_pedido(
                db,
                tenant_id=tenant_id,
                pedido_id=int(pedido_canonico_id),
                source="scheduler",
                auto_fix_applied=True,
                resolution_note="Duplicidades seguras consolidadas automaticamente pelo scheduler.",
            )
        except Exception as exc:
            db.rollback()
            erros += 1
            logger.error(
                "pedido_duplicate_reconciliation_failed",
                f"Falha ao reconciliar duplicidade recente do pedido canonico {pedido_canonico_id}: {exc}",
                pedido_canonico_id=pedido_canonico_id,
                error=str(exc),
            )
            resultados.append(
                {
                    "pedido_canonico_id": pedido_canonico_id,
                    "numero_pedido_loja": grupo.get("numero_pedido_loja"),
                    "acao": "erro",
                    "success": False,
                    "motivo": str(exc),
                }
            )
            continue

        if resultado.get("success"):
            grupos_consolidados += 1
            pedidos_mesclados += len(resultado.get("pedidos_mesclados") or [])
            resultados.append(
                {
                    "pedido_canonico_id": resultado.get("pedido_canonico_id"),
                    "pedido_canonico_bling_numero": resultado.get("pedido_canonico_bling_numero"),
                    "numero_pedido_loja": resultado.get("numero_pedido_loja"),
                    "acao": "consolidado",
                    "success": True,
                    "pedidos_mesclados": len(resultado.get("pedidos_mesclados") or []),
                    "pedidos_bloqueados_ids": resultado.get("pedidos_bloqueados_ids") or [],
                }
            )
            continue

        resultados.append(
            {
                "pedido_canonico_id": pedido_canonico_id,
                "numero_pedido_loja": grupo.get("numero_pedido_loja"),
                "acao": "nao_consolidado",
                "success": False,
                "motivo": resultado.get("motivo"),
            }
        )

    return {
        "executada": True,
        "tenant_id": tenant_id,
        "grupos_mapeados": len(grupos),
        "grupos_consolidados": grupos_consolidados,
        "grupos_seguros": grupos_seguros,
        "grupos_com_revisao_manual": grupos_com_revisao_manual,
        "pedidos_mesclados": pedidos_mesclados,
        "erros": erros,
        "resultados": resultados,
    }


def executar_reconciliacao_automatica_duplicidades_pedidos(
    db: Session,
    *,
    dias: int = 7,
    limite_grupos_por_tenant: int = 20,
    _correlation_context_applied: bool = False,
) -> dict:
    if not _correlation_context_applied:
        with operation_correlation_context("job.pedido_duplicate_reconciliation") as correlation_id:
            result = executar_reconciliacao_automatica_duplicidades_pedidos(
                db,
                dias=dias,
                limite_grupos_por_tenant=limite_grupos_por_tenant,
                _correlation_context_applied=True,
            )
            result.setdefault("correlation_id", correlation_id)
            return result

    tenants = listar_tenants_com_duplicidades_recentes(db, dias=dias)

    resultados = []
    grupos_mapeados_total = 0
    grupos_consolidados_total = 0
    pedidos_mesclados_total = 0
    erros_total = 0

    for tenant_id in tenants:
        with tenant_context(tenant_id):
            resultado = reconciliar_duplicidades_recentes_pedido_loja(
                db,
                tenant_id,
                dias=dias,
                limite_grupos=limite_grupos_por_tenant,
            )
        resultados.append(resultado)
        grupos_mapeados_total += int(resultado.get("grupos_mapeados") or 0)
        grupos_consolidados_total += int(resultado.get("grupos_consolidados") or 0)
        pedidos_mesclados_total += int(resultado.get("pedidos_mesclados") or 0)
        erros_total += int(resultado.get("erros") or 0)

    return {
        "correlation_id": current_correlation_id("job.pedido_duplicate_reconciliation"),
        "tenants_processados": len(tenants),
        "tenants_com_duplicidades": sum(1 for item in resultados if item.get("grupos_mapeados")),
        "grupos_mapeados_total": grupos_mapeados_total,
        "grupos_consolidados_total": grupos_consolidados_total,
        "pedidos_mesclados_total": pedidos_mesclados_total,
        "erros_total": erros_total,
        "resultados": resultados,
    }
