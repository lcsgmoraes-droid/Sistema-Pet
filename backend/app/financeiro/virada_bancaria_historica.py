"""Virada bancaria historica controlada por tenant."""

from __future__ import annotations

from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session


CENT = Decimal("0.01")
CONFIRM_TOKEN_VIRADA_BANCARIA = "VIRADA_BANCARIA_HISTORICA"


def _money(value: Any) -> Decimal:
    return Decimal(str(value or 0)).quantize(CENT, rounding=ROUND_HALF_UP)


def _money_str(value: Any) -> str:
    return f"{_money(value):.2f}"


def _rows(db: Session, sql: str, params: dict[str, Any]) -> list[dict[str, Any]]:
    return [dict(row) for row in db.execute(text(sql), params).mappings().all()]


def _one(db: Session, sql: str, params: dict[str, Any]) -> dict[str, Any] | None:
    row = db.execute(text(sql), params).mappings().first()
    return dict(row) if row else None


def _append_marker(existing: str | None, marker: str) -> str:
    current = str(existing or "").strip()
    if marker in current:
        return current
    return f"{current} | {marker}" if current else marker


def _fetch_cr_actions(db: Session, params: dict[str, Any]) -> list[dict[str, Any]]:
    rows = _rows(
        db,
        """
        SELECT
            id AS conta_receber_id,
            descricao,
            status,
            valor_final,
            COALESCE(valor_recebido, 0) AS valor_recebido,
            data_vencimento,
            forma_pagamento_id,
            user_id
        FROM contas_receber
        WHERE CAST(tenant_id AS TEXT) = :tenant_id
          AND data_vencimento <= :data_corte
          AND COALESCE(status, '') IN ('pendente', 'parcial', 'vencido')
          AND COALESCE(valor_final, 0) > COALESCE(valor_recebido, 0)
        ORDER BY data_vencimento ASC, id ASC
        """,
        params,
    )
    actions: list[dict[str, Any]] = []
    for row in rows:
        valor_final = _money(row["valor_final"])
        valor_recebido = _money(row["valor_recebido"])
        saldo = valor_final - valor_recebido
        if saldo <= Decimal("0.00"):
            continue
        actions.append(
            {
                "tipo": "baixar_conta_receber_historica",
                "conta_receber_id": int(row["conta_receber_id"]),
                "descricao": row["descricao"],
                "status_antes": row["status"],
                "data_vencimento": str(row["data_vencimento"])[:10],
                "data_recebimento": params["data_corte"],
                "valor_final": _money_str(valor_final),
                "valor_recebido_antes": _money_str(valor_recebido),
                "valor_recebimento_historico": _money_str(saldo),
                "forma_pagamento_id": row["forma_pagamento_id"],
                "user_id": int(row["user_id"]),
                "tenant_id": params["tenant_id"],
            }
        )
    return actions


def _fetch_cp_actions(db: Session, params: dict[str, Any]) -> list[dict[str, Any]]:
    rows = _rows(
        db,
        """
        SELECT
            id AS conta_pagar_id,
            descricao,
            status,
            valor_final,
            COALESCE(valor_pago, 0) AS valor_pago,
            data_vencimento,
            user_id
        FROM contas_pagar
        WHERE CAST(tenant_id AS TEXT) = :tenant_id
          AND data_vencimento <= :data_corte
          AND COALESCE(status, '') IN ('pendente', 'parcial', 'vencido')
          AND COALESCE(valor_final, 0) > COALESCE(valor_pago, 0)
        ORDER BY data_vencimento ASC, id ASC
        """,
        params,
    )
    actions: list[dict[str, Any]] = []
    for row in rows:
        valor_final = _money(row["valor_final"])
        valor_pago = _money(row["valor_pago"])
        saldo = valor_final - valor_pago
        if saldo <= Decimal("0.00"):
            continue
        actions.append(
            {
                "tipo": "baixar_conta_pagar_historica",
                "conta_pagar_id": int(row["conta_pagar_id"]),
                "descricao": row["descricao"],
                "status_antes": row["status"],
                "data_vencimento": str(row["data_vencimento"])[:10],
                "data_pagamento": params["data_corte"],
                "valor_final": _money_str(valor_final),
                "valor_pago_antes": _money_str(valor_pago),
                "valor_pagamento_historico": _money_str(saldo),
                "user_id": int(row["user_id"]),
                "tenant_id": params["tenant_id"],
            }
        )
    return actions


def _saldo_plan(
    db: Session,
    *,
    tenant_id: str,
    conta_bancaria_id: int | None,
    saldo_real: Decimal | None,
) -> dict[str, Any] | None:
    if conta_bancaria_id is None:
        return None
    row = _one(
        db,
        """
        SELECT id, nome, saldo_inicial, saldo_atual, observacoes
        FROM contas_bancarias
        WHERE CAST(tenant_id AS TEXT) = :tenant_id
          AND id = :conta_bancaria_id
        """,
        {"tenant_id": tenant_id, "conta_bancaria_id": conta_bancaria_id},
    )
    if not row:
        raise ValueError(
            f"Conta bancaria {conta_bancaria_id} nao encontrada no tenant {tenant_id}."
        )

    payload: dict[str, Any] = {
        "conta_bancaria_id": int(row["id"]),
        "nome": row["nome"],
        "saldo_inicial_antes": _money_str(row["saldo_inicial"]),
        "saldo_atual_antes": _money_str(row["saldo_atual"]),
        "saldo_atual_depois": None,
        "diferenca": None,
        "observacoes_antes": row.get("observacoes"),
    }
    if saldo_real is not None:
        saldo_real_money = _money(saldo_real)
        saldo_atual = _money(row["saldo_atual"])
        payload["saldo_inicial_depois"] = _money_str(saldo_real_money)
        payload["saldo_atual_depois"] = _money_str(saldo_real_money)
        payload["diferenca"] = _money_str(saldo_real_money - saldo_atual)
    return payload


def _insert_recebimento(db: Session, action: dict[str, Any]) -> int:
    row = db.execute(
        text(
            """
            INSERT INTO recebimentos (
                conta_receber_id, forma_pagamento_id, valor_recebido,
                data_recebimento, observacoes, user_id, tenant_id
            )
            VALUES (
                :conta_receber_id, :forma_pagamento_id,
                :valor_recebimento_historico, :data_recebimento,
                :observacoes, :user_id, :tenant_id
            )
            RETURNING id
            """
        ),
        {
            **action,
            "observacoes": (
                "Virada bancaria historica: recebimento registrado sem "
                "movimentar banco."
            ),
        },
    ).first()
    return int(row[0])


def _insert_pagamento(db: Session, action: dict[str, Any]) -> int:
    row = db.execute(
        text(
            """
            INSERT INTO pagamentos (
                conta_pagar_id, forma_pagamento_id, valor_pago,
                data_pagamento, observacoes, user_id, tenant_id
            )
            VALUES (
                :conta_pagar_id, NULL, :valor_pagamento_historico,
                :data_pagamento, :observacoes, :user_id, :tenant_id
            )
            RETURNING id
            """
        ),
        {
            **action,
            "observacoes": (
                "Virada bancaria historica: pagamento registrado sem movimentar banco."
            ),
        },
    ).first()
    return int(row[0])


def _apply_baixas(
    db: Session,
    *,
    cr_actions: list[dict[str, Any]],
    cp_actions: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    cr_applied: list[dict[str, Any]] = []
    for action in cr_actions:
        recebimento_id = _insert_recebimento(db, action)
        db.execute(
            text(
                """
                UPDATE contas_receber
                   SET valor_recebido = valor_final,
                       status = 'recebido',
                       data_recebimento = :data_recebimento
                 WHERE id = :conta_receber_id
                   AND CAST(tenant_id AS TEXT) = :tenant_id
                   AND COALESCE(valor_final, 0) > COALESCE(valor_recebido, 0)
                """
            ),
            action,
        )
        cr_applied.append({**action, "recebimento_id": recebimento_id})

    cp_applied: list[dict[str, Any]] = []
    for action in cp_actions:
        pagamento_id = _insert_pagamento(db, action)
        db.execute(
            text(
                """
                UPDATE contas_pagar
                   SET valor_pago = valor_final,
                       status = 'pago',
                       data_pagamento = :data_pagamento
                 WHERE id = :conta_pagar_id
                   AND CAST(tenant_id AS TEXT) = :tenant_id
                   AND COALESCE(valor_final, 0) > COALESCE(valor_pago, 0)
                """
            ),
            action,
        )
        cp_applied.append({**action, "pagamento_id": pagamento_id})

    return cr_applied, cp_applied


def _apply_saldo(
    db: Session,
    *,
    tenant_id: str,
    saldo: dict[str, Any],
):
    marker = (
        "Virada bancaria historica: saldo inicial/atual definido pelo saldo "
        f"real informado ({saldo['saldo_atual_depois']})."
    )
    db.execute(
        text(
            """
            UPDATE contas_bancarias
               SET saldo_inicial = :saldo_atual_depois,
                   saldo_atual = :saldo_atual_depois,
                   observacoes = :observacoes
             WHERE id = :conta_bancaria_id
               AND CAST(tenant_id AS TEXT) = :tenant_id
            """
        ),
        {
            **saldo,
            "tenant_id": tenant_id,
            "observacoes": _append_marker(saldo.get("observacoes_antes"), marker),
        },
    )


def _total(actions: list[dict[str, Any]], key: str) -> str:
    value = sum((_money(action[key]) for action in actions), Decimal("0.00"))
    return _money_str(value)


def _build_report(
    *,
    tenant_id: str,
    data_corte: date,
    apply_baixas: bool,
    apply_saldo: bool,
    cr_actions: list[dict[str, Any]],
    cp_actions: list[dict[str, Any]],
    cr_applied: list[dict[str, Any]],
    cp_applied: list[dict[str, Any]],
    saldo: dict[str, Any] | None,
) -> dict[str, Any]:
    return {
        "ok": True,
        "applied": {"baixas": bool(apply_baixas), "saldo": bool(apply_saldo)},
        "dry_run": not (apply_baixas or apply_saldo),
        "tenant_id": tenant_id,
        "data_corte": data_corte.isoformat(),
        "resumo": {
            "contas_receber_baixadas": len(cr_actions),
            "valor_receber_baixado": _total(cr_actions, "valor_recebimento_historico"),
            "contas_pagar_baixadas": len(cp_actions),
            "valor_pagar_baixado": _total(cp_actions, "valor_pagamento_historico"),
            "movimentacoes_criadas": 0,
            "saldo_bancario_alterado": bool(apply_saldo),
        },
        "contas_receber": cr_applied if apply_baixas else cr_actions,
        "contas_pagar": cp_applied if apply_baixas else cp_actions,
        "saldo_bancario": saldo,
    }


def _error(message: str) -> dict[str, Any]:
    return {"ok": False, "applied": {"baixas": False, "saldo": False}, "error": message}


def executar_virada_bancaria_historica(
    db: Session,
    *,
    tenant_id: str,
    data_corte: date,
    conta_bancaria_id: int | None = None,
    saldo_real: Decimal | None = None,
    expected_saldo_atual: Decimal | None = None,
    apply_baixas: bool = False,
    apply_saldo: bool = False,
    confirm_token: str | None = None,
) -> dict[str, Any]:
    """Planeja ou executa a virada historica sem movimentos bancarios retroativos."""

    if (apply_baixas or apply_saldo) and confirm_token != CONFIRM_TOKEN_VIRADA_BANCARIA:
        db.rollback()
        return _error(f"confirm_token deve ser {CONFIRM_TOKEN_VIRADA_BANCARIA}")

    if apply_saldo:
        if conta_bancaria_id is None or saldo_real is None:
            db.rollback()
            return _error("apply_saldo exige conta_bancaria_id e saldo_real.")
        if expected_saldo_atual is None:
            db.rollback()
            return _error("apply_saldo exige expected_saldo_atual.")

    params = {"tenant_id": str(tenant_id), "data_corte": data_corte.isoformat()}

    try:
        cr_actions = _fetch_cr_actions(db, params)
        cp_actions = _fetch_cp_actions(db, params)
        saldo = _saldo_plan(
            db,
            tenant_id=str(tenant_id),
            conta_bancaria_id=conta_bancaria_id,
            saldo_real=_money(saldo_real) if saldo_real is not None else None,
        )

        if apply_saldo and saldo is not None:
            atual = _money(saldo["saldo_atual_antes"])
            esperado = _money(expected_saldo_atual)
            if atual != esperado:
                db.rollback()
                return _error(
                    "Saldo atual divergente antes do apply: "
                    f"esperado {esperado:.2f}, encontrado {atual:.2f}."
                )

        cr_applied: list[dict[str, Any]] = []
        cp_applied: list[dict[str, Any]] = []
        if apply_baixas:
            cr_applied, cp_applied = _apply_baixas(
                db, cr_actions=cr_actions, cp_actions=cp_actions
            )
        if apply_saldo and saldo is not None:
            _apply_saldo(db, tenant_id=str(tenant_id), saldo=saldo)

        if apply_baixas or apply_saldo:
            db.commit()
        else:
            db.rollback()

        return _build_report(
            tenant_id=str(tenant_id),
            data_corte=data_corte,
            apply_baixas=apply_baixas,
            apply_saldo=apply_saldo,
            cr_actions=cr_actions,
            cp_actions=cp_actions,
            cr_applied=cr_applied,
            cp_applied=cp_applied,
            saldo=saldo,
        )
    except Exception:
        db.rollback()
        raise
