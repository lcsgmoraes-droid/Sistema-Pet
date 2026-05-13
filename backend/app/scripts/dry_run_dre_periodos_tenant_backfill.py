"""Dry-run read-only diagnostics for making dre_periodos tenant-safe.

This module intentionally runs aggregate SELECT statements only. It does not
print names, emails, documents, financial values, tokens, or full tenant IDs.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from typing import Any

from sqlalchemy import inspect as sa_inspect
from sqlalchemy import text
from sqlalchemy.orm import Session


def _get_bind(db: Session):
    return db.get_bind()


def _table_exists(db: Session, table_name: str) -> bool:
    return sa_inspect(_get_bind(db)).has_table(table_name)


def _columns(db: Session, table_name: str) -> set[str]:
    if not _table_exists(db, table_name):
        return set()
    return {column["name"] for column in sa_inspect(_get_bind(db)).get_columns(table_name)}


def _has_columns(db: Session, table_name: str, required: set[str]) -> bool:
    return required.issubset(_columns(db, table_name))


def _scalar(db: Session, sql: str, params: dict[str, Any] | None = None) -> int:
    value = db.execute(text(sql), params or {}).scalar()
    return int(value or 0)


def _rows(db: Session, sql: str, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    return [dict(row._mapping) for row in db.execute(text(sql), params or {}).fetchall()]


def _fingerprint(value: Any) -> str | None:
    if value is None:
        return None
    digest = hashlib.sha256(str(value).encode("utf-8")).hexdigest()
    return digest[:12]


def _safe_canal(value: Any) -> str:
    if value is None or value == "":
        return "sem_canal"
    return str(value)[:80]


def _sanitize_distribution(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "ano": row.get("ano"),
            "mes": row.get("mes"),
            "canal": _safe_canal(row.get("canal")),
            "total": int(row.get("total") or 0),
        }
        for row in rows
    ]


def _sanitize_duplicate_groups(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "tenant_ref": _fingerprint(row.get("tenant_id")),
            "ano": row.get("ano"),
            "mes": row.get("mes"),
            "canal": _safe_canal(row.get("canal")),
            "total": int(row.get("total") or 0),
        }
        for row in rows
    ]


def _empty_report(db: Session) -> dict[str, Any]:
    return {
        "modo": "dry_run_read_only",
        "privacidade": {
            "sem_dados_pessoais": True,
            "sem_valores_financeiros_detalhados": True,
            "tenant_id_pseudonimizado": True,
        },
        "schema": {
            "dre_periodos_existe": _table_exists(db, "dre_periodos"),
            "users_existe": _table_exists(db, "users"),
            "dre_detalhe_canais_existe": _table_exists(db, "dre_detalhe_canais"),
            "dre_periodos_tem_tenant_id": "tenant_id" in _columns(db, "dre_periodos"),
            "dre_periodos_tem_fechado": "fechado" in _columns(db, "dre_periodos"),
            "dre_detalhe_canais_tem_periodo_id": "periodo_id"
            in _columns(db, "dre_detalhe_canais"),
        },
        "dre_periodos": {
            "total": 0,
            "usuario_id_preenchido": 0,
            "usuario_id_nulo": 0,
            "data_inicio_nula": 0,
            "data_fim_nula": 0,
            "data_inicio_ou_fim_nula": 0,
        },
        "usuarios": {
            "referenciados_distintos": 0,
            "referenciados_encontrados": 0,
            "referenciados_nao_encontrados": 0,
            "referenciados_com_tenant_id": 0,
            "referenciados_sem_tenant_id": 0,
        },
        "backfill": {
            "mapeaveis_via_usuario": 0,
            "orfaos_ou_sem_tenant": 0,
            "duplicidades_potenciais_grupos": 0,
            "duplicidades_potenciais_registros": 0,
        },
        "distribuicao_ano_mes_canal": [],
        "duplicidades_potenciais": [],
        "periodos_sobrepostos": {
            "pares": 0,
            "usuarios_afetados": 0,
        },
        "dre_detalhe_canais": {
            "total": 0,
            "vinculaveis_por_chave_completa": 0,
            "sem_vinculo_por_chave_completa": 0,
            "vinculos_ambiguos": 0,
            "classificacao": "nao_avaliado",
        },
    }


def analisar_dre_periodos_backfill(db: Session) -> dict[str, Any]:
    """Return an aggregate dry-run report for dre_periodos tenant backfill.

    The function is intentionally read-only and privacy-safe: it returns counts,
    pseudonymized tenant references, dates/month/year/channel buckets, and schema
    flags only.
    """

    report = _empty_report(db)
    dre_required = {"id", "usuario_id", "data_inicio", "data_fim", "mes", "ano", "canal"}

    if not _has_columns(db, "dre_periodos", dre_required):
        report["schema"]["erro"] = "dre_periodos ausente ou sem colunas minimas"
        return report

    report["dre_periodos"].update(
        {
            "total": _scalar(db, "SELECT COUNT(*) FROM dre_periodos"),
            "usuario_id_preenchido": _scalar(
                db, "SELECT COUNT(*) FROM dre_periodos WHERE usuario_id IS NOT NULL"
            ),
            "usuario_id_nulo": _scalar(
                db, "SELECT COUNT(*) FROM dre_periodos WHERE usuario_id IS NULL"
            ),
            "data_inicio_nula": _scalar(
                db, "SELECT COUNT(*) FROM dre_periodos WHERE data_inicio IS NULL"
            ),
            "data_fim_nula": _scalar(
                db, "SELECT COUNT(*) FROM dre_periodos WHERE data_fim IS NULL"
            ),
            "data_inicio_ou_fim_nula": _scalar(
                db,
                """
                SELECT COUNT(*)
                FROM dre_periodos
                WHERE data_inicio IS NULL OR data_fim IS NULL
                """,
            ),
        }
    )

    report["distribuicao_ano_mes_canal"] = _sanitize_distribution(
        _rows(
            db,
            """
            SELECT ano, mes, COALESCE(canal, 'sem_canal') AS canal, COUNT(*) AS total
            FROM dre_periodos
            GROUP BY ano, mes, COALESCE(canal, 'sem_canal')
            ORDER BY ano, mes, canal
            """,
        )
    )

    report["periodos_sobrepostos"] = {
        "pares": _scalar(
            db,
            """
            SELECT COUNT(*)
            FROM (
                SELECT a.id AS periodo_a, b.id AS periodo_b
                FROM dre_periodos a
                JOIN dre_periodos b
                    ON a.usuario_id = b.usuario_id
                    AND a.id < b.id
                WHERE a.usuario_id IS NOT NULL
                  AND a.data_inicio IS NOT NULL
                  AND a.data_fim IS NOT NULL
                  AND b.data_inicio IS NOT NULL
                  AND b.data_fim IS NOT NULL
                  AND a.data_inicio <= b.data_fim
                  AND b.data_inicio <= a.data_fim
            ) sobrepostos
            """,
        ),
        "usuarios_afetados": _scalar(
            db,
            """
            SELECT COUNT(DISTINCT usuario_id)
            FROM (
                SELECT a.usuario_id AS usuario_id
                FROM dre_periodos a
                JOIN dre_periodos b
                    ON a.usuario_id = b.usuario_id
                    AND a.id < b.id
                WHERE a.usuario_id IS NOT NULL
                  AND a.data_inicio IS NOT NULL
                  AND a.data_fim IS NOT NULL
                  AND b.data_inicio IS NOT NULL
                  AND b.data_fim IS NOT NULL
                  AND a.data_inicio <= b.data_fim
                  AND b.data_inicio <= a.data_fim
            ) usuarios_sobrepostos
            """,
        ),
    }

    users_required = {"id", "tenant_id"}
    if _has_columns(db, "users", users_required):
        report["usuarios"].update(
            {
                "referenciados_distintos": _scalar(
                    db,
                    """
                    SELECT COUNT(DISTINCT usuario_id)
                    FROM dre_periodos
                    WHERE usuario_id IS NOT NULL
                    """,
                ),
                "referenciados_encontrados": _scalar(
                    db,
                    """
                    SELECT COUNT(DISTINCT dp.usuario_id)
                    FROM dre_periodos dp
                    JOIN users u ON u.id = dp.usuario_id
                    WHERE dp.usuario_id IS NOT NULL
                    """,
                ),
                "referenciados_nao_encontrados": _scalar(
                    db,
                    """
                    SELECT COUNT(DISTINCT dp.usuario_id)
                    FROM dre_periodos dp
                    LEFT JOIN users u ON u.id = dp.usuario_id
                    WHERE dp.usuario_id IS NOT NULL
                      AND u.id IS NULL
                    """,
                ),
                "referenciados_com_tenant_id": _scalar(
                    db,
                    """
                    SELECT COUNT(DISTINCT u.id)
                    FROM dre_periodos dp
                    JOIN users u ON u.id = dp.usuario_id
                    WHERE u.tenant_id IS NOT NULL
                    """,
                ),
                "referenciados_sem_tenant_id": _scalar(
                    db,
                    """
                    SELECT COUNT(DISTINCT u.id)
                    FROM dre_periodos dp
                    JOIN users u ON u.id = dp.usuario_id
                    WHERE u.tenant_id IS NULL
                    """,
                ),
            }
        )

        duplicate_rows = _rows(
            db,
            """
            SELECT
                CAST(u.tenant_id AS TEXT) AS tenant_id,
                dp.ano AS ano,
                dp.mes AS mes,
                COALESCE(dp.canal, 'sem_canal') AS canal,
                COUNT(*) AS total
            FROM dre_periodos dp
            JOIN users u ON u.id = dp.usuario_id
            WHERE u.tenant_id IS NOT NULL
            GROUP BY CAST(u.tenant_id AS TEXT), dp.ano, dp.mes, COALESCE(dp.canal, 'sem_canal')
            HAVING COUNT(*) > 1
            ORDER BY total DESC, ano, mes, canal
            """,
        )
        duplicate_groups = _sanitize_duplicate_groups(duplicate_rows)
        report["duplicidades_potenciais"] = duplicate_groups
        report["backfill"].update(
            {
                "mapeaveis_via_usuario": _scalar(
                    db,
                    """
                    SELECT COUNT(*)
                    FROM dre_periodos dp
                    JOIN users u ON u.id = dp.usuario_id
                    WHERE dp.usuario_id IS NOT NULL
                      AND u.tenant_id IS NOT NULL
                    """,
                ),
                "orfaos_ou_sem_tenant": _scalar(
                    db,
                    """
                    SELECT COUNT(*)
                    FROM dre_periodos dp
                    LEFT JOIN users u ON u.id = dp.usuario_id
                    WHERE dp.usuario_id IS NULL
                       OR u.id IS NULL
                       OR u.tenant_id IS NULL
                    """,
                ),
                "duplicidades_potenciais_grupos": len(duplicate_groups),
                "duplicidades_potenciais_registros": sum(
                    int(row["total"]) for row in duplicate_groups
                ),
            }
        )

    _analisar_dre_detalhe_canais(db, report)
    return report


def _analisar_dre_detalhe_canais(db: Session, report: dict[str, Any]) -> None:
    required = {
        "id",
        "tenant_id",
        "usuario_id",
        "data_inicio",
        "data_fim",
        "canal",
    }
    if not (
        _has_columns(db, "dre_detalhe_canais", required)
        and _has_columns(db, "users", {"id", "tenant_id"})
        and _has_columns(
            db,
            "dre_periodos",
            {"id", "usuario_id", "data_inicio", "data_fim", "canal"},
        )
    ):
        return

    total = _scalar(db, "SELECT COUNT(*) FROM dre_detalhe_canais")
    vinculaveis = _scalar(
        db,
        """
        SELECT COUNT(*)
        FROM (
            SELECT d.id
            FROM dre_detalhe_canais d
            JOIN users u
                ON u.id = d.usuario_id
                AND u.tenant_id IS NOT NULL
                AND CAST(u.tenant_id AS TEXT) = CAST(d.tenant_id AS TEXT)
            JOIN dre_periodos p
                ON p.usuario_id = d.usuario_id
                AND p.data_inicio = d.data_inicio
                AND p.data_fim = d.data_fim
                AND COALESCE(p.canal, '') = COALESCE(d.canal, '')
            GROUP BY d.id
            HAVING COUNT(p.id) >= 1
        ) matches
        """,
    )
    ambiguos = _scalar(
        db,
        """
        SELECT COUNT(*)
        FROM (
            SELECT d.id
            FROM dre_detalhe_canais d
            JOIN users u
                ON u.id = d.usuario_id
                AND u.tenant_id IS NOT NULL
                AND CAST(u.tenant_id AS TEXT) = CAST(d.tenant_id AS TEXT)
            JOIN dre_periodos p
                ON p.usuario_id = d.usuario_id
                AND p.data_inicio = d.data_inicio
                AND p.data_fim = d.data_fim
                AND COALESCE(p.canal, '') = COALESCE(d.canal, '')
            GROUP BY d.id
            HAVING COUNT(p.id) > 1
        ) matches
        """,
    )
    sem_vinculo = max(total - vinculaveis, 0)
    if total == 0:
        classificacao = "sem_dados"
    elif vinculaveis == total and ambiguos == 0:
        classificacao = "ligacao_confiavel"
    elif vinculaveis > 0:
        classificacao = "ligacao_ambigua"
    else:
        classificacao = "ligacao_impossivel_sem_intervencao"

    report["dre_detalhe_canais"] = {
        "total": total,
        "vinculaveis_por_chave_completa": vinculaveis,
        "sem_vinculo_por_chave_completa": sem_vinculo,
        "vinculos_ambiguos": ambiguos,
        "classificacao": classificacao,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Dry-run read-only diagnostics for dre_periodos tenant backfill."
    )
    parser.add_argument(
        "--compact",
        action="store_true",
        help="Print compact JSON instead of indented JSON.",
    )
    args = parser.parse_args()

    from app.db import SessionLocal

    db = SessionLocal()
    try:
        report = analisar_dre_periodos_backfill(db)
        print(
            json.dumps(
                report,
                ensure_ascii=False,
                sort_keys=True,
                indent=None if args.compact else 2,
            )
        )
    finally:
        db.close()


if __name__ == "__main__":
    main()
