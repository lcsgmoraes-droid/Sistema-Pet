"""Perfis operacionais padrao para novos tenants."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import Permission, Role, RolePermission


CAIXA_PERMISSIONS = frozenset(
    {
        "clientes.criar",
        "clientes.editar",
        "clientes.visualizar",
        "produtos.visualizar",
        "vendas.criar",
        "vendas.editar",
        "vendas.visualizar",
    }
)

CLIENTE_PERMISSIONS = frozenset()

ESTOQUE_COMPRAS_PERMISSIONS = frozenset(
    {
        "cadastros.categorias_produtos",
        "compras.entrada_xml",
        "compras.gerenciar",
        "compras.pedidos",
        "produtos.criar",
        "produtos.editar",
        "produtos.visualizar",
    }
)

FINANCEIRO_PERMISSIONS = frozenset(
    {
        "cadastros.bancos",
        "cadastros.categorias_financeiras",
        "cadastros.formas_pagamento",
        "cadastros.operadoras",
        "financeiro.conciliacao_bancaria",
        "financeiro.conciliacao_cartao",
        "financeiro.contas_bancarias",
        "financeiro.contas_pagar",
        "financeiro.contas_receber",
        "financeiro.dashboard",
        "financeiro.dre",
        "financeiro.fluxo_caixa",
        "financeiro.formas_pagamento",
        "financeiro.relatorio_taxas",
        "financeiro.vendas",
        "relatorios.financeiro",
    }
)

GERENTE_PERMISSIONS = frozenset(
    {
        "cadastros.bancos",
        "cadastros.cargos",
        "cadastros.categorias_financeiras",
        "cadastros.categorias_produtos",
        "cadastros.especies_racas",
        "cadastros.formas_pagamento",
        "cadastros.operadoras",
        "clientes.criar",
        "clientes.editar",
        "clientes.excluir",
        "clientes.visualizar",
        "comissoes.abertas",
        "comissoes.configurar",
        "comissoes.demonstrativo",
        "comissoes.fechamentos",
        "comissoes.relatorios",
        "compras.entrada_xml",
        "compras.gerenciar",
        "compras.pedidos",
        "compras.sincronizacao_bling",
        "configuracoes.custos_moto",
        "configuracoes.entregas",
        "configuracoes.fechamento_mensal",
        "entregas.abertas",
        "entregas.dashboard",
        "entregas.historico",
        "entregas.rotas",
        "financeiro.conciliacao_bancaria",
        "financeiro.conciliacao_cartao",
        "financeiro.contas_bancarias",
        "financeiro.contas_pagar",
        "financeiro.contas_receber",
        "financeiro.dashboard",
        "financeiro.dre",
        "financeiro.fluxo_caixa",
        "financeiro.formas_pagamento",
        "financeiro.relatorio_taxas",
        "financeiro.vendas",
        "ia.fluxo_caixa",
        "ia.whatsapp",
        "produtos.criar",
        "produtos.editar",
        "produtos.excluir",
        "produtos.visualizar",
        "relatorios.financeiro",
        "relatorios.gerencial",
        "rh.funcionarios",
        "vendas.criar",
        "vendas.editar",
        "vendas.excluir",
        "vendas.visualizar",
    }
)

DEFAULT_TENANT_ROLES: dict[str, frozenset[str]] = {
    "Caixa": CAIXA_PERMISSIONS,
    "Cliente": CLIENTE_PERMISSIONS,
    "Estoque e Compras": ESTOQUE_COMPRAS_PERMISSIONS,
    "Financeiro": FINANCEIRO_PERMISSIONS,
    "Gerente": GERENTE_PERMISSIONS,
}


def _normalize_tenant_id(tenant_id: Any) -> UUID:
    if isinstance(tenant_id, UUID):
        return tenant_id
    return UUID(str(tenant_id))


def create_default_roles_for_new_tenant(
    db: Session,
    tenant_id: Any,
) -> dict[str, Any]:
    """
    Cria os perfis operacionais durante o cadastro de um tenant novo.

    Novas permissoes do sistema nunca entram automaticamente nos perfis
    operacionais. Cada perfil usa uma lista explicita para manter o principio
    do menor privilegio. Um perfil que ja exista nunca e alterado.
    """
    tenant_uuid = _normalize_tenant_id(tenant_id)
    required_codes = set().union(*DEFAULT_TENANT_ROLES.values())
    permissions = db.query(Permission).filter(Permission.code.in_(required_codes)).all()
    permission_by_code = {permission.code: permission for permission in permissions}
    missing_permissions = sorted(required_codes - permission_by_code.keys())

    result: dict[str, Any] = {
        "tenant_id": str(tenant_uuid),
        "missing_permissions": missing_permissions,
        "roles": {},
    }

    for role_name, configured_codes in DEFAULT_TENANT_ROLES.items():
        role = (
            db.query(Role)
            .filter(
                Role.tenant_id == tenant_uuid,
                func.lower(Role.name) == role_name.lower(),
            )
            .first()
        )
        role_created = role is None
        available_codes = set(configured_codes) & permission_by_code.keys()

        if role_created:
            role = Role(name=role_name, tenant_id=tenant_uuid)
            db.add(role)
            db.flush()
            added_codes = sorted(available_codes)
            for code in added_codes:
                db.add(
                    RolePermission(
                        tenant_id=tenant_uuid,
                        role_id=role.id,
                        permission_id=permission_by_code[code].id,
                    )
                )
        else:
            added_codes = []

        result["roles"][role_name] = {
            "role_id": role.id if role is not None else None,
            "created": role_created,
            "permission_count": len(available_codes),
            "added_permissions": added_codes,
        }

    return result
