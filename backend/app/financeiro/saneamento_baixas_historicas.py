"""Saneamento de baixas historicas de contas a pagar."""

from __future__ import annotations

from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.financeiro.saneamento_historico_common import _run_saneamento_transacional


CENT = Decimal("0.01")
CONFIRM_TOKEN_BAIXAS_HISTORICAS = "SANEAR_BAIXAS_HISTORICAS_CP"


def _money(value: Any) -> Decimal:
    return Decimal(str(value or 0)).quantize(CENT, rounding=ROUND_HALF_UP)


def _money_str(value: Any) -> str:
    return f"{_money(value):.2f}"


def _rows(db: Session, sql: str, params: dict[str, Any]) -> list[dict[str, Any]]:
    return [dict(row) for row in db.execute(text(sql), params).mappings().all()]


def _fetch_candidates(db: Session, params: dict[str, Any]) -> list[dict[str, Any]]:
    return _rows(
        db,
        """
        WITH pg AS (
            SELECT
                conta_pagar_id,
                tenant_id,
                COALESCE(SUM(valor_pago), 0) AS soma_pagamentos,
                COUNT(*) AS qtd_pagamentos
            FROM pagamentos
            WHERE CAST(tenant_id AS TEXT) = :tenant_id
            GROUP BY conta_pagar_id, tenant_id
        ),
        mf AS (
            SELECT
                origem_id AS conta_pagar_id,
                tenant_id,
                COUNT(*) AS qtd_movimentacoes,
                COALESCE(SUM(CASE WHEN tipo = 'saida' THEN valor ELSE 0 END), 0)
                    AS soma_movimentacoes_saida
            FROM movimentacoes_financeiras
            WHERE CAST(tenant_id AS TEXT) = :tenant_id
              AND origem_tipo = 'conta_pagar'
            GROUP BY origem_id, tenant_id
        )
        SELECT
            cp.id AS conta_pagar_id,
            cp.descricao AS descricao,
            cp.data_pagamento AS data_pagamento,
            cp.valor_final AS valor_final,
            cp.valor_pago AS valor_pago,
            cp.user_id AS user_id,
            COALESCE(pg.soma_pagamentos, 0) AS soma_pagamentos,
            COALESCE(pg.qtd_pagamentos, 0) AS qtd_pagamentos,
            COALESCE(mf.qtd_movimentacoes, 0) AS qtd_movimentacoes,
            COALESCE(mf.soma_movimentacoes_saida, 0) AS soma_movimentacoes_saida
        FROM contas_pagar cp
        LEFT JOIN pg
          ON pg.conta_pagar_id = cp.id
         AND CAST(pg.tenant_id AS TEXT) = CAST(cp.tenant_id AS TEXT)
        LEFT JOIN mf
          ON mf.conta_pagar_id = cp.id
         AND CAST(mf.tenant_id AS TEXT) = CAST(cp.tenant_id AS TEXT)
        WHERE CAST(cp.tenant_id AS TEXT) = :tenant_id
          AND cp.status = 'pago'
          AND cp.data_pagamento >= :data_inicio
          AND cp.data_pagamento < :data_fim
          AND COALESCE(cp.valor_pago, 0) > 0
          AND COALESCE(cp.valor_pago, 0) > COALESCE(pg.soma_pagamentos, 0)
        ORDER BY cp.data_pagamento ASC, cp.id ASC
        """,
        params,
    )


def _build_actions(
    rows: list[dict[str, Any]], *, tenant_id: str
) -> list[dict[str, Any]]:
    actions: list[dict[str, Any]] = []
    for row in rows:
        valor_pago = _money(row["valor_pago"])
        soma_pagamentos = _money(row["soma_pagamentos"])
        valor_baixa = valor_pago - soma_pagamentos
        if valor_baixa <= Decimal("0.00"):
            continue

        actions.append(
            {
                "tipo": "criar_pagamento_historico_conta_pagar",
                "conta_pagar_id": int(row["conta_pagar_id"]),
                "descricao": row["descricao"],
                "data_pagamento": str(row["data_pagamento"])[:10],
                "valor_final": _money_str(row["valor_final"]),
                "valor_pago_conta": _money_str(valor_pago),
                "soma_pagamentos_antes": _money_str(soma_pagamentos),
                "valor_pagamento_historico": _money_str(valor_baixa),
                "qtd_pagamentos_antes": int(row["qtd_pagamentos"] or 0),
                "qtd_movimentacoes": int(row["qtd_movimentacoes"] or 0),
                "soma_movimentacoes_saida": _money_str(row["soma_movimentacoes_saida"]),
                "user_id": int(row["user_id"]),
                "tenant_id": tenant_id,
            }
        )
    return actions


def _build_report(
    *,
    tenant_id: str,
    data_inicio: date,
    data_fim: date,
    apply_changes: bool,
    actions: list[dict[str, Any]],
    applied: list[dict[str, Any]],
) -> dict[str, Any]:
    total = sum(
        (_money(item["valor_pagamento_historico"]) for item in actions),
        Decimal("0.00"),
    )
    return {
        "ok": True,
        "applied": bool(apply_changes),
        "dry_run": not bool(apply_changes),
        "tenant_id": tenant_id,
        "periodo": {
            "data_inicio": data_inicio.isoformat(),
            "data_fim": data_fim.isoformat(),
        },
        "resumo": {
            "pagamentos_candidatos": len(actions),
            "valor_pagamentos_planejado": _money_str(total),
            "movimentacoes_criadas": 0,
            "saldo_bancario_alterado": False,
        },
        "pagamentos": applied if apply_changes else actions,
    }


def _insert_pagamento_historico(db: Session, action: dict[str, Any]) -> int:
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
                "Saneamento historico: baixa registrada a partir de "
                "contas_pagar.valor_pago, sem movimentar banco."
            ),
        },
    ).first()
    return int(row[0])


def _apply_actions(db: Session, actions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    applied: list[dict[str, Any]] = []
    for action in actions:
        pagamento_id = _insert_pagamento_historico(db, action)
        applied.append({**action, "pagamento_id": pagamento_id})
    return applied


def sanear_baixas_historicas_contas_pagar(
    db: Session,
    *,
    tenant_id: str,
    data_inicio: date,
    data_fim: date,
    apply_changes: bool = False,
    confirm_token: str | None = None,
) -> dict[str, Any]:
    """Planeja ou registra baixas historicas faltantes em pagamentos.

    Este saneamento nao cria movimentacoes financeiras e nao altera saldo bancario.
    Ele cobre contas a pagar ja marcadas como pagas, dentro do periodo, cujo
    valor_pago e maior que a soma registrada na tabela pagamentos.
    """

    if apply_changes and confirm_token != CONFIRM_TOKEN_BAIXAS_HISTORICAS:
        db.rollback()
        return {
            "ok": False,
            "applied": False,
            "dry_run": False,
            "error": f"confirm_token deve ser {CONFIRM_TOKEN_BAIXAS_HISTORICAS}",
        }

    params = {
        "tenant_id": str(tenant_id),
        "data_inicio": data_inicio.isoformat(),
        "data_fim": data_fim.isoformat(),
    }
    actions = _build_actions(_fetch_candidates(db, params), tenant_id=str(tenant_id))

    applied = _run_saneamento_transacional(
        db,
        actions=actions,
        apply_changes=apply_changes,
        apply_actions=_apply_actions,
    )

    return _build_report(
        tenant_id=str(tenant_id),
        data_inicio=data_inicio,
        data_fim=data_fim,
        apply_changes=apply_changes,
        actions=actions,
        applied=applied,
    )
