"""Read-only diagnostics for linking dre_detalhe_canais to dre_periodos.

The report intentionally avoids names, emails, documents, financial values,
full tenant IDs, and secrets. It only returns aggregate counters and
pseudonymized references.
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
CANAL_CANONICO_PROVISAO = "provisao"


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


def _canal_detalhe_expr(alias: str) -> str:
    aliases = ", ".join(f"'{canal}'" for canal in sorted(CANAL_PROVISAO_ALIASES))
    return f"""
        CASE
            WHEN LOWER(COALESCE({alias}.canal, '')) IN ({aliases})
                THEN '{CANAL_CANONICO_PROVISAO}'
            ELSE COALESCE({alias}.canal, '')
        END
    """


def _empty_report(db: Session) -> dict[str, Any]:
    return {
        "modo": "diagnostico_read_only",
        "privacidade": {
            "sem_dados_pessoais": True,
            "sem_valores_financeiros_detalhados": True,
            "tenant_id_pseudonimizado": True,
            "usuario_id_pseudonimizado_nas_amostras": True,
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
            "dre_detalhe_canais_total": 0,
            "dre_periodos_total": 0,
            "vinculo_completo_univoco": 0,
            "vinculo_completo_ambiguo": 0,
            "sem_vinculo_completo": 0,
            "classificacao": "nao_avaliado",
        },
        "compatibilidade": {
            "periodo_compativel_por_tenant_mes_ano": 0,
            "periodo_compativel_por_tenant_datas": 0,
            "periodo_compativel_por_tenant_usuario_mes_ano_canal": 0,
            "periodo_compativel_por_tenant_usuario_datas_canal": 0,
        },
        "causas_sem_vinculo": {
            "tenant_id_nao_bate": 0,
            "usuario_id_nao_bate": 0,
            "data_inicio_data_fim_nao_batem": 0,
            "canal_nao_bate": 0,
            "mes_ano_equivalente_datas_diferentes": 0,
            "tenant_equivalente_periodo_ausente": 0,
            "usuario_equivalente_periodo_ausente": 0,
            "usuario_inexistente": 0,
            "usuario_tenant_diferente_do_detalhe": 0,
            "chaves_nulas_no_detalhe": 0,
            "precisariam_novo_dre_periodos": 0,
            "vinculo_ambiguo": 0,
            "vinculo_impossivel": 0,
        },
        "amostras_agregadas_sem_vinculo": [],
    }


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
    canal_detalhe = _canal_detalhe_expr("d")
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
                {canal_detalhe} AS canal
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
        match_counts AS (
            SELECT d.id, COUNT(p.id) AS matches
            FROM detalhes d
            LEFT JOIN periodos p
                ON p.tenant_id = d.tenant_id
               AND p.usuario_id = d.usuario_id
               AND p.data_inicio = d.data_inicio
               AND p.data_fim = d.data_fim
               AND p.canal = d.canal
            GROUP BY d.id
        ),
        sem_vinculo AS (
            SELECT d.*
            FROM detalhes d
            JOIN match_counts m ON m.id = d.id
            WHERE m.matches = 0
        )
    """


def _count_details_where(db: Session, condition: str) -> int:
    return _scalar(
        db,
        f"""
        {_base_cte(db)}
        SELECT COUNT(*)
        FROM detalhes d
        WHERE {condition}
        """,
    )


def _count_sem_vinculo_where(db: Session, condition: str) -> int:
    return _scalar(
        db,
        f"""
        {_base_cte(db)}
        SELECT COUNT(*)
        FROM sem_vinculo d
        WHERE {condition}
        """,
    )


def analisar_dre_detalhe_canais_vinculo(db: Session) -> dict[str, Any]:
    """Return aggregate diagnostics for DRE detail/period linkage.

    Matching key considered complete:
    tenant_id + usuario_id + data_inicio + data_fim + canal.
    The function is read-only and intentionally does not expose row-level
    financial or personal data.
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
    total_detalhes = _scalar(db, f"{base} SELECT COUNT(*) FROM detalhes")
    total_periodos = _scalar(db, f"{base} SELECT COUNT(*) FROM periodos")
    univocos = _scalar(
        db,
        f"""
        {base}
        SELECT COUNT(*) FROM match_counts WHERE matches = 1
        """,
    )
    ambiguos = _scalar(
        db,
        f"""
        {base}
        SELECT COUNT(*) FROM match_counts WHERE matches > 1
        """,
    )
    sem_vinculo = _scalar(
        db,
        f"""
        {base}
        SELECT COUNT(*) FROM match_counts WHERE matches = 0
        """,
    )

    if total_detalhes == 0:
        classificacao = "sem_dados"
    elif sem_vinculo == 0 and ambiguos == 0:
        classificacao = "ligacao_confiavel"
    elif univocos > 0 or ambiguos > 0:
        classificacao = "ligacao_parcial_ou_ambigua"
    else:
        classificacao = "ligacao_impossivel_sem_intervencao"

    report["resumo"].update(
        {
            "dre_detalhe_canais_total": total_detalhes,
            "dre_periodos_total": total_periodos,
            "vinculo_completo_univoco": univocos,
            "vinculo_completo_ambiguo": ambiguos,
            "sem_vinculo_completo": sem_vinculo,
            "classificacao": classificacao,
        }
    )

    report["compatibilidade"].update(
        {
            "periodo_compativel_por_tenant_mes_ano": _count_details_where(
                db,
                """
                EXISTS (
                    SELECT 1 FROM periodos p
                    WHERE p.tenant_id = d.tenant_id
                      AND p.mes = d.mes
                      AND p.ano = d.ano
                )
                """,
            ),
            "periodo_compativel_por_tenant_datas": _count_details_where(
                db,
                """
                EXISTS (
                    SELECT 1 FROM periodos p
                    WHERE p.tenant_id = d.tenant_id
                      AND p.data_inicio = d.data_inicio
                      AND p.data_fim = d.data_fim
                )
                """,
            ),
            "periodo_compativel_por_tenant_usuario_mes_ano_canal": _count_details_where(
                db,
                """
                EXISTS (
                    SELECT 1 FROM periodos p
                    WHERE p.tenant_id = d.tenant_id
                      AND p.usuario_id = d.usuario_id
                      AND p.mes = d.mes
                      AND p.ano = d.ano
                      AND p.canal = d.canal
                )
                """,
            ),
            "periodo_compativel_por_tenant_usuario_datas_canal": _count_details_where(
                db,
                """
                EXISTS (
                    SELECT 1 FROM periodos p
                    WHERE p.tenant_id = d.tenant_id
                      AND p.usuario_id = d.usuario_id
                      AND p.data_inicio = d.data_inicio
                      AND p.data_fim = d.data_fim
                      AND p.canal = d.canal
                )
                """,
            ),
        }
    )

    report["causas_sem_vinculo"].update(
        {
            "tenant_id_nao_bate": _count_sem_vinculo_where(
                db,
                """
                EXISTS (
                    SELECT 1 FROM periodos p
                    WHERE p.usuario_id = d.usuario_id
                      AND p.data_inicio = d.data_inicio
                      AND p.data_fim = d.data_fim
                      AND p.canal = d.canal
                      AND (p.tenant_id IS NULL OR p.tenant_id <> d.tenant_id)
                )
                """,
            ),
            "usuario_id_nao_bate": _count_sem_vinculo_where(
                db,
                """
                EXISTS (
                    SELECT 1 FROM periodos p
                    WHERE p.tenant_id = d.tenant_id
                      AND p.data_inicio = d.data_inicio
                      AND p.data_fim = d.data_fim
                      AND p.canal = d.canal
                      AND (p.usuario_id IS NULL OR p.usuario_id <> d.usuario_id)
                )
                """,
            ),
            "data_inicio_data_fim_nao_batem": _count_sem_vinculo_where(
                db,
                """
                EXISTS (
                    SELECT 1 FROM periodos p
                    WHERE p.tenant_id = d.tenant_id
                      AND p.usuario_id = d.usuario_id
                      AND p.canal = d.canal
                      AND (p.data_inicio <> d.data_inicio OR p.data_fim <> d.data_fim)
                )
                """,
            ),
            "canal_nao_bate": _count_sem_vinculo_where(
                db,
                """
                EXISTS (
                    SELECT 1 FROM periodos p
                    WHERE p.tenant_id = d.tenant_id
                      AND p.usuario_id = d.usuario_id
                      AND p.data_inicio = d.data_inicio
                      AND p.data_fim = d.data_fim
                      AND p.canal <> d.canal
                )
                """,
            ),
            "mes_ano_equivalente_datas_diferentes": _count_sem_vinculo_where(
                db,
                """
                EXISTS (
                    SELECT 1 FROM periodos p
                    WHERE p.tenant_id = d.tenant_id
                      AND p.usuario_id = d.usuario_id
                      AND p.mes = d.mes
                      AND p.ano = d.ano
                      AND p.canal = d.canal
                      AND (p.data_inicio <> d.data_inicio OR p.data_fim <> d.data_fim)
                )
                """,
            ),
            "tenant_equivalente_periodo_ausente": _count_sem_vinculo_where(
                db,
                """
                EXISTS (SELECT 1 FROM periodos p WHERE p.tenant_id = d.tenant_id)
                AND NOT EXISTS (
                    SELECT 1 FROM periodos p
                    WHERE p.tenant_id = d.tenant_id
                      AND p.mes = d.mes
                      AND p.ano = d.ano
                )
                """,
            ),
            "usuario_equivalente_periodo_ausente": _count_sem_vinculo_where(
                db,
                """
                EXISTS (SELECT 1 FROM periodos p WHERE p.usuario_id = d.usuario_id)
                AND NOT EXISTS (
                    SELECT 1 FROM periodos p
                    WHERE p.usuario_id = d.usuario_id
                      AND p.mes = d.mes
                      AND p.ano = d.ano
                )
                """,
            ),
            "usuario_inexistente": _count_sem_vinculo_where(
                db,
                """
                NOT EXISTS (
                    SELECT 1 FROM detalhe_users du
                    WHERE du.id = d.id
                      AND du.usuario_encontrado IS NOT NULL
                )
                """,
            ),
            "usuario_tenant_diferente_do_detalhe": _count_sem_vinculo_where(
                db,
                """
                EXISTS (
                    SELECT 1 FROM detalhe_users du
                    WHERE du.id = d.id
                      AND du.usuario_encontrado IS NOT NULL
                      AND (du.usuario_tenant_id IS NULL OR du.usuario_tenant_id <> d.tenant_id)
                )
                """,
            ),
            "chaves_nulas_no_detalhe": _count_sem_vinculo_where(
                db,
                """
                d.tenant_id IS NULL
                OR d.usuario_id IS NULL
                OR d.data_inicio IS NULL
                OR d.data_fim IS NULL
                OR d.canal = ''
                """,
            ),
            "precisariam_novo_dre_periodos": _count_sem_vinculo_where(
                db,
                """
                EXISTS (
                    SELECT 1 FROM detalhe_users du
                    WHERE du.id = d.id
                      AND du.usuario_encontrado IS NOT NULL
                      AND du.usuario_tenant_id = d.tenant_id
                )
                AND d.data_inicio IS NOT NULL
                AND d.data_fim IS NOT NULL
                AND d.canal <> ''
                AND NOT EXISTS (
                    SELECT 1 FROM periodos p
                    WHERE p.tenant_id = d.tenant_id
                      AND p.usuario_id = d.usuario_id
                      AND p.mes = d.mes
                      AND p.ano = d.ano
                      AND p.canal = d.canal
                )
                """,
            ),
            "vinculo_ambiguo": ambiguos,
            "vinculo_impossivel": _count_sem_vinculo_where(
                db,
                """
                d.tenant_id IS NULL
                OR d.usuario_id IS NULL
                OR d.data_inicio IS NULL
                OR d.data_fim IS NULL
                OR d.canal = ''
                OR NOT EXISTS (
                    SELECT 1 FROM detalhe_users du
                    WHERE du.id = d.id
                      AND du.usuario_encontrado IS NOT NULL
                      AND du.usuario_tenant_id = d.tenant_id
                )
                """,
            ),
        }
    )

    sample_rows = _rows(
        db,
        f"""
        {_base_cte(db)}
        SELECT
            d.tenant_id,
            d.usuario_id,
            d.ano,
            d.mes,
            d.canal,
            COUNT(*) AS total
        FROM sem_vinculo d
        GROUP BY d.tenant_id, d.usuario_id, d.ano, d.mes, d.canal
        ORDER BY total DESC, d.ano, d.mes, d.canal
        LIMIT 20
        """,
    )
    report["amostras_agregadas_sem_vinculo"] = [
        {
            "tenant_ref": _fingerprint(row.get("tenant_id")),
            "usuario_ref": _fingerprint(row.get("usuario_id")),
            "ano": row.get("ano"),
            "mes": row.get("mes"),
            "canal": _safe_canal(row.get("canal")),
            "total": int(row.get("total") or 0),
        }
        for row in sample_rows
    ]

    return report


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Read-only diagnostics for dre_detalhe_canais/dre_periodos linkage."
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
        report = analisar_dre_detalhe_canais_vinculo(db)
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
