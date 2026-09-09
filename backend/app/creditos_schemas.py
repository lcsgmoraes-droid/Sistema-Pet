"""Payloads canonicos: o orcamento autoriza exatamente uma acao do usuario."""

from typing import Any, Literal

from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict, Field, ValidationError


SERVICE_PERMISSIONS = {
    "produto.descricao_fiscal": "produtos.editar",
    "oferta.imagem": "vendas.criar",
}


class DescricaoCreditPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    codigo_barras: str = Field(min_length=8, max_length=14, pattern=r"^\d+$")
    nome: str | None = Field(default=None, max_length=255)


class ImagemCreditPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    produto_id: int = Field(gt=0)
    estilo: Literal["profissional", "natural", "fundo_limpo"] = "profissional"
    orientacao: Literal["quadrada", "vertical"] = "quadrada"
    prompt_usuario: str = Field(default="", max_length=800)
    imagem_url: str = Field(default="", max_length=2048)
    file_sha256: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")


class CreditoOrcamentoRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    service_code: Literal["produto.descricao_fiscal", "oferta.imagem"]
    request_payload: dict[str, Any]
    idempotency_key: str | None = Field(default=None, min_length=8, max_length=120)


def normalizar_credit_payload(service_code: str, payload: dict) -> dict:
    schema = {
        "produto.descricao_fiscal": DescricaoCreditPayload,
        "oferta.imagem": ImagemCreditPayload,
    }.get(service_code)
    if schema is None:
        raise HTTPException(400, "Recurso ainda nao disponivel na carteira.")
    try:
        result = schema.model_validate(payload).model_dump(mode="json")
    except ValidationError as exc:
        # Nao devolver entrada arbitraria, prompts ou detalhes internos na falha.
        raise HTTPException(
            422, "Confira os dados da acao antes de solicitar o orcamento."
        ) from exc
    if service_code == "oferta.imagem" and not (
        result["file_sha256"] or result["imagem_url"].strip()
    ):
        raise HTTPException(422, "Escolha uma foto real para solicitar o orcamento.")
    return result
