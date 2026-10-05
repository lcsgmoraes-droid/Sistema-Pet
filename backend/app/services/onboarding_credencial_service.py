"""Limpeza do alerta de credencial pendente do onboarding de grupo comercial.

A flag `onboarding_credencial_email_pendente` e ligada quando a loja e criada
mas o e-mail de definicao de senha do titular nao sai. Ela e desligada quando:
- o titular define a senha (fluxo de redefinicao de senha), para todas as lojas
  em que ele tem acesso ativo;
- a operacao confirma manualmente que repassou as credenciais por outro canal.
"""

from sqlalchemy.orm import Session

from app.models import Tenant, UserTenant
from app.tenancy.context import clear_current_tenant, get_current_tenant, set_current_tenant


def confirmar_credenciais_do_usuario(db: Session, *, user_id: int) -> int:
    contexto_anterior = get_current_tenant()
    clear_current_tenant()
    try:
        tenant_ids = [
            str(tenant_id)
            for (tenant_id,) in db.query(UserTenant.tenant_id).filter(
                UserTenant.user_id == user_id,
                UserTenant.is_active.is_(True),
            )
        ]
        if not tenant_ids:
            return 0
        return (
            db.query(Tenant)
            .filter(
                Tenant.id.in_(tenant_ids),
                Tenant.onboarding_credencial_email_pendente.is_(True),
            )
            .update(
                {Tenant.onboarding_credencial_email_pendente: False},
                synchronize_session="fetch",
            )
        )
    finally:
        if contexto_anterior is not None:
            set_current_tenant(contexto_anterior)


def confirmar_credencial_repassada(db: Session, *, tenant_id: str) -> None:
    tenant = db.query(Tenant).filter(Tenant.id == str(tenant_id)).first()
    if tenant is None:
        raise LookupError("Loja nao encontrada.")
    tenant.onboarding_credencial_email_pendente = False
