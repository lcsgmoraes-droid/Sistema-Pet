"""Regras unificadas de cotacao de entrega para app e ecommerce."""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from typing import Callable
import unicodedata

from app.services.google_maps_service import calcular_distancia_km


MONEY = Decimal("0.01")
DISTANCE = Decimal("0.01")


class DeliveryQuoteError(ValueError):
    """Erro de regra ou de configuracao que impede uma cotacao segura."""


def _normalize_text(value: str | None) -> str:
    text = unicodedata.normalize("NFKD", str(value or "").strip().lower())
    return "".join(
        character for character in text if not unicodedata.combining(character)
    )


def _decimal(value, default: Decimal | None = None) -> Decimal | None:
    if value is None or value == "":
        return default
    try:
        return Decimal(str(value))
    except (TypeError, ValueError, ArithmeticError):
        return default


def _money(value) -> Decimal:
    return max(_decimal(value, Decimal("0")) or Decimal("0"), Decimal("0")).quantize(
        MONEY, rounding=ROUND_HALF_UP
    )


def resolve_delivery_policy(config, tenant) -> dict:
    """Combina a configuracao nova com os campos legados do tenant."""

    has_unified_config = config is not None and hasattr(config, "modalidade_cobranca")

    def configured(name, legacy_name=None, default=None):
        if has_unified_config:
            value = getattr(config, name, None)
            if value is not None:
                return value
        if tenant is not None and legacy_name:
            value = getattr(tenant, legacy_name, None)
            if value is not None:
                return value
        return default

    modalidade = str(configured("modalidade_cobranca", default="fixa") or "fixa")
    if modalidade not in {"fixa", "por_km"}:
        modalidade = "fixa"

    return {
        "unificada": has_unified_config,
        "entrega_ativa": bool(
            configured("entrega_ativa", "ecommerce_entrega_ativa", True)
        ),
        "retirada_ativa": bool(
            configured("retirada_ativa", "ecommerce_retirada_ativa", True)
        ),
        "modalidade_cobranca": modalidade,
        "taxa_fixa": _money(
            configured("taxa_fixa", "ecommerce_taxa_entrega", Decimal("0"))
        ),
        "valor_por_km_cobrado": _money(
            configured("valor_por_km_cobrado", default=Decimal("0"))
        ),
        "taxa_minima": _money(configured("taxa_minima", default=Decimal("0"))),
        "distancia_maxima_entrega_km": _decimal(
            configured("distancia_maxima_entrega_km")
        ),
        "frete_gratis_acima": _decimal(
            configured("frete_gratis_acima", "ecommerce_frete_gratis_acima")
        ),
        "distancia_maxima_frete_gratis_km": _decimal(
            configured("distancia_maxima_frete_gratis_km")
        ),
        "pedido_minimo": _money(
            configured("pedido_minimo", "ecommerce_pedido_minimo", Decimal("0"))
        ),
        "prazo_entrega_texto": configured(
            "prazo_entrega_texto",
            "ecommerce_prazo_entrega_texto",
            "Prazo combinado com a loja",
        ),
    }


def build_origin_address(config, tenant) -> str:
    """Monta o endereco da loja priorizando a configuracao operacional."""

    logradouro = getattr(config, "logradouro", None) or getattr(
        tenant, "endereco", None
    )
    numero = getattr(config, "numero", None) or getattr(tenant, "numero", None)
    bairro = getattr(config, "bairro", None) or getattr(tenant, "bairro", None)
    cidade = getattr(config, "cidade", None) or getattr(tenant, "cidade", None)
    estado = getattr(config, "estado", None) or getattr(tenant, "uf", None)
    cep = getattr(config, "cep", None) or getattr(tenant, "cep", None)

    return ", ".join(
        str(part).strip()
        for part in (logradouro, numero, bairro, cidade, estado, cep)
        if part and str(part).strip()
    )


def quote_delivery(
    *,
    config,
    tenant,
    cidade_destino: str,
    endereco_destino: str | None,
    subtotal_elegivel: float,
    distance_calculator: Callable[[str, str], Decimal] = calcular_distancia_km,
) -> dict:
    """Calcula o frete conforme a mesma politica para qualquer canal de venda."""

    policy = resolve_delivery_policy(config, tenant)
    if not policy["entrega_ativa"]:
        raise DeliveryQuoteError(
            "Entrega desativada para esta loja. Escolha retirada na loja."
        )

    cidade_loja = getattr(config, "cidade", None) or getattr(tenant, "cidade", None)
    cidade_destino = str(cidade_destino or "").strip()
    if not cidade_destino:
        raise DeliveryQuoteError("Informe a cidade do endereco de entrega.")
    if not cidade_loja:
        raise DeliveryQuoteError(
            "Entrega ainda nao configurada: informe a cidade da loja nas configuracoes de entrega."
        )

    fixed_city_only = bool(
        policy["modalidade_cobranca"] == "fixa"
        and policy["distancia_maxima_entrega_km"] is None
    )
    if fixed_city_only and _normalize_text(cidade_destino) != _normalize_text(
        cidade_loja
    ):
        raise DeliveryQuoteError(
            "A taxa fixa atende apenas a cidade da loja. Configure uma area maxima por km para entregar em outra cidade."
        )

    endereco_destino = str(endereco_destino or "").strip()
    origem = build_origin_address(config, tenant)
    needs_distance = bool(
        policy["modalidade_cobranca"] == "por_km"
        or policy["distancia_maxima_entrega_km"] is not None
        or (
            policy["frete_gratis_acima"] is not None
            and _money(subtotal_elegivel) >= policy["frete_gratis_acima"]
            and policy["distancia_maxima_frete_gratis_km"] is not None
        )
    )

    distancia_km = None
    if needs_distance:
        if not endereco_destino:
            raise DeliveryQuoteError(
                "Informe o endereco completo para calcular a distancia da entrega."
            )
        if not origem or not getattr(config, "logradouro", None):
            raise DeliveryQuoteError(
                "Entrega por distancia ainda nao configurada: complete o endereco de partida da loja."
            )
        try:
            distancia_km = max(
                _decimal(distance_calculator(origem, endereco_destino), Decimal("0"))
                or Decimal("0"),
                Decimal("0"),
            ).quantize(DISTANCE, rounding=ROUND_HALF_UP)
        except DeliveryQuoteError:
            raise
        except Exception as exc:
            raise DeliveryQuoteError(
                "Nao foi possivel calcular a rota para este endereco. Confira rua, numero, cidade e UF."
            ) from exc

    limite_entrega = policy["distancia_maxima_entrega_km"]
    if (
        distancia_km is not None
        and limite_entrega is not None
        and distancia_km > limite_entrega
    ):
        raise DeliveryQuoteError(
            f"Endereco fora da area de entrega. O limite desta loja e {float(limite_entrega):g} km."
        )

    if policy["modalidade_cobranca"] == "por_km":
        if policy["valor_por_km_cobrado"] <= 0:
            raise DeliveryQuoteError(
                "Entrega por km ainda nao configurada: informe um valor por km maior que zero."
            )
        valor_base = max(
            (distancia_km or Decimal("0")) * policy["valor_por_km_cobrado"],
            policy["taxa_minima"],
        ).quantize(MONEY, rounding=ROUND_HALF_UP)
    else:
        valor_base = policy["taxa_fixa"]

    subtotal_money = _money(subtotal_elegivel)
    threshold = policy["frete_gratis_acima"]
    free_distance_limit = policy["distancia_maxima_frete_gratis_km"]
    threshold_reached = bool(
        threshold is not None and threshold > 0 and subtotal_money >= threshold
    )
    within_free_distance = bool(
        free_distance_limit is None
        or (distancia_km is not None and distancia_km <= free_distance_limit)
    )
    free_shipping = threshold_reached and within_free_distance

    return {
        "disponivel": True,
        "valor_frete": float(Decimal("0") if free_shipping else valor_base),
        "valor_frete_base": float(valor_base),
        "prazo_estimado": policy["prazo_entrega_texto"] or "Prazo combinado com a loja",
        "tipo": "entrega_por_km"
        if policy["modalidade_cobranca"] == "por_km"
        else "entrega_taxa_fixa",
        "modalidade_cobranca": policy["modalidade_cobranca"],
        "cidade_loja": cidade_loja,
        "cidade_destino": cidade_destino,
        "distancia_km": float(distancia_km) if distancia_km is not None else None,
        "valor_por_km": float(policy["valor_por_km_cobrado"])
        if policy["modalidade_cobranca"] == "por_km"
        else None,
        "taxa_minima": float(policy["taxa_minima"]),
        "frete_gratis_aplicado": free_shipping,
        "frete_gratis_acima": float(threshold) if threshold is not None else None,
        "distancia_maxima_frete_gratis_km": (
            float(free_distance_limit) if free_distance_limit is not None else None
        ),
        "distancia_maxima_entrega_km": (
            float(limite_entrega) if limite_entrega is not None else None
        ),
        "observacao": "Distancia de rota, em um unico sentido, entre a loja e o cliente."
        if distancia_km is not None
        else "Taxa fixa de entrega.",
    }
