"""Rascunho assistido de descricao comercial e classificacao fiscal por EAN."""

from __future__ import annotations

import json
import logging
import os
import re
from typing import Literal

from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict, Field, field_validator

logger = logging.getLogger(__name__)


class ProdutoAIRascunho(BaseModel):
    model_config = ConfigDict(extra="forbid")

    descricao: str = Field(min_length=40, max_length=4000)
    ncm: str | None = None
    cest: str | None = None
    origem_mercadoria: str | None = None
    confianca_fiscal: Literal["baixa", "media", "alta"]
    alertas_revisao: list[str] = Field(default_factory=list, max_length=8)
    fontes: list[str] = Field(default_factory=list, max_length=8)

    @field_validator("ncm")
    @classmethod
    def validar_ncm(cls, value: str | None) -> str | None:
        if value is None:
            return None
        digits = re.sub(r"\D", "", value)
        return digits if len(digits) == 8 else None

    @field_validator("cest")
    @classmethod
    def validar_cest(cls, value: str | None) -> str | None:
        if value is None:
            return None
        digits = re.sub(r"\D", "", value)
        return digits if len(digits) == 7 else None

    @field_validator("origem_mercadoria")
    @classmethod
    def validar_origem(cls, value: str | None) -> str | None:
        return value if value in {str(numero) for numero in range(9)} else None


PRODUTO_AI_SCHEMA = {
    "type": "object",
    "properties": {
        "descricao": {"type": "string"},
        "ncm": {"type": ["string", "null"]},
        "cest": {"type": ["string", "null"]},
        "origem_mercadoria": {"type": ["string", "null"]},
        "confianca_fiscal": {"type": "string", "enum": ["baixa", "media", "alta"]},
        "alertas_revisao": {"type": "array", "items": {"type": "string"}},
        "fontes": {"type": "array", "items": {"type": "string"}},
    },
    "required": [
        "descricao",
        "ncm",
        "cest",
        "origem_mercadoria",
        "confianca_fiscal",
        "alertas_revisao",
        "fontes",
    ],
    "additionalProperties": False,
}


def gerar_rascunho_produto_por_ean(
    *, api_key: str, codigo_barras: str, nome: str | None = None, client=None
) -> ProdutoAIRascunho:
    """Pesquisa o EAN e devolve somente um rascunho sujeito a revisao humana."""
    if not re.fullmatch(r"\d{8,14}", codigo_barras):
        raise HTTPException(
            status_code=400,
            detail="Informe um codigo de barras valido (8 a 14 digitos).",
        )

    if client is None:
        from openai import OpenAI

        client = OpenAI(api_key=api_key, timeout=90)

    # Nao herdar OPENAI_MODEL: essa variavel global ainda pode apontar para um
    # modelo legado sem suporte ao web_search/JSON Schema. Este recurso tem uma
    # configuracao propria e um padrao compativel com a Responses API.
    model = os.getenv("PRODUTO_AI_MODEL") or "gpt-5.6"
    prompt = f"""
Pesquise na web o produto brasileiro com EAN/GTIN {codigo_barras}.
Nome informado no cadastro: {nome or "nao informado"}.

Crie uma descricao em portugues brasileiro, pronta para e-commerce, em Markdown simples.
Use apenas fatos encontrados em fontes confiaveis (fabricante, orgao oficial ou varejistas
relevantes que identifiquem exatamente o mesmo EAN). Nao invente beneficios, composicao,
indicacoes veterinarias, peso, sabor ou alegacoes de saude.

Para a parte fiscal, sugira apenas NCM (8 digitos), CEST (7 digitos, quando aplicavel) e
origem da mercadoria (0 a 8) que puderem ser sustentados pelas fontes. Quando nao houver
confirmacao suficiente, devolva null e explique em alertas_revisao. Nao sugira CFOP nem
aliquotas: esses dados dependem da operacao, UF e regime da empresa. O resultado e um
rascunho que precisa ser conferido antes da emissao fiscal.
""".strip()

    try:
        response = client.responses.create(
            model=model,
            tools=[{"type": "web_search"}],
            input=[
                {
                    "role": "system",
                    "content": "Voce auxilia cadastro de produtos pet com pesquisa cuidadosa e sem inventar dados.",
                },
                {"role": "user", "content": prompt},
            ],
            reasoning={"effort": "low"},
            text={
                "format": {
                    "type": "json_schema",
                    "name": "produto_ecommerce_fiscal",
                    "schema": PRODUTO_AI_SCHEMA,
                    "strict": True,
                }
            },
            max_output_tokens=2200,
            store=False,
        )
        return ProdutoAIRascunho.model_validate(json.loads(response.output_text))
    except HTTPException:
        raise
    except Exception as exc:
        status_code = getattr(exc, "status_code", None)
        logger.warning(
            "Falha ao gerar rascunho do produto por EAN: %s", type(exc).__name__
        )
        if status_code == 401:
            raise HTTPException(
                status_code=401,
                detail="A chave da OpenAI desta empresa esta invalida. Revise a integracao.",
            ) from exc
        if status_code == 429:
            raise HTTPException(
                status_code=429,
                detail="A IA atingiu o limite de uso. Aguarde um pouco e tente novamente.",
            ) from exc
        raise HTTPException(
            status_code=502,
            detail="Nao foi possivel pesquisar este produto com IA agora. Tente novamente.",
        ) from exc
