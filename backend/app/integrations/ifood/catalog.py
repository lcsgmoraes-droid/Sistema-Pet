"""Traducao do cadastro de produtos do CorePet para o modulo Item do iFood."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Iterable
from urllib.parse import urljoin, urlparse

_MONEY = Decimal("0.01")


@dataclass(frozen=True)
class IfoodCatalogItem:
    product_id: int
    sku: str
    eligible: bool
    payload: dict[str, Any] | None
    errors: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return {
            "product_id": self.product_id,
            "sku": self.sku,
            "eligible": self.eligible,
            "payload": self.payload,
            "errors": list(self.errors),
            "warnings": list(self.warnings),
        }


def _number(value: Any) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def _money(value: Any, markup_percent: float) -> float:
    amount = Decimal(str(_number(value))) * (
        Decimal("1") + Decimal(str(markup_percent)) / Decimal("100")
    )
    return float(amount.quantize(_MONEY, rounding=ROUND_HALF_UP))


def _aware(value: datetime | None) -> datetime | None:
    if value is None or value.tzinfo is not None:
        return value
    return value.replace(tzinfo=timezone.utc)


def _within_window(now: datetime, start: datetime | None, end: datetime | None) -> bool:
    start_value = _aware(start)
    end_value = _aware(end)
    return (start_value is None or now >= start_value) and (
        end_value is None or now <= end_value
    )


def _related_name(product: Any, field: str) -> str | None:
    value = getattr(getattr(product, field, None), "nome", None)
    value = str(value or "").strip()
    return value or None


def _image_url(raw: Any, public_base_url: str) -> str | None:
    value = str(raw or "").strip()
    if not value:
        return None

    parsed = urlparse(value)
    if parsed.scheme or parsed.netloc:
        return value if parsed.scheme.lower() == "https" and parsed.netloc else None

    absolute_url = urljoin(f"{public_base_url.rstrip('/')}/", value.lstrip("/"))
    parsed_absolute = urlparse(absolute_url)
    if parsed_absolute.scheme.lower() != "https" or not parsed_absolute.netloc:
        return None
    return absolute_url


def _channel_prices(
    product: Any, *, source: str, now: datetime
) -> tuple[Any, Any, bool]:
    if source == "ecommerce":
        base = getattr(product, "preco_ecommerce", None)
        if base is None:
            base = getattr(product, "preco_venda", None)
        promo = getattr(product, "preco_ecommerce_promo", None)
        promo_active = _within_window(
            now,
            getattr(product, "preco_ecommerce_promo_inicio", None),
            getattr(product, "preco_ecommerce_promo_fim", None),
        )
        return base, promo, promo_active

    base = getattr(product, "preco_venda", None)
    promo = getattr(product, "preco_promocional", None)
    promo_active = bool(getattr(product, "promocao_ativa", False)) and _within_window(
        now,
        getattr(product, "promocao_inicio", None),
        getattr(product, "promocao_fim", None),
    )
    return base, promo, promo_active


def _eligibility_errors(
    product: Any, *, source: str, name: str, barcode: str
) -> list[str]:
    errors: list[str] = []
    if not bool(getattr(product, "situacao", True)) or not bool(
        getattr(product, "ativo", True)
    ):
        errors.append("Produto inativo no CorePet.")
    if getattr(product, "deleted_at", None) is not None:
        errors.append("Produto excluido no CorePet.")
    if bool(getattr(product, "is_parent", False)) or not bool(
        getattr(product, "is_sellable", True)
    ):
        errors.append("Produto agrupador ou nao vendavel.")
    if str(getattr(product, "tipo", "produto") or "").strip().lower() == "servico":
        errors.append("Servicos nao pertencem ao catalogo de itens do iFood.")
    if source == "ecommerce" and not bool(
        getattr(product, "anunciar_ecommerce", False)
    ):
        errors.append("Produto nao esta marcado para anunciar no e-commerce.")
    if not name:
        errors.append("Nome do produto ausente.")
    if not barcode:
        errors.append("EAN ou codigo interno ausente.")
    return errors


def _promotion_price(
    *,
    promo_active: bool,
    promo_raw: Any,
    base_price: float,
    markup_percent: float,
) -> tuple[float | None, list[str]]:
    if not promo_active or _number(promo_raw) <= 0:
        return None, []

    candidate = _money(promo_raw, markup_percent)
    if candidate >= base_price:
        return None, ["Promocao ignorada: preco promocional nao e menor que o normal."]
    if candidate > base_price * 0.95:
        return None, ["Promocao ignorada: o iFood exige desconto superior a 5%."]
    return candidate, []


def build_catalog_item(
    product: Any,
    *,
    source: str = "ecommerce",
    markup_percent: float = 0,
    stock_safety: float = 0,
    public_base_url: str = "",
    now: datetime | None = None,
) -> IfoodCatalogItem:
    """Monta um item completo para POST, sem executar qualquer envio."""

    current_time = _aware(now) if now else datetime.now(timezone.utc)
    assert current_time is not None
    warnings: list[str] = []
    product_id = int(getattr(product, "id", 0) or 0)
    sku = str(getattr(product, "codigo", "") or "").strip()
    name = str(getattr(product, "nome", "") or "").strip()
    ean = str(
        getattr(product, "codigo_barras", None)
        or getattr(product, "gtin_ean", None)
        or ""
    ).strip()
    # O modulo Item aceita EAN ou codigo interno de balanca. O SKU evita
    # cadastro manual para itens fracionados que legitimamente nao possuem EAN.
    barcode = ean or sku

    errors = _eligibility_errors(product, source=source, name=name, barcode=barcode)
    if barcode and not ean:
        warnings.append(
            "Produto sem EAN; o SKU sera usado como codigo interno no iFood."
        )

    base_raw, promo_raw, promo_active = _channel_prices(
        product, source=source, now=current_time
    )
    base_price = _money(base_raw, markup_percent)
    if base_price <= 0:
        errors.append("Preco de venda deve ser maior que zero.")

    promo_price, promo_warnings = _promotion_price(
        promo_active=promo_active,
        promo_raw=promo_raw,
        base_price=base_price,
        markup_percent=markup_percent,
    )
    warnings.extend(promo_warnings)

    if errors:
        return IfoodCatalogItem(
            product_id=product_id,
            sku=sku,
            eligible=False,
            payload=None,
            errors=tuple(errors),
            warnings=tuple(warnings),
        )

    stock = max(0.0, _number(getattr(product, "estoque_atual", 0)) - stock_safety)
    description = str(
        getattr(product, "descricao_completa", None)
        or getattr(product, "descricao_curta", None)
        or ""
    ).strip()
    categorization = {
        "department": _related_name(product, "departamento"),
        "category": _related_name(product, "categoria"),
        "subCategory": str(getattr(product, "subcategoria", "") or "").strip() or None,
    }
    details = {
        "categorization": categorization,
        "brand": _related_name(product, "marca"),
        "unit": str(getattr(product, "unidade", "") or "").strip() or None,
        # O campo volume do CorePet representa cubagem logistica, nao o volume
        # comercial esperado pelo iFood; nao misturar os dois conceitos.
        "volume": None,
        "imageUrl": _image_url(
            getattr(product, "imagem_principal", None), public_base_url
        ),
        "description": description or None,
    }
    prices: dict[str, float | None] = {
        "price": base_price,
        # Enviar null tambem encerra eventual promocao anterior no iFood.
        "promotionPrice": promo_price,
    }
    payload = {
        "barcode": barcode,
        "name": name,
        "plu": sku or None,
        "active": True,
        "inventory": {"stock": round(stock, 3)},
        "details": details,
        "prices": prices,
        "channels": ["ifood-app"],
    }
    return IfoodCatalogItem(
        product_id=product_id,
        sku=sku,
        eligible=True,
        payload=payload,
        warnings=tuple(warnings),
    )


def build_catalog_preview(
    products: Iterable[Any],
    *,
    source: str,
    markup_percent: float,
    stock_safety: float,
    public_base_url: str,
    now: datetime | None = None,
) -> list[IfoodCatalogItem]:
    return [
        build_catalog_item(
            product,
            source=source,
            markup_percent=markup_percent,
            stock_safety=stock_safety,
            public_base_url=public_base_url,
            now=now,
        )
        for product in products
    ]
