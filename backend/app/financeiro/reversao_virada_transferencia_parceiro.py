"""Reversao controlada das baixas de Transferencia Parceiro feitas pela virada."""

from __future__ import annotations

from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session


CENT = Decimal("0.01")
CONFIRM_TOKEN_REVERSAO_TRANSFERENCIA_PARCEIRO = "REVERTER_VIRADA_TRANSFERENCIA_PARCEIRO"
OBSERVACAO_VIRADA_RECEBIMENTO = (
    "Virada bancaria historica: recebimento registrado sem movimentar banco."
)


def _money(value: Any) -> Decimal:
    return Decimal(str(value or 0)).quantize(CENT, rounding=ROUND_HALF_UP)


def _money_str(value: Any) -> str:
    return f"{_money(value):.2f}"


def _rows(db: Session, sql: str, params: dict[str, Any]) -> list[dict[str, Any]]:
    return [dict(row) for row in db.execute(text(sql), params).mappings().all()]


def _append_marker(existing: str | None, marker: str) -> str:
    current = str(existing or "").strip()
    if marker in current:
        return current
    return f"{current} | {marker}" if current else marker


def _fetch_targets(
    db: Session,
    *,
    tenant_id: str,
    data_virada: date,
) -> list[dict[str, Any]]:
    return _rows(
        db,
        """
        SELECT
            r.id AS recebimento_id,
            cr.id AS conta_receber_id,
            cr.cliente_id,
            cr.documento,
            cr.descricao,
            cr.status AS status_antes,
            cr.valor_final,
            COALESCE(cr.valor_recebido, 0) AS valor_recebido_antes,
            cr.data_vencimento,
            cr.observacoes AS observacoes_conta,
            r.valor_recebido AS valor_baixa_revertida,
            r.data_recebimento
        FROM recebimentos r
        JOIN contas_receber cr ON cr.id = r.conta_receber_id
        WHERE CAST(cr.tenant_id AS TEXT) = :tenant_id
          AND CAST(r.tenant_id AS TEXT) = :tenant_id
          AND cr.canal = 'transferencia_parceiro'
          AND r.data_recebimento = :data_virada
          AND r.observacoes = :observacao_virada
        ORDER BY cr.id ASC, r.id ASC
        """,
        {
            "tenant_id": tenant_id,
            "data_virada": data_virada.isoformat(),
            "observacao_virada": OBSERVACAO_VIRADA_RECEBIMENTO,
        },
    )


def _remaining_receipts(
    db: Session,
    *,
    tenant_id: str,
    conta_receber_id: int,
    excluded_ids: set[int],
) -> list[dict[str, Any]]:
    rows = _rows(
        db,
        """
        SELECT id, valor_recebido, data_recebimento
        FROM recebimentos
        WHERE CAST(tenant_id AS TEXT) = :tenant_id
          AND conta_receber_id = :conta_receber_id
        ORDER BY data_recebimento DESC, id DESC
        """,
        {"tenant_id": tenant_id, "conta_receber_id": conta_receber_id},
    )
    return [row for row in rows if int(row["id"]) not in excluded_ids]


def _status_reaberto(
    *,
    valor_final: Decimal,
    valor_recebido: Decimal,
    data_vencimento: date | str,
) -> str:
    if valor_recebido >= valor_final - CENT:
        return "recebido"
    if valor_recebido > Decimal("0.00"):
        return "parcial"
    vencimento = (
        data_vencimento
        if isinstance(data_vencimento, date)
        else date.fromisoformat(str(data_vencimento)[:10])
    )
    return "vencido" if vencimento < date.today() else "pendente"


def _build_account_plans(
    db: Session,
    *,
    tenant_id: str,
    data_virada: date,
    targets: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    targets_by_account: dict[int, list[dict[str, Any]]] = {}
    for target in targets:
        targets_by_account.setdefault(int(target["conta_receber_id"]), []).append(
            target
        )

    plans: list[dict[str, Any]] = []
    for conta_receber_id, account_targets in targets_by_account.items():
        first = account_targets[0]
        excluded_ids = {int(item["recebimento_id"]) for item in account_targets}
        remaining = _remaining_receipts(
            db,
            tenant_id=tenant_id,
            conta_receber_id=conta_receber_id,
            excluded_ids=excluded_ids,
        )
        valor_restante = sum(
            (_money(item["valor_recebido"]) for item in remaining),
            Decimal("0.00"),
        )
        valor_final = _money(first["valor_final"])
        ultima_data = remaining[0]["data_recebimento"] if remaining else None
        marker = (
            "Reversao da virada bancaria de "
            f"{data_virada.strftime('%d/%m/%Y')}: baixa de Transferencia Parceiro "
            "removida e saldo reaberto."
        )
        plans.append(
            {
                "conta_receber_id": conta_receber_id,
                "cliente_id": first["cliente_id"],
                "documento": first["documento"],
                "descricao": first["descricao"],
                "status_antes": first["status_antes"],
                "status_depois": _status_reaberto(
                    valor_final=valor_final,
                    valor_recebido=valor_restante,
                    data_vencimento=first["data_vencimento"],
                ),
                "valor_final": _money_str(valor_final),
                "valor_recebido_antes": _money_str(first["valor_recebido_antes"]),
                "valor_baixa_revertida": _money_str(
                    sum(
                        (
                            _money(item["valor_baixa_revertida"])
                            for item in account_targets
                        ),
                        Decimal("0.00"),
                    )
                ),
                "valor_recebido_depois": _money_str(valor_restante),
                "data_recebimento_depois": (
                    str(ultima_data)[:10] if ultima_data is not None else None
                ),
                "recebimento_ids": sorted(excluded_ids),
                "observacoes_depois": _append_marker(
                    first["observacoes_conta"], marker
                ),
            }
        )
    return plans


def _error(message: str) -> dict[str, Any]:
    return {"ok": False, "applied": False, "dry_run": False, "error": message}


def reverter_virada_transferencia_parceiro(
    db: Session,
    *,
    tenant_id: str,
    data_virada: date,
    apply: bool = False,
    confirm_token: str | None = None,
    expected_count: int | None = None,
    expected_total: Decimal | None = None,
) -> dict[str, Any]:
    """Planeja ou reverte apenas recebimentos exatos da virada em transferencias."""

    if apply and confirm_token != CONFIRM_TOKEN_REVERSAO_TRANSFERENCIA_PARCEIRO:
        db.rollback()
        return _error(
            f"confirm_token deve ser {CONFIRM_TOKEN_REVERSAO_TRANSFERENCIA_PARCEIRO}"
        )
    if apply and (expected_count is None or expected_total is None):
        db.rollback()
        return _error("Apply exige expected_count e expected_total.")

    tenant_id = str(tenant_id)
    try:
        targets = _fetch_targets(
            db,
            tenant_id=tenant_id,
            data_virada=data_virada,
        )
        total = sum(
            (_money(item["valor_baixa_revertida"]) for item in targets),
            Decimal("0.00"),
        )

        if apply and len(targets) != int(expected_count):
            db.rollback()
            return _error(
                "Quantidade divergente antes do apply: "
                f"esperado {expected_count}, encontrado {len(targets)}."
            )
        if apply and total != _money(expected_total):
            db.rollback()
            return _error(
                "Total divergente antes do apply: "
                f"esperado {_money_str(expected_total)}, encontrado {_money_str(total)}."
            )

        plans = _build_account_plans(
            db,
            tenant_id=tenant_id,
            data_virada=data_virada,
            targets=targets,
        )

        if apply:
            for plan in plans:
                for recebimento_id in plan["recebimento_ids"]:
                    deleted = db.execute(
                        text(
                            """
                            DELETE FROM recebimentos
                            WHERE id = :recebimento_id
                              AND CAST(tenant_id AS TEXT) = :tenant_id
                              AND data_recebimento = :data_virada
                              AND observacoes = :observacao_virada
                            """
                        ),
                        {
                            "recebimento_id": recebimento_id,
                            "tenant_id": tenant_id,
                            "data_virada": data_virada.isoformat(),
                            "observacao_virada": OBSERVACAO_VIRADA_RECEBIMENTO,
                        },
                    )
                    if deleted.rowcount != 1:
                        db.rollback()
                        return _error(
                            "Recebimento mudou durante a reversao; apply cancelado "
                            "sem persistir alteracoes."
                        )
                updated = db.execute(
                    text(
                        """
                        UPDATE contas_receber
                           SET valor_recebido = :valor_recebido_depois,
                               status = :status_depois,
                               data_recebimento = :data_recebimento_depois,
                               observacoes = :observacoes_depois
                         WHERE id = :conta_receber_id
                           AND CAST(tenant_id AS TEXT) = :tenant_id
                           AND canal = 'transferencia_parceiro'
                           AND ABS(
                               COALESCE(valor_recebido, 0) - :valor_recebido_antes
                           ) < 0.005
                        """
                    ),
                    {**plan, "tenant_id": tenant_id},
                )
                if updated.rowcount != 1:
                    db.rollback()
                    return _error(
                        "Conta mudou durante a reversao; apply cancelado sem "
                        "persistir alteracoes."
                    )
            db.commit()
        else:
            db.rollback()

        return {
            "ok": True,
            "applied": bool(apply),
            "dry_run": not apply,
            "tenant_id": tenant_id,
            "data_virada": data_virada.isoformat(),
            "resumo": {
                "recebimentos_revertidos": len(targets),
                "contas_reabertas": len(plans),
                "valor_reaberto": _money_str(total),
                "movimentacoes_bancarias_alteradas": 0,
            },
            "contas_receber": plans,
        }
    except Exception:
        db.rollback()
        raise
