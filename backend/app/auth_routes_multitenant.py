"""Fachada das rotas de autenticacao multi-tenant."""

from fastapi import APIRouter, HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from app.auth import create_access_token as create_access_token
from app.auth import get_current_user, hash_password, verify_password
from app.auth import auth_multitenant_account_routes as _account_routes
from app.auth import auth_multitenant_recovery_routes as _recovery_routes
from app.auth import auth_multitenant_session_routes as _session_routes
from app.auth import auth_multitenant_support as _support
from app.auth.auth_multitenant_account_routes import (
    router as account_router,
)
from app.auth.auth_multitenant_recovery_routes import (
    router as recovery_router,
)
from app.auth.auth_multitenant_schemas import (
    ForgotPasswordRequest,
    LoginRequest,
    LoginResponse,
    RefreshTokenRequest,
    RefreshTokenResponse,
    RegisterRequest,
    ResendVerificationRequest,
    ResetPasswordRequest,
    SelectTenantRequest,
    SelectTenantResponse,
    VerifyEmailRequest,
)
from app.auth.auth_multitenant_session_routes import (
    router as session_router,
)
from app.auth.auth_multitenant_support import (
    ALLOWED_SIGNUP_PLANS,
    DEFAULT_TRIAL_DAYS,
    EMAIL_VERIFICATION_TOKEN_HOURS,
    LOCAL_REQUEST_HOSTS,
    PRIVACY_VERSION,
    RESET_TOKEN_MINUTES,
    STRICT_EMAIL_ENVS,
    TERMS_VERSION,
    _auth_payload,
    _build_email_verification_email,
    _build_password_reset_email,
    _create_token_pair,
    _current_environment_name,
    _hash_token,
    _is_local_signup_request,
    _is_token_expired,
    _issue_email_verification_token,
    _issue_password_reset_tokens,
    _mark_user_consent,
    _now_utc,
    _password_reset_token_matches,
    _resolve_frontend_base_url,
    _session_expiry_utc,
    _validate_refresh_tenant,
    grant_all_permissions_to_role,
    send_email,
)
from app.auth.core import ALGORITHM, ACCESS_TOKEN_EXPIRE_DAYS
from app.config import JWT_SECRET_KEY as SECRET_KEY
from app.models import Permission, Role, RolePermission, Tenant, User, UserTenant
from app.security.jwt_compat import JWTError, jwt
from app.services.tenant_onboarding_service import onboard_tenant_defaults


router = APIRouter(prefix="/auth", tags=["auth-multitenant"])
router.include_router(account_router)
router.include_router(recovery_router)
router.include_router(session_router)

security = _session_routes.security
EMAIL_VERIFICATION_REQUIRED = _support.EMAIL_VERIFICATION_REQUIRED


def _sync_compat_overrides() -> None:
    _support.EMAIL_VERIFICATION_REQUIRED = EMAIL_VERIFICATION_REQUIRED
    _support.send_email = send_email
    _account_routes.hash_password = hash_password
    _account_routes.verify_password = verify_password
    _account_routes.onboard_tenant_defaults = onboard_tenant_defaults
    _recovery_routes.hash_password = hash_password
    _recovery_routes.send_email = send_email


def _email_verification_required_for_request(request):
    _sync_compat_overrides()
    return _support._email_verification_required_for_request(request)


def _send_email_verification(user: User, request) -> bool:
    _sync_compat_overrides()
    return _support._send_email_verification(user, request)


def _email_verification_block(user: User) -> bool:
    _sync_compat_overrides()
    return _support._email_verification_block(user)


def register(*args, **kwargs):
    _sync_compat_overrides()
    return _account_routes.register(*args, **kwargs)


def login_multitenant(*args, **kwargs):
    _sync_compat_overrides()
    return _account_routes.login_multitenant(*args, **kwargs)


def verify_email(*args, **kwargs):
    _sync_compat_overrides()
    return _recovery_routes.verify_email(*args, **kwargs)


def resend_verification(*args, **kwargs):
    _sync_compat_overrides()
    return _recovery_routes.resend_verification(*args, **kwargs)


def forgot_password(*args, **kwargs):
    _sync_compat_overrides()
    return _recovery_routes.forgot_password(*args, **kwargs)


def reset_password(*args, **kwargs):
    _sync_compat_overrides()
    return _recovery_routes.reset_password(*args, **kwargs)


def refresh_access_token(*args, **kwargs):
    return _session_routes.refresh_access_token(*args, **kwargs)


def select_tenant(*args, **kwargs):
    return _session_routes.select_tenant(*args, **kwargs)


def get_me_multitenant(*args, **kwargs):
    return _session_routes.get_me_multitenant(*args, **kwargs)


def logout_multitenant(*args, **kwargs):
    return _session_routes.logout_multitenant(*args, **kwargs)


__all__ = [
    "ACCESS_TOKEN_EXPIRE_DAYS",
    "ALGORITHM",
    "ALLOWED_SIGNUP_PLANS",
    "DEFAULT_TRIAL_DAYS",
    "EMAIL_VERIFICATION_REQUIRED",
    "EMAIL_VERIFICATION_TOKEN_HOURS",
    "ForgotPasswordRequest",
    "HTTPAuthorizationCredentials",
    "HTTPException",
    "JWTError",
    "LOCAL_REQUEST_HOSTS",
    "LoginRequest",
    "LoginResponse",
    "PRIVACY_VERSION",
    "Permission",
    "RESET_TOKEN_MINUTES",
    "RefreshTokenRequest",
    "RefreshTokenResponse",
    "RegisterRequest",
    "ResendVerificationRequest",
    "ResetPasswordRequest",
    "Role",
    "RolePermission",
    "SECRET_KEY",
    "STRICT_EMAIL_ENVS",
    "SelectTenantRequest",
    "SelectTenantResponse",
    "TERMS_VERSION",
    "Tenant",
    "User",
    "UserTenant",
    "VerifyEmailRequest",
    "_auth_payload",
    "_build_email_verification_email",
    "_build_password_reset_email",
    "_create_token_pair",
    "_current_environment_name",
    "_email_verification_block",
    "_email_verification_required_for_request",
    "_hash_token",
    "_is_local_signup_request",
    "_is_token_expired",
    "_issue_email_verification_token",
    "_issue_password_reset_tokens",
    "_mark_user_consent",
    "_now_utc",
    "_password_reset_token_matches",
    "_resolve_frontend_base_url",
    "_send_email_verification",
    "_session_expiry_utc",
    "_validate_refresh_tenant",
    "create_access_token",
    "forgot_password",
    "get_current_user",
    "get_me_multitenant",
    "grant_all_permissions_to_role",
    "hash_password",
    "jwt",
    "login_multitenant",
    "logout_multitenant",
    "onboard_tenant_defaults",
    "refresh_access_token",
    "register",
    "resend_verification",
    "reset_password",
    "router",
    "security",
    "select_tenant",
    "send_email",
    "verify_email",
    "verify_password",
]
