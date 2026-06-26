"""Schemas Pydantic das rotas de autenticacao multi-tenant."""

from typing import List, Optional

from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    email: str
    password: str


class RegisterRequest(BaseModel):
    email: str
    password: str
    nome: Optional[str] = None
    nome_loja: Optional[str] = None
    plan: Optional[str] = "basico"
    organization_type: Optional[str] = "petshop"
    accepted_terms: bool = False
    accepted_privacy: bool = False
    terms_version: Optional[str] = None
    privacy_version: Optional[str] = None


class LoginResponse(BaseModel):
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    token_type: str
    expires_in: Optional[int] = None
    user: dict
    tenants: List[dict]
    requires_email_verification: bool = False
    email_verification_sent: bool = False


class SelectTenantRequest(BaseModel):
    tenant_id: str


class SelectTenantResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str
    expires_in: int
    tenant: dict


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class RefreshTokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str
    expires_in: int


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    email: EmailStr | None = None
    nova_senha: str = Field(min_length=8)


class VerifyEmailRequest(BaseModel):
    token: str
    email: EmailStr | None = None


class ResendVerificationRequest(BaseModel):
    email: EmailStr
