"""Configuracao, diagnostico e catalogo da integracao iFood."""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from typing import Any, Literal
from types import SimpleNamespace
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy.orm import Session, joinedload

from app.auth.dependencies import get_current_user_and_tenant
from app.config import settings
from app.db import get_session
from app.ifood_integration_models import IfoodMerchantConfig
from app.integrations.ifood import (
    IfoodClient,
    IfoodClientError,
    build_catalog_preview,
)
from app.models import User
from app.produtos_catalogo_models import Produto
from app.produtos.schemas import ProdutoUpdate
from app.security import permissions_service
from app.integrations.ifood.management import (
    MARGIN_CONFIG_FIELDS,
    build_management_item,
    product_identifier,
)
from app.security.permissions_decorator import (
    require_permission,
    require_any_permission,
)

router = APIRouter(prefix="/integracoes/ifood", tags=["iFood"])


class IfoodCatalogSettings(BaseModel):
    default_markup_percent: float = Field(default=0, ge=-50, le=300)
    stock_safety: float = Field(default=0, ge=0, le=1000000)
    commission_merchant_percent: float | None = Field(
        default=None, ge=0, le=100, allow_inf_nan=False
    )
    commission_ifood_percent: float | None = Field(
        default=None, ge=0, le=100, allow_inf_nan=False
    )
    payment_fee_percent: float | None = Field(
        default=None, ge=0, le=100, allow_inf_nan=False
    )
    tax_percent: float | None = Field(default=None, ge=0, le=100, allow_inf_nan=False)
    additional_unit_cost: float | None = Field(
        default=None, ge=0, le=1000000, allow_inf_nan=False
    )
    target_margin_percent: float | None = Field(
        default=None, ge=0, le=99.99, allow_inf_nan=False
    )


class IfoodCatalogConfigPayload(IfoodCatalogSettings):
    # Esta superficie local nao permite ativar/vincular nem operar o provedor.
    model_config = ConfigDict(extra="forbid")


class IfoodConfigPayload(IfoodCatalogSettings):
    merchant_id: str | None = Field(default=None, max_length=36)
    active: bool = False
    catalog_source: Literal["ecommerce", "erp"] = "ecommerce"

    @field_validator("merchant_id")
    @classmethod
    def validate_merchant_id(cls, value: str | None) -> str | None:
        normalized = str(value or "").strip()
        if not normalized:
            return None
        try:
            return str(UUID(normalized))
        except ValueError as exc:
            raise ValueError("Informe um Merchant ID valido do iFood.") from exc


class IfoodSyncPayload(BaseModel):
    operation: Literal["create", "update"] = "update"
    product_ids: list[int] | None = Field(default=None, max_length=500)
    dry_run: bool = True
    confirm_send: bool = False
    reset_catalog: bool = False
    confirm_reset: bool = False


class IfoodPreviewProduto(ProdutoUpdate):
    id: int | None = Field(default=None, gt=0)
    imagem_principal: str | None = Field(default=None, max_length=2048)
    ativo: bool | None = None
    situacao: bool | None = None


class IfoodProductPreviewPayload(BaseModel):
    produto: IfoodPreviewProduto
    modalidade: Literal["MERCHANT", "IFOOD"] = "MERCHANT"


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _require_admin(user: User) -> None:
    if not any(
        bool(getattr(user, flag, False))
        for flag in ("is_admin", "is_superadmin", "is_system_admin")
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Somente um administrador pode alterar a integracao do iFood.",
        )


def _credentials_configured() -> bool:
    return bool(
        str(settings.IFOOD_CLIENT_ID or "").strip()
        and str(settings.IFOOD_CLIENT_SECRET or "").strip()
    )


def _can_configure_catalog(db: Session, user: User, tenant_id: UUID) -> bool:
    try:
        permissions_service.check_permission(
            db, user.id, "configuracoes.editar", tenant_id, current_user=user
        )
    except HTTPException as exc:
        if exc.status_code == status.HTTP_403_FORBIDDEN:
            return False
        raise
    return True


def _provider_http_status(exc: IfoodClientError) -> int:
    # Nunca devolver 401/403 do provedor: o frontend poderia interpretar isso
    # como expiracao da sessao do usuario CorePet. Apenas o 429 preserva sentido.
    if exc.status_code == status.HTTP_429_TOO_MANY_REQUESTS:
        return status.HTTP_429_TOO_MANY_REQUESTS
    return status.HTTP_502_BAD_GATEWAY


def _get_config(
    db: Session, tenant_id: UUID, *, create: bool = False
) -> IfoodMerchantConfig | None:
    config = (
        db.query(IfoodMerchantConfig)
        .filter(IfoodMerchantConfig.tenant_id == tenant_id)
        .first()
    )
    if config is None and create:
        config = IfoodMerchantConfig(
            tenant_id=tenant_id,
            active=False,
            catalog_source="ecommerce",
            default_markup_percent=0,
            stock_safety=0,
            status="draft",
        )
        db.add(config)
        db.flush()
    return config


def _config_view(config: IfoodMerchantConfig | None) -> dict[str, Any]:
    return {
        "merchant_id": config.merchant_id if config else None,
        "active": bool(config.active) if config else False,
        "catalog_source": config.catalog_source if config else "ecommerce",
        "default_markup_percent": config.default_markup_percent if config else 0,
        "stock_safety": config.stock_safety if config else 0,
        "status": config.status if config else "draft",
        "last_connection_check_at": (
            config.last_connection_check_at if config else None
        ),
        "last_catalog_sync_at": config.last_catalog_sync_at if config else None,
        "last_orders_poll_at": config.last_orders_poll_at if config else None,
        "last_orders_error": config.last_orders_error if config else None,
        "last_error": config.last_error if config else None,
        **{field: getattr(config, field, None) for field in MARGIN_CONFIG_FIELDS},
    }


def _products(
    db: Session, tenant_id: UUID, product_ids: list[int] | None = None
) -> list[Produto]:
    query = (
        db.query(Produto)
        .options(
            joinedload(Produto.categoria),
            joinedload(Produto.marca),
            joinedload(Produto.departamento),
        )
        .filter(Produto.tenant_id == tenant_id, Produto.deleted_at.is_(None))
    )
    if product_ids is not None:
        if not product_ids:
            return []
        query = query.filter(Produto.id.in_(product_ids))
    return query.order_by(Produto.id.asc()).all()


def _catalog(
    db: Session,
    tenant_id: UUID,
    config: IfoodMerchantConfig | None,
    product_ids: list[int] | None = None,
):
    products = _products(db, tenant_id, product_ids)
    stocks = _available_stocks(db, tenant_id, products)
    for product in products:
        product.ifood_available_stock = stocks.get(product.id)
    return build_catalog_preview(
        products,
        source="ifood",
        markup_percent=float(config.default_markup_percent or 0) if config else 0,
        stock_safety=float(config.stock_safety or 0) if config else 0,
        public_base_url=settings.COREPET_FRONTEND_URL,
    )


def _available_stocks(
    db: Session, tenant_id: UUID, products: list[Produto]
) -> dict[int, float | None]:
    from app.estoque_reserva_service import EstoqueReservaService
    from app.services.kit_estoque_service import KitEstoqueService

    reserves = EstoqueReservaService.mapa_reservas_ativas_por_produto(db, tenant_id)
    virtual_stocks = KitEstoqueService.calcular_estoques_virtuais_em_lote(
        db, products, tenant_id=tenant_id, reservas_por_produto=reserves
    )
    result = {}
    for product in products:
        if (
            product.tipo_produto in ("KIT", "VARIACAO")
            and product.tipo_kit == "VIRTUAL"
        ):
            result[product.id] = float(virtual_stocks.get(product.id, 0))
        else:
            result[product.id] = max(
                0.0,
                float(product.estoque_atual or 0) - float(reserves.get(product.id, 0)),
            )
    return result


def _management_items(
    db: Session, tenant_id: UUID, config: IfoodMerchantConfig | None
) -> list[dict]:
    from app.services.kit_custo_service import KitCustoService

    products = _products(db, tenant_id)
    stocks = _available_stocks(db, tenant_id, products)
    kit_costs = KitCustoService.calcular_custos_kits_em_lote(db, products)
    identifiers = Counter(
        product_identifier(product).casefold()
        for product in products
        if product.anunciar_ifood
    )
    safety = float(config.stock_safety or 0) if config else 0
    items = []
    for product in products:
        snapshot = SimpleNamespace(
            **{
                column.key: getattr(product, column.key)
                for column in Produto.__table__.columns
            }
        )
        if product.id in kit_costs:
            snapshot.preco_custo = float(kit_costs[product.id])
        stock = stocks.get(product.id)
        items.append(
            build_management_item(
                snapshot,
                config,
                available_stock=max(0, stock - safety) if stock is not None else None,
                duplicate_identifier=identifiers[product_identifier(product).casefold()]
                > 1,
            )
        )
    return items


def _catalog_response(
    items: list[Any], *, limit: int, only_issues: bool = False
) -> dict[str, Any]:
    eligible = [item for item in items if item.eligible]
    rejected = [item for item in items if not item.eligible]
    selected = rejected if only_issues else items
    error_counts = Counter(error for item in rejected for error in item.errors)
    warning_counts = Counter(warning for item in items for warning in item.warnings)
    return {
        "summary": {
            "total_scanned": len(items),
            "eligible": len(eligible),
            "rejected": len(rejected),
        },
        "issues": [
            {"message": message, "count": count}
            for message, count in error_counts.most_common()
        ],
        "warnings": [
            {"message": message, "count": count}
            for message, count in warning_counts.most_common()
        ],
        "items": [item.as_dict() for item in selected[:limit]],
        "has_more": len(selected) > limit,
    }


def _client() -> IfoodClient:
    return IfoodClient(
        client_id=settings.IFOOD_CLIENT_ID,
        client_secret=settings.IFOOD_CLIENT_SECRET,
        base_url=settings.IFOOD_API_BASE_URL,
        timeout_seconds=settings.IFOOD_REQUEST_TIMEOUT_SECONDS,
    )


def _merchant_entries(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if isinstance(payload, dict):
        for key in ("merchants", "data"):
            if isinstance(payload.get(key), list):
                return [item for item in payload[key] if isinstance(item, dict)]
    return []


@router.get("/status")
def get_ifood_status(
    auth=Depends(get_current_user_and_tenant),
    db: Session = Depends(get_session),
):
    _user, tenant_id = auth
    config = _get_config(db, tenant_id)
    items = _catalog(db, tenant_id, config)
    eligible = sum(1 for item in items if item.eligible)
    return {
        "configured": bool(config and config.merchant_id),
        "credentials_configured": _credentials_configured(),
        "catalog_write_enabled": bool(settings.IFOOD_CATALOG_WRITE_ENABLED),
        "order_operations_enabled": bool(settings.IFOOD_ORDER_OPERATIONS_ENABLED),
        "order_polling_enabled": bool(settings.IFOOD_ORDER_POLLING_ENABLED),
        "config": _config_view(config),
        "catalog": {
            "total_scanned": len(items),
            "eligible": eligible,
            "rejected": len(items) - eligible,
        },
    }


@router.put("/config")
def save_ifood_config(
    body: IfoodConfigPayload,
    auth=Depends(get_current_user_and_tenant),
    db: Session = Depends(get_session),
):
    current_user, tenant_id = auth
    _require_admin(current_user)
    config = _get_config(db, tenant_id, create=True)
    assert config is not None
    active = body.active if "active" in body.model_fields_set else config.active
    merchant_id = (
        body.merchant_id
        if "merchant_id" in body.model_fields_set
        else config.merchant_id
    )
    if active and not merchant_id:
        raise HTTPException(
            status_code=422,
            detail="Informe o Merchant ID antes de ativar a integracao.",
        )
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(config, field, value)
    if "merchant_id" in body.model_fields_set or "active" in body.model_fields_set:
        config.status = "ready" if config.merchant_id else "draft"
        config.last_error = None
    db.commit()
    db.refresh(config)
    return {"config": _config_view(config)}


@router.get("/catalogo/preview")
def preview_ifood_catalog(
    limit: int = Query(default=50, ge=1, le=200),
    only_issues: bool = Query(default=False),
    auth=Depends(get_current_user_and_tenant),
    db: Session = Depends(get_session),
):
    _user, tenant_id = auth
    config = _get_config(db, tenant_id)
    return _catalog_response(
        _catalog(db, tenant_id, config), limit=limit, only_issues=only_issues
    )


@router.put("/catalogo/configuracao")
@require_permission("configuracoes.editar")
def save_ifood_catalog_config(
    body: IfoodCatalogConfigPayload,
    user_and_tenant=Depends(get_current_user_and_tenant),
    db: Session = Depends(get_session),
):
    """Premissas locais da loja; nao altera vinculo, ativacao ou flags externas."""
    _, tenant_id = user_and_tenant
    config = _get_config(db, tenant_id, create=True)
    assert config is not None
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(config, field, value)
    db.commit()
    db.refresh(config)
    return {"config": _config_view(config)}


@router.get("/catalogo/gestao")
@require_permission("produtos.visualizar")
def get_ifood_management_catalog(
    q: str = Query(default="", max_length=200),
    filtro: Literal[
        "todos",
        "selecionados",
        "pendencias",
        "sem_estoque",
        "preco_especifico",
        "nao_selecionados",
    ] = "todos",
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    user_and_tenant=Depends(get_current_user_and_tenant),
    db: Session = Depends(get_session),
):
    current_user, tenant_id = user_and_tenant
    config = _get_config(db, tenant_id)
    items = _management_items(db, tenant_id, config)

    def has_issues(item):
        return item["selected"] and any(
            p["kind"] != "recomendacao" for p in item["pending"]
        )

    summary = {
        "total": len(items),
        "selected": sum(item["selected"] for item in items),
        "issues": sum(has_issues(item) for item in items),
        "out_of_stock": sum(
            item["available_stock"] is not None and item["available_stock"] <= 0
            for item in items
        ),
        "specific_price": sum(item["price_source"] == "especifico" for item in items),
    }
    filters = {
        "todos": lambda item: True,
        "selecionados": lambda item: item["selected"],
        "pendencias": has_issues,
        "sem_estoque": lambda item: (
            item["available_stock"] is not None and item["available_stock"] <= 0
        ),
        "preco_especifico": lambda item: item["price_source"] == "especifico",
        "nao_selecionados": lambda item: not item["selected"],
    }
    terms = q.casefold().split()
    filtered = [
        item
        for item in items
        if filters[filtro](item)
        and all(
            term in f"{item['name']} {item['sku']} {item['identifier']}".casefold()
            for term in terms
        )
    ]
    return {
        "items": filtered[offset : offset + limit],
        "total": len(filtered),
        "summary": summary,
        "config": _config_view(config),
        "has_more": offset + limit < len(filtered),
        "can_configure": _can_configure_catalog(db, current_user, tenant_id),
    }


@router.post("/catalogo/produto/preview")
@require_any_permission(("produtos.criar", "produtos.editar"))
def preview_ifood_product(
    body: IfoodProductPreviewPayload,
    user_and_tenant=Depends(get_current_user_and_tenant),
    db: Session = Depends(get_session),
):
    _, tenant_id = user_and_tenant
    config = _get_config(db, tenant_id)
    product = None
    if body.produto.id:
        product = (
            db.query(Produto)
            .filter(
                Produto.tenant_id == tenant_id,
                Produto.id == body.produto.id,
                Produto.deleted_at.is_(None),
            )
            .first()
        )
        if product is None:
            raise HTTPException(
                status_code=404, detail="Produto nao encontrado nesta loja."
            )
    snapshot = SimpleNamespace(
        **(
            {
                column.key: getattr(product, column.key)
                for column in Produto.__table__.columns
            }
            if product
            else {
                "ativo": True,
                "situacao": True,
                "is_sellable": True,
                "is_parent": False,
                "tipo_produto": "SIMPLES",
                "tipo": "produto",
                "unidade": "UN",
            }
        )
    )
    changes = body.produto.model_dump(exclude_unset=True)
    for field, value in changes.items():
        setattr(snapshot, field, value)
    stock = (
        _available_stocks(db, tenant_id, [product]).get(product.id) if product else None
    )
    composition_changed = False
    if product:
        composition_changed = (
            snapshot.tipo_produto != product.tipo_produto
            or snapshot.tipo_kit != product.tipo_kit
        )
        if "composicao_kit" in changes:
            from app.produtos_models import ProdutoKitComponente

            persisted = (
                db.query(ProdutoKitComponente)
                .filter(
                    ProdutoKitComponente.tenant_id == tenant_id,
                    ProdutoKitComponente.kit_id == product.id,
                )
                .all()
            )
            before = sorted(
                (row.produto_componente_id, float(row.quantidade), bool(row.opcional))
                for row in persisted
            )
            after = sorted(
                (
                    row["produto_componente_id"],
                    float(row["quantidade"]),
                    bool(row.get("opcional", False)),
                )
                for row in changes["composicao_kit"] or []
            )
            composition_changed = composition_changed or before != after
        if composition_changed:
            stock = None
    if getattr(snapshot, "tipo_produto", None) in ("KIT", "VARIACAO") and getattr(
        snapshot, "tipo_kit", None
    ):
        if not product or composition_changed:
            snapshot.preco_custo = None
        else:
            from app.services.kit_custo_service import KitCustoService

            snapshot.preco_custo = float(
                KitCustoService.calcular_custo_kit(product.id, db)
            )
    identifier = product_identifier(snapshot)
    duplicate = any(
        p.id != getattr(snapshot, "id", None)
        and p.anunciar_ifood
        and product_identifier(p).casefold() == identifier.casefold()
        for p in _products(db, tenant_id)
    )
    safety = float(config.stock_safety or 0) if config else 0
    return build_management_item(
        snapshot,
        config,
        available_stock=max(0, stock - safety) if stock is not None else None,
        duplicate_identifier=duplicate,
    )


@router.post("/testar-conexao")
def test_ifood_connection(
    auth=Depends(get_current_user_and_tenant),
    db: Session = Depends(get_session),
):
    current_user, tenant_id = auth
    _require_admin(current_user)
    config = _get_config(db, tenant_id, create=True)
    assert config is not None
    if not config.merchant_id:
        raise HTTPException(status_code=422, detail="Informe primeiro o Merchant ID.")
    try:
        with _client() as client:
            response = client.list_merchants()
        merchants = _merchant_entries(response)
        allowed_ids = {
            str(item.get("id") or item.get("merchantId") or "").strip()
            for item in merchants
        }
        if config.merchant_id not in allowed_ids:
            raise IfoodClientError(
                "O Merchant ID informado nao esta vinculado ao aplicativo CorePet."
            )
        config.status = "connected"
        config.last_connection_check_at = _utcnow()
        config.last_error = None
        db.commit()
        return {
            "connected": True,
            "merchant_id": config.merchant_id,
            "accessible_merchants": len(merchants),
        }
    except IfoodClientError as exc:
        config.status = "error"
        config.last_connection_check_at = _utcnow()
        config.last_error = str(exc)
        db.commit()
        raise HTTPException(
            status_code=_provider_http_status(exc),
            detail=str(exc),
        ) from exc


@router.post("/catalogo/sincronizar")
def sync_ifood_catalog(
    body: IfoodSyncPayload,
    auth=Depends(get_current_user_and_tenant),
    db: Session = Depends(get_session),
):
    current_user, tenant_id = auth
    _require_admin(current_user)
    config = _get_config(db, tenant_id)
    items = _catalog(db, tenant_id, config, body.product_ids)
    eligible = [item for item in items if item.eligible and item.payload]
    preview = _catalog_response(items, limit=200)
    if body.dry_run:
        return {
            "dry_run": True,
            "operation": body.operation,
            "reset_catalog": body.reset_catalog,
            **preview,
        }

    if body.reset_catalog and body.operation != "create":
        raise HTTPException(
            status_code=422,
            detail="Reset de catalogo so pode ser usado na criacao via POST.",
        )
    if body.reset_catalog and not body.confirm_reset:
        raise HTTPException(
            status_code=422,
            detail=(
                "Confirme o reset do catalogo de teste. Produtos omitidos serao "
                "desativados no iFood."
            ),
        )

    if not settings.IFOOD_CATALOG_WRITE_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Envios reais estao bloqueados ate concluir a homologacao do iFood.",
        )
    if not body.confirm_send:
        raise HTTPException(
            status_code=422,
            detail="Confirme explicitamente o envio real do catalogo.",
        )
    if not config or not config.active or not config.merchant_id:
        raise HTTPException(
            status_code=409,
            detail="Ative a integracao e informe o Merchant ID antes de enviar.",
        )
    if not _credentials_configured():
        raise HTTPException(
            status_code=503,
            detail="Credenciais do aplicativo iFood nao configuradas no servidor.",
        )
    if len(eligible) > 200:
        raise HTTPException(
            status_code=422,
            detail="Selecione no maximo 200 produtos por envio para respeitar a volumetria do iFood.",
        )
    payloads = [item.payload for item in eligible if item.payload]
    if not payloads:
        raise HTTPException(
            status_code=422,
            detail="Nenhum produto elegivel foi selecionado para o envio.",
        )
    if body.operation == "update":
        payloads = [
            {
                "barcode": payload["barcode"],
                "name": payload["name"],
                "inventory": payload["inventory"],
                "details": payload["details"],
                "prices": payload["prices"],
                "channels": payload["channels"],
            }
            for payload in payloads
        ]
    try:
        with _client() as client:
            result = client.ingest_items(
                config.merchant_id,
                payloads,
                method="POST" if body.operation == "create" else "PATCH",
                reset_catalog=body.reset_catalog,
            )
        config.status = "connected"
        config.last_catalog_sync_at = _utcnow()
        config.last_error = None
        db.commit()
        return {
            "dry_run": False,
            "operation": body.operation,
            "reset_catalog": body.reset_catalog,
            "sent": len(payloads),
            "rejected": len(items) - len(eligible),
            **result,
        }
    except IfoodClientError as exc:
        config.status = "error"
        config.last_error = str(exc)
        db.commit()
        raise HTTPException(
            status_code=_provider_http_status(exc),
            detail=str(exc),
        ) from exc
