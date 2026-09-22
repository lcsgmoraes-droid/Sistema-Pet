"""Provisionamento de tenant reutilizavel.

Extraido do fluxo de cadastro publico (`POST /auth/register`) para que o
mesmo caminho de criacao de tenant possa ser chamado tambem quando uma loja
e adicionada a um grupo comercial ja existente (mesmo usuario, tenant novo)
e no onboarding assistido feito por ops (`POST /admin/grupos-comerciais/onboarding`).

Os campos de billing/plano/trial (`plan`, `billing_status`, `trial_started_at`,
`trial_ends_at`, `subscription_source`) sao definidos exatamente como no
cadastro publico de hoje, EXCETO quando `grant_trial=False` — usado pela loja
adicionada a um grupo comercial ja existente (`GrupoComercialService.adicionar_loja`),
que nao deve ganhar os 30 dias de acesso completo gratuito de um cliente novo
(decisao de negocio de 21/09/2026).

Controle de transacao (`commit`/`rollback`) e responsabilidade de quem chama,
nao desta funcao — isso permite que o onboarding assistido crie N tenants
numa unica transacao atomica.
"""

import uuid
from dataclasses import dataclass
from datetime import timedelta

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth import hash_password
from app.auth.auth_multitenant_support import DEFAULT_TRIAL_DAYS, _now_utc
from app.models import Role, Tenant, User, UserTenant
from app.auth.auth_multitenant_support import grant_all_permissions_to_role
from app.services.default_roles_service import create_default_roles_for_new_tenant
from app.services.tenant_onboarding_service import onboard_tenant_defaults
from app.services.tenant_login_name_service import (
    TenantLoginNameError,
    set_primary_tenant_login_name,
)
from app.tenancy.context import clear_tenant_context, set_tenant_context


class TenantOnboardingError(Exception):
    """Falha ao aplicar os dados padrao de onboarding de um tenant novo."""


@dataclass
class TenantProvisioningResult:
    tenant: Tenant
    tenant_id: uuid.UUID
    user: User
    admin_role: Role
    user_tenant: UserTenant
    login_name: str
    created_new_user: bool


def provision_tenant(
    db: Session,
    *,
    tenant_name: str,
    login_name: str,
    plan_code: str,
    organization_type: str | None,
    user: User | None = None,
    new_user_email: str | None = None,
    new_user_password: str | None = None,
    new_user_nome: str | None = None,
    new_user_email_verified: bool = True,
    restore_tenant_id: uuid.UUID | None = None,
    grant_trial: bool = True,
) -> TenantProvisioningResult:
    """Cria um Tenant novo com toda a estrutura inicial (papel admin, perfis
    operacionais padrao, dados de onboarding) e o vincula a um usuario.

    Se ``user`` for informado, reaproveita esse usuario (cria so um novo
    ``UserTenant``) — caso de uma loja nova sendo adicionada a um grupo
    comercial por quem ja esta logado. Caso contrario, cria um usuario novo
    a partir de ``new_user_email``/``new_user_password``/``new_user_nome``
    — caso do cadastro publico.

    ``restore_tenant_id``: ao final, restaura o contexto de tenant para esse
    valor em vez de limpar — necessario quando quem chama e uma requisicao
    ja autenticada num tenant existente (adicionar loja ao proprio grupo).
    Se ``None``, o contexto e limpo no final (comportamento do cadastro
    publico, que nao tem "tenant chamador" para restaurar).

    ``grant_trial``: quando ``False``, o tenant nasce com ``billing_status``
    ``"pending"`` e sem ``trial_started_at``/``trial_ends_at`` — sem os 30
    dias de acesso completo gratuito. Usado quando quem esta criando a loja
    ja e cliente pagante adicionando mais uma loja ao proprio grupo, nao um
    cliente novo sendo adquirido. Os modulos/recursos premium do plano
    escolhido so liberam depois que a assinatura for de fato ativada (mesmo
    caminho ja usado hoje por um tenant com trial expirado).
    """
    if user is None and not (new_user_email and new_user_password):
        raise ValueError(
            "provision_tenant precisa de 'user' ou de "
            "'new_user_email'+'new_user_password'"
        )

    tenant_id = uuid.uuid4()
    trial_started_at = _now_utc() if grant_trial else None
    tenant = Tenant(
        id=str(tenant_id),
        name=tenant_name,
        status="active",
        plan=plan_code,
        billing_status="trial" if grant_trial else "pending",
        trial_started_at=trial_started_at,
        trial_ends_at=(
            trial_started_at + timedelta(days=DEFAULT_TRIAL_DAYS) if grant_trial else None
        ),
        subscription_source="manual",
        organization_type=organization_type,
    )
    db.add(tenant)
    # Sem context ainda — falhas daqui pra baixo (nome de acesso duplicado)
    # nao precisam limpar tenant context, porque ele ainda nao foi setado.
    db.flush()
    login_name_change = set_primary_tenant_login_name(db, tenant_id, login_name)

    set_tenant_context(tenant_id)
    try:
        created_new_user = user is None
        if created_new_user:
            user = User(
                email=new_user_email,
                hashed_password=hash_password(new_user_password),
                nome=new_user_nome,
                nome_loja=tenant_name,
                is_active=True,
                is_admin=False,
                email_verified=new_user_email_verified,
                email_verified_at=_now_utc() if new_user_email_verified else None,
                tenant_id=tenant_id,
            )
            db.add(user)
            db.flush()

        admin_role = Role(name="Administrador", tenant_id=tenant_id)
        db.add(admin_role)
        db.flush()

        grant_all_permissions_to_role(role_id=admin_role.id, tenant_id=tenant_id, db=db)
        db.flush()

        try:
            create_default_roles_for_new_tenant(db, tenant_id)
            db.flush()
            onboard_tenant_defaults(
                db=db,
                tenant_id=tenant_id,
                user_id=user.id,
                dry_run=False,
                strict_required=True,
            )
            db.flush()
        except Exception as exc:  # noqa: BLE001 - convertido para tipo proprio
            raise TenantOnboardingError(
                f"Nao foi possivel aplicar os dados padrao do tenant {tenant_id}"
            ) from exc

        user_tenant = UserTenant(
            user_id=user.id,
            tenant_id=tenant_id,
            role_id=admin_role.id,
            is_active=True,
        )
        db.add(user_tenant)
        db.flush()
    finally:
        if restore_tenant_id is not None:
            set_tenant_context(restore_tenant_id)
        else:
            clear_tenant_context()

    return TenantProvisioningResult(
        tenant=tenant,
        tenant_id=tenant_id,
        user=user,
        admin_role=admin_role,
        user_tenant=user_tenant,
        login_name=login_name_change.new_name,
        created_new_user=created_new_user,
    )
