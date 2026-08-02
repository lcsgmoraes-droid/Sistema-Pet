"""Schemas e helpers compartilhados do checkout ecommerce."""

from uuid import UUID
from datetime import datetime, timedelta
import hashlib
import json
import os
import secrets
import unicodedata

from fastapi import Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.models import ConfiguracaoEntrega, Tenant, User
from app.pedido_models import Pedido, PedidoItem
from app.routes.ecommerce_auth import (
    _activate_user_tenant_context,
    _get_current_ecommerce_user,
)
from app.services.ecommerce_payment_config import get_active_mercado_pago_runtime_config
from app.services.sales_channel import resolve_checkout_sales_channel
from app.tenancy.context import (
    clear_current_tenant,
    get_current_tenant,
    set_current_tenant,
)


# Mantido por compatibilidade com imports antigos; carrinhos nao expiram mais.
RESERVA_EXPIRACAO_CARRINHO_MINUTOS = 30
RESERVA_EXPIRACAO_PENDENTE_MINUTOS = 60
FORMAS_PAGAMENTO_ONLINE = ("pix", "cartao_debito", "cartao_credito")

# Palavras do mundo pet para código de retirada por terceiro
_PALAVRAS_PET = [
    "patinha",
    "focinho",
    "coleira",
    "bigodinho",
    "rabinho",
    "pelagem",
    "latido",
    "miado",
    "ronronar",
    "arranhado",
    "mordisco",
    "felpudo",
    "manchado",
    "listrado",
    "tigrao",
    "leaozinho",
    "pompom",
    "bolota",
    "amendoim",
    "biscoito",
    "caramelo",
    "chocolate",
    "baunilha",
    "canela",
    "malhado",
    "pintado",
    "bolinha",
    "fralda",
    "petisco",
    "ossinhos",
    "aquario",
    "gaiola",
    "gambito",
    "pinscher",
    "vira-lata",
    "siames",
    "labrador",
    "poodle",
    "bulldog",
    "dachshund",
    "beagle",
    "shih-tzu",
    "periquito",
    "calopsita",
    "hamster",
    "coelho",
    "porquinho",
    "tartaruga",
]


def _gerar_palavra_chave_retirada() -> str:
    """Gera código de retirada com 1 palavra do mundo pet, ex: 'patinha'"""
    return secrets.choice(_PALAVRAS_PET)


class EcommerceIdentity(BaseModel):
    user_id: int
    tenant_id: str


class CheckoutCalcularFreteRequest(BaseModel):
    cidade_destino: str = Field(min_length=2)
    subtotal: float = Field(default=0, ge=0)


class CheckoutFinalizarRequest(BaseModel):
    cidade_destino: str = Field(min_length=2)
    endereco_entrega: str | None = None
    cupom: str | None = None
    tipo_retirada: str | None = (
        None  # proprio, terceiro (usado quando delivery_mode=retirada)
    )
    is_drive: bool = (
        False  # Cliente quer usar drive (avisa quando chega no estacionamento)
    )
    forma_pagamento_nome: str | None = (
        None  # Nome da forma de pagamento selecionada pelo cliente
    )
    origem: str | None = None  # 'app' | 'web' — canal de origem do pedido


def _current_identity(
    current_user: User = Depends(_get_current_ecommerce_user),
) -> EcommerceIdentity:
    tenant_id = _activate_user_tenant_context(current_user)
    return EcommerceIdentity(
        user_id=current_user.id, tenant_id=str(UUID(str(tenant_id)))
    )


def _activate_checkout_tenant_context(identity: EcommerceIdentity) -> str:
    try:
        tenant_id = UUID(str(identity.tenant_id))
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token invalido",
            headers={"WWW-Authenticate": "Bearer"},
        )
    set_current_tenant(tenant_id)
    return str(tenant_id)


def _normalize_text(value: str | None) -> str:
    text = unicodedata.normalize("NFKD", (value or "").strip().lower())
    return "".join(
        character for character in text if not unicodedata.combining(character)
    )


def _frete_local_por_cidade(
    db: Session,
    tenant_id: str,
    cidade_destino: str,
    subtotal: float = 0,
) -> dict:
    cidade_loja_raw = None
    tenant = None
    previous_tenant = get_current_tenant()
    try:
        tenant_uuid = UUID(str(tenant_id))
        set_current_tenant(tenant_uuid)
        config = (
            db.query(ConfiguracaoEntrega)
            .filter(ConfiguracaoEntrega.tenant_id == tenant_uuid)
            .first()
        )
        tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
        if config:
            cidade_loja_raw = config.cidade
        if not cidade_loja_raw and tenant:
            cidade_loja_raw = tenant.cidade
    finally:
        if previous_tenant is None:
            clear_current_tenant()
        else:
            set_current_tenant(previous_tenant)

    cidade_loja = _normalize_text(cidade_loja_raw)
    destino = _normalize_text(cidade_destino)

    if not destino:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cidade de destino obrigatória",
        )
    if tenant and getattr(tenant, "ecommerce_entrega_ativa", True) is False:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Entrega desativada para esta loja. Escolha retirada na loja.",
        )
    if not cidade_loja:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Entrega ainda não configurada: informe a cidade da loja nas "
                "configurações de entrega."
            ),
        )
    if destino != cidade_loja:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Entrega disponível apenas na cidade da loja",
        )

    taxa = max(float(getattr(tenant, "ecommerce_taxa_entrega", 0) or 0), 0)
    frete_gratis_acima = getattr(tenant, "ecommerce_frete_gratis_acima", None)
    ganhou_frete_gratis = (
        frete_gratis_acima is not None
        and float(frete_gratis_acima) > 0
        and float(subtotal or 0) >= float(frete_gratis_acima)
    )
    prazo = (
        getattr(tenant, "ecommerce_prazo_entrega_texto", None)
        or "Prazo combinado com a loja"
    )

    return {
        "disponivel": True,
        "valor_frete": round(0.0 if ganhou_frete_gratis else taxa, 2),
        "prazo_estimado": prazo,
        "tipo": "entrega_local",
        "cidade_loja": cidade_loja_raw,
        "cidade_destino": cidade_destino,
        "frete_gratis_aplicado": ganhou_frete_gratis,
        "frete_gratis_acima": (
            float(frete_gratis_acima) if frete_gratis_acima is not None else None
        ),
        "observacao": "Entrega local da loja",
    }


def _buscar_carrinho(db: Session, identity: EcommerceIdentity) -> Pedido | None:
    tenant_id = _activate_checkout_tenant_context(identity)
    _expirar_reservas_automaticamente(db, tenant_id)

    return (
        db.query(Pedido)
        .filter(
            Pedido.cliente_id == identity.user_id,
            Pedido.tenant_id == tenant_id,
            Pedido.status == "carrinho",
        )
        .order_by(Pedido.id.desc())
        .first()
    )


def _buscar_itens(db: Session, pedido_id: str) -> list[PedidoItem]:
    return (
        db.query(PedidoItem)
        .filter(PedidoItem.pedido_id == pedido_id)
        .order_by(PedidoItem.id.asc())
        .all()
    )


def _expirar_reservas_automaticamente(db: Session, tenant_id: str) -> None:
    agora = datetime.utcnow()
    limite_pendente = agora - timedelta(minutes=RESERVA_EXPIRACAO_PENDENTE_MINUTOS)

    # Carrinhos nao reservam estoque e devem permanecer disponiveis quando o
    # cliente fecha e reabre o app. Somente pedidos enviados ao pagamento
    # possuem expiracao operacional.
    pendentes_expirados = (
        db.query(Pedido)
        .filter(
            Pedido.tenant_id == tenant_id,
            Pedido.status == "pendente",
            Pedido.created_at < limite_pendente,
        )
        .all()
    )
    for pedido in pendentes_expirados:
        pedido.status = "cancelado"

    if pendentes_expirados:
        db.flush()


def _request_hash(data: dict) -> str:
    serialized = json.dumps(data, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _pagamento_online_configurado(
    db: Session | None = None, tenant_id: str | None = None
) -> bool:
    if db is not None and tenant_id is not None:
        return get_active_mercado_pago_runtime_config(db, tenant_id) is not None

    enabled = str(os.getenv("ECOMMERCE_PAYMENT_GATEWAY_ENABLED", "")).strip().lower()
    provider = str(os.getenv("ECOMMERCE_PAYMENT_PROVIDER", "")).strip()
    return enabled in {"1", "true", "yes", "on"} and bool(provider)


def _payment_provider() -> str:
    return str(os.getenv("ECOMMERCE_PAYMENT_PROVIDER", "") or "").strip().lower()


def _public_base_url() -> str:
    return (
        (
            os.getenv("ECOMMERCE_PUBLIC_BASE_URL")
            or os.getenv("ECOMMERCE_BASE_URL")
            or os.getenv("FRONTEND_URL")
            or "https://corepet.com.br"
        )
        .strip()
        .rstrip("/")
    )


def _app_payment_return_url() -> str:
    return (
        (os.getenv("ECOMMERCE_APP_PAYMENT_RETURN_URL") or "corepet://app/pedidos")
        .strip()
        .rstrip("/")
    )


def _classificar_forma_pagamento_online(nome: str | None) -> str | None:
    valor = (nome or "").strip().lower()
    if not valor:
        return None
    if valor.startswith("pix"):
        return "pix"
    if valor.startswith("debito") or valor.startswith("débito"):
        return "cartao_debito"
    if valor.startswith("credito") or valor.startswith("crédito"):
        return "cartao_credito"
    return None


def _validar_forma_pagamento_online(nome: str | None) -> str:
    tipo = _classificar_forma_pagamento_online(nome)
    if tipo not in FORMAS_PAGAMENTO_ONLINE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Forma de pagamento invalida para app/ecommerce. Use PIX, debito ou credito.",
        )
    return tipo


def _resolver_origem_checkout(
    payload: CheckoutFinalizarRequest, request: Request
) -> str:
    return resolve_checkout_sales_channel(payload, request)


def _checkout_idempotency_payload(
    identity: EcommerceIdentity,
    payload: CheckoutFinalizarRequest,
    origem: str | None = None,
) -> dict:
    return {
        "user_id": identity.user_id,
        "tenant_id": str(UUID(identity.tenant_id)),
        "cidade_destino": payload.cidade_destino,
        "endereco_entrega": payload.endereco_entrega,
        "cupom": payload.cupom,
        "tipo_retirada": payload.tipo_retirada,
        "is_drive": payload.is_drive,
        "forma_pagamento_nome": payload.forma_pagamento_nome,
        "origem": origem if origem is not None else payload.origem,
    }


def _calcular_desconto(
    subtotal: float, cupom: str | None
) -> tuple[str | None, int, float]:
    if not cupom:
        return None, 0, 0.0

    codigo = cupom.strip().upper()
    descontos = {
        "MVP5": 5,
        "MVP10": 10,
    }
    percentual = descontos.get(codigo, 0)
    if percentual == 0:
        return codigo, 0, 0.0

    valor = round((subtotal * percentual) / 100.0, 2)
    return codigo, percentual, valor


__all__ = [
    "CheckoutCalcularFreteRequest",
    "CheckoutFinalizarRequest",
    "EcommerceIdentity",
    "FORMAS_PAGAMENTO_ONLINE",
    "RESERVA_EXPIRACAO_CARRINHO_MINUTOS",
    "RESERVA_EXPIRACAO_PENDENTE_MINUTOS",
    "_activate_checkout_tenant_context",
    "_app_payment_return_url",
    "_buscar_carrinho",
    "_buscar_itens",
    "_calcular_desconto",
    "_checkout_idempotency_payload",
    "_classificar_forma_pagamento_online",
    "_current_identity",
    "_expirar_reservas_automaticamente",
    "_frete_local_por_cidade",
    "_gerar_palavra_chave_retirada",
    "_normalize_text",
    "_pagamento_online_configurado",
    "_payment_provider",
    "_public_base_url",
    "_request_hash",
    "_resolver_origem_checkout",
    "_validar_forma_pagamento_online",
]
