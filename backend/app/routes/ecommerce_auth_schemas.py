from typing import Literal

from pydantic import BaseModel, EmailStr, Field


class EcommerceRegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    nome: str | None = None
    telefone: str = Field(
        min_length=8, max_length=20, description="Telefone obrigatorio"
    )
    canal: str | None = None
    accepted_terms: bool = False
    accepted_privacy: bool = False
    terms_version: str | None = None
    privacy_version: str | None = None
    cpf: str = Field(
        min_length=11,
        max_length=14,
        description="CPF obrigatório (11 dígitos, com ou sem formatação)",
    )


class EcommerceLoginRequest(BaseModel):
    email: EmailStr
    password: str


class EcommerceForgotPasswordRequest(BaseModel):
    email: EmailStr
    canal: str | None = None


class EcommerceResetPasswordRequest(BaseModel):
    token: str
    email: EmailStr | None = None
    nova_senha: str = Field(min_length=8)


class EcommerceProfileUpdateRequest(BaseModel):
    nome: str | None = None
    telefone: str | None = None
    cpf: str | None = None
    cep: str | None = None
    endereco: str | None = None
    numero: str | None = None
    complemento: str | None = None
    bairro: str | None = None
    cidade: str | None = None
    estado: str | None = None
    endereco_entrega: str | None = None
    usar_endereco_entrega_diferente: bool | None = None
    entrega_nome: str | None = None
    entrega_cep: str | None = None
    entrega_endereco: str | None = None
    entrega_numero: str | None = None
    entrega_complemento: str | None = None
    entrega_bairro: str | None = None
    entrega_cidade: str | None = None
    entrega_estado: str | None = None


class EcommerceSelectProfileRequest(BaseModel):
    profile_type: str = Field(
        description="cliente | funcionario | entregador | veterinario"
    )


class EcommerceAccountDeletionRequest(BaseModel):
    password: str = Field(min_length=1)
    confirmation: Literal["EXCLUIR"]
