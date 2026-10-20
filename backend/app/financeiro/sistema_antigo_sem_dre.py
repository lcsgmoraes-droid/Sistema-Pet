"""Retira da DRE contas importadas, preservando os registros financeiros.

Operação pontual: exige tenant por ID e nome, prévia e hash dessa prévia.
Não altera a regra global da DRE nem tenta estornar snapshots legados de IA.
"""

from __future__ import annotations

import hashlib
import json
from decimal import Decimal
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.tenancy.context import tenant_context
from app.tenancy.rls import sync_rls_tenant
from app.utils.tenant_safe_sql import execute_tenant_safe


MARCADOR = "%(sistema antigo)%"


def _valor(valor) -> str:
    return str(Decimal(str(valor or 0)).quantize(Decimal("0.01")))


def _contas_marcadas(db: Session, tenant_id: str, *, bloquear: bool) -> list[dict]:
    lock = (
        " FOR UPDATE" if bloquear and db.get_bind().dialect.name == "postgresql" else ""
    )
    rows = (
        execute_tenant_safe(
            db,
            """
        SELECT id, descricao, status, valor_final, valor_pago,
               data_emissao, data_vencimento, afeta_dre, dre_subcategoria_id
          FROM contas_pagar
         WHERE {tenant_filter}
           AND lower(descricao) LIKE :marcador
         ORDER BY id
        """
            + lock,
            {"marcador": MARCADOR},
            tenant_id=tenant_id,
        )
        .mappings()
        .all()
    )
    return [
        {
            "id": row["id"],
            "descricao": row["descricao"],
            "status": row["status"],
            "valor_final": _valor(row["valor_final"]),
            "valor_pago": _valor(row["valor_pago"]),
            "data_emissao": str(row["data_emissao"]),
            "data_vencimento": str(row["data_vencimento"]),
            "afeta_dre_antes": bool(row["afeta_dre"]),
            "dre_subcategoria_id_antes": row["dre_subcategoria_id"],
        }
        for row in rows
    ]


def retirar_sistema_antigo_dre(
    db: Session,
    *,
    tenant_id: str,
    tenant_nome: str = "Tecno Agropet",
    apply_changes: bool = False,
    plano_hash: str | None = None,
) -> dict:
    """Consulta todas as datas/status; só grava com a mesma prévia conferida.

    A aplicação muda somente afeta_dre e dre_subcategoria_id, como a opção
    existente da API. Não usa PATCH em lote, pois ele pode gerar recorrências.
    """
    try:
        tenant_id = str(UUID(str(tenant_id)))
        if not tenant_nome.strip():
            raise ValueError("Informe o nome esperado do tenant.")
        with tenant_context(tenant_id):
            sync_rls_tenant(db, tenant_id)
            tenant = (
                db.execute(
                    text(
                        "SELECT name FROM tenants WHERE CAST(id AS TEXT) = :tenant_id"
                    ),
                    {"tenant_id": tenant_id},
                )
                .mappings()
                .one_or_none()
            )
            if tenant is None or tenant["name"] != tenant_nome:
                raise ValueError(
                    "ID e nome do tenant não conferem; nenhuma alteração aplicada."
                )

            marcadas = _contas_marcadas(db, tenant_id, bloquear=apply_changes)
            candidatas = [
                row
                for row in marcadas
                if row["afeta_dre_antes"]
                or row["dre_subcategoria_id_antes"] is not None
            ]
            hash_atual = hashlib.sha256(
                json.dumps(
                    {
                        "tenant_id": tenant_id,
                        "tenant_nome": tenant_nome,
                        "contas": marcadas,
                    },
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                ).encode("utf-8")
            ).hexdigest()
            if apply_changes and plano_hash != hash_atual:
                raise ValueError(
                    "Hash da prévia ausente ou desatualizado; gere uma nova prévia."
                )

            report = {
                "ok": True,
                "dry_run": not apply_changes,
                "applied": apply_changes,
                "tenant_id": tenant_id,
                "tenant_nome": tenant_nome,
                "marcador": "(sistema antigo)",
                "plano_hash": hash_atual,
                "resumo": {
                    "contas_marcadas": len(marcadas),
                    "contas_a_alterar": len(candidatas),
                    "valor_total": _valor(
                        sum(
                            (Decimal(row["valor_final"]) for row in candidatas),
                            Decimal("0"),
                        )
                    ),
                    "campos_alterados": ["afeta_dre", "dre_subcategoria_id"],
                },
                "contas_pagar": [
                    {
                        **row,
                        "afeta_dre_depois": False,
                        "dre_subcategoria_id_depois": None,
                    }
                    for row in candidatas
                ],
            }
            if apply_changes:
                for row in candidatas:
                    result = execute_tenant_safe(
                        db,
                        """
                        UPDATE contas_pagar
                           SET afeta_dre = false, dre_subcategoria_id = NULL
                         WHERE {tenant_filter}
                           AND id = :conta_id
                           AND lower(descricao) LIKE :marcador
                        """,
                        {"conta_id": row["id"], "marcador": MARCADOR},
                        tenant_id=tenant_id,
                    )
                    if result.rowcount != 1:
                        raise ValueError(
                            "Conta mudou durante a aplicação; operação cancelada."
                        )
                restantes = _contas_marcadas(db, tenant_id, bloquear=False)
                if any(
                    row["afeta_dre_antes"]
                    or row["dre_subcategoria_id_antes"] is not None
                    for row in restantes
                ):
                    raise ValueError(
                        "Ainda há contas marcadas afetando a DRE; operação cancelada."
                    )
                db.commit()
            else:
                db.rollback()
            return report
    except Exception:
        db.rollback()
        raise
