"""Onboarding assistido de ops: cadastra N lojas do mesmo cliente de uma vez,
todas dentro de um unico grupo comercial novo — o equivalente ao cadastro
negociado "1 -> N" (contrato inicial com varias lojas), sempre acionado pela
equipe interna, nunca pelo cliente final.

Reaproveita exatamente o mesmo provisionamento de tenant do cadastro publico
(``provision_tenant``) e o mesmo metodo ``adicionar_loja`` usado pelo
self-service — a unica diferenca e que aqui a autorizacao vem de um admin de
plataforma (``require_platform_admin``), nao de uma sessao de tenant, entao
nenhuma checagem de "responsavel do grupo" se aplica.

O titular recebe um e-mail para definir a propria senha, reaproveitando o
mesmo fluxo de recuperacao de senha que ja existe (``/auth/forgot-password``).
Nao inventa nenhum mecanismo novo de credencial.
"""

import secrets
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from urllib.parse import quote

from fastapi import Request
from sqlalchemy.orm import Session

from app.auth.auth_multitenant_support import (
    RESET_TOKEN_MINUTES,
    _build_password_reset_email,
    _issue_password_reset_tokens,
    _resolve_frontend_base_url,
)
from app.grupo_comercial_service import GrupoComercialService
from app.models import User
from app.services.email_service import send_email
from app.services.plan_catalog import resolve_signup_selection
from app.services.tenant_provisioning_service import (
    TenantOnboardingError,
    provision_tenant,
)


class OpsGrupoComercialOnboardingError(Exception):
    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail
        super().__init__(detail)


@dataclass
class OpsLojaOnboarding:
    nome_loja: str
    nome_acesso: str | None = None
    plan: str | None = None
    organization_type: str | None = None


@dataclass
class OpsGrupoComercialOnboardingResult:
    grupo_id: int
    titular_email: str
    lojas: list[dict] = field(default_factory=list)


def onboard_grupo_comercial(
    db: Session,
    *,
    request: Request,
    titular_email: str,
    titular_nome: str | None,
    lojas: list[OpsLojaOnboarding],
) -> OpsGrupoComercialOnboardingResult:
    if not lojas:
        raise OpsGrupoComercialOnboardingError(400, "Informe ao menos uma loja.")

    email = titular_email.strip().lower()
    existing = db.query(User).filter(User.email == email).first()
    if existing:
        raise OpsGrupoComercialOnboardingError(
            409,
            "Ja existe uma conta com este e-mail. Para adicionar uma loja a um "
            "titular existente, use 'Adicionar loja ao grupo' com o usuario "
            "dele ja logado, em vez do onboarding assistido.",
        )

    primeira_loja = lojas[0]
    try:
        selected_plan, organization_type = resolve_signup_selection(
            primeira_loja.plan, primeira_loja.organization_type
        )
    except ValueError as exc:
        raise OpsGrupoComercialOnboardingError(400, str(exc)) from exc

    senha_temporaria = secrets.token_urlsafe(24)
    try:
        provisionamento = provision_tenant(
            db,
            tenant_name=primeira_loja.nome_loja,
            login_name=primeira_loja.nome_acesso or primeira_loja.nome_loja,
            plan_code=selected_plan.code,
            organization_type=organization_type,
            new_user_email=email,
            new_user_password=senha_temporaria,
            new_user_nome=titular_nome,
            new_user_email_verified=True,
            restore_tenant_id=None,
        )
    except TenantOnboardingError as exc:
        db.rollback()
        raise OpsGrupoComercialOnboardingError(
            500, "Nao foi possivel provisionar a primeira loja."
        ) from exc

    usuario = provisionamento.user
    grupo_nome = f"Grupo comercial de {titular_nome or email}"
    grupo = GrupoComercialService(db).criar_grupo(
        empresa_id=str(provisionamento.tenant_id),
        usuario_id=usuario.id,
        nome=grupo_nome,
        commit=False,
    )

    lojas_criadas = [
        {
            "tenant_id": str(provisionamento.tenant_id),
            "nome": provisionamento.tenant.name,
            "login_name": provisionamento.login_name,
        }
    ]

    for loja in lojas[1:]:
        try:
            adicionada = GrupoComercialService(db).adicionar_loja(
                grupo_id=grupo["id"],
                usuario=usuario,
                nome_loja=loja.nome_loja,
                nome_acesso=loja.nome_acesso,
                plan=loja.plan,
                organization_type=loja.organization_type,
                restore_tenant_id=None,
                empresa_acionadora_id=None,
                commit=False,
            )
        except TenantOnboardingError as exc:
            db.rollback()
            raise OpsGrupoComercialOnboardingError(
                500, f"Nao foi possivel provisionar a loja '{loja.nome_loja}'."
            ) from exc
        lojas_criadas.append(adicionada)

    reset_code, reset_link_token, stored_reset_token = _issue_password_reset_tokens()
    usuario.reset_token = stored_reset_token
    usuario.reset_token_expires = datetime.now(timezone.utc) + timedelta(
        minutes=RESET_TOKEN_MINUTES
    )
    reset_link = (
        f"{_resolve_frontend_base_url(request)}/recuperar-senha"
        f"?email={quote(usuario.email)}&token={quote(reset_link_token)}"
    )
    subject, html_body, text_body = _build_password_reset_email(
        usuario, reset_code, reset_link
    )
    enviado = send_email(
        to=usuario.email,
        subject=subject,
        html_body=html_body,
        text_body=text_body,
        simulate_if_unconfigured=False,
    )
    if not enviado:
        db.rollback()
        raise OpsGrupoComercialOnboardingError(
            503,
            "Lojas nao criadas: nao foi possivel enviar o e-mail de definicao "
            "de senha. Tente novamente em instantes.",
        )

    db.commit()
    return OpsGrupoComercialOnboardingResult(
        grupo_id=grupo["id"], titular_email=usuario.email, lojas=lojas_criadas
    )
