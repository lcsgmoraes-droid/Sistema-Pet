"""Provedor de rascunhos controlados para o catalogo mestre."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field, field_validator


CATALOG_DESCRIPTION_PROMPT_VERSION = "catalog-description-v1"
DEFAULT_CATALOG_DESCRIPTION_MODEL = "gpt-5.6"


class CatalogDescriptionDraft(BaseModel):
    """Resposta estruturada que o worker aceita do provedor."""

    model_config = ConfigDict(extra="forbid")

    descricao_completa: str = Field(min_length=80, max_length=2500)
    tags: list[str] = Field(max_length=12)
    confianca: Literal["baixa", "media", "alta"]
    alertas_revisao: list[str] = Field(max_length=8)

    @field_validator("descricao_completa")
    @classmethod
    def normalize_description(cls, value: str) -> str:
        return " ".join(value.split())

    @field_validator("tags")
    @classmethod
    def normalize_tags(cls, values: list[str]) -> list[str]:
        normalized: list[str] = []
        for value in values:
            tag = " ".join(str(value).strip().lower().split())[:80]
            if tag and tag not in normalized:
                normalized.append(tag)
        return normalized[:12]

    @field_validator("alertas_revisao")
    @classmethod
    def normalize_alerts(cls, values: list[str]) -> list[str]:
        return [" ".join(str(value).split())[:300] for value in values if value][:8]


@dataclass(frozen=True)
class CatalogDescriptionResult:
    draft: CatalogDescriptionDraft
    provider: str
    model: str
    prompt_version: str


class CatalogDescriptionProvider(Protocol):
    provider_name: str
    model: str
    prompt_version: str

    def generate(self, product_context: dict[str, Any]) -> CatalogDescriptionResult:
        """Gera um rascunho usando somente os fatos recebidos."""


SYSTEM_PROMPT = """
Voce redige descricoes de catalogo para produtos pet no Brasil.
Use exclusivamente os fatos presentes no JSON fornecido. Nunca invente composicao,
ingredientes, beneficios, indicacoes clinicas, alegacoes de saude, posologia, dados
nutricionais, EAN ou dados fiscais. Nao transforme ausencia de informacao em fato.
Nao ofereca aconselhamento veterinario. Escreva em portugues brasileiro, de forma
objetiva e comercialmente neutra. O texto e um rascunho que passara por revisao
humana. Inclua em alertas_revisao qualquer limitacao relevante dos dados recebidos.
""".strip()


def build_product_context(product: Any) -> dict[str, Any]:
    """Seleciona apenas dados publicos do produto; IDs do tenant nunca saem daqui."""

    field_names = (
        "nome",
        "tipo_catalogo",
        "marca",
        "categoria",
        "departamento",
        "subcategoria",
        "descricao_curta",
        "tags",
        "unidade",
        "dados_fisicos",
        "dados_racao",
    )
    return {
        field_name: getattr(product, field_name, None)
        for field_name in field_names
        if getattr(product, field_name, None) not in (None, "", [], {})
    }


class OpenAICatalogDescriptionProvider:
    provider_name = "openai"
    prompt_version = CATALOG_DESCRIPTION_PROMPT_VERSION

    def __init__(self, *, api_key: str | None = None, model: str | None = None):
        resolved_key = api_key or os.getenv("OPENAI_API_KEY")
        if not resolved_key:
            raise RuntimeError(
                "OPENAI_API_KEY nao configurada para o worker do catalogo."
            )

        from openai import OpenAI

        self.model = (
            model
            or os.getenv("CATALOGO_MESTRE_OPENAI_MODEL")
            or DEFAULT_CATALOG_DESCRIPTION_MODEL
        )
        self._client = OpenAI(api_key=resolved_key, timeout=60)

    def generate(self, product_context: dict[str, Any]) -> CatalogDescriptionResult:
        reasoning_effort = (
            os.getenv("CATALOGO_MESTRE_OPENAI_REASONING_EFFORT") or "low"
        ).strip()
        if reasoning_effort not in {"none", "minimal", "low", "medium", "high"}:
            reasoning_effort = "low"
        response = self._client.responses.parse(
            model=self.model,
            input=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": (
                        "Crie o rascunho estruturado para este produto:\n"
                        + json.dumps(
                            product_context,
                            ensure_ascii=False,
                            sort_keys=True,
                            default=str,
                        )
                    ),
                },
            ],
            text_format=CatalogDescriptionDraft,
            reasoning={"effort": reasoning_effort},
            max_output_tokens=1200,
            store=False,
        )
        draft = response.output_parsed
        if draft is None:
            raise RuntimeError("A OpenAI nao retornou um rascunho estruturado.")
        return CatalogDescriptionResult(
            draft=draft,
            provider=self.provider_name,
            model=self.model,
            prompt_version=self.prompt_version,
        )
