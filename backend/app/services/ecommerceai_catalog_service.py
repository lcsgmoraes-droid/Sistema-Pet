"""Read-only marketplace catalog; unsupported stock policies fail closed."""

from __future__ import annotations

from collections import defaultdict
from contextlib import contextmanager
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any
from urllib.parse import urljoin, urlparse

from sqlalchemy import or_, text
from sqlalchemy.orm import Session, selectinload

from app.empresa_grupo_models import EmpresaGrupoEstoqueCompartilhado
from app.empresa_grupo_sql import empresa_id_igual
from app.estoque_reserva_service import EstoqueReservaService
from app.models import Tenant
from app.produtos.tipos import tipo_controla_estoque
from app.produtos_catalogo_models import Produto
from app.services.produto_sku_service import chaves_sku_produto, normalizar_sku


@contextmanager
def marketplace_catalog_read_session(db: Session):
    """Give each PostgreSQL page one read-only snapshot, including authorization.

    Use a separate connection so an existing request transaction/identity map
    cannot mix older product rows with newer reservations. Isolation is scoped
    to this connection and reset by SQLAlchemy when it returns to the pool.
    SQLite keeps the injected session used by isolated contract tests.
    """
    bind = db.get_bind()
    if bind.dialect.name != "postgresql":
        yield db
        return

    with bind.engine.connect().execution_options(
        isolation_level="REPEATABLE READ"
    ) as connection:
        with Session(
            bind=connection, autoflush=False, expire_on_commit=False
        ) as snapshot:
            snapshot.execute(text("SET TRANSACTION READ ONLY"))
            yield snapshot


def _decimal(value: Any) -> Decimal | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None
    return result if result.is_finite() else None


def _decimal_text(value: Decimal | None) -> str | None:
    return format(value, "f") if value is not None else None


def _iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    # Legacy product timestamps are stored as naive UTC.
    aware = value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    return aware.astimezone(timezone.utc).isoformat()


class EcommerceAICatalogService:
    """Projects facts without updating products, reservations or connections."""

    def __init__(self, db: Session, *, tenant_id, public_api_url: str):
        self.db = db
        self.tenant_id = tenant_id
        self.public_api_url = public_api_url.rstrip("/") + "/"

    def _reservations(self) -> tuple[dict[int, Decimal], set[int], str | None]:
        # The central resolver accepts SKU aliases and chooses the first match.
        # Validate its inputs before claiming an unambiguous stock snapshot.
        items = EstoqueReservaService._itens_reservados_ativos(self.db, self.tenant_id)
        if not items:
            return {}, set(), None
        identities = (
            self.db.query(
                Produto.id,
                Produto.codigo,
                Produto.codigo_barras,
                Produto.codigos_barras_alternativos,
                Produto.tipo_produto,
                Produto.tipo_kit,
                Produto.is_parent,
                Produto.deleted_at,
            )
            .filter(
                Produto.tenant_id == self.tenant_id,
            )
            .all()
        )
        candidates: dict[str, dict[int, Any]] = defaultdict(dict)
        identities_by_id = {product.id: product for product in identities}
        for product in identities:
            for alias in chaves_sku_produto(product):
                candidates[normalizar_sku(alias)][product.id] = product
        reservations: dict[int, Decimal] = defaultdict(Decimal)
        blocked_ids: set[int] = set()
        virtual_kit_ids: set[int] = set()
        for item in items:
            matches = candidates.get(normalizar_sku(item.sku), {})
            quantity = _decimal(item.quantidade)
            if len(matches) != 1 or quantity is None or quantity <= 0:
                return {}, set(), "reservation_identity_unverified"
            product = next(iter(matches.values()))
            if (
                product.deleted_at is not None
                or product.tipo_produto == "PAI"
                or product.is_parent
            ):
                return {}, set(), "reservation_identity_unverified"
            if product.tipo_produto == "KIT" or product.tipo_kit:
                blocked_ids.add(product.id)
                if EstoqueReservaService._usa_composicao_virtual(product):
                    virtual_kit_ids.add(product.id)
                    continue
                # The central policy reserves physical kits on their own stock.
                # Their catalog stock remains unsupported; unrelated products do not.
            reservations[product.id] += quantity

        if virtual_kit_ids:
            compositions = EstoqueReservaService._componentes_por_kit(
                self.db, sorted(virtual_kit_ids)
            )
            for kit_id in virtual_kit_ids:
                components = compositions.get(kit_id, [])
                if not components:
                    return {}, set(), "reservation_composition_unverified"
                for component in components:
                    product = identities_by_id.get(component.produto_componente_id)
                    quantity = _decimal(component.quantidade)
                    if (
                        str(component.tenant_id) != str(self.tenant_id)
                        or product is None
                        or product.deleted_at is not None
                        or product.is_parent
                        or product.tipo_produto not in {"SIMPLES", "VARIACAO"}
                        or product.tipo_kit
                        or quantity is None
                        or quantity <= 0
                    ):
                        # Unknown or nested composition may affect products we
                        # cannot identify. Never scope this uncertainty narrowly.
                        return {}, set(), "reservation_composition_unverified"
                    # Do not claim kit-derived available stock in this first slice.
                    # Known components are unavailable; unrelated simple stock is safe.
                    blocked_ids.add(product.id)
        # Aggregate the exact items and identities validated above. Calling the
        # central map again would reread reservations and resolve aliases again.
        # Query/database failures intentionally propagate; no empty-map fallback.
        return dict(reservations), blocked_ids, None

    def _media(self, product: Produto) -> tuple[list[dict[str, str]], list[str]]:
        images = sorted(
            (
                item
                for item in product.imagens
                if str(item.tenant_id) == str(product.tenant_id)
            ),
            key=lambda item: (
                not bool(item.e_principal),
                item.ordem or 0,
                item.id or 0,
            ),
        )
        urls = [product.imagem_principal, *(item.url for item in images)]
        result = []
        seen = set()
        warnings = []
        for value in urls:
            raw = str(value or "").strip()
            if not raw:
                continue
            # Only known local upload paths are resolved against the public API.
            url = (
                urljoin(self.public_api_url, raw)
                if raw.startswith("/uploads/")
                else raw
            )
            try:
                parsed = urlparse(url)
            except ValueError:
                warnings.append("image_url_unavailable")
                continue
            if (
                parsed.scheme not in {"https", "http"}
                or not parsed.netloc
                or parsed.username
            ):
                warnings.append("image_url_unavailable")
                continue
            if url not in seen:
                result.append({"url": url, "type": "image"})
                seen.add(url)
        return result, warnings

    def _product(
        self,
        product: Produto,
        *,
        channel_stock: bool,
        shared_ids: set[int],
        reservations: dict[int, Decimal],
        reservation_reason: str | None,
    ) -> dict[str, Any]:
        product_type = str(product.tipo_produto or "").upper()
        active = bool(product.ativo and product.situacao and product.deleted_at is None)
        sellable = bool(
            active
            and product.is_sellable
            and not product.is_parent
            and product_type in {"SIMPLES", "VARIACAO", "KIT"}
            and tipo_controla_estoque(product.tipo)
        )
        complex_product = product_type == "KIT" or bool(product.tipo_kit)
        warnings = []
        if complex_product:
            unsupported = "kit_policy_unsupported"
        elif product_type not in {"SIMPLES", "VARIACAO"} or product.is_parent:
            unsupported = "product_type_unsupported"
        elif not tipo_controla_estoque(product.tipo):
            unsupported = "service_has_no_stock"
        elif product.e_granel:
            unsupported = "bulk_policy_unsupported"
        else:
            unsupported = None

        amount = _decimal(product.preco_custo)
        cost_reason = unsupported or (
            None if amount is not None and amount > 0 else "cost_not_informed"
        )
        # Cadastro defaults to zero: zero is not evidence of a known free cost.
        cost = {
            "amount": None if cost_reason else _decimal_text(amount),
            "currency": "BRL",
            "status": "unavailable" if cost_reason else "ready",
            "reason": cost_reason,
        }
        physical = _decimal(product.estoque_atual)
        reserved = _decimal(reservations.get(product.id, 0))
        stock_reason = unsupported
        if stock_reason is None and product.id in shared_ids:
            stock_reason = "shared_stock_unsupported"
        if stock_reason is None and channel_stock:
            stock_reason = "channel_stock_unsupported"
        stock_reason = stock_reason or reservation_reason
        if stock_reason is None and (
            physical is None or reserved is None or reserved < 0
        ):
            stock_reason = "stock_value_unavailable"
        stock = {
            "physical": None,
            "reserved": None,
            "available": None,
            "status": "unavailable" if stock_reason else "ready",
            "reason": stock_reason,
            "owner_tenant_id": str(product.tenant_id),
        }
        if stock_reason is None:
            # Same standard-product policy as the operational CorePet listing.
            # Validity blocks already reflected in estoque_atual are not subtracted again.
            stock.update(
                physical=_decimal_text(physical),
                reserved=_decimal_text(reserved),
                available=_decimal_text(max(physical - reserved, Decimal("0"))),
            )
        warnings.extend(reason for reason in (cost_reason, stock_reason) if reason)
        if not sellable:
            warnings.append("product_not_sellable")
        media, media_warnings = self._media(product)
        warnings.extend(media_warnings)
        return {
            "corepet_id": str(product.id),
            "sku": str(product.codigo or ""),
            "name": str(product.nome or ""),
            "description": product.descricao_completa
            or product.descricao_curta
            or None,
            "barcode": product.codigo_barras or None,
            "unit": product.unidade or None,
            "product_type": product_type,
            "active": active,
            "sellable": sellable,
            "cost": cost,
            "stock": stock,
            "updated_at": _iso(product.updated_at),
            "media": media,
            "warnings": list(dict.fromkeys(warnings)),
        }

    def list_products(
        self, *, page: int = 1, page_size: int = 100, q: str | None = None
    ) -> dict[str, Any]:
        if page < 1 or not 1 <= page_size <= 200:
            raise ValueError("Invalid catalog pagination")
        with self.db.no_autoflush:
            tenant = (
                self.db.query(Tenant).filter(Tenant.id == str(self.tenant_id)).one()
            )
            query = self.db.query(Produto).filter(
                Produto.tenant_id == self.tenant_id,
                Produto.deleted_at.is_(None),
            )
            search = str(q or "").strip()
            if search:
                pattern = (
                    "%"
                    + search.replace("\\", "\\\\")
                    .replace("%", "\\%")
                    .replace("_", "\\_")
                    + "%"
                )
                query = query.filter(
                    or_(
                        Produto.codigo.ilike(pattern, escape="\\"),
                        Produto.nome.ilike(pattern, escape="\\"),
                        Produto.codigo_barras.ilike(pattern, escape="\\"),
                    )
                )
            total = query.count()
            products = (
                query.options(selectinload(Produto.imagens))
                .order_by(Produto.id)
                .offset((page - 1) * page_size)
                .limit(page_size)
                .all()
            )
            product_ids = [product.id for product in products]
            shared_ids = (
                {
                    row[0]
                    for row in self.db.query(
                        EmpresaGrupoEstoqueCompartilhado.produto_origem_id
                    )
                    .filter(
                        empresa_id_igual(
                            EmpresaGrupoEstoqueCompartilhado.empresa_origem_id,
                            self.tenant_id,
                        ),
                        EmpresaGrupoEstoqueCompartilhado.produto_origem_id.in_(
                            product_ids
                        ),
                        EmpresaGrupoEstoqueCompartilhado.status == "ativo",
                    )
                    .all()
                }
                if product_ids
                else set()
            )
            reservations, reservation_blocked_ids, reservation_reason = (
                self._reservations() if products else ({}, set(), None)
            )
            projected = [
                self._product(
                    product,
                    channel_stock=bool(tenant.ecommerce_usar_estoque_canal),
                    shared_ids=shared_ids,
                    reservations=reservations,
                    reservation_reason=reservation_reason
                    or (
                        "reservation_composition_unsupported"
                        if product.id in reservation_blocked_ids
                        else None
                    ),
                )
                for product in products
            ]
        return {
            "schema_version": "corepet.catalog.v1",
            "tenant_id": str(self.tenant_id),
            "generated_at": _iso(datetime.now(timezone.utc)),
            "page": page,
            "page_size": page_size,
            "total": total,
            "has_next": page * page_size < total,
            "products": projected,
        }
