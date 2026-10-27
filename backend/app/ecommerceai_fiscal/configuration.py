"""Configuração pública da trilha fiscal por tenant; nunca inclui credenciais/PII."""

from urllib.parse import urlparse
from fastapi.encoders import jsonable_encoder
from app.config import settings
from app.ecommerceai_fiscal.models import FiscalAccount, FiscalSkuMapping
from app.ecommerceai_fiscal import payload
from app.ecommerceai_fiscal.service import digest, aware
from app.intnfe.models import IntNFeConnection
from app.intnfe.repository import get_tenant
from app.intnfe.presentation import normalize_cnpj
from app.produtos_models import Produto


PUBLIC_FIELDS = (
    "id",
    "channel",
    "seller_id",
    "marketplace_id",
    "emitter_cnpj",
    "active",
    "auto_issue_enabled",
    "upload_enabled",
    "discount_policy",
    "activated_at",
)
PRODUCT_FIELDS = (
    "id",
    "codigo",
    "codigo_barras",
    "nome",
    "tipo_produto",
    "unidade",
    "ativo",
    "situacao",
    "deleted_at",
)


def public_account(row):
    result = {field: getattr(row, field) for field in PUBLIC_FIELDS}
    result["activated_at"] = aware(result["activated_at"])
    return result


def fiscal_context(db, tenant_id):
    tenant = get_tenant(db, tenant_id)
    profile, pending = payload.local_profile(db, tenant_id)
    columns = ("cnpj", "emission_enabled", "emission_environment", "nfe_series")
    connection = (
        db.query(*(getattr(IntNFeConnection, key) for key in columns))
        .filter(IntNFeConnection.tenant_id == tenant_id)
        .first()
    )
    return {
        "tenant_cnpj": normalize_cnpj(tenant.cnpj),
        "profile": profile,
        "pending": pending,
        "connection": dict(zip(columns, connection)) if connection else None,
    }


def account_revision(db, row, *, context=None):
    mappings = (
        db.query(FiscalSkuMapping)
        .filter(
            FiscalSkuMapping.tenant_id == row.tenant_id,
            FiscalSkuMapping.account_id == row.id,
        )
        .order_by(FiscalSkuMapping.seller_sku, FiscalSkuMapping.id)
        .all()
    )
    ids = {item.product_id for item in mappings}
    products = (
        {
            p.id: p
            for p in db.query(Produto)
            .filter(Produto.tenant_id == row.tenant_id, Produto.id.in_(ids))
            .all()
        }
        if ids
        else {}
    )
    fiscal_by_product = {}
    for product_id, product in products.items():
        fiscal_by_product[product_id] = {
            "product": {key: getattr(product, key) for key in PRODUCT_FIELDS},
            "fiscal": payload._resolver_fiscal_item_nfe(
                db,
                payload.FiscalTenantContext(row.tenant_id),
                payload.FiscalProductContext(product),
            ),
        }
    revision = {
        "account": public_account(row),
        "version": row.configuration_version,
        "mappings": [
            {
                "id": m.id,
                "seller_sku": m.seller_sku,
                "product_id": m.product_id,
                "active": m.active,
            }
            for m in mappings
        ],
        "mapped_fiscal": fiscal_by_product,
        "issuer_fiscal": context
        if context is not None
        else fiscal_context(db, row.tenant_id),
    }
    return digest(jsonable_encoder(revision))


def settings_url():
    base = str(settings.COREPET_FRONTEND_URL or "").rstrip("/")
    try:
        parsed = urlparse(base)
        parsed.port
    except ValueError:
        return None
    valid = parsed.scheme == "https" or (
        parsed.scheme == "http" and parsed.hostname in {"localhost", "127.0.0.1"}
    )
    if (
        not valid
        or not parsed.netloc
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
        or parsed.path.rstrip("/").endswith("/api")
    ):
        return None
    return base + "/configuracoes/integracoes"


def configuration_accounts(db, tenant_id):
    rows = (
        db.query(FiscalAccount)
        .filter(FiscalAccount.tenant_id == tenant_id)
        .order_by(FiscalAccount.id)
        .all()
    )
    context = fiscal_context(db, tenant_id) if rows else None
    accounts = [
        dict(
            public_account(row),
            configuration_revision=account_revision(db, row, context=context),
        )
        for row in rows
    ]
    return {
        "schema_version": "1.1",
        "configuration_revision": digest(
            {"tenant_id": str(tenant_id), "accounts": jsonable_encoder(accounts)}
        ),
        "corepet_settings_url": settings_url(),
        "accounts": accounts,
    }
