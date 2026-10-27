"""Registro e leitura do historico de alteracoes do OPS nas lojas."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.ops_tenant_log_models import OpsTenantChangeLog
from app.platform_auth_models import PlatformAdmin

CATEGORIA_MODULO = "modulo"
CATEGORIA_COMERCIAL = "comercial"
CATEGORIA_ACOMPANHAMENTO = "acompanhamento"
LIMITE_PADRAO = 200


def _texto(valor: Any) -> str | None:
    if valor is None:
        return None
    if isinstance(valor, bool):
        return "sim" if valor else "não"
    return str(valor)


def registrar_alteracoes(
    db: Session,
    *,
    tenant_id: str,
    admin: PlatformAdmin,
    categoria: str,
    antes: dict[str, Any],
    depois: dict[str, Any],
) -> int:
    """Grava uma linha por campo que realmente mudou. Nao faz commit."""
    gravadas = 0
    for campo, valor_depois in depois.items():
        valor_antes = antes.get(campo)
        if _texto(valor_antes) == _texto(valor_depois):
            continue
        db.add(
            OpsTenantChangeLog(
                tenant_id=UUID(str(tenant_id)),
                admin_id=getattr(admin, "id", None),
                admin_email=getattr(admin, "email", None) or "desconhecido",
                categoria=categoria,
                campo=campo,
                antes=_texto(valor_antes),
                depois=_texto(valor_depois),
            )
        )
        gravadas += 1
    return gravadas


def ler_campos_da_loja(
    db: Session, tenant_id: str, campos: list[str]
) -> dict[str, Any]:
    """Valores atuais de colunas da loja (nomes vindos do codigo, nunca do usuario)."""
    if not campos:
        return {}
    colunas = ", ".join(campos)
    linha = (
        db.execute(
            text(f"SELECT {colunas} FROM tenants WHERE CAST(id AS TEXT) = :id"),
            {"id": str(tenant_id)},
        )
        .mappings()
        .first()
    )
    return dict(linha) if linha else {}


def listar_historico(
    db: Session, *, tenant_id: str | None = None, limite: int = LIMITE_PADRAO
) -> list[dict[str, Any]]:
    consulta = db.query(OpsTenantChangeLog)
    if tenant_id:
        consulta = consulta.filter(OpsTenantChangeLog.tenant_id == UUID(str(tenant_id)))
    linhas = (
        consulta.order_by(
            OpsTenantChangeLog.criado_em.desc(), OpsTenantChangeLog.id.desc()
        )
        .limit(max(1, min(limite, 500)))
        .all()
    )
    return [
        {
            "id": linha.id,
            "tenant_id": str(linha.tenant_id),
            "quando": linha.criado_em.isoformat() if linha.criado_em else None,
            "quem": linha.admin_email,
            "categoria": linha.categoria,
            "campo": linha.campo,
            "antes": linha.antes,
            "depois": linha.depois,
        }
        for linha in linhas
    ]
