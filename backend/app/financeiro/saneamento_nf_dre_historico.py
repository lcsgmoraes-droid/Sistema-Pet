"""Saneamento historico de contas de NF que nao devem afetar DRE."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.financeiro.saneamento_baixas_historicas import _money, _money_str, _rows
from app.financeiro.saneamento_historico_common import _run_saneamento_transacional


CONFIRM_TOKEN_NF_DRE_HISTORICO = "SANEAR_NF_DRE_HISTORICO_CP"


def _fetch_candidates(db: Session, params: dict[str, Any]) -> list[dict[str, Any]]:
    return _rows(
        db,
        """
        SELECT
            cp.id AS conta_pagar_id,
            cp.descricao AS descricao,
            cp.status AS status,
            cp.valor_final AS valor_final,
            cp.data_emissao AS data_emissao,
            cp.nota_entrada_id AS nota_entrada_id,
            cp.nfe_numero AS nfe_numero,
            cp.dre_subcategoria_id AS dre_subcategoria_id,
            cp.afeta_dre AS afeta_dre
        FROM contas_pagar cp
        WHERE CAST(cp.tenant_id AS TEXT) = :tenant_id
          AND cp.nota_entrada_id IS NOT NULL
          AND cp.data_emissao >= :data_inicio
          AND cp.data_emissao < :data_fim
          AND (
                COALESCE(cp.afeta_dre, true) = true
             OR cp.dre_subcategoria_id IS NOT NULL
          )
        ORDER BY cp.data_emissao ASC, cp.id ASC
        """,
        params,
    )


def _build_actions(
    rows: list[dict[str, Any]], *, tenant_id: str
) -> list[dict[str, Any]]:
    actions: list[dict[str, Any]] = []
    for row in rows:
        actions.append(
            {
                "tipo": "blindar_conta_pagar_nf_dre",
                "conta_pagar_id": int(row["conta_pagar_id"]),
                "descricao": row["descricao"],
                "status": row["status"],
                "valor_final": _money_str(row["valor_final"]),
                "data_emissao": str(row["data_emissao"])[:10],
                "nota_entrada_id": int(row["nota_entrada_id"]),
                "nfe_numero": row["nfe_numero"],
                "dre_subcategoria_id_antes": row["dre_subcategoria_id"],
                "dre_subcategoria_id_depois": None,
                "afeta_dre_antes": bool(row["afeta_dre"]),
                "afeta_dre_depois": False,
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
    total = sum((_money(item["valor_final"]) for item in actions), Decimal("0.00"))
    return {
        "ok": True,
        "applied": bool(apply_changes),
        "dry_run": not bool(apply_changes),
        "tenant_id": tenant_id,
        "periodo": {
            "data_inicio": data_inicio.isoformat(),
            "data_fim": data_fim.isoformat(),
            "campo_data": "contas_pagar.data_emissao",
        },
        "resumo": {
            "contas_candidatas": len(actions),
            "valor_total": _money_str(total),
            "afeta_dre_desativadas": sum(
                1 for item in actions if item["afeta_dre_antes"]
            ),
            "dre_subcategorias_removidas": sum(
                1 for item in actions if item["dre_subcategoria_id_antes"] is not None
            ),
            "status_alterado": False,
            "valores_alterados": False,
            "saldo_bancario_alterado": False,
        },
        "contas_pagar": applied if apply_changes else actions,
    }


def _apply_actions(db: Session, actions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    for action in actions:
        db.execute(
            text(
                """
                UPDATE contas_pagar
                   SET afeta_dre = false,
                       dre_subcategoria_id = NULL
                 WHERE id = :conta_pagar_id
                   AND CAST(tenant_id AS TEXT) = :tenant_id
                   AND nota_entrada_id IS NOT NULL
                   AND (
                         COALESCE(afeta_dre, true) = true
                      OR dre_subcategoria_id IS NOT NULL
                   )
                """
            ),
            action,
        )
    return actions


def sanear_contas_pagar_nf_dre_historico(
    db: Session,
    *,
    tenant_id: str,
    data_inicio: date,
    data_fim: date,
    apply_changes: bool = False,
    confirm_token: str | None = None,
) -> dict[str, Any]:
    """Planeja ou aplica a blindagem historica de CPs de NF contra DRE.

    O saneamento cobre apenas contas a pagar do tenant/periodo vinculadas a
    nota de entrada. Ele nao altera status, valores, pagamentos, movimentacoes
    financeiras ou saldo bancario.
    """

    if apply_changes and confirm_token != CONFIRM_TOKEN_NF_DRE_HISTORICO:
        db.rollback()
        return {
            "ok": False,
            "applied": False,
            "dry_run": False,
            "error": f"confirm_token deve ser {CONFIRM_TOKEN_NF_DRE_HISTORICO}",
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
