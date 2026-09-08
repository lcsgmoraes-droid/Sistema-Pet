"""Precondicoes e auditoria da fusao; nenhuma publicacao remota nesta transacao."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone

from sqlalchemy import Float, inspect, text

from app.produto_identity_models import ProdutoFusaoLog, ProdutoSkuAlias
from app.produtos_models import ProdutoBlingSync, ProdutoBlingSyncQueue
from app.produtos_estoque_models import ProdutoBlingCostSyncQueue
from app.services.produto_alias_service import registrar_alias, validar_alias

STOCK_FIELDS = ("estoque_atual", "estoque_fisico", "estoque_ecommerce")
PROTECTED_FIELDS = {
    "codigo",
    "codigo_barras",
    "codigos_barras_alternativos",
    "nome",
    "unidade",
    "preco_custo",
    "preco_venda",
    "preco_ecommerce",
    "preco_app",
    "preco_promocional",
}
PENDING = ("pendente", "processando", "erro")


def snapshot(row):
    values = {}
    for column in row.__table__.columns:
        value = getattr(row, column.name)
        if value is not None and isinstance(column.type, Float):
            value = float(value)
        if isinstance(value, datetime):
            value = (
                (value if value.tzinfo else value.replace(tzinfo=timezone.utc))
                .astimezone(timezone.utc)
                .isoformat()
            )
        values[column.name] = value
    return json.loads(json.dumps(values, default=str))


def state_for_preview(db, principal, duplicado):
    links = (
        db.query(ProdutoBlingSync)
        .filter(
            ProdutoBlingSync.tenant_id == principal.tenant_id,
            ProdutoBlingSync.produto_id.in_([principal.id, duplicado.id]),
        )
        .order_by(ProdutoBlingSync.id)
        .all()
    )
    queues = (
        db.query(ProdutoBlingSyncQueue)
        .filter(
            ProdutoBlingSyncQueue.tenant_id == principal.tenant_id,
            ProdutoBlingSyncQueue.produto_id.in_([principal.id, duplicado.id]),
            ProdutoBlingSyncQueue.status.in_(PENDING),
        )
        .order_by(ProdutoBlingSyncQueue.id)
        .all()
    )
    costs = (
        db.query(ProdutoBlingCostSyncQueue)
        .filter(
            ProdutoBlingCostSyncQueue.tenant_id == principal.tenant_id,
            ProdutoBlingCostSyncQueue.produto_id.in_([principal.id, duplicado.id]),
            ProdutoBlingCostSyncQueue.status.in_(PENDING),
        )
        .order_by(ProdutoBlingCostSyncQueue.id)
        .all()
    )
    return {
        "principal": snapshot(principal),
        "duplicado": snapshot(duplicado),
        "bling": [snapshot(link) for link in links],
        "filas_pendentes": [snapshot(row) for row in queues],
        "filas_custo_pendentes": [snapshot(row) for row in costs],
    }


def preview_safety(db, principal, duplicado, estrategia):
    if estrategia not in {"somar", "manter_principal"}:
        raise ValueError("Estrategia de estoque invalida.")
    state = state_for_preview(db, principal, duplicado)
    digest = hashlib.sha256(
        json.dumps({"estado": state, "estrategia": estrategia}, sort_keys=True).encode()
    ).hexdigest()
    links = {row["produto_id"]: row for row in state["bling"]}
    a, b = links.get(principal.id, {}), links.get(duplicado.id, {})
    conflict = bool(
        a.get("bling_produto_id")
        and b.get("bling_produto_id")
        and a["bling_produto_id"] != b["bling_produto_id"]
    )
    return {
        "preview_token": digest,
        "estrategia_estoque": estrategia,
        "estoque_final": {
            field: float(getattr(principal, field) or 0)
            + (float(getattr(duplicado, field) or 0) if estrategia == "somar" else 0)
            for field in STOCK_FIELDS
        },
        "vinculos_bling": [
            {
                "produto_id": row["produto_id"],
                "bling_produto_id": row["bling_produto_id"],
                "sincronizar": row["sincronizar"],
            }
            for row in state["bling"]
        ],
        "conflito_bling": conflict,
        "filas_pendentes": len(state["filas_pendentes"])
        + len(state["filas_custo_pendentes"]),
        "rollback_automatico": False,
    }


def prepare_merge(
    db,
    principal,
    duplicado,
    *,
    estrategia,
    preview_token,
    preservar_bling,
    aliases,
    motivo,
):
    if principal.deleted_at is not None or duplicado.deleted_at is not None:
        raise ValueError("Produto ja arquivado/fundido; a fusao nao pode ser repetida.")
    if (
        db.query(ProdutoFusaoLog.id)
        .filter(
            ProdutoFusaoLog.tenant_id == principal.tenant_id,
            ProdutoFusaoLog.duplicado_id == duplicado.id,
        )
        .first()
    ):
        raise ValueError("Este produto ja possui fusao registrada.")
    db.query(ProdutoBlingSync).filter(
        ProdutoBlingSync.tenant_id == principal.tenant_id,
        ProdutoBlingSync.produto_id.in_([principal.id, duplicado.id]),
    ).order_by(ProdutoBlingSync.id).with_for_update().populate_existing().all()
    preview = preview_safety(db, principal, duplicado, estrategia)
    if any(
        link["retirado_para_produto_id"] is not None
        for link in state_for_preview(db, principal, duplicado)["bling"]
    ):
        raise ValueError(
            "Produto ativo possui vinculo Bling retirado; revisar a identidade antes da fusao."
        )
    if not preview_token or preview_token != preview["preview_token"]:
        raise ValueError(
            "Cadastro ou saldo alterado desde o preview; revise a fusao novamente."
        )
    if preview["filas_pendentes"]:
        raise ValueError("Aguarde as filas Bling de estoque/custo antes de fundir.")
    if preview["conflito_bling"] and not preservar_bling:
        raise ValueError(
            "Ha dois vinculos Bling: confirme a preservacao do retirado sem envio."
        )
    if estrategia == "manter_principal" and (
        not str(motivo or "").strip()
        or any(
            p.tipo_produto != "SIMPLES" or p.tipo_kit or p.e_granel
            for p in (principal, duplicado)
        )
        or principal.unidade != duplicado.unidade
    ):
        raise ValueError(
            "Manter o saldo exige motivo, produtos simples e a mesma unidade local."
        )
    for sku in [duplicado.codigo, *aliases]:
        validar_alias(
            db,
            tenant_id=principal.tenant_id,
            produto_id=principal.id,
            sku=sku,
            absorvido_id=duplicado.id,
        )
    return state_for_preview(db, principal, duplicado)


def preserve_aliases(db, principal, duplicado, *, aliases, user_id, motivo):
    previous = (
        db.query(ProdutoSkuAlias)
        .filter(
            ProdutoSkuAlias.tenant_id == principal.tenant_id,
            ProdutoSkuAlias.produto_id == duplicado.id,
        )
        .all()
    )
    values = [duplicado.codigo, *(row.sku for row in previous), *aliases]
    result = []
    for sku in dict.fromkeys(values):
        row = registrar_alias(
            db,
            tenant_id=principal.tenant_id,
            produto_id=principal.id,
            sku=sku,
            user_id=user_id,
            motivo=motivo,
            origem="fusao_confirmada",
            absorvido_id=duplicado.id,
        )
        result.append({"id": row.id, "sku": row.sku, "produto_id": row.produto_id})
    return result


def reference_snapshot(db, duplicado_id, fks, *, tenant_id):
    """Keep original rows/keys so a later reviewed recovery can distinguish histories."""
    result = []
    for fk in fks:
        table, column = fk["table_name"], fk["column_name"]
        quote = db.get_bind().dialect.identifier_preparer.quote
        rows = (
            db.execute(
                text(f"SELECT * FROM {quote(table)} WHERE {quote(column)} = :id"),
                {"id": duplicado_id},
            )
            .mappings()
            .all()
        )
        if rows:
            if any(
                "tenant_id" in row
                and str(row["tenant_id"]).replace("-", "")
                != str(tenant_id).replace("-", "")
                for row in rows
            ):
                raise ValueError(
                    "Referencia de produto pertence a outro tenant; fusao bloqueada."
                )
            result.append(
                {
                    "tabela": table,
                    "campo": column,
                    "chave_primaria": inspect(db.connection())
                    .get_pk_constraint(table)
                    .get("constrained_columns", []),
                    "antes": json.loads(
                        json.dumps([dict(row) for row in rows], default=str)
                    ),
                }
            )
    return result


def record_merge(
    db,
    principal,
    duplicado,
    *,
    user_id,
    estrategia,
    motivo,
    before,
    references,
    aliases,
):
    log = ProdutoFusaoLog(
        tenant_id=principal.tenant_id,
        principal_id=principal.id,
        duplicado_id=duplicado.id,
        user_id=user_id,
        estrategia_estoque=estrategia,
        motivo=motivo,
        antes=before,
        depois={
            "principal": snapshot(principal),
            "duplicado": snapshot(duplicado),
            "aliases": aliases,
        },
        referencias=references,
    )
    db.add(log)
    db.flush()
    return log
