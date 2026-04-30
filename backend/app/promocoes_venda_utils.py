from __future__ import annotations

from datetime import datetime
from typing import Any, Optional


TOLERANCIA_PRECO_PROMOCAO = 0.01


def _as_float(valor: Any, default: float = 0.0) -> float:
    try:
        if valor is None:
            return default
        return float(valor)
    except (TypeError, ValueError):
        return default


def _datetime_sem_timezone(valor: Any) -> Optional[datetime]:
    if not valor:
        return None
    if getattr(valor, "tzinfo", None) is not None:
        return valor.replace(tzinfo=None)
    return valor


def _janela_ativa(inicio: Any, fim: Any, data_ref: Optional[datetime]) -> bool:
    data_base = _datetime_sem_timezone(data_ref) or datetime.utcnow()
    inicio = _datetime_sem_timezone(inicio)
    fim = _datetime_sem_timezone(fim)
    if inicio and data_base < inicio:
        return False
    if fim and data_base > fim:
        return False
    return True


def normalizar_canal_promocao(valor: Any) -> str:
    texto = str(valor or "").strip().lower()
    texto_normalizado = texto.replace("_", " ").replace("-", " ")

    if any(chave in texto_normalizado for chave in ("app", "aplicativo", "mobile")):
        return "app"

    if any(
        chave in texto_normalizado
        for chave in ("ecommerce", "e commerce", "loja virtual", "site", "web", "online")
    ):
        return "ecommerce"

    if any(chave in texto_normalizado for chave in ("loja", "pdv", "fisica", "erp", "bling")):
        return "loja_fisica"

    return texto or "loja_fisica"


def _canal_da_venda(venda: Any) -> str:
    for origem in (
        getattr(venda, "canal", None),
        getattr(venda, "loja_origem", None),
    ):
        canal = normalizar_canal_promocao(origem)
        if canal in {"app", "ecommerce"}:
            return canal

    return normalizar_canal_promocao(getattr(venda, "canal", None))


def _adicionar_candidato(
    candidatos: list[dict[str, Any]],
    *,
    origem: str,
    preco_promocional: Any,
    preco_regular: Any,
    inicio: Any,
    fim: Any,
    data_ref: Optional[datetime],
) -> None:
    preco_promo = _as_float(preco_promocional)
    preco_base = _as_float(preco_regular)

    if preco_promo <= 0:
        return
    if preco_base > 0 and preco_promo >= (preco_base - TOLERANCIA_PRECO_PROMOCAO):
        return
    if not _janela_ativa(inicio, fim, data_ref):
        return

    candidatos.append(
        {
            "origem": origem,
            "preco_promocional": round(preco_promo, 2),
            "preco_regular": round(preco_base, 2),
        }
    )


def detectar_promocao_por_preco_vendido(
    produto: Any,
    venda: Any,
    *,
    preco_unitario: Any,
    quantidade: Any = 1,
    subtotal_item: Any = 0,
) -> dict[str, Any]:
    """Detecta promocao somente quando o preco vendido bate com preco promocional ativo."""

    preco_vendido = round(_as_float(preco_unitario), 2)
    quantidade_num = _as_float(quantidade, 1.0)
    subtotal = _as_float(subtotal_item) or round(preco_vendido * quantidade_num, 2)
    preco_cadastro = round(_as_float(getattr(produto, "preco_venda", 0) if produto else 0), 2)

    base = {
        "em_promocao": False,
        "promocao_origem": None,
        "preco_cadastro": preco_cadastro,
        "preco_promocional_cadastro": None,
        "desconto_promocional": 0,
        "valor_promocional": 0,
    }

    if not produto or preco_vendido <= 0:
        return base

    data_venda = getattr(venda, "data_venda", None)
    canal = _canal_da_venda(venda)
    candidatos: list[dict[str, Any]] = []

    if getattr(produto, "promocao_ativa", False) is True:
        _adicionar_candidato(
            candidatos,
            origem="Promocao ERP",
            preco_promocional=getattr(produto, "preco_promocional", None),
            preco_regular=getattr(produto, "preco_venda", None),
            inicio=getattr(produto, "promocao_inicio", None),
            fim=getattr(produto, "promocao_fim", None),
            data_ref=data_venda,
        )

    if canal == "app":
        _adicionar_candidato(
            candidatos,
            origem="Promocao App",
            preco_promocional=getattr(produto, "preco_app_promo", None),
            preco_regular=(
                getattr(produto, "preco_app", None)
                if getattr(produto, "preco_app", None) is not None
                else getattr(produto, "preco_venda", None)
            ),
            inicio=getattr(produto, "preco_app_promo_inicio", None),
            fim=getattr(produto, "preco_app_promo_fim", None),
            data_ref=data_venda,
        )
    elif canal == "ecommerce":
        _adicionar_candidato(
            candidatos,
            origem="Promocao Ecommerce",
            preco_promocional=getattr(produto, "preco_ecommerce_promo", None),
            preco_regular=(
                getattr(produto, "preco_ecommerce", None)
                if getattr(produto, "preco_ecommerce", None) is not None
                else getattr(produto, "preco_venda", None)
            ),
            inicio=getattr(produto, "preco_ecommerce_promo_inicio", None),
            fim=getattr(produto, "preco_ecommerce_promo_fim", None),
            data_ref=data_venda,
        )

    candidatos_match = [
        candidato
        for candidato in candidatos
        if abs(preco_vendido - candidato["preco_promocional"]) <= TOLERANCIA_PRECO_PROMOCAO
    ]
    if not candidatos_match:
        return base

    preco_regular_ref = max(_as_float(candidato["preco_regular"]) for candidato in candidatos_match)
    preco_promocional_ref = min(
        _as_float(candidato["preco_promocional"]) for candidato in candidatos_match
    )
    desconto_promocional = max((preco_regular_ref - preco_promocional_ref) * quantidade_num, 0)
    origens = list(dict.fromkeys(candidato["origem"] for candidato in candidatos_match))

    return {
        "em_promocao": True,
        "promocao_origem": ", ".join(origens),
        "preco_cadastro": round(preco_regular_ref or preco_cadastro, 2),
        "preco_promocional_cadastro": round(preco_promocional_ref, 2),
        "desconto_promocional": round(desconto_promocional, 2),
        "valor_promocional": round(subtotal, 2),
    }
