from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.pedido_integrado_item_models import PedidoIntegradoItem
from app.pedido_integrado_models import PedidoIntegrado
from app.utils.logger import logger


_STATUS_PEDIDOS_RECONCILIAVEIS = ("aberto", "confirmado", "expirado")


def _utc_now() -> datetime:
    return datetime.utcnow()


def _limite_data_recentes(dias: int) -> datetime:
    dias_ref = max(int(dias or 1), 1)
    return _utc_now() - timedelta(days=dias_ref)


def _buscar_pedidos_recentes_reconciliaveis(
    db: Session,
    tenant_id,
    *,
    dias: int,
    limite_pedidos: int,
) -> list[PedidoIntegrado]:
    return (
        db.query(PedidoIntegrado)
        .filter(
            PedidoIntegrado.tenant_id == tenant_id,
            PedidoIntegrado.pedido_bling_id.isnot(None),
            func.length(func.trim(PedidoIntegrado.pedido_bling_id)) > 0,
            PedidoIntegrado.criado_em >= _limite_data_recentes(dias),
            PedidoIntegrado.status.in_(_STATUS_PEDIDOS_RECONCILIAVEIS),
        )
        .order_by(PedidoIntegrado.criado_em.desc(), PedidoIntegrado.id.desc())
        .limit(max(int(limite_pedidos or 0), 1))
        .all()
    )


def _contar_pedidos_recentes_reconciliaveis(db: Session, tenant_id, *, dias: int) -> int:
    total = (
        db.query(func.count(PedidoIntegrado.id))
        .filter(
            PedidoIntegrado.tenant_id == tenant_id,
            PedidoIntegrado.pedido_bling_id.isnot(None),
            func.length(func.trim(PedidoIntegrado.pedido_bling_id)) > 0,
            PedidoIntegrado.criado_em >= _limite_data_recentes(dias),
            PedidoIntegrado.status.in_(_STATUS_PEDIDOS_RECONCILIAVEIS),
        )
        .scalar()
    )
    return int(total or 0)


def listar_tenants_com_pedidos_reconciliaveis(db: Session, *, dias: int) -> list:
    return [
        tenant_id
        for (tenant_id,) in (
            db.query(PedidoIntegrado.tenant_id)
            .filter(
                PedidoIntegrado.pedido_bling_id.isnot(None),
                func.length(func.trim(PedidoIntegrado.pedido_bling_id)) > 0,
                PedidoIntegrado.criado_em >= _limite_data_recentes(dias),
                PedidoIntegrado.status.in_(_STATUS_PEDIDOS_RECONCILIAVEIS),
            )
            .distinct()
            .all()
        )
    ]


def _consultar_pedido_bling(pedido_bling_id: str) -> dict:
    from app.bling_integration import BlingAPI

    return BlingAPI().consultar_pedido(pedido_bling_id)


def _carregar_itens_pedido(db: Session, pedido_id: int) -> list[PedidoIntegradoItem]:
    return (
        db.query(PedidoIntegradoItem)
        .filter(PedidoIntegradoItem.pedido_integrado_id == pedido_id)
        .all()
    )


def reconciliar_status_pedido_local(
    db: Session,
    pedido: PedidoIntegrado,
    *,
    processed_at=None,
) -> dict:
    from app.integracao_bling_pedido_routes import (
        _SITUACOES_PEDIDO_ATENDIDO,
        _SITUACOES_PEDIDO_CANCELADO,
        _cancelar_pedido,
        _confirmar_pedido,
        _dict,
        _montar_payload_pedido,
        _sincronizar_nf_do_pedido,
        _situacao_codigo_bling,
    )

    pedido_bling_id = str(getattr(pedido, "pedido_bling_id", "") or "").strip()
    if not pedido_bling_id:
        return {
            "success": False,
            "executada": False,
            "motivo": "pedido_sem_bling_id",
            "pedido_integrado_id": getattr(pedido, "id", None),
        }

    pedido_api = _consultar_pedido_bling(pedido_bling_id)
    payload_atual = _dict(getattr(pedido, "payload", None))
    webhook_atual = _dict(payload_atual.get("webhook")) or None
    ultima_nf_atual = _dict(payload_atual.get("ultima_nf")) or None

    pedido.payload = _montar_payload_pedido(
        webhook_data=webhook_atual,
        pedido_completo=pedido_api,
        payload_atual=pedido.payload,
        ultima_nf=ultima_nf_atual,
    )
    db.add(pedido)

    resumo_nf = _sincronizar_nf_do_pedido(
        db=db,
        pedido=pedido,
        pedido_payload=pedido_api,
        webhook_data=webhook_atual,
        processed_at=processed_at,
        source="scheduler",
        message="NF identificada na reconciliacao automatica do pedido.",
        link_source="pedido.status_reconciliation",
    )

    situacao_id = _situacao_codigo_bling(_dict(pedido_api).get("situacao"))
    itens = _carregar_itens_pedido(db, pedido.id)
    status_anterior = getattr(pedido, "status", None)

    if situacao_id and situacao_id in _SITUACOES_PEDIDO_CANCELADO:
        if pedido.status != "cancelado":
            _cancelar_pedido(db=db, pedido=pedido, itens=itens, processed_at=processed_at)
            return {
                "success": True,
                "executada": True,
                "acao": "cancelado",
                "pedido_integrado_id": pedido.id,
                "pedido_bling_id": pedido_bling_id,
                "status_anterior": status_anterior,
                "status_atual": pedido.status,
                "nf_numero": _dict(resumo_nf).get("numero"),
            }

        db.commit()
        return {
            "success": True,
            "executada": True,
            "acao": "ja_cancelado",
            "pedido_integrado_id": pedido.id,
            "pedido_bling_id": pedido_bling_id,
            "status_anterior": status_anterior,
            "status_atual": pedido.status,
            "nf_numero": _dict(resumo_nf).get("numero"),
        }

    if situacao_id and situacao_id in _SITUACOES_PEDIDO_ATENDIDO:
        if pedido.status not in {"confirmado", "cancelado"}:
            erros = _confirmar_pedido(
                db=db,
                pedido=pedido,
                itens=itens,
                motivo="pedido_status_reconciliation",
                observacao="Pedido atendido no Bling; venda aguardando NF",
                processed_at=processed_at,
                aplicar_baixa_estoque=False,
            )
            return {
                "success": True,
                "executada": True,
                "acao": "confirmado",
                "pedido_integrado_id": pedido.id,
                "pedido_bling_id": pedido_bling_id,
                "status_anterior": status_anterior,
                "status_atual": pedido.status,
                "nf_numero": _dict(resumo_nf).get("numero"),
                "erros_estoque": erros,
            }

        db.commit()
        return {
            "success": True,
            "executada": True,
            "acao": "ja_confirmado",
            "pedido_integrado_id": pedido.id,
            "pedido_bling_id": pedido_bling_id,
            "status_anterior": status_anterior,
            "status_atual": pedido.status,
            "nf_numero": _dict(resumo_nf).get("numero"),
        }

    db.commit()
    return {
        "success": True,
        "executada": True,
        "acao": "sem_mudanca_relevante",
        "pedido_integrado_id": pedido.id,
        "pedido_bling_id": pedido_bling_id,
        "status_anterior": status_anterior,
        "status_atual": pedido.status,
        "nf_numero": _dict(resumo_nf).get("numero"),
        "situacao_codigo_bling": situacao_id,
    }


def reconciliar_status_pedidos_recentes(
    db: Session,
    tenant_id,
    *,
    dias: int = 7,
    limite_pedidos: int = 200,
) -> dict:
    pedidos_antes = _contar_pedidos_recentes_reconciliaveis(db, tenant_id, dias=dias)
    pedidos = _buscar_pedidos_recentes_reconciliaveis(
        db,
        tenant_id,
        dias=dias,
        limite_pedidos=limite_pedidos,
    )

    if not pedidos:
        return {
            "tenant_id": str(tenant_id),
            "executada": False,
            "motivo": "sem_pedidos_reconciliaveis_recentes",
            "dias": dias,
            "limite_pedidos": limite_pedidos,
            "pedidos_antes": pedidos_antes,
            "pedidos_processados": 0,
            "confirmados": 0,
            "cancelados": 0,
            "sem_mudanca": 0,
            "erros": [],
            "resultados": [],
        }

    resultados: list[dict] = []
    confirmados = 0
    cancelados = 0
    sem_mudanca = 0
    erros: list[dict] = []

    for pedido in pedidos:
        try:
            resultado = reconciliar_status_pedido_local(db, pedido)
            resultados.append(resultado)
            acao = resultado.get("acao")
            if acao == "confirmado":
                confirmados += 1
            elif acao == "cancelado":
                cancelados += 1
            else:
                sem_mudanca += 1
        except Exception as exc:
            logger.warning(
                "pedido_status_reconciliacao",
                f"Falha ao reconciliar pedido {getattr(pedido, 'pedido_bling_id', None)}: {exc}",
            )
            db.rollback()
            erro = {
                "pedido_integrado_id": getattr(pedido, "id", None),
                "pedido_bling_id": getattr(pedido, "pedido_bling_id", None),
                "erro": str(exc),
            }
            erros.append(erro)
            resultados.append({"success": False, "executada": False, **erro})

    return {
        "tenant_id": str(tenant_id),
        "executada": True,
        "dias": dias,
        "limite_pedidos": limite_pedidos,
        "pedidos_antes": pedidos_antes,
        "pedidos_processados": len(pedidos),
        "confirmados": confirmados,
        "cancelados": cancelados,
        "sem_mudanca": sem_mudanca,
        "erros": erros,
        "resultados": resultados,
    }


def executar_reconciliacao_automatica_status_pedidos(
    db: Session,
    *,
    dias: int = 7,
    limite_pedidos_por_tenant: int = 200,
) -> dict:
    tenant_ids = listar_tenants_com_pedidos_reconciliaveis(db, dias=dias)
    resultados: list[dict] = []

    for tenant_id in tenant_ids:
        try:
            resultados.append(
                reconciliar_status_pedidos_recentes(
                    db,
                    tenant_id,
                    dias=dias,
                    limite_pedidos=limite_pedidos_por_tenant,
                )
            )
        except Exception as exc:
            logger.warning(
                "pedido_status_reconciliacao",
                f"Falha ao reconciliar tenant {tenant_id}: {exc}",
            )
            db.rollback()
            resultados.append(
                {
                    "tenant_id": str(tenant_id),
                    "executada": False,
                    "erro": str(exc),
                    "dias": dias,
                    "limite_pedidos": limite_pedidos_por_tenant,
                }
            )

    return {
        "tenants_processados": len(resultados),
        "tenants_com_pedidos_reconciliaveis": len(tenant_ids),
        "pedidos_processados_total": sum(int(item.get("pedidos_processados") or 0) for item in resultados),
        "confirmados_total": sum(int(item.get("confirmados") or 0) for item in resultados),
        "cancelados_total": sum(int(item.get("cancelados") or 0) for item in resultados),
        "sem_mudanca_total": sum(int(item.get("sem_mudanca") or 0) for item in resultados),
        "erros_total": sum(len(item.get("erros") or []) for item in resultados),
        "resultados": resultados,
    }
