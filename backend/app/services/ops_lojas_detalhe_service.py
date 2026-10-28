"""OPS: visao completa de uma loja (dados, modulos, usuarios, grupo) e resumo de usuarios.

Responde as perguntas do dia a dia de quem cuida das lojas: quem e a loja, em que grupo
esta, quais modulos tem ativos e quem tem acesso a ela. Somente leitura.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models import Tenant
from app.services.ops_lojas_modulos_service import (
    OpsLojaError,
    _modulos_da_loja,
    catalogo_de_modulos,
)
from app.services.ops_tenants_read_service import _fetch_tenant_item
from app.tenancy.context import tenant_context
from app.tenancy.rls import sync_rls_tenant


def _iso(valor: Any) -> str | None:
    return valor.isoformat() if valor else None


def resumo_de_usuarios_por_loja(db: Session) -> dict[str, dict[str, Any]]:
    """Total, ativos e ultimo acesso de cada loja, numa unica consulta."""
    linhas = db.execute(
        text(
            """
            SELECT CAST(ut.tenant_id AS TEXT) AS tenant_id,
                   COUNT(*) AS total,
                   COUNT(*) FILTER (WHERE ut.is_active AND COALESCE(u.is_active, TRUE)) AS ativos,
                   MAX(u.last_login_at) AS ultimo_acesso
            FROM user_tenants ut
            JOIN users u ON u.id = ut.user_id
            GROUP BY ut.tenant_id
            """
        )
    ).mappings()
    return {
        linha["tenant_id"]: {
            "total": int(linha["total"]),
            "ativos": int(linha["ativos"]),
            "ultimo_acesso": _iso(linha["ultimo_acesso"]),
        }
        for linha in linhas
    }


def usuarios_da_loja(db: Session, tenant_id: str) -> list[dict[str, Any]]:
    """Quem tem acesso a esta loja, com perfil, situacao e ultimo acesso."""
    tid = UUID(str(tenant_id))
    with tenant_context(tid):
        sync_rls_tenant(db, tid)
        linhas = db.execute(
            text(
                """
                SELECT u.id, u.nome, u.email, u.username, u.login_phone,
                       u.is_active AS usuario_ativo, u.email_verified AS email_verificado,
                       u.last_login_at, ut.is_active AS acesso_ativo,
                       r.name AS perfil
                FROM user_tenants ut
                JOIN users u ON u.id = ut.user_id
                LEFT JOIN roles r ON r.id = ut.role_id AND r.tenant_id = ut.tenant_id
                WHERE ut.tenant_id = :tenant_id
                ORDER BY (ut.is_active AND COALESCE(u.is_active, TRUE)) DESC,
                         lower(COALESCE(u.nome, u.email, u.username, ''))
                """
            ),
            {"tenant_id": str(tid)},
        ).mappings()
        return [
            {
                "id": linha["id"],
                "nome": linha["nome"],
                "email": linha["email"],
                "usuario": linha["username"],
                "telefone_de_login": linha["login_phone"],
                "perfil": linha["perfil"],
                "ativo": bool(linha["acesso_ativo"])
                and bool(linha["usuario_ativo"] is not False),
                "acesso_ativo_na_loja": bool(linha["acesso_ativo"]),
                "email_verificado": bool(linha["email_verificado"]),
                "ultimo_acesso": _iso(linha["last_login_at"]),
            }
            for linha in linhas
        ]


def lojas_do_mesmo_grupo(
    db: Session, tenant_id: str, grupo_id: int | None
) -> list[dict[str, str]]:
    if grupo_id is None:
        return []
    linhas = db.execute(
        text(
            """
            SELECT CAST(m.empresa_id AS TEXT) AS id, t.name AS nome, m.papel
            FROM grupo_comercial_membros m
            JOIN tenants t ON CAST(t.id AS TEXT) = CAST(m.empresa_id AS TEXT)
            WHERE m.grupo_id = :grupo AND m.status = 'ativo'
            ORDER BY t.name
            """
        ),
        {"grupo": grupo_id},
    ).mappings()
    return [
        {
            "id": linha["id"],
            "nome": linha["nome"],
            "papel": linha["papel"],
            "atual": linha["id"] == str(tenant_id),
        }
        for linha in linhas
    ]


def detalhe_da_loja(db: Session, tenant_id: str) -> dict[str, Any]:
    tenant = db.query(Tenant).filter(Tenant.id == str(tenant_id)).first()
    if tenant is None:
        raise OpsLojaError("Loja não encontrada", 404)
    item = _fetch_tenant_item(db, str(tenant.id))
    grupo = item.get("grupo_comercial")
    usuarios = usuarios_da_loja(db, str(tenant.id))
    modulos = _modulos_da_loja(db, tenant)
    uso = item.get("usage") or {}
    return {
        "id": str(tenant.id),
        "nome": tenant.name,
        "status": item["status"],
        "tipo": item.get("organization_type"),
        "criada_em": _iso(item.get("created_at")),
        "plano": {
            "geral": item.get("plan"),
            "pet": item.get("plan_pet"),
            "vet": item.get("plan_vet"),
            "banho_tosa": item.get("plan_grooming"),
            "situacao_da_cobranca": item.get("billing_status"),
            "origem_da_assinatura": item.get("subscription_source"),
            "valor_cobrado_centavos": item.get("valor_cobrado_cents"),
        },
        "grupo": grupo,
        "lojas_do_grupo": lojas_do_mesmo_grupo(
            db, str(tenant.id), (grupo or {}).get("id")
        ),
        "responsavel": item.get("principal_user"),
        "uso": uso,
        "usuarios": usuarios,
        "usuarios_resumo": {
            "total": len(usuarios),
            "ativos": sum(1 for u in usuarios if u["ativo"]),
        },
        "catalogo_de_modulos": catalogo_de_modulos(),
        **modulos,
    }
