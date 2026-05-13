"""Dry-run for creating missing dre_periodos for dre_detalhe_canais.

This script is read-only. It simulates which DRE periods would be needed to
reconcile DRE detail rows without exposing personal data, financial values, or
full tenant IDs.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from typing import Any

from sqlalchemy import inspect as sa_inspect
from sqlalchemy import text
from sqlalchemy.orm import Session


CANAL_PROVISAO_ALIASES = {
    "provisao",
    "provisao_consumo",
    "provisao_consumo_13",
    "ajuste_ferias",
    "ajuste_13",
}

CANAL_NAO_CLASSIFICADO = "nao_classificado"


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


def _canal_case_sql(alias: str) -> str:
    aliases = ", ".join(f"'{canal}'" for canal in sorted(CANAL_PROVISAO_ALIASES))
    return f"""
        CASE
            WHEN LOWER(COALESCE({alias}.canal, '')) IN ({aliases}) THEN 'provisao'
            ELSE '{CANAL_NAO_CLASSIFICADO}'
        END
    """


def _periodos_select(db: Session) -> str:
    period_cols = _columns(db, "dre_periodos")
    if "tenant_id" in period_cols:
        tenant_expr = "CAST(p.tenant_id AS TEXT)"
        join_users = ""
    else:
        tenant_expr = "CAST(up.tenant_id AS TEXT)"
        join_users = "LEFT JOIN users up ON up.id = p.usuario_id"

    return f"""
        SELECT
            p.id,
            {tenant_expr} AS tenant_id,
            p.usuario_id,
            p.data_inicio,
            p.data_fim,
            p.mes,
            p.ano,
            COALESCE(p.canal, '') AS canal
        FROM dre_periodos p
        {join_users}
    """


def _base_cte(db: Session) -> str:
    canal_canonico = _canal_case_sql("d")
    return f"""
        WITH detalhes AS (
            SELECT
                d.id,
                CAST(d.tenant_id AS TEXT) AS tenant_id,
                d.usuario_id,
                d.data_inicio,
                d.data_fim,
                d.mes,
                d.ano,
                COALESCE(d.canal, '') AS canal_original,
                {canal_canonico} AS canal_canonico
            FROM dre_detalhe_canais d
        ),
        periodos AS (
            {_periodos_select(db)}
        ),
        detalhe_users AS (
            SELECT
                d.id,
                u.id AS usuario_encontrado,
                CAST(u.tenant_id AS TEXT) AS usuario_tenant_id
            FROM detalhes d
            LEFT JOIN users u ON u.id = d.usuario_id
        ),
        match_original AS (
            SELECT d.id, COUNT(p.id) AS matches
            FROM detalhes d
            LEFT JOIN periodos p
                ON p.tenant_id = d.tenant_id
               AND p.usuario_id = d.usuario_id
               AND p.data_inicio = d.data_inicio
               AND p.data_fim = d.data_fim
               AND p.canal = d.canal_original
            GROUP BY d.id
        ),
        candidatos AS (
            SELECT d.*, m.matches AS vinculos_originais
            FROM detalhes d
            JOIN match_original m ON m.id = d.id
            WHERE d.canal_canonico = 'provisao'
               OR m.matches = 0
        ),
        grupos AS (
            SELECT
                d.tenant_id,
                d.usuario_id,
                d.data_inicio,
                d.data_fim,
                d.mes,
                d.ano,
                d.canal_canonico,
                COUNT(*) AS detalhes_total,
                SUM(CASE WHEN d.canal_canonico = 'provisao' THEN 1 ELSE 0 END) AS detalhes_provisao,
                SUM(CASE WHEN d.canal_canonico = '{CANAL_NAO_CLASSIFICADO}' THEN 1 ELSE 0 END) AS detalhes_nao_classificados,
                MAX(CASE WHEN du.usuario_encontrado IS NOT NULL THEN 1 ELSE 0 END)
                    AS usuario_valido,
                MAX(
                    CASE
                        WHEN du.usuario_encontrado IS NOT NULL
                         AND du.usuario_tenant_id = d.tenant_id THEN 1
                        ELSE 0
                    END
                ) AS tenant_valido,
                CASE
                    WHEN d.data_inicio IS NOT NULL
                     AND d.data_fim IS NOT NULL
                     AND d.mes IS NOT NULL
                     AND d.ano IS NOT NULL THEN 1 ELSE 0
                END AS datas_validas,
                CASE
                    WHEN EXISTS (
                        SELECT 1 FROM periodos p
                        WHERE p.tenant_id = d.tenant_id
                          AND p.usuario_id = d.usuario_id
                          AND p.data_inicio = d.data_inicio
                          AND p.data_fim = d.data_fim
                          AND p.canal = d.canal_canonico
                    ) THEN 1 ELSE 0
                END AS periodo_canonico_existente
            FROM candidatos d
            LEFT JOIN detalhe_users du ON du.id = d.id
            GROUP BY
                d.tenant_id,
                d.usuario_id,
                d.data_inicio,
                d.data_fim,
                d.mes,
                d.ano,
                d.canal_canonico
        )
    """


def _empty_report(db: Session) -> dict[str, Any]:
    return {
        "modo": "dry_run_read_only",
        "privacidade": {
            "sem_dados_pessoais": True,
            "sem_valores_financeiros_detalhados": True,
            "tenant_id_pseudonimizado": True,
            "usuario_id_pseudonimizado_nas_amostras": True,
        },
        "regra_canal_canonico": {
            "provisao": sorted(CANAL_PROVISAO_ALIASES),
            "nao_classificado": CANAL_NAO_CLASSIFICADO,
        },
        "schema": {
            "dre_detalhe_canais_existe": _table_exists(db, "dre_detalhe_canais"),
            "dre_periodos_existe": _table_exists(db, "dre_periodos"),
            "users_existe": _table_exists(db, "users"),
            "dre_periodos_tem_tenant_id": "tenant_id" in _columns(db, "dre_periodos"),
            "dre_detalhe_canais_tem_periodo_id": "periodo_id"
            in _columns(db, "dre_detalhe_canais"),
        },
        "resumo": {
            "dre_detalhe_canais_analisados": 0,
            "dre_detalhe_canais_sem_vinculo": 0,
            "grupos_unicos_periodos_ausentes": 0,
            "detalhes_cobertos_por_grupos": 0,
            "detalhes_para_canal_provisao": 0,
            "detalhes_canal_nao_classificado": 0,
            "grupos_usuario_valido": 0,
            "grupos_tenant_valido": 0,
            "grupos_datas_validas": 0,
            "grupos_com_periodo_canonico_existente": 0,
            "grupos_poderiam_ser_criados_automaticamente": 0,
            "grupos_exigem_decisao_manual": 0,
            "dre_periodos_seriam_criados": 0,
        },
        "distribuicao_canal_original": [],
        "distribuicao_canal_canonico": [],
        "canais_nao_classificados": [],
        "amostras_agregadas_grupos": [],
    }


def analisar_dre_periodos_ausentes_para_detalhes(db: Session) -> dict[str, Any]:
    """Simulate missing DRE periods needed by unlinked DRE detail rows.

    The simulation groups unlinked detail rows by tenant, user, dates, month,
    year, and canonical channel. It does not write to the database.
    """

    report = _empty_report(db)
    detalhe_required = {
        "id",
        "tenant_id",
        "usuario_id",
        "data_inicio",
        "data_fim",
        "mes",
        "ano",
        "canal",
    }
    periodo_required = {"id", "usuario_id", "data_inicio", "data_fim", "mes", "ano", "canal"}

    if not _has_columns(db, "dre_detalhe_canais", detalhe_required):
        report["schema"]["erro"] = "dre_detalhe_canais ausente ou sem colunas minimas"
        return report
    if not _has_columns(db, "dre_periodos", periodo_required):
        report["schema"]["erro"] = "dre_periodos ausente ou sem colunas minimas"
        return report
    if not _has_columns(db, "users", {"id", "tenant_id"}):
        report["schema"]["erro"] = "users ausente ou sem colunas minimas"
        return report

    base = _base_cte(db)
    details_total = _scalar(db, f"{base} SELECT COUNT(*) FROM detalhes")
    unlinked_total = _scalar(
        db,
        f"""
        {base}
        SELECT COALESCE(SUM(detalhes_total), 0)
        FROM grupos
        WHERE periodo_canonico_existente = 0
        """,
    )
    groups_total = _scalar(
        db,
        f"""
        {base}
        SELECT COUNT(*)
        FROM grupos
        WHERE periodo_canonico_existente = 0
        """,
    )
    covered_total = unlinked_total
    provisao_details = _scalar(
        db,
        """
        SELECT COUNT(*)
        FROM dre_detalhe_canais
        WHERE LOWER(COALESCE(canal, '')) IN (
            'ajuste_13',
            'ajuste_ferias',
            'provisao',
            'provisao_consumo',
            'provisao_consumo_13'
        )
        """,
    )
    unlinked_provisao_details = _scalar(
        db,
        f"""
        {base}
        SELECT COUNT(*)
        FROM candidatos
        WHERE canal_canonico = 'provisao'
          AND NOT EXISTS (
              SELECT 1 FROM periodos p
              WHERE p.tenant_id = candidatos.tenant_id
                AND p.usuario_id = candidatos.usuario_id
                AND p.data_inicio = candidatos.data_inicio
                AND p.data_fim = candidatos.data_fim
                AND p.canal = candidatos.canal_canonico
          )
        """,
    )
    unlinked_unclassified_details = _scalar(
        db,
        f"""
        {base}
        SELECT COUNT(*)
        FROM candidatos
        WHERE canal_canonico = '{CANAL_NAO_CLASSIFICADO}'
          AND NOT EXISTS (
              SELECT 1 FROM periodos p
              WHERE p.tenant_id = candidatos.tenant_id
                AND p.usuario_id = candidatos.usuario_id
                AND p.data_inicio = candidatos.data_inicio
                AND p.data_fim = candidatos.data_fim
                AND p.canal = candidatos.canal_canonico
          )
        """,
    )
    auto_groups = _scalar(
        db,
        f"""
        {base}
        SELECT COUNT(*)
        FROM grupos
        WHERE canal_canonico <> '{CANAL_NAO_CLASSIFICADO}'
          AND usuario_valido = 1
          AND tenant_valido = 1
          AND datas_validas = 1
          AND periodo_canonico_existente = 0
        """,
    )
    manual_groups = max(groups_total - auto_groups, 0)

    report["resumo"].update(
        {
            "dre_detalhe_canais_analisados": details_total,
            "dre_detalhe_canais_sem_vinculo": unlinked_total,
            "grupos_unicos_periodos_ausentes": groups_total,
            "detalhes_cobertos_por_grupos": covered_total,
            "detalhes_para_canal_provisao": unlinked_provisao_details,
            "detalhes_canal_nao_classificado": unlinked_unclassified_details,
            "grupos_usuario_valido": _scalar(
                db, f"{base} SELECT COUNT(*) FROM grupos WHERE usuario_valido = 1"
            ),
            "grupos_tenant_valido": _scalar(
                db, f"{base} SELECT COUNT(*) FROM grupos WHERE tenant_valido = 1"
            ),
            "grupos_datas_validas": _scalar(
                db, f"{base} SELECT COUNT(*) FROM grupos WHERE datas_validas = 1"
            ),
            "grupos_com_periodo_canonico_existente": _scalar(
                db,
                f"{base} SELECT COUNT(*) FROM grupos WHERE periodo_canonico_existente = 1",
            ),
            "grupos_poderiam_ser_criados_automaticamente": auto_groups,
            "grupos_exigem_decisao_manual": manual_groups,
            "dre_periodos_seriam_criados": auto_groups,
            "detalhes_tecnicos_totais_mesmo_ja_vinculados": provisao_details,
        }
    )

    original_rows = _rows(
        db,
        f"""
        {base}
        SELECT canal_original AS canal, COUNT(*) AS total
        FROM candidatos
        WHERE NOT EXISTS (
            SELECT 1 FROM periodos p
            WHERE p.tenant_id = candidatos.tenant_id
              AND p.usuario_id = candidatos.usuario_id
              AND p.data_inicio = candidatos.data_inicio
              AND p.data_fim = candidatos.data_fim
              AND p.canal = candidatos.canal_canonico
        )
        GROUP BY canal_original
        ORDER BY total DESC, canal_original
        """,
    )
    report["distribuicao_canal_original"] = [
        {"canal": _safe_canal(row.get("canal")), "total": int(row.get("total") or 0)}
        for row in original_rows
    ]

    canonical_rows = _rows(
        db,
        f"""
        {base}
        SELECT canal_canonico AS canal, COUNT(*) AS total
        FROM candidatos
        WHERE NOT EXISTS (
            SELECT 1 FROM periodos p
            WHERE p.tenant_id = candidatos.tenant_id
              AND p.usuario_id = candidatos.usuario_id
              AND p.data_inicio = candidatos.data_inicio
              AND p.data_fim = candidatos.data_fim
              AND p.canal = candidatos.canal_canonico
        )
        GROUP BY canal_canonico
        ORDER BY total DESC, canal_canonico
        """,
    )
    report["distribuicao_canal_canonico"] = [
        {"canal": _safe_canal(row.get("canal")), "total": int(row.get("total") or 0)}
        for row in canonical_rows
    ]

    unknown_rows = _rows(
        db,
        f"""
        {base}
        SELECT canal_original AS canal, COUNT(*) AS total
        FROM candidatos
        WHERE canal_canonico = '{CANAL_NAO_CLASSIFICADO}'
          AND NOT EXISTS (
              SELECT 1 FROM periodos p
              WHERE p.tenant_id = candidatos.tenant_id
                AND p.usuario_id = candidatos.usuario_id
                AND p.data_inicio = candidatos.data_inicio
                AND p.data_fim = candidatos.data_fim
                AND p.canal = candidatos.canal_canonico
          )
        GROUP BY canal_original
        ORDER BY total DESC, canal_original
        """,
    )
    report["canais_nao_classificados"] = [
        {"canal": _safe_canal(row.get("canal")), "total": int(row.get("total") or 0)}
        for row in unknown_rows
    ]

    sample_rows = _rows(
        db,
        f"""
        {base}
        SELECT
            tenant_id,
            usuario_id,
            data_inicio,
            data_fim,
            mes,
            ano,
            canal_canonico,
            detalhes_total,
            usuario_valido,
            tenant_valido,
            datas_validas,
            periodo_canonico_existente
        FROM grupos
        WHERE periodo_canonico_existente = 0
        ORDER BY detalhes_total DESC, ano, mes, canal_canonico
        LIMIT 20
        """,
    )
    report["amostras_agregadas_grupos"] = [
        {
            "tenant_ref": _fingerprint(row.get("tenant_id")),
            "usuario_ref": _fingerprint(row.get("usuario_id")),
            "data_inicio": str(row.get("data_inicio")) if row.get("data_inicio") else None,
            "data_fim": str(row.get("data_fim")) if row.get("data_fim") else None,
            "mes": row.get("mes"),
            "ano": row.get("ano"),
            "canal_canonico": _safe_canal(row.get("canal_canonico")),
            "detalhes_total": int(row.get("detalhes_total") or 0),
            "usuario_valido": bool(row.get("usuario_valido")),
            "tenant_valido": bool(row.get("tenant_valido")),
            "datas_validas": bool(row.get("datas_validas")),
            "periodo_canonico_existente": bool(row.get("periodo_canonico_existente")),
        }
        for row in sample_rows
    ]

    return report


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Dry-run read-only diagnostics for missing dre_periodos."
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
        report = analisar_dre_periodos_ausentes_para_detalhes(db)
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
