"""Saneamento operacional para movimentos bancarios financeiros."""

from __future__ import annotations

from collections import defaultdict
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session


CENT = Decimal("0.01")
CONFIRM_TOKEN_100X = "NORMALIZAR_CAIXA_100X"


def _money(value: Any) -> Decimal:
    return Decimal(str(value or 0)).quantize(CENT, rounding=ROUND_HALF_UP)


def _money_str(value: Any) -> str:
    return f"{_money(value):.2f}"


def _fetch_movimentos_conta_pagar(
    db: Session, tenant_id: str, conta_bancaria_id: int | None
):
    return (
        db.execute(
            text(
                """
                SELECT
                    mf.id AS movimentacao_id,
                    CAST(mf.tenant_id AS TEXT) AS tenant_id,
                    mf.conta_bancaria_id AS conta_bancaria_id,
                    mf.tipo AS tipo,
                    mf.valor AS valor_movimento,
                    mf.observacoes AS observacoes,
                    cp.id AS conta_pagar_id,
                    cp.valor_pago AS valor_pago,
                    cb.nome AS conta_bancaria_nome,
                    cb.saldo_atual AS saldo_atual
                FROM movimentacoes_financeiras mf
                JOIN contas_pagar cp
                  ON cp.id = mf.origem_id
                 AND CAST(cp.tenant_id AS TEXT) = CAST(mf.tenant_id AS TEXT)
                JOIN contas_bancarias cb
                  ON cb.id = mf.conta_bancaria_id
                 AND CAST(cb.tenant_id AS TEXT) = CAST(mf.tenant_id AS TEXT)
                WHERE CAST(mf.tenant_id AS TEXT) = :tenant_id
                  AND mf.origem_tipo = 'conta_pagar'
                  AND mf.tipo = 'saida'
                  AND (
                        :conta_bancaria_id IS NULL
                     OR mf.conta_bancaria_id = :conta_bancaria_id
                  )
                ORDER BY mf.conta_bancaria_id ASC, mf.id ASC
                """
            ),
            {
                "tenant_id": str(tenant_id),
                "conta_bancaria_id": conta_bancaria_id,
            },
        )
        .mappings()
        .all()
    )


def _build_candidates(rows) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for row in rows:
        valor_pago = _money(row["valor_pago"])
        valor_movimento = _money(row["valor_movimento"])
        if valor_pago == Decimal("0.00"):
            continue
        valor_esperado_bug = (valor_pago * Decimal("100")).quantize(CENT)
        if valor_movimento != valor_esperado_bug:
            continue

        candidates.append(
            {
                "movimentacao_id": int(row["movimentacao_id"]),
                "tenant_id": row["tenant_id"],
                "conta_bancaria_id": int(row["conta_bancaria_id"]),
                "conta_bancaria_nome": row["conta_bancaria_nome"],
                "conta_pagar_id": int(row["conta_pagar_id"]),
                "tipo": row["tipo"],
                "valor_antes": _money_str(valor_movimento),
                "valor_depois": _money_str(valor_pago),
                "diferenca_saldo": _money_str(valor_movimento - valor_pago),
                "saldo_atual_antes": _money_str(row["saldo_atual"]),
                "observacoes": row["observacoes"],
            }
        )
    return candidates


def _account_summary(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[int, dict[str, Any]] = {}
    deltas: defaultdict[int, Decimal] = defaultdict(lambda: Decimal("0.00"))

    for item in candidates:
        conta_id = item["conta_bancaria_id"]
        grouped.setdefault(
            conta_id,
            {
                "conta_bancaria_id": conta_id,
                "nome": item["conta_bancaria_nome"],
                "saldo_atual_antes": item["saldo_atual_antes"],
                "movimentos_candidatos": 0,
            },
        )
        grouped[conta_id]["movimentos_candidatos"] += 1
        deltas[conta_id] += _money(item["valor_antes"]) - _money(item["valor_depois"])

    accounts = []
    for conta_id, payload in sorted(grouped.items()):
        saldo_antes = _money(payload["saldo_atual_antes"])
        diferenca = deltas[conta_id]
        accounts.append(
            {
                **payload,
                "diferenca_saldo": _money_str(diferenca),
                "saldo_atual_depois": _money_str(saldo_antes + diferenca),
            }
        )
    return accounts


def _append_observacao(
    existing: str | None, valor_antes: str, valor_depois: str
) -> str:
    marker = (
        f"Saneamento caixa 100x: valor normalizado de {valor_antes} para {valor_depois}"
    )
    current = str(existing or "").strip()
    if marker in current:
        return current
    return f"{current} | {marker}" if current else marker


def _build_report(
    *,
    tenant_id: str,
    conta_bancaria_id: int | None,
    candidates: list[dict[str, Any]],
    apply_changes: bool,
) -> dict[str, Any]:
    total_antes = sum(
        (_money(item["valor_antes"]) for item in candidates), Decimal("0.00")
    )
    total_depois = sum(
        (_money(item["valor_depois"]) for item in candidates), Decimal("0.00")
    )
    accounts = _account_summary(candidates)
    return {
        "ok": True,
        "applied": bool(apply_changes),
        "dry_run": not bool(apply_changes),
        "tenant_id": str(tenant_id),
        "conta_bancaria_id": conta_bancaria_id,
        "resumo": {
            "movimentos_candidatos": len(candidates),
            "contas_afetadas": len(accounts),
            "valor_movimentos_antes": _money_str(total_antes),
            "valor_movimentos_depois": _money_str(total_depois),
            "diferenca_saldo": _money_str(total_antes - total_depois),
        },
        "contas": accounts,
        "movimentos": [
            {
                key: value
                for key, value in item.items()
                if key not in {"observacoes", "saldo_atual_antes"}
            }
            for item in candidates
        ],
    }


def _apply_candidates(
    db: Session, candidates: list[dict[str, Any]], accounts: list[dict[str, Any]]
):
    for item in candidates:
        db.execute(
            text(
                """
                UPDATE movimentacoes_financeiras
                   SET valor = :valor_depois,
                       observacoes = :observacoes
                 WHERE id = :movimentacao_id
                   AND CAST(tenant_id AS TEXT) = :tenant_id
                """
            ),
            {
                "valor_depois": item["valor_depois"],
                "observacoes": _append_observacao(
                    item.get("observacoes"), item["valor_antes"], item["valor_depois"]
                ),
                "movimentacao_id": item["movimentacao_id"],
                "tenant_id": item["tenant_id"],
            },
        )

    for account in accounts:
        db.execute(
            text(
                """
                UPDATE contas_bancarias
                   SET saldo_atual = :saldo_atual_depois
                 WHERE id = :conta_bancaria_id
                   AND CAST(tenant_id AS TEXT) = :tenant_id
                """
            ),
            {
                "saldo_atual_depois": account["saldo_atual_depois"],
                "conta_bancaria_id": account["conta_bancaria_id"],
                "tenant_id": candidates[0]["tenant_id"] if candidates else "",
            },
        )


def sanear_movimentos_100x(
    db: Session,
    *,
    tenant_id: str,
    conta_bancaria_id: int | None = None,
    apply_changes: bool = False,
    confirm_token: str | None = None,
) -> dict[str, Any]:
    """Diagnostica ou normaliza movimentos de conta a pagar gravados 100x maiores.

    O caso coberto e especifico: movimento bancario de saida, origem conta_pagar,
    mesmo tenant, cujo valor atual e exatamente valor_pago da conta a pagar vezes 100.
    """

    if apply_changes and confirm_token != CONFIRM_TOKEN_100X:
        db.rollback()
        return {
            "ok": False,
            "applied": False,
            "dry_run": False,
            "error": f"confirm_token deve ser {CONFIRM_TOKEN_100X}",
        }

    rows = _fetch_movimentos_conta_pagar(db, tenant_id, conta_bancaria_id)
    candidates = _build_candidates(rows)
    report = _build_report(
        tenant_id=tenant_id,
        conta_bancaria_id=conta_bancaria_id,
        candidates=candidates,
        apply_changes=apply_changes,
    )

    try:
        if apply_changes and candidates:
            _apply_candidates(db, candidates, report["contas"])
            db.commit()
        elif apply_changes:
            db.commit()
        else:
            db.rollback()
    except Exception:
        db.rollback()
        raise

    return report
