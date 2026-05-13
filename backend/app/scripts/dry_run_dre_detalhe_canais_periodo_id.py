"""Dry-run for a future dre_detalhe_canais.periodo_id backfill.

This script is read-only. It simulates which DRE detail rows could receive a
periodo_id based on a unique canonical link to dre_periodos, without exposing
personal data, financial values, full tenant IDs, or secrets.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from typing import Any

from sqlalchemy import inspect as sa_inspect
from sqlalchemy import text
from sqlalchemy.orm import Session


TECHNICAL_CHANNELS_TO_PROVISAO = {
    "provisao",
    "provisao_consumo",
    "provisao_consumo_13",
    "ajuste_ferias",
    "ajuste_13",
}
KNOWN_CANONICAL_CHANNELS = {
    "provisao",
    "loja_fisica",
    "mercado_livre",
    "shopee",
    "amazon",
    "todos",
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


def _quoted(values: set[str]) -> str:
    return ", ".join(f"'{value}'" for value in sorted(values))


def _canal_canonico_sql(alias: str) -> str:
    technical = _quoted(TECHNICAL_CHANNELS_TO_PROVISAO)
    known = _quoted(KNOWN_CANONICAL_CHANNELS)
    return f"""
        CASE
            WHEN LOWER(COALESCE({alias}.canal, '')) IN ({technical}) THEN 'provisao'
            WHEN LOWER(COALESCE({alias}.canal, '')) IN ({known})
                THEN LOWER(COALESCE({alias}.canal, ''))
            ELSE '{CANAL_NAO_CLASSIFICADO}'
        END
    """


def _detalhe_periodo_id_expr(db: Session) -> str:
    if "periodo_id" in _columns(db, "dre_detalhe_canais"):
        return "d.periodo_id"
    return "NULL"


def _base_cte(db: Session) -> str:
    canal_canonico = _canal_canonico_sql("d")
    periodo_id_expr = _detalhe_periodo_id_expr(db)
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
                {canal_canonico} AS canal_canonico,
                {periodo_id_expr} AS periodo_id
            FROM dre_detalhe_canais d
        ),
        periodos AS (
            SELECT
                p.id,
                CAST(p.tenant_id AS TEXT) AS tenant_id,
                p.usuario_id,
                p.data_inicio,
                p.data_fim,
                COALESCE(p.canal, '') AS canal
            FROM dre_periodos p
        ),
        match_counts AS (
            SELECT
                d.id,
                COUNT(p.id) AS matches
            FROM detalhes d
            LEFT JOIN periodos p
                ON p.tenant_id = d.tenant_id
               AND p.usuario_id = d.usuario_id
               AND p.data_inicio = d.data_inicio
               AND p.data_fim = d.data_fim
               AND p.canal = d.canal_canonico
               AND d.canal_canonico <> '{CANAL_NAO_CLASSIFICADO}'
            GROUP BY d.id
        ),
        detalhes_classificados AS (
            SELECT
                d.*,
                m.matches,
                CASE
                    WHEN d.canal_canonico = '{CANAL_NAO_CLASSIFICADO}'
                        THEN 'canal_nao_classificado'
                    WHEN m.matches = 1 THEN 'univoco'
                    WHEN m.matches > 1 THEN 'ambiguo'
                    ELSE 'sem_vinculo'
                END AS situacao
            FROM detalhes d
            JOIN match_counts m ON m.id = d.id
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
            "provisao": sorted(TECHNICAL_CHANNELS_TO_PROVISAO),
            "canais_conhecidos_sem_mapeamento": sorted(KNOWN_CANONICAL_CHANNELS),
            "nao_classificado": CANAL_NAO_CLASSIFICADO,
        },
        "schema": {
            "dre_detalhe_canais_existe": _table_exists(db, "dre_detalhe_canais"),
            "dre_periodos_existe": _table_exists(db, "dre_periodos"),
            "dre_detalhe_canais_tem_periodo_id": "periodo_id"
            in _columns(db, "dre_detalhe_canais"),
            "dre_periodos_tem_tenant_id": "tenant_id" in _columns(db, "dre_periodos"),
        },
        "resumo": {
            "dre_detalhe_canais_total": 0,
            "periodo_id_ja_existe": False,
            "periodo_id_ja_preenchido": 0,
            "vinculo_completo_univoco": 0,
            "vinculo_completo_ambiguo": 0,
            "sem_vinculo_completo": 0,
            "canais_nao_classificados_total": 0,
            "detalhes_elegiveis": 0,
            "seriam_atualizados_com_periodo_id": 0,
            "ficariam_sem_periodo_id": 0,
            "exigiriam_revisao_manual": 0,
        },
        "seguranca": {
            "pode_criar_migration_periodo_id": False,
            "motivos_bloqueio": [],
        },
        "distribuicao_canal_original": [],
        "distribuicao_canal_canonico": [],
        "total_por_tenant": [],
        "amostras_agregadas": [],
    }


def analisar_periodo_id_dre_detalhe_canais(db: Session) -> dict[str, Any]:
    """Return a read-only report for a future periodo_id backfill."""

    report = _empty_report(db)
    detalhe_required = {
        "id",
        "tenant_id",
        "usuario_id",
        "data_inicio",
        "data_fim",
        "canal",
    }
    periodo_required = {
        "id",
        "tenant_id",
        "usuario_id",
        "data_inicio",
        "data_fim",
        "canal",
    }

    if not _has_columns(db, "dre_detalhe_canais", detalhe_required):
        report["schema"]["erro"] = "dre_detalhe_canais ausente ou sem colunas minimas"
        return report
    if not _has_columns(db, "dre_periodos", periodo_required):
        report["schema"]["erro"] = "dre_periodos ausente ou sem colunas minimas"
        return report

    periodo_id_exists = report["schema"]["dre_detalhe_canais_tem_periodo_id"]
    base = _base_cte(db)
    total = _scalar(db, f"{base} SELECT COUNT(*) FROM detalhes_classificados")
    univocos = _scalar(
        db, f"{base} SELECT COUNT(*) FROM detalhes_classificados WHERE situacao = 'univoco'"
    )
    ambiguos = _scalar(
        db, f"{base} SELECT COUNT(*) FROM detalhes_classificados WHERE situacao = 'ambiguo'"
    )
    sem_vinculo = _scalar(
        db,
        f"{base} SELECT COUNT(*) FROM detalhes_classificados WHERE situacao = 'sem_vinculo'",
    )
    nao_classificados = _scalar(
        db,
        f"""
        {base}
        SELECT COUNT(*)
        FROM detalhes_classificados
        WHERE situacao = 'canal_nao_classificado'
        """,
    )
    ja_preenchidos = _scalar(
        db,
        f"""
        {base}
        SELECT COUNT(*)
        FROM detalhes_classificados
        WHERE periodo_id IS NOT NULL
        """,
    )
    seriam_atualizados = _scalar(
        db,
        f"""
        {base}
        SELECT COUNT(*)
        FROM detalhes_classificados
        WHERE situacao = 'univoco'
          AND periodo_id IS NULL
        """,
    )
    ficariam_sem = max(total - ja_preenchidos - seriam_atualizados, 0)
    exigiriam_revisao = _scalar(
        db,
        f"""
        {base}
        SELECT COUNT(*)
        FROM detalhes_classificados
        WHERE situacao <> 'univoco'
        """,
    )
    elegiveis = total - nao_classificados

    report["resumo"].update(
        {
            "dre_detalhe_canais_total": total,
            "periodo_id_ja_existe": periodo_id_exists,
            "periodo_id_ja_preenchido": ja_preenchidos,
            "vinculo_completo_univoco": univocos,
            "vinculo_completo_ambiguo": ambiguos,
            "sem_vinculo_completo": sem_vinculo,
            "canais_nao_classificados_total": nao_classificados,
            "detalhes_elegiveis": elegiveis,
            "seriam_atualizados_com_periodo_id": seriam_atualizados,
            "ficariam_sem_periodo_id": ficariam_sem,
            "exigiriam_revisao_manual": exigiriam_revisao,
        }
    )

    motivos: list[str] = []
    if univocos != elegiveis:
        motivos.append("nem_todos_os_detalhes_elegiveis_tem_vinculo_univoco")
    if ambiguos:
        motivos.append("ha_vinculos_ambiguos")
    if sem_vinculo:
        motivos.append("ha_detalhes_sem_vinculo")
    if nao_classificados:
        motivos.append("ha_canais_nao_classificados")

    report["seguranca"] = {
        "pode_criar_migration_periodo_id": not motivos,
        "motivos_bloqueio": motivos,
    }

    report["distribuicao_canal_original"] = [
        {"canal": _safe_canal(row.get("canal")), "total": int(row.get("total") or 0)}
        for row in _rows(
            db,
            f"""
            {base}
            SELECT canal_original AS canal, COUNT(*) AS total
            FROM detalhes_classificados
            GROUP BY canal_original
            ORDER BY total DESC, canal_original
            """,
        )
    ]
    report["distribuicao_canal_canonico"] = [
        {"canal": _safe_canal(row.get("canal")), "total": int(row.get("total") or 0)}
        for row in _rows(
            db,
            f"""
            {base}
            SELECT canal_canonico AS canal, COUNT(*) AS total
            FROM detalhes_classificados
            GROUP BY canal_canonico
            ORDER BY total DESC, canal_canonico
            """,
        )
    ]
    report["total_por_tenant"] = [
        {
            "tenant_ref": _fingerprint(row.get("tenant_id")),
            "total": int(row.get("total") or 0),
            "univocos": int(row.get("univocos") or 0),
            "ambiguos": int(row.get("ambiguos") or 0),
            "sem_vinculo": int(row.get("sem_vinculo") or 0),
            "nao_classificados": int(row.get("nao_classificados") or 0),
        }
        for row in _rows(
            db,
            f"""
            {base}
            SELECT
                tenant_id,
                COUNT(*) AS total,
                SUM(CASE WHEN situacao = 'univoco' THEN 1 ELSE 0 END) AS univocos,
                SUM(CASE WHEN situacao = 'ambiguo' THEN 1 ELSE 0 END) AS ambiguos,
                SUM(CASE WHEN situacao = 'sem_vinculo' THEN 1 ELSE 0 END) AS sem_vinculo,
                SUM(CASE WHEN situacao = 'canal_nao_classificado' THEN 1 ELSE 0 END)
                    AS nao_classificados
            FROM detalhes_classificados
            GROUP BY tenant_id
            ORDER BY total DESC
            """,
        )
    ]
    report["amostras_agregadas"] = [
        {
            "tenant_ref": _fingerprint(row.get("tenant_id")),
            "usuario_ref": _fingerprint(row.get("usuario_id")),
            "ano": row.get("ano"),
            "mes": row.get("mes"),
            "canal_original": _safe_canal(row.get("canal_original")),
            "canal_canonico": _safe_canal(row.get("canal_canonico")),
            "situacao": row.get("situacao"),
            "total": int(row.get("total") or 0),
        }
        for row in _rows(
            db,
            f"""
            {base}
            SELECT
                tenant_id,
                usuario_id,
                ano,
                mes,
                canal_original,
                canal_canonico,
                situacao,
                COUNT(*) AS total
            FROM detalhes_classificados
            GROUP BY
                tenant_id,
                usuario_id,
                ano,
                mes,
                canal_original,
                canal_canonico,
                situacao
            ORDER BY total DESC, ano, mes, canal_original
            LIMIT 20
            """,
        )
    ]

    return report


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Dry-run read-only diagnostics for dre_detalhe_canais.periodo_id."
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
        report = analisar_periodo_id_dre_detalhe_canais(db)
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
