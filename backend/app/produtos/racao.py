from __future__ import annotations

from typing import Any, Optional

from sqlalchemy import and_, func, or_

from app.produtos_models import Produto


def _produto_eh_racao_expr():
    tipo_normalizado = func.lower(func.coalesce(Produto.tipo, ""))
    classificacao_normalizada = func.lower(func.coalesce(Produto.classificacao_racao, ""))
    return or_(
        tipo_normalizado.like("ra%"),
        and_(
            classificacao_normalizada != "",
            classificacao_normalizada != "nao",
        ),
    )


def _normalizar_classificacao_racao(valor: Any) -> Optional[str]:
    if valor is None:
        return None

    texto = str(valor).strip().lower()
    if not texto:
        return None

    aliases = {
        "super premium": "super_premium",
        "super-premium": "super_premium",
        "premium": "premium",
        "standard": "standard",
        "standardo": "standard",
        "especial": "especial",
        "especial premium": "especial",
        "terapeutica": "terapeutica",
        "terapêutica": "terapeutica",
    }
    return aliases.get(texto, texto)


def _normalizar_payload_racao(dados: dict[str, Any]) -> dict[str, Any]:
    eh_racao = dados.pop("eh_racao", None)
    classificacao_racao = dados.get("classificacao_racao", None)
    classificacao_normalizada = _normalizar_classificacao_racao(classificacao_racao)

    if eh_racao is None and classificacao_normalizada in {"sim", "nao", "não"}:
        eh_racao = classificacao_normalizada == "sim"
        classificacao_normalizada = None

    if eh_racao is None and classificacao_normalizada:
        eh_racao = True

    if classificacao_racao is not None:
        dados["classificacao_racao"] = classificacao_normalizada

    if eh_racao is not None:
        eh_racao = bool(eh_racao)
        dados["tipo"] = "ração" if eh_racao else "produto"

        if not eh_racao:
            for campo in (
                "classificacao_racao",
                "peso_embalagem",
                "tabela_nutricional",
                "categoria_racao",
                "especies_indicadas",
                "tabela_consumo",
                "linha_racao_id",
                "porte_animal_id",
                "fase_publico_id",
                "tipo_tratamento_id",
                "sabor_proteina_id",
                "apresentacao_peso_id",
            ):
                dados[campo] = None

    return dados

