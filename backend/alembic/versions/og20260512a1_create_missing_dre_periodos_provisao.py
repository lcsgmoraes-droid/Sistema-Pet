"""create missing dre_periodos for provisao details

Revision ID: og20260512a1
Revises: of20260512a1
Create Date: 2026-05-13 10:00:00.000000
"""

from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime
from typing import Any

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text


revision = "og20260512a1"
down_revision = "of20260512a1"
branch_labels = None
depends_on = None


TABLE_PERIODOS = "dre_periodos"
TABLE_DETALHES = "dre_detalhe_canais"
TABLE_USERS = "users"
CANAL_CANONICO = "provisao"
STATUS_RECONCILIADO = "reconciliado"
MARKER = "reconciliacao_dre_detalhe_canais_2b3_8"
TECHNICAL_CHANNELS = {
    "provisao",
    "provisao_consumo",
    "provisao_consumo_13",
    "ajuste_ferias",
    "ajuste_13",
}
FINANCIAL_ZERO_COLUMNS = (
    "receita_bruta",
    "deducoes_receita",
    "receita_liquida",
    "custo_produtos_vendidos",
    "lucro_bruto",
    "margem_bruta_percent",
    "despesas_vendas",
    "despesas_administrativas",
    "despesas_financeiras",
    "outras_despesas",
    "total_despesas_operacionais",
    "lucro_operacional",
    "margem_operacional_percent",
    "impostos",
    "lucro_liquido",
    "margem_liquida_percent",
)


def _bind():
    return op.get_bind()


def _inspector():
    return sa.inspect(_bind())


def _table_exists(table_name: str) -> bool:
    return _inspector().has_table(table_name)


def _columns(table_name: str) -> set[str]:
    if not _table_exists(table_name):
        return set()
    return {column["name"] for column in _inspector().get_columns(table_name)}


def _required_schema_available() -> bool:
    return (
        _table_exists(TABLE_PERIODOS)
        and _table_exists(TABLE_DETALHES)
        and _table_exists(TABLE_USERS)
        and {
            "tenant_id",
            "usuario_id",
            "data_inicio",
            "data_fim",
            "mes",
            "ano",
            "canal",
        }.issubset(_columns(TABLE_PERIODOS))
        and {
            "tenant_id",
            "usuario_id",
            "data_inicio",
            "data_fim",
            "mes",
            "ano",
            "canal",
        }.issubset(_columns(TABLE_DETALHES))
        and {"id", "tenant_id"}.issubset(_columns(TABLE_USERS))
    )


def _technical_channel_sql() -> str:
    return ", ".join(f"'{channel}'" for channel in sorted(TECHNICAL_CHANNELS))


def _candidate_rows() -> list[dict[str, Any]]:
    rows = _bind().execute(
        text(
            f"""
            SELECT
                d.tenant_id AS tenant_id,
                CAST(d.tenant_id AS TEXT) AS tenant_id_text,
                d.usuario_id AS usuario_id,
                d.data_inicio AS data_inicio,
                d.data_fim AS data_fim,
                d.mes AS mes,
                d.ano AS ano,
                LOWER(COALESCE(d.canal, '')) AS canal_original
            FROM dre_detalhe_canais d
            JOIN users u
                ON u.id = d.usuario_id
               AND u.tenant_id IS NOT NULL
               AND CAST(u.tenant_id AS TEXT) = CAST(d.tenant_id AS TEXT)
            WHERE d.tenant_id IS NOT NULL
              AND d.usuario_id IS NOT NULL
              AND d.data_inicio IS NOT NULL
              AND d.data_fim IS NOT NULL
              AND d.mes IS NOT NULL
              AND d.ano IS NOT NULL
              AND LOWER(COALESCE(d.canal, '')) IN ({_technical_channel_sql()})
              AND NOT EXISTS (
                  SELECT 1
                  FROM dre_periodos p
                  WHERE CAST(p.tenant_id AS TEXT) = CAST(d.tenant_id AS TEXT)
                    AND p.usuario_id = d.usuario_id
                    AND p.data_inicio = d.data_inicio
                    AND p.data_fim = d.data_fim
                    AND COALESCE(p.canal, '') = COALESCE(d.canal, '')
              )
              AND NOT EXISTS (
                  SELECT 1
                  FROM dre_periodos p
                  WHERE CAST(p.tenant_id AS TEXT) = CAST(d.tenant_id AS TEXT)
                    AND p.usuario_id = d.usuario_id
                    AND p.data_inicio = d.data_inicio
                    AND p.data_fim = d.data_fim
                    AND COALESCE(p.canal, '') = :canal_canonico
              )
            """
        ),
        {"canal_canonico": CANAL_CANONICO},
    )
    return [dict(row._mapping) for row in rows.fetchall()]


def _group_candidates(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[Any, ...], dict[str, Any]] = {}
    channels_by_key: dict[tuple[Any, ...], set[str]] = defaultdict(set)
    for row in rows:
        key = (
            row["tenant_id_text"],
            row["usuario_id"],
            row["data_inicio"],
            row["data_fim"],
            row["mes"],
            row["ano"],
        )
        grouped.setdefault(
            key,
            {
                "tenant_id": row["tenant_id"],
                "usuario_id": row["usuario_id"],
                "data_inicio": row["data_inicio"],
                "data_fim": row["data_fim"],
                "mes": row["mes"],
                "ano": row["ano"],
                "detalhes_total": 0,
            },
        )
        grouped[key]["detalhes_total"] += 1
        channels_by_key[key].add(row["canal_original"])

    groups: list[dict[str, Any]] = []
    for key, group in grouped.items():
        group["canais_originais"] = sorted(channels_by_key[key])
        groups.append(group)
    return groups


def _insert_group(group: dict[str, Any]) -> None:
    table_columns = _columns(TABLE_PERIODOS)
    now = datetime.utcnow()
    marker_payload = json.dumps(
        {
            "marcador": MARKER,
            "canal_canonico": CANAL_CANONICO,
            "canais_originais": group["canais_originais"],
        },
        ensure_ascii=True,
        sort_keys=True,
    )
    values: dict[str, Any] = {
        "tenant_id": group["tenant_id"],
        "usuario_id": group["usuario_id"],
        "data_inicio": group["data_inicio"],
        "data_fim": group["data_fim"],
        "mes": group["mes"],
        "ano": group["ano"],
        "canal": CANAL_CANONICO,
        "status": STATUS_RECONCILIADO,
        "canais_incluidos": marker_payload,
        "criado_em": now,
        "atualizado_em": now,
    }
    for column in FINANCIAL_ZERO_COLUMNS:
        values[column] = 0

    insert_values = {key: value for key, value in values.items() if key in table_columns}
    columns_sql = ", ".join(insert_values.keys())
    params_sql = ", ".join(f":{key}" for key in insert_values)
    _bind().execute(
        text(f"INSERT INTO {TABLE_PERIODOS} ({columns_sql}) VALUES ({params_sql})"),
        insert_values,
    )


def upgrade() -> None:
    if not _required_schema_available():
        return

    for group in _group_candidates(_candidate_rows()):
        _insert_group(group)


def downgrade() -> None:
    if not _table_exists(TABLE_PERIODOS):
        return
    if not {"status", "canal", "canais_incluidos"}.issubset(_columns(TABLE_PERIODOS)):
        return

    _bind().execute(
        text(
            f"""
            DELETE FROM {TABLE_PERIODOS}
            WHERE status = :status
              AND canal = :canal
              AND canais_incluidos LIKE :marker_like
            """
        ),
        {
            "status": STATUS_RECONCILIADO,
            "canal": CANAL_CANONICO,
            "marker_like": f"%{MARKER}%",
        },
    )
