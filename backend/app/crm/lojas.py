"""Multi-loja do CRM (etapa 1.5): quais lojas o usuario pode ver juntas.

O CRM e por loja (tenant). Um usuario com acesso a mais de uma loja pode ver o
CRM de varias ao mesmo tempo, mas so se:
- tem `crm.todas_lojas` na loja em que esta logado;
- tem vinculo ativo com a outra loja e `crm.visualizar` nela;
- a outra loja tem o modulo CRM ativo.

Cada consulta roda dentro do contexto de UMA loja por vez (o isolamento por RLS
nunca e contornado) e o resultado volta marcado com a loja de origem.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models import Tenant, UserTenant
from app.security.module_access import tenant_has_active_module
from app.security.permissions_service import get_user_permissions
from app.tenancy.context import tenant_context
from app.tenancy.rls import sync_rls_auth_user, sync_rls_tenant

MODULO_CRM = "crm"
PERM_VISUALIZAR = "crm.visualizar"
PERM_TODAS_LOJAS = "crm.todas_lojas"


@dataclass(frozen=True)
class Loja:
    id: UUID
    nome: str

    def como_dict(self) -> dict[str, str]:
        return {"loja_id": str(self.id), "loja_nome": self.nome}


def _nome_da_loja(db: Session, tenant_id: UUID) -> str:
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    return (getattr(tenant, "name", None) or "Loja").strip()


def _lojas_vinculadas(db: Session, user_id: int) -> list[UUID]:
    sync_rls_auth_user(db, user_id)
    linhas = (
        db.query(UserTenant.tenant_id)
        .filter(UserTenant.user_id == user_id, UserTenant.is_active.is_(True))
        .all()
    )
    return [linha[0] for linha in linhas]


def _pode_ver_crm(db: Session, user_id: int, tenant_id: UUID) -> bool:
    with tenant_context(tenant_id):
        sync_rls_tenant(db, tenant_id)
        if not tenant_has_active_module(db, str(tenant_id), MODULO_CRM):
            return False
        return PERM_VISUALIZAR in get_user_permissions(db, user_id, tenant_id)


def lojas_permitidas(db: Session, user: Any, tenant_atual: UUID) -> list[Loja]:
    """Lojas cujo CRM o usuario pode ver; a loja atual vem sempre primeiro.

    Sem `crm.todas_lojas` na loja atual, so a loja atual.
    """
    tenant_atual = UUID(str(tenant_atual))
    try:
        permissoes_atuais = get_user_permissions(db, user.id, tenant_atual)
        ids = [tenant_atual]
        if PERM_TODAS_LOJAS in permissoes_atuais:
            for tenant_id in _lojas_vinculadas(db, user.id):
                if tenant_id != tenant_atual and _pode_ver_crm(db, user.id, tenant_id):
                    ids.append(tenant_id)
        lojas = []
        for tenant_id in ids:
            with tenant_context(tenant_id):
                sync_rls_tenant(db, tenant_id)
                lojas.append(Loja(tenant_id, _nome_da_loja(db, tenant_id)))
        return lojas
    finally:
        sync_rls_tenant(db, tenant_atual)


def resolver_lojas(permitidas: list[Loja], pedidas: Iterable[Any] | None) -> list[Loja]:
    """Aplica o filtro de lojas escolhido na tela. Loja nao permitida = 403."""
    pedidas = [UUID(str(item)) for item in (pedidas or []) if str(item).strip()]
    if not pedidas:
        return list(permitidas)
    por_id = {loja.id: loja for loja in permitidas}
    if any(item not in por_id for item in pedidas):
        raise HTTPException(
            status_code=403,
            detail="Você não tem acesso ao CRM de uma das lojas escolhidas.",
        )
    return [por_id[item] for item in dict.fromkeys(pedidas)]


def consultar_por_loja(
    db: Session,
    lojas: Iterable[Loja],
    consulta: Callable[[Loja], list[dict[str, Any]]],
    tenant_atual: UUID,
) -> list[dict[str, Any]]:
    """Roda `consulta` em cada loja (contexto proprio) e junta, marcando a loja."""
    resultado: list[dict[str, Any]] = []
    try:
        for loja in lojas:
            with tenant_context(loja.id):
                sync_rls_tenant(db, loja.id)
                for item in consulta(loja):
                    resultado.append({**item, **loja.como_dict()})
    finally:
        sync_rls_tenant(db, UUID(str(tenant_atual)))
    return resultado
