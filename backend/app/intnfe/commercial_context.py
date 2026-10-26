"""Dados comerciais informados antes da emissão, sem alterar a venda."""

import re
from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    field_validator,
    model_validator,
)

from app.services.pessoa_duplicate_service import _cnpj_valido


class CommercialContextError(Exception):
    def __init__(self, message, *, status=422):
        super().__init__(message)
        self.status = status


class CommercialData(BaseModel):
    model_config = ConfigDict(extra="forbid")

    canal: Literal["loja_fisica", "venda_direta_online", "amazon"] = "loja_fisica"
    numero_pedido: str = Field(default="", max_length=100)
    codigo_rastreamento: str = Field(default="", max_length=100)
    informacoes_complementares: str = Field(default="", max_length=4000)
    intermediador_cnpj: str = Field(default="", max_length=18)
    intermediador_identificacao: str = Field(default="", max_length=60)

    @field_validator(
        "numero_pedido",
        "codigo_rastreamento",
        "intermediador_identificacao",
        mode="before",
    )
    @classmethod
    def normalize_line(cls, value):
        if not isinstance(value, str):
            raise ValueError("Informe um texto válido.")
        return " ".join(value.split())

    @field_validator("informacoes_complementares", mode="before")
    @classmethod
    def normalize_information(cls, value):
        if not isinstance(value, str):
            raise ValueError("Informe um texto válido.")
        return value.strip()

    @field_validator("intermediador_cnpj", mode="before")
    @classmethod
    def valid_document(cls, value):
        if not isinstance(value, str) or re.search(r"[^\d.\s/\-]", value):
            raise ValueError("Informe um CNPJ válido do intermediador com 14 dígitos.")
        digits = re.sub(r"\D", "", value)
        if digits and not _cnpj_valido(digits):
            raise ValueError("Informe um CNPJ válido do intermediador com 14 dígitos.")
        return digits

    @model_validator(mode="after")
    def require_amazon_data(self):
        if self.canal == "amazon":
            missing = [
                label
                for label, value in (
                    ("número do pedido Amazon", self.numero_pedido),
                    ("CNPJ do intermediador", self.intermediador_cnpj),
                    (
                        "identificação da sua loja/vendedor na Amazon",
                        self.intermediador_identificacao,
                    ),
                )
                if not value
            ]
            if missing:
                raise ValueError(
                    "Para emitir pela Amazon, informe " + ", ".join(missing) + "."
                )
            if self.intermediador_identificacao == self.numero_pedido:
                raise ValueError(
                    "A identificação da loja/vendedor na Amazon é diferente do número do pedido. Confira o cadastro da sua loja na plataforma."
                )
        return self


def context_data(venda, *, override=None):
    raw = (
        override
        if override is not None
        else getattr(venda, "nfe_contexto_comercial", None)
    )
    try:
        return CommercialData.model_validate(raw or {}).model_dump()
    except ValidationError as exc:
        message = exc.errors()[0]["msg"]
        raise CommercialContextError(
            str(message).removeprefix("Value error, ")
        ) from None


def has_context(venda):
    return getattr(venda, "nfe_contexto_comercial", None) is not None


def can_edit(venda):
    if str(getattr(venda, "status", "") or "").lower() == "cancelada":
        return False
    if str(getattr(venda, "nfe_status", "") or "").lower() not in {"", "rejeitada"}:
        return False
    # Rejeições confirmadas com identificadores usam primeiro o descarte
    # seguro já existente. Resultado inconclusivo nunca libera edição.
    return not any(
        getattr(venda, name, None)
        for name in (
            "nfe_correlation_id",
            "nfe_idempotency_key",
            "nfe_bling_id",
            "nfe_numero",
            "nfe_chave",
            "nfe_protocolo",
            "nfe_payload_hash",
            "nfe_data_emissao",
            "nfe_data_autorizacao",
            "nfe_xml",
        )
    )


def context_lines(data):
    labels = {
        "loja_fisica": "Loja física",
        "venda_direta_online": "Venda direta pela internet",
        "amazon": "Amazon",
    }
    lines = [f"Canal de venda: {labels[data['canal']]}"]
    if data["numero_pedido"]:
        lines.append(f"Nº Pedido Loja: {data['numero_pedido']}")
    if data["codigo_rastreamento"]:
        lines.append(f"Código de rastreamento: {data['codigo_rastreamento']}")
    if data["informacoes_complementares"]:
        lines.append(data["informacoes_complementares"])
    return lines


def payload_context(venda, document_type):
    if not has_context(venda):
        return None
    data = context_data(venda)
    if data["canal"] == "amazon" and document_type != "nfe":
        raise CommercialContextError(
            "A venda Amazon deve usar NF-e (modelo 55), própria para envio da mercadoria."
        )
    return data
