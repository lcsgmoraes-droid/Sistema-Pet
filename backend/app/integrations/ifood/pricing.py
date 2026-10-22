"""Preco independente do iFood; nenhuma operacao de rede ou escrita."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any
from app.utils.timezone import BRASILIA_TZ

MAX_IFOOD_MONEY = 999_999_999.99


def decimal_value(value: Any) -> Decimal | None:
    if value is None or value == "":
        return None
    try:
        number = Decimal(str(value))
        return number if number.is_finite() else None
    except (InvalidOperation, TypeError, ValueError):
        return None


def money(value: Decimal) -> float:
    return float(value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def monetary_value(value: Any) -> Decimal | None:
    number = decimal_value(value)
    return (
        number
        if number is not None and abs(number) <= Decimal(str(MAX_IFOOD_MONEY))
        else None
    )


def aware(value: Any) -> datetime | None:
    if value is None or value == "":
        return None
    if isinstance(value, str):
        value = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return value if value.tzinfo else value.replace(tzinfo=BRASILIA_TZ)


def utc_timestamp(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def resolve_ifood_prices(product: Any, markup_percent=0, now=None) -> dict:
    current = aware(now) or datetime.now(timezone.utc)
    specific_raw = getattr(product, "preco_ifood", None)
    specific = monetary_value(specific_raw)
    base = monetary_value(getattr(product, "preco_venda", None))
    markup = decimal_value(markup_percent) or Decimal(0)
    regular = (
        specific
        if specific_raw is not None
        else (base * (1 + markup / 100) if base is not None else None)
    )
    regular = monetary_value(regular)
    regular = Decimal(str(money(regular))) if regular is not None else None
    promo_raw = getattr(product, "preco_ifood_promo", None)
    promo = monetary_value(promo_raw)
    # Validar o valor monetario que sera exibido/enviado: uma fracao positiva
    # de centavo pode arredondar a zero, ou alterar o desconto de 5%.
    promo = Decimal(str(money(promo))) if promo is not None else None
    start = aware(getattr(product, "preco_ifood_promo_inicio", None))
    end = aware(getattr(product, "preco_ifood_promo_fim", None))
    errors = []
    if promo_raw is not None and promo is None:
        errors.append(
            (
                "promo_preco",
                "Informe um preço promocional iFood dentro da faixa monetária suportada.",
                "preco_ifood_promo",
            )
        )
    if promo is None and (start or end):
        errors.append(
            (
                "promo_sem_preco",
                "Informe o preço da promoção iFood ou remova suas datas.",
                "preco_ifood_promo",
            )
        )
    if start and end and start > end:
        errors.append(
            (
                "promo_datas",
                "O fim da promoção iFood deve ser posterior ao início.",
                "preco_ifood_promo_fim",
            )
        )
    if promo is not None:
        if promo <= 0 or regular is None or promo >= regular:
            errors.append(
                (
                    "promo_preco",
                    "O preço promocional iFood deve ser positivo e menor que o regular.",
                    "preco_ifood_promo",
                )
            )
        elif promo > regular * Decimal("0.95"):
            errors.append(
                (
                    "promo_desconto",
                    "A promoção iFood precisa ter desconto de pelo menos 5%.",
                    "preco_ifood_promo",
                )
            )
    active = bool(
        promo is not None
        and not errors
        and (not start or current >= start)
        and (not end or current <= end)
    )
    # O cliente agenda apenas a proxima leitura local; o servidor continua
    # decidindo preco, margem e pendencias em cada consulta. O fim e inclusivo.
    next_change = None
    if promo is not None and not errors:
        if start and current < start:
            next_change = start
        elif end and current <= end:
            try:
                next_change = end + timedelta(milliseconds=1)
            except OverflowError:
                # Nao ha instante representavel depois de datetime.max.
                next_change = None
    return {
        "evaluated_at": utc_timestamp(current),
        "next_price_change_at": utc_timestamp(next_change) if next_change else None,
        "price_source": "especifico"
        if getattr(product, "preco_ifood", None) is not None
        else "regra_loja",
        "regular_price": money(regular) if regular is not None else None,
        "effective_price": money(promo)
        if active
        else (money(regular) if regular is not None else None),
        "promotion_active": active,
        "promotion_errors": errors,
    }
