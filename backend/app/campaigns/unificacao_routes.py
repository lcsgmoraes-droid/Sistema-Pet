"""
Rotas de unificacao cross-canal das campanhas.

Sub-router incluido por ``app.campaigns.routes`` sob o prefixo ``/campanhas``.
"""

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user_and_tenant
from app.campaigns.models import (
    CampaignEventQueue,
    CampaignExecution,
    CashbackTransaction,
    Coupon,
    CustomerMergeLog,
    CustomerRankHistory,
    DrawingEntry,
    EventStatusEnum,
    LoyaltyStamp,
    NotificationQueue,
    NotificationStatusEnum,
)
from app.db import SessionLocal
from app.models import Cliente
from app.vendas_models import Venda

router = APIRouter()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class ConfirmarMergeBody(BaseModel):
    customer_keep_id: int
    customer_remove_id: int
    motivo: Optional[str] = "manual"


def _serialize_cliente_resumo(c):
    return {
        "id": c.id,
        "nome": c.nome,
        "cpf": getattr(c, "cpf", None),
        "telefone": getattr(c, "telefone", None),
        "email": getattr(c, "email", None),
    }


def _adicionar_sugestoes_por_grupo(
    sugestoes: list[dict],
    seen_pairs: set[tuple[int, int]],
    grupos: dict[str, list[Cliente]],
    motivo: str,
) -> None:
    for grupo in grupos.values():
        if len(grupo) < 2:
            continue
        for i in range(len(grupo)):
            for j in range(i + 1, len(grupo)):
                a, b = grupo[i], grupo[j]
                key = (min(a.id, b.id), max(a.id, b.id))
                if key in seen_pairs:
                    continue
                seen_pairs.add(key)
                sugestoes.append(
                    {
                        "motivo": motivo,
                        "cliente_a": _serialize_cliente_resumo(a),
                        "cliente_b": _serialize_cliente_resumo(b),
                    }
                )


def _ids_customer_scoped(
    db: Session,
    model,
    tenant_id: int,
    customer_id: int,
    *extra_filters,
) -> list[int]:
    return [
        r.id
        for r in db.query(model.id)
        .filter(
            model.tenant_id == tenant_id,
            model.customer_id == customer_id,
            *extra_filters,
        )
        .all()
    ]


def _mover_customer_ids(db: Session, model, ids: list[int], customer_id: int) -> None:
    if ids:
        db.query(model).filter(model.id.in_(ids)).update(
            {"customer_id": customer_id}, synchronize_session=False
        )


def _ids_vendas_cliente(db: Session, customer_id: int) -> list[int]:
    return [
        r.id
        for r in db.query(Venda.id)
        .filter(
            Venda.cliente_id == customer_id,
        )
        .all()
    ]


def _mover_vendas_cliente(db: Session, ids: list[int], customer_id: int) -> None:
    if ids:
        db.query(Venda).filter(Venda.id.in_(ids)).update(
            {"cliente_id": customer_id}, synchronize_session=False
        )


def _ids_eventos_pendentes_cliente(
    db: Session, tenant_id: int, customer_id: int
) -> list[int]:
    return [
        r.id
        for r in db.query(CampaignEventQueue.id)
        .filter(
            CampaignEventQueue.tenant_id == tenant_id,
            CampaignEventQueue.status == EventStatusEnum.pending,
            CampaignEventQueue.payload["customer_id"].astext == str(customer_id),
        )
        .all()
    ]


def _atualizar_payload_customer_eventos(
    db: Session, event_ids: list[int], customer_id: int
) -> None:
    if not event_ids:
        return
    for ev in (
        db.query(CampaignEventQueue).filter(CampaignEventQueue.id.in_(event_ids)).all()
    ):
        payload = dict(ev.payload)
        payload["customer_id"] = customer_id
        ev.payload = payload


@router.get("/unificacao/sugestoes")
def listar_sugestoes_unificacao(
    db: Session = Depends(get_db),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    Retorna pares de clientes que provavelmente sao a mesma pessoa,
    identificados por mesmo CPF ou mesmo telefone no mesmo tenant.
    """
    _, tenant_id = user_and_tenant
    sugestoes = []
    seen_pairs: set[tuple[int, int]] = set()

    cpf_groups: dict[str, list[Cliente]] = {}
    for c in (
        db.query(Cliente)
        .filter(
            Cliente.tenant_id == tenant_id,
            Cliente.cpf.isnot(None),
            Cliente.cpf != "",
        )
        .all()
    ):
        cpf_groups.setdefault(c.cpf, []).append(c)
    _adicionar_sugestoes_por_grupo(sugestoes, seen_pairs, cpf_groups, "mesmo_cpf")

    tel_groups: dict[str, list[Cliente]] = {}
    for c in (
        db.query(Cliente)
        .filter(
            Cliente.tenant_id == tenant_id,
            Cliente.telefone.isnot(None),
            Cliente.telefone != "",
        )
        .all()
    ):
        tel_normalizado = "".join(d for d in (c.telefone or "") if d.isdigit())
        if len(tel_normalizado) >= 8:
            tel_groups.setdefault(tel_normalizado, []).append(c)
    _adicionar_sugestoes_por_grupo(sugestoes, seen_pairs, tel_groups, "mesmo_telefone")

    return sugestoes


@router.post("/unificacao/confirmar", status_code=200)
def confirmar_unificacao(
    body: ConfirmarMergeBody,
    db: Session = Depends(get_db),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    Mescla o cliente 'remove' no cliente 'keep':
    - Transfere registros de campanhas (cashback, carimbos, cupons, ranking, sorteios)
    - Cria CustomerMergeLog com snapshot dos IDs movidos (para permitir desfazer)
    """
    user, tenant_id = user_and_tenant

    keep = (
        db.query(Cliente)
        .filter(
            Cliente.id == body.customer_keep_id,
            Cliente.tenant_id == tenant_id,
        )
        .first()
    )
    remove = (
        db.query(Cliente)
        .filter(
            Cliente.id == body.customer_remove_id,
            Cliente.tenant_id == tenant_id,
        )
        .first()
    )

    if not keep or not remove:
        raise HTTPException(
            status_code=404, detail="Cliente não encontrado neste tenant."
        )
    if keep.id == remove.id:
        raise HTTPException(status_code=400, detail="Os clientes devem ser diferentes.")

    existing = (
        db.query(CustomerMergeLog)
        .filter(
            CustomerMergeLog.tenant_id == tenant_id,
            CustomerMergeLog.customer_keep_id == keep.id,
            CustomerMergeLog.customer_remove_id == remove.id,
            CustomerMergeLog.undone.is_(False),
        )
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=400,
            detail="Estes clientes já foram unificados. Desfaça antes de refazer.",
        )

    snapshot: dict = {}

    transferencias_customer_id = {
        "cashback_ids": CashbackTransaction,
        "stamp_ids": LoyaltyStamp,
        "coupon_ids": Coupon,
        "rank_ids": CustomerRankHistory,
        "drawing_ids": DrawingEntry,
    }
    for snapshot_key, model in transferencias_customer_id.items():
        ids = _ids_customer_scoped(db, model, tenant_id, remove.id)
        _mover_customer_ids(db, model, ids, keep.id)
        snapshot[snapshot_key] = ids

    notif_ids = _ids_customer_scoped(
        db,
        NotificationQueue,
        tenant_id,
        remove.id,
        NotificationQueue.status == NotificationStatusEnum.pending,
    )
    _mover_customer_ids(db, NotificationQueue, notif_ids, keep.id)
    snapshot["notif_ids"] = notif_ids

    venda_ids = _ids_vendas_cliente(db, remove.id)
    _mover_vendas_cliente(db, venda_ids, keep.id)
    snapshot["venda_ids"] = venda_ids

    exec_transferidos = []
    exec_descartados = []
    executions_remove = (
        db.query(CampaignExecution)
        .filter(
            CampaignExecution.tenant_id == tenant_id,
            CampaignExecution.customer_id == remove.id,
        )
        .all()
    )
    for exc_row in executions_remove:
        conflito = (
            db.query(CampaignExecution)
            .filter(
                CampaignExecution.tenant_id == tenant_id,
                CampaignExecution.campaign_id == exc_row.campaign_id,
                CampaignExecution.customer_id == keep.id,
                CampaignExecution.reference_period == exc_row.reference_period,
            )
            .first()
        )
        if conflito:
            exec_descartados.append(exc_row.id)
            db.delete(exc_row)
        else:
            exc_row.customer_id = keep.id
            exec_transferidos.append(exc_row.id)
    snapshot["exec_transferidos"] = exec_transferidos
    snapshot["exec_descartados"] = exec_descartados

    event_ids = _ids_eventos_pendentes_cliente(db, tenant_id, remove.id)
    _atualizar_payload_customer_eventos(db, event_ids, keep.id)
    snapshot["event_ids"] = event_ids

    if not keep.cpf and remove.cpf:
        keep.cpf = remove.cpf

    merge_log = CustomerMergeLog(
        tenant_id=tenant_id,
        customer_keep_id=keep.id,
        customer_remove_id=remove.id,
        motivo=body.motivo,
        merged_by_user_id=user.id if user else None,
        snapshot_json=snapshot,
        undone=False,
    )
    db.add(merge_log)
    db.commit()
    db.refresh(merge_log)

    return {
        "ok": True,
        "merge_id": merge_log.id,
        "customer_keep": _serialize_cliente_resumo(keep),
        "transferencias": {
            "cashback": len(snapshot["cashback_ids"]),
            "carimbos": len(snapshot["stamp_ids"]),
            "cupons": len(snapshot["coupon_ids"]),
            "ranking": len(snapshot["rank_ids"]),
            "sorteios": len(snapshot["drawing_ids"]),
            "notificacoes": len(notif_ids),
            "vendas": len(venda_ids),
            "execucoes_campanhas": len(exec_transferidos),
            "execucoes_descartadas": len(exec_descartados),
            "eventos_pendentes": len(event_ids),
        },
    }


@router.delete("/unificacao/{merge_id}", status_code=200)
def desfazer_unificacao(
    merge_id: int,
    db: Session = Depends(get_db),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    Desfaz uma unificacao anterior, restaurando customer_id nas linhas
    que foram movidas (usando o snapshot_json do merge log).
    """
    _, tenant_id = user_and_tenant

    merge_log = (
        db.query(CustomerMergeLog)
        .filter(
            CustomerMergeLog.id == merge_id,
            CustomerMergeLog.tenant_id == tenant_id,
        )
        .first()
    )
    if not merge_log:
        raise HTTPException(status_code=404, detail="Merge não encontrado.")
    if merge_log.undone:
        raise HTTPException(status_code=400, detail="Este merge já foi desfeito.")

    snap = merge_log.snapshot_json or {}
    remove_id = merge_log.customer_remove_id

    restauracoes_customer_id = {
        "cashback_ids": CashbackTransaction,
        "stamp_ids": LoyaltyStamp,
        "coupon_ids": Coupon,
        "rank_ids": CustomerRankHistory,
        "drawing_ids": DrawingEntry,
        "notif_ids": NotificationQueue,
    }
    for snapshot_key, model in restauracoes_customer_id.items():
        _mover_customer_ids(db, model, snap.get(snapshot_key, []), remove_id)

    _mover_vendas_cliente(db, snap.get("venda_ids", []), remove_id)
    _mover_customer_ids(
        db, CampaignExecution, snap.get("exec_transferidos", []), remove_id
    )
    _atualizar_payload_customer_eventos(db, snap.get("event_ids", []), remove_id)

    merge_log.undone = True
    merge_log.undone_at = datetime.now(timezone.utc)
    db.commit()

    return {"ok": True, "merge_id": merge_log.id, "desfeito": True}
