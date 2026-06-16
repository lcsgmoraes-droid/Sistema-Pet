"""Read-only dry-run for oe20260512a1_single_supplier_principal.

The migration marks the only active supplier link of a product as principal and
syncs produtos.fornecedor_id from that single link. This script reports only
aggregate counts and pseudonymized tenant references.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from typing import Any

from sqlalchemy import inspect as sa_inspect
from sqlalchemy import text
from sqlalchemy.orm import Session


def _table_exists(db: Session, table_name: str) -> bool:
    return sa_inspect(db.get_bind()).has_table(table_name)


def _columns(db: Session, table_name: str) -> set[str]:
    if not _table_exists(db, table_name):
        return set()
    return {
        column["name"] for column in sa_inspect(db.get_bind()).get_columns(table_name)
    }


def _has_columns(db: Session, table_name: str, required: set[str]) -> bool:
    return required.issubset(_columns(db, table_name))


def _scalar(db: Session, sql: str) -> int:
    value = db.execute(text(sql)).scalar()
    return int(value or 0)


def _rows(db: Session, sql: str) -> list[dict[str, Any]]:
    return [dict(row._mapping) for row in db.execute(text(sql)).fetchall()]


def _fingerprint(value: Any) -> str | None:
    if value is None:
        return None
    return hashlib.sha256(str(value).encode("utf-8")).hexdigest()[:12]


def _empty_report(db: Session) -> dict[str, Any]:
    return {
        "modo": "dry_run_read_only",
        "privacidade": {
            "sem_dados_pessoais": True,
            "sem_valores_financeiros": True,
            "tenant_id_pseudonimizado": True,
        },
        "schema": {
            "produto_fornecedores_existe": _table_exists(db, "produto_fornecedores"),
            "produtos_existe": _table_exists(db, "produtos"),
            "clientes_existe": _table_exists(db, "clientes"),
        },
        "produto_fornecedores": {
            "total": 0,
            "ativos": 0,
            "inativos": 0,
            "ativos_com_e_principal_true": 0,
            "ativos_com_e_principal_false_ou_null": 0,
        },
        "produtos": {
            "total": 0,
            "com_fornecedor_id": 0,
            "sem_fornecedor_id": 0,
        },
        "impacto_migration": {
            "grupos_produto_tenant_com_um_fornecedor_ativo": 0,
            "produto_fornecedores_seriam_marcados_principais": 0,
            "produtos_seriam_atualizados_fornecedor_id": 0,
        },
        "consistencia": {
            "grupos_com_multiplos_fornecedores_ativos": 0,
            "grupos_ativos_sem_principal": 0,
            "grupos_ativos_com_multiplos_principais": 0,
            "vinculos_sem_produto_mesmo_tenant": 0,
            "vinculos_sem_fornecedor_mesmo_tenant": None,
            "produtos_fornecedor_id_sem_cliente_mesmo_tenant": None,
        },
        "por_tenant": [],
    }


def analisar_single_supplier_principal(db: Session) -> dict[str, Any]:
    """Return an aggregate, read-only impact report for migration oe20260512a1."""

    report = _empty_report(db)
    pf_required = {
        "id",
        "tenant_id",
        "produto_id",
        "fornecedor_id",
        "ativo",
        "e_principal",
    }
    produtos_required = {"id", "tenant_id", "fornecedor_id"}

    if not (
        _has_columns(db, "produto_fornecedores", pf_required)
        and _has_columns(db, "produtos", produtos_required)
    ):
        report["schema"]["erro"] = (
            "produto_fornecedores/produtos ausentes ou sem colunas minimas"
        )
        return report

    report["produto_fornecedores"] = {
        "total": _scalar(db, "SELECT COUNT(*) FROM produto_fornecedores"),
        "ativos": _scalar(
            db, "SELECT COUNT(*) FROM produto_fornecedores WHERE ativo IS TRUE"
        ),
        "inativos": _scalar(
            db,
            """
            SELECT COUNT(*)
            FROM produto_fornecedores
            WHERE ativo IS DISTINCT FROM TRUE
            """,
        ),
        "ativos_com_e_principal_true": _scalar(
            db,
            """
            SELECT COUNT(*)
            FROM produto_fornecedores
            WHERE ativo IS TRUE
              AND e_principal IS TRUE
            """,
        ),
        "ativos_com_e_principal_false_ou_null": _scalar(
            db,
            """
            SELECT COUNT(*)
            FROM produto_fornecedores
            WHERE ativo IS TRUE
              AND e_principal IS DISTINCT FROM TRUE
            """,
        ),
    }

    report["produtos"] = {
        "total": _scalar(db, "SELECT COUNT(*) FROM produtos"),
        "com_fornecedor_id": _scalar(
            db, "SELECT COUNT(*) FROM produtos WHERE fornecedor_id IS NOT NULL"
        ),
        "sem_fornecedor_id": _scalar(
            db, "SELECT COUNT(*) FROM produtos WHERE fornecedor_id IS NULL"
        ),
    }

    unicos_cte = """
        WITH unicos AS (
            SELECT
                produto_id,
                tenant_id,
                MIN(id) AS vinculo_id,
                MIN(fornecedor_id) AS fornecedor_id
            FROM produto_fornecedores
            WHERE ativo IS TRUE
            GROUP BY produto_id, tenant_id
            HAVING COUNT(*) = 1
        )
    """

    report["impacto_migration"] = {
        "grupos_produto_tenant_com_um_fornecedor_ativo": _scalar(
            db,
            unicos_cte
            + """
            SELECT COUNT(*)
            FROM unicos
            """,
        ),
        "produto_fornecedores_seriam_marcados_principais": _scalar(
            db,
            unicos_cte
            + """
            SELECT COUNT(*)
            FROM produto_fornecedores pf
            JOIN unicos u ON u.vinculo_id = pf.id
            WHERE pf.e_principal IS DISTINCT FROM TRUE
            """,
        ),
        "produtos_seriam_atualizados_fornecedor_id": _scalar(
            db,
            unicos_cte
            + """
            SELECT COUNT(*)
            FROM produtos p
            JOIN unicos u
              ON p.id = u.produto_id
             AND p.tenant_id = u.tenant_id
            WHERE p.fornecedor_id IS DISTINCT FROM u.fornecedor_id
            """,
        ),
    }

    report["consistencia"] = {
        "grupos_com_multiplos_fornecedores_ativos": _scalar(
            db,
            """
            SELECT COUNT(*)
            FROM (
                SELECT produto_id, tenant_id
                FROM produto_fornecedores
                WHERE ativo IS TRUE
                GROUP BY produto_id, tenant_id
                HAVING COUNT(*) > 1
            ) grupos
            """,
        ),
        "grupos_ativos_sem_principal": _scalar(
            db,
            """
            SELECT COUNT(*)
            FROM (
                SELECT produto_id, tenant_id
                FROM produto_fornecedores
                WHERE ativo IS TRUE
                GROUP BY produto_id, tenant_id
                HAVING SUM(CASE WHEN e_principal IS TRUE THEN 1 ELSE 0 END) = 0
            ) grupos
            """,
        ),
        "grupos_ativos_com_multiplos_principais": _scalar(
            db,
            """
            SELECT COUNT(*)
            FROM (
                SELECT produto_id, tenant_id
                FROM produto_fornecedores
                WHERE ativo IS TRUE
                GROUP BY produto_id, tenant_id
                HAVING SUM(CASE WHEN e_principal IS TRUE THEN 1 ELSE 0 END) > 1
            ) grupos
            """,
        ),
        "vinculos_sem_produto_mesmo_tenant": _scalar(
            db,
            """
            SELECT COUNT(*)
            FROM produto_fornecedores pf
            LEFT JOIN produtos p
              ON p.id = pf.produto_id
             AND p.tenant_id = pf.tenant_id
            WHERE p.id IS NULL
            """,
        ),
        "vinculos_sem_fornecedor_mesmo_tenant": None,
        "produtos_fornecedor_id_sem_cliente_mesmo_tenant": None,
    }

    if _has_columns(db, "clientes", {"id", "tenant_id"}):
        report["consistencia"]["vinculos_sem_fornecedor_mesmo_tenant"] = _scalar(
            db,
            """
            SELECT COUNT(*)
            FROM produto_fornecedores pf
            LEFT JOIN clientes c
              ON c.id = pf.fornecedor_id
             AND c.tenant_id = pf.tenant_id
            WHERE c.id IS NULL
            """,
        )
        report["consistencia"]["produtos_fornecedor_id_sem_cliente_mesmo_tenant"] = (
            _scalar(
                db,
                """
            SELECT COUNT(*)
            FROM produtos p
            LEFT JOIN clientes c
              ON c.id = p.fornecedor_id
             AND c.tenant_id = p.tenant_id
            WHERE p.fornecedor_id IS NOT NULL
              AND c.id IS NULL
            """,
            )
        )

    tenant_rows = _rows(
        db,
        unicos_cte
        + """
        SELECT
            CAST(u.tenant_id AS TEXT) AS tenant_id,
            COUNT(*) AS grupos_unicos,
            SUM(CASE WHEN pf.e_principal IS DISTINCT FROM TRUE THEN 1 ELSE 0 END)
                AS vinculos_a_marcar_principal,
            SUM(CASE WHEN p.fornecedor_id IS DISTINCT FROM u.fornecedor_id THEN 1 ELSE 0 END)
                AS produtos_a_atualizar
        FROM unicos u
        JOIN produto_fornecedores pf ON pf.id = u.vinculo_id
        JOIN produtos p
          ON p.id = u.produto_id
         AND p.tenant_id = u.tenant_id
        GROUP BY CAST(u.tenant_id AS TEXT)
        ORDER BY grupos_unicos DESC
        """,
    )
    report["por_tenant"] = [
        {
            "tenant_ref": _fingerprint(row.get("tenant_id")),
            "grupos_unicos": int(row.get("grupos_unicos") or 0),
            "vinculos_a_marcar_principal": int(
                row.get("vinculos_a_marcar_principal") or 0
            ),
            "produtos_a_atualizar": int(row.get("produtos_a_atualizar") or 0),
        }
        for row in tenant_rows
    ]

    return report


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Read-only dry-run for oe20260512a1_single_supplier_principal."
    )
    parser.add_argument("--compact", action="store_true")
    args = parser.parse_args()

    from app.db import SessionLocal

    db = SessionLocal()
    try:
        report = analisar_single_supplier_principal(db)
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
