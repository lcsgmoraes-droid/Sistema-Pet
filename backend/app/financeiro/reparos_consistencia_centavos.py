"""Reparos conservadores de diferencas de centavos em contas a receber."""

from __future__ import annotations

from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.financeiro.reparos_consistencia_common import _money, _money_str, _one, _rows


def _fetch_centavo_rows(db: Session, params: dict[str, Any]) -> list[dict[str, Any]]:
    return _rows(
        db,
        """
        WITH vendas_periodo AS (
            SELECT id, numero_venda, total, data_venda
            FROM vendas
            WHERE CAST(tenant_id AS TEXT) = :tenant_id
              AND data_venda >= :data_inicio
              AND data_venda < :data_fim
              AND status = 'finalizada'
        ),
        cr_por_venda AS (
            SELECT venda_id, COUNT(*) AS qtd_cr, COALESCE(SUM(valor_final), 0) AS total_cr
            FROM contas_receber
            WHERE CAST(tenant_id AS TEXT) = :tenant_id
              AND venda_id IN (SELECT id FROM vendas_periodo)
              AND COALESCE(status, '') NOT IN ('cancelado', 'cancelada')
            GROUP BY venda_id
        )
        SELECT
            v.id AS venda_id,
            v.numero_venda AS numero_venda,
            v.total AS total_venda,
            c.total_cr AS total_cr,
            c.qtd_cr AS qtd_cr
        FROM vendas_periodo v
        JOIN cr_por_venda c ON c.venda_id = v.id
        WHERE c.qtd_cr > 0
          AND c.total_cr <> v.total
          AND ABS(c.total_cr - v.total) <= 0.05
        ORDER BY v.data_venda ASC, v.id ASC
        """,
        params,
    )


def _build_centavo_actions(
    db: Session, *, tenant_id: str, params: dict[str, Any]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    actions: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []

    for row in _fetch_centavo_rows(db, params):
        ajuste = _money(row["total_venda"]) - _money(row["total_cr"])
        target = _one(
            db,
            """
            SELECT id, valor_original, valor_final
            FROM contas_receber cr
            WHERE CAST(cr.tenant_id AS TEXT) = :tenant_id
              AND cr.venda_id = :venda_id
              AND cr.status = 'pendente'
              AND COALESCE(cr.valor_recebido, 0) = 0
              AND NOT EXISTS (
                  SELECT 1
                  FROM recebimentos r
                  WHERE CAST(r.tenant_id AS TEXT) = CAST(cr.tenant_id AS TEXT)
                    AND r.conta_receber_id = cr.id
              )
            ORDER BY COALESCE(cr.numero_parcela, 0) DESC, cr.id DESC
            LIMIT 1
            """,
            {
                "tenant_id": tenant_id,
                "venda_id": int(row["venda_id"]),
            },
        )
        if not target:
            skipped.append(
                {
                    "tipo": "ajuste_centavos",
                    "venda_id": int(row["venda_id"]),
                    "numero_venda": row["numero_venda"],
                    "ajuste_sugerido": _money_str(ajuste),
                    "motivo": "Nenhuma parcela pendente e sem recebimento para ajuste seguro.",
                }
            )
            continue

        valor_original_depois = _money(target["valor_original"]) + ajuste
        valor_final_depois = _money(target["valor_final"]) + ajuste
        if valor_original_depois <= 0 or valor_final_depois <= 0:
            skipped.append(
                {
                    "tipo": "ajuste_centavos",
                    "venda_id": int(row["venda_id"]),
                    "numero_venda": row["numero_venda"],
                    "conta_receber_id": int(target["id"]),
                    "ajuste_sugerido": _money_str(ajuste),
                    "motivo": "Ajuste deixaria valor da parcela menor ou igual a zero.",
                }
            )
            continue

        actions.append(
            {
                "tipo": "ajustar_centavos_conta_receber",
                "venda_id": int(row["venda_id"]),
                "numero_venda": row["numero_venda"],
                "conta_receber_id": int(target["id"]),
                "total_venda": _money_str(row["total_venda"]),
                "total_cr_antes": _money_str(row["total_cr"]),
                "ajuste": _money_str(ajuste),
                "valor_original_antes": _money_str(target["valor_original"]),
                "valor_original_depois": _money_str(valor_original_depois),
                "valor_final_antes": _money_str(target["valor_final"]),
                "valor_final_depois": _money_str(valor_final_depois),
                "tenant_id": tenant_id,
            }
        )

    return actions, skipped


def _apply_centavo_actions(
    db: Session, actions: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    for action in actions:
        db.execute(
            text(
                """
                UPDATE contas_receber
                   SET valor_original = :valor_original_depois,
                       valor_final = :valor_final_depois
                 WHERE id = :conta_receber_id
                   AND CAST(tenant_id AS TEXT) = :tenant_id
                   AND status = 'pendente'
                   AND COALESCE(valor_recebido, 0) = 0
                """
            ),
            action,
        )
    return actions
