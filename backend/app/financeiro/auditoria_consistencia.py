"""Auditoria read-only de consistencia financeira por tenant."""

from __future__ import annotations

from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session


CENT = Decimal("0.01")


def _money(value: Any) -> Decimal:
    return Decimal(str(value or 0)).quantize(CENT, rounding=ROUND_HALF_UP)


def _money_str(value: Any) -> str:
    return f"{_money(value):.2f}"


def _rows(db: Session, sql: str, params: dict[str, Any]) -> list[dict[str, Any]]:
    return [dict(row) for row in db.execute(text(sql), params).mappings().all()]


def _empty_bucket() -> dict[str, Any]:
    return {"quantidade": 0, "valor_total": "0.00", "itens": []}


def _bucket(rows: list[dict[str, Any]], valor_key: str) -> dict[str, Any]:
    total = sum((_money(row.get(valor_key)) for row in rows), Decimal("0.00"))
    return {
        "quantidade": len(rows),
        "valor_total": _money_str(total),
        "itens": rows,
    }


def _auditar_vendas_contas_receber(
    db: Session, params: dict[str, Any]
) -> dict[str, Any]:
    rows = _rows(
        db,
        """
        WITH vendas_periodo AS (
            SELECT id, numero_venda, tenant_id, data_venda, total
            FROM vendas
            WHERE tenant_id = :tenant_id
              AND data_venda >= :data_inicio
              AND data_venda < :data_fim
              AND status = 'finalizada'
        ),
        cr_por_venda AS (
            SELECT
                venda_id,
                COUNT(*) AS qtd_cr,
                COALESCE(SUM(valor_final), 0) AS total_cr
            FROM contas_receber
            WHERE tenant_id = :tenant_id
              AND venda_id IN (SELECT id FROM vendas_periodo)
              AND COALESCE(status, '') NOT IN ('cancelado', 'cancelada')
            GROUP BY venda_id
        )
        SELECT
            v.id AS venda_id,
            v.numero_venda AS numero_venda,
            v.data_venda AS data_venda,
            v.total AS total_venda,
            COALESCE(c.qtd_cr, 0) AS qtd_cr,
            COALESCE(c.total_cr, 0) AS total_cr
        FROM vendas_periodo v
        LEFT JOIN cr_por_venda c ON c.venda_id = v.id
        ORDER BY v.data_venda ASC, v.id ASC
        """,
        params,
    )

    sem_cr: list[dict[str, Any]] = []
    centavos: list[dict[str, Any]] = []
    maiores: list[dict[str, Any]] = []

    for row in rows:
        total_venda = _money(row["total_venda"])
        total_cr = _money(row["total_cr"])
        diferenca = total_cr - total_venda
        qtd_cr = int(row["qtd_cr"] or 0)
        if qtd_cr and diferenca == Decimal("0.00"):
            continue

        payload = {
            "venda_id": int(row["venda_id"]),
            "numero_venda": row["numero_venda"],
            "data_venda": str(row["data_venda"]),
            "qtd_cr": qtd_cr,
            "total_venda": _money_str(total_venda),
            "total_cr": _money_str(total_cr),
            "diferenca": _money_str(diferenca),
            "ajuste_sugerido": _money_str(-diferenca),
        }
        if qtd_cr == 0:
            sem_cr.append(payload)
        elif abs(diferenca) <= Decimal("0.05"):
            centavos.append(payload)
        else:
            maiores.append(payload)

    return {
        "sem_contas_receber": _bucket(sem_cr, "total_venda"),
        "diferencas_centavos": _bucket(centavos, "diferenca"),
        "divergencias_maiores": _bucket(maiores, "diferenca"),
    }


def _auditar_notas_contas_pagar(db: Session, params: dict[str, Any]) -> dict[str, Any]:
    rows = _rows(
        db,
        """
        WITH cp_por_nota AS (
            SELECT
                nota_entrada_id,
                tenant_id,
                COUNT(*) AS qtd_cp,
                COALESCE(SUM(valor_final), 0) AS total_cp
            FROM contas_pagar
            WHERE tenant_id = :tenant_id
              AND nota_entrada_id IS NOT NULL
              AND COALESCE(status, '') NOT IN ('cancelado', 'cancelada')
            GROUP BY nota_entrada_id, tenant_id
        )
        SELECT
            ne.id AS nota_id,
            ne.numero_nota AS numero_nota,
            ne.data_entrada AS data_entrada,
            ne.valor_total AS valor_total,
            ne.fornecedor_id AS fornecedor_id,
            ne.status AS status,
            COALESCE(cp.qtd_cp, 0) AS qtd_cp,
            COALESCE(cp.total_cp, 0) AS total_cp
        FROM notas_entrada ne
        LEFT JOIN cp_por_nota cp
          ON cp.nota_entrada_id = ne.id
         AND cp.tenant_id = ne.tenant_id
        WHERE ne.tenant_id = :tenant_id
          AND ne.data_entrada >= :data_inicio
          AND ne.data_entrada < :data_fim
        ORDER BY ne.data_entrada ASC, ne.id ASC
        """,
        params,
    )
    sem_cp: list[dict[str, Any]] = []
    centavos: list[dict[str, Any]] = []
    maiores: list[dict[str, Any]] = []

    for row in rows:
        valor_total = _money(row["valor_total"])
        total_cp = _money(row["total_cp"])
        diferenca = total_cp - valor_total
        qtd_cp = int(row["qtd_cp"] or 0)

        payload = {
            "nota_id": int(row["nota_id"]),
            "numero_nota": row["numero_nota"],
            "data_entrada": str(row["data_entrada"]),
            "valor_total": _money_str(valor_total),
            "fornecedor_id": row["fornecedor_id"],
            "status": row["status"],
            "qtd_contas_pagar": qtd_cp,
            "total_contas_pagar": _money_str(total_cp),
            "diferenca": _money_str(diferenca),
            "diferenca_abs": _money_str(abs(diferenca)),
        }

        if qtd_cp == 0:
            sem_cp.append(payload)
        elif diferenca == Decimal("0.00"):
            continue
        elif abs(diferenca) <= Decimal("0.05"):
            centavos.append(payload)
        else:
            maiores.append(payload)

    return {
        "sem_contas_pagar": _bucket(sem_cp, "valor_total"),
        "diferencas_centavos": _bucket(centavos, "diferenca_abs"),
        "divergencias_valor": _bucket(maiores, "diferenca_abs"),
    }


def _auditar_contas_pagar_pagamentos(
    db: Session, params: dict[str, Any]
) -> dict[str, Any]:
    rows = _rows(
        db,
        """
        WITH pg AS (
            SELECT
                conta_pagar_id,
                tenant_id,
                COALESCE(SUM(valor_pago), 0) AS soma_pagamentos,
                COUNT(*) AS qtd_pagamentos
            FROM pagamentos
            WHERE tenant_id = :tenant_id
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
            WHERE tenant_id = :tenant_id
              AND origem_tipo = 'conta_pagar'
            GROUP BY origem_id, tenant_id
        )
        SELECT
            cp.id AS conta_pagar_id,
            cp.descricao AS descricao,
            cp.data_pagamento AS data_pagamento,
            cp.status AS status,
            cp.valor_final AS valor_final,
            cp.valor_pago AS valor_pago,
            COALESCE(pg.soma_pagamentos, 0) AS soma_pagamentos,
            COALESCE(pg.qtd_pagamentos, 0) AS qtd_pagamentos,
            COALESCE(mf.qtd_movimentacoes, 0) AS qtd_movimentacoes,
            COALESCE(mf.soma_movimentacoes_saida, 0) AS soma_movimentacoes_saida
        FROM contas_pagar cp
        LEFT JOIN pg
          ON pg.conta_pagar_id = cp.id
         AND pg.tenant_id = cp.tenant_id
        LEFT JOIN mf
          ON mf.conta_pagar_id = cp.id
         AND mf.tenant_id = cp.tenant_id
        WHERE cp.tenant_id = :tenant_id
          AND cp.data_pagamento >= :data_inicio
          AND cp.data_pagamento < :data_fim
          AND cp.valor_pago <> COALESCE(pg.soma_pagamentos, 0)
          AND NOT (
              COALESCE(cp.observacoes, '') LIKE 'Gerada automaticamente pelo PDV (Caixa #%'
              AND EXISTS (
                  SELECT 1
                  FROM movimentacoes_caixa mc
                  WHERE mc.tenant_id = cp.tenant_id
                    AND COALESCE(mc.tipo, '') = 'despesa'
                    AND ABS(CAST(COALESCE(mc.valor, 0) AS NUMERIC) - CAST(COALESCE(cp.valor_pago, 0) AS NUMERIC)) < 0.01
                    AND SUBSTR(CAST(mc.data_movimento AS TEXT), 1, 10) = SUBSTR(CAST(cp.data_pagamento AS TEXT), 1, 10)
                    AND (
                        lower(trim(COALESCE(mc.descricao, ''))) = lower(trim(COALESCE(cp.descricao, '')))
                        OR lower(trim(COALESCE(mc.categoria, ''))) = lower(trim(COALESCE(cp.descricao, '')))
                        OR (
                            COALESCE(cp.documento, '') <> ''
                            AND lower(trim(COALESCE(mc.documento, ''))) = lower(trim(COALESCE(cp.documento, '')))
                        )
                    )
              )
          )
        ORDER BY cp.data_pagamento ASC, cp.id ASC
        """,
        params,
    )
    payload = []
    for row in rows:
        valor_pago = _money(row["valor_pago"])
        soma_pagamentos = _money(row["soma_pagamentos"])
        payload.append(
            {
                "conta_pagar_id": int(row["conta_pagar_id"]),
                "descricao": row["descricao"],
                "data_pagamento": str(row["data_pagamento"]),
                "status": row["status"],
                "valor_final": _money_str(row["valor_final"]),
                "valor_pago": _money_str(valor_pago),
                "soma_pagamentos": _money_str(soma_pagamentos),
                "diferenca": _money_str(valor_pago - soma_pagamentos),
                "qtd_pagamentos": int(row["qtd_pagamentos"] or 0),
                "qtd_movimentacoes": int(row["qtd_movimentacoes"] or 0),
                "soma_movimentacoes_saida": _money_str(row["soma_movimentacoes_saida"]),
            }
        )

    return {"valor_pago_sem_pagamento": _bucket(payload, "diferenca")}


def auditar_financeiro_tenant(
    db: Session,
    *,
    tenant_id: str,
    data_inicio: date,
    data_fim: date,
) -> dict[str, Any]:
    """Retorna inconsistencias financeiras em modo somente leitura."""
    params = {
        "tenant_id": str(tenant_id),
        "data_inicio": data_inicio.isoformat(),
        "data_fim": data_fim.isoformat(),
    }
    return {
        "ok": True,
        "mode": "read_only",
        "tenant_id": str(tenant_id),
        "periodo": {
            "data_inicio": data_inicio.isoformat(),
            "data_fim": data_fim.isoformat(),
        },
        "vendas_contas_receber": _auditar_vendas_contas_receber(db, params),
        "notas_entrada_contas_pagar": _auditar_notas_contas_pagar(db, params),
        "contas_pagar_pagamentos": _auditar_contas_pagar_pagamentos(db, params),
    }
