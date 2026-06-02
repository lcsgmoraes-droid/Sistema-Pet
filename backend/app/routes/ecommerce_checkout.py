from uuid import UUID
from datetime import datetime, timedelta
import hashlib
import json
import logging
import os
import random

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Header, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.db import get_session
from app.financeiro_models import FormaPagamento
from app.idempotency_models import IdempotencyKey
from app.models import Cliente, Tenant, User
from app.pedido_models import Pedido, PedidoItem
from app.routes.ecommerce_auth import _activate_user_tenant_context, _get_current_ecommerce_user
from app.services.ecommerce_payment_config import get_active_mercado_pago_runtime_config
from app.services.mercado_pago_checkout import (
    create_preference,
    is_mercado_pago_provider,
    normalizar_canal_venda_online,
)
from app.tenancy.context import clear_current_tenant, get_current_tenant, set_current_tenant
from app.utils.timezone import now_brasilia


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/checkout", tags=["ecommerce-checkout"])

RESERVA_EXPIRACAO_CARRINHO_MINUTOS = 30
RESERVA_EXPIRACAO_PENDENTE_MINUTOS = 60
FORMAS_PAGAMENTO_ONLINE = ("pix", "cartao_debito", "cartao_credito")

# Palavras do mundo pet para código de retirada por terceiro
_PALAVRAS_PET = [
    "patinha", "focinho", "coleira", "bigodinho", "rabinho", "pelagem",
    "latido", "miado", "ronronar", "arranhado", "mordisco", "felpudo",
    "manchado", "listrado", "tigrao", "leaozinho", "pompom", "bolota",
    "amendoim", "biscoito", "caramelo", "chocolate", "baunilha", "canela",
    "malhado", "pintado", "bolinha", "fralda", "petisco", "ossinhos",
    "aquario", "gaiola", "gambito", "pinscher", "vira-lata", "siames",
    "labrador", "poodle", "bulldog", "dachshund", "beagle", "shih-tzu",
    "periquito", "calopsita", "hamster", "coelho", "porquinho", "tartaruga",
]


def _gerar_palavra_chave_retirada() -> str:
    """Gera código de retirada com 1 palavra do mundo pet, ex: 'patinha'"""
    return random.choice(_PALAVRAS_PET)


class EcommerceIdentity(BaseModel):
    user_id: int
    tenant_id: str


class CheckoutCalcularFreteRequest(BaseModel):
    cidade_destino: str = Field(min_length=2)


class CheckoutFinalizarRequest(BaseModel):
    cidade_destino: str = Field(min_length=2)
    endereco_entrega: str | None = None
    cupom: str | None = None
    tipo_retirada: str | None = None  # proprio, terceiro (usado quando delivery_mode=retirada)
    is_drive: bool = False  # Cliente quer usar drive (avisa quando chega no estacionamento)
    forma_pagamento_nome: str | None = None  # Nome da forma de pagamento selecionada pelo cliente
    origem: str | None = None  # 'app' | 'web' — canal de origem do pedido


def _current_identity(current_user: User = Depends(_get_current_ecommerce_user)) -> EcommerceIdentity:
    tenant_id = _activate_user_tenant_context(current_user)
    return EcommerceIdentity(user_id=current_user.id, tenant_id=str(UUID(str(tenant_id))))


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
    return (value or "").strip().lower()


def _frete_local_por_cidade(db: Session, tenant_id: str, cidade_destino: str) -> dict:
    cidade_loja_raw = None
    try:
        result = db.execute(
            text("""
                SELECT cidade
                FROM configuracoes_entrega
                WHERE tenant_id = :tenant_id
                LIMIT 1
            """),
            {"tenant_id": tenant_id},
        ).fetchone()
        if result:
            cidade_loja_raw = result[0]
    except Exception:
        cidade_loja_raw = None

    cidade_loja = _normalize_text(cidade_loja_raw)
    destino = _normalize_text(cidade_destino)

    if not destino:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cidade de destino obrigatória")

    if not cidade_loja:
        return {
            "disponivel": True,
            "valor_frete": 0.0,
            "prazo_estimado": "mesmo_dia",
            "tipo": "entrega_local",
            "cidade_loja": None,
            "cidade_destino": cidade_destino,
            "observacao": "Cidade da loja não configurada; aplicado frete local padrão",
        }

    if destino != cidade_loja:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Entrega disponível apenas na cidade da loja",
        )

    return {
        "disponivel": True,
        "valor_frete": 0.0,
        "prazo_estimado": "mesmo_dia",
        "tipo": "entrega_local",
        "cidade_loja": cidade_loja_raw,
        "cidade_destino": cidade_destino,
        "observacao": "Entrega local da loja (sem integração logística)",
    }


def _buscar_carrinho(db: Session, identity: EcommerceIdentity) -> Pedido | None:
    _expirar_reservas_automaticamente(db, identity.tenant_id)

    return (
        db.query(Pedido)
        .filter(
            Pedido.cliente_id == identity.user_id,
            Pedido.tenant_id == identity.tenant_id,
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


def _payment_info_for_pedido(db: Session, pedido: Pedido) -> dict[str, str | None]:
    payment_info = {
        "payment_provider": pedido.payment_provider,
        "payment_preference_id": pedido.payment_preference_id,
        "payment_url": pedido.payment_url,
    }
    if payment_info["payment_url"] or payment_info["payment_preference_id"]:
        return payment_info

    previous_tenant = get_current_tenant()
    set_current_tenant(UUID(str(pedido.tenant_id)))
    try:
        idem_rows = (
            db.query(IdempotencyKey)
            .filter(
                IdempotencyKey.user_id == pedido.cliente_id,
                IdempotencyKey.tenant_id == pedido.tenant_id,
                IdempotencyKey.endpoint == "POST /api/checkout/finalizar",
                IdempotencyKey.status == "completed",
                IdempotencyKey.response_body.isnot(None),
                IdempotencyKey.response_body.contains(pedido.pedido_id),
            )
            .order_by(IdempotencyKey.completed_at.desc(), IdempotencyKey.id.desc())
            .limit(5)
            .all()
        )
    finally:
        if previous_tenant is None:
            clear_current_tenant()
        else:
            set_current_tenant(previous_tenant)

    for idem_row in idem_rows:
        try:
            response = json.loads(idem_row.response_body or "{}")
        except (TypeError, json.JSONDecodeError):
            continue
        if response.get("pedido_id") != pedido.pedido_id:
            continue
        return {
            "payment_provider": response.get("payment_provider"),
            "payment_preference_id": response.get("payment_preference_id"),
            "payment_url": response.get("payment_url"),
        }

    return payment_info


def _venda_info_for_pedido(db: Session, pedido: Pedido) -> dict[str, str | bool | None]:
    venda_info = {
        "venda_id": None,
        "status_entrega": None,
        "retirado_por": None,
        "tem_entrega": None,
        "canal": None,
    }
    previous_tenant = get_current_tenant()
    set_current_tenant(UUID(str(pedido.tenant_id)))
    try:
        registry = (
            db.query(IdempotencyKey)
            .filter(
                IdempotencyKey.user_id == 0,
                IdempotencyKey.tenant_id == pedido.tenant_id,
                IdempotencyKey.endpoint == "POST /api/ecommerce/integracao/venda",
                IdempotencyKey.chave_idempotencia == f"ecommerce-venda:{pedido.pedido_id}",
                IdempotencyKey.status == "completed",
                IdempotencyKey.response_body.isnot(None),
            )
            .order_by(IdempotencyKey.completed_at.desc(), IdempotencyKey.id.desc())
            .first()
        )

        if not registry or not registry.response_body:
            return venda_info

        try:
            response_body = json.loads(registry.response_body or "{}")
            venda_id = int(response_body.get("venda_id")) if response_body.get("venda_id") else None
        except (TypeError, ValueError, json.JSONDecodeError):
            venda_id = None

        if not venda_id:
            return venda_info

        from app.vendas_models import Venda

        venda = (
            db.query(Venda)
            .filter(Venda.id == venda_id, Venda.tenant_id == pedido.tenant_id)
            .first()
        )
        if not venda:
            return venda_info

        return {
            "venda_id": venda.id,
            "status_entrega": venda.status_entrega,
            "retirado_por": venda.retirado_por,
            "tem_entrega": bool(venda.tem_entrega),
            "canal": venda.canal,
        }
    finally:
        if previous_tenant is None:
            clear_current_tenant()
        else:
            set_current_tenant(previous_tenant)


def _expirar_reservas_automaticamente(db: Session, tenant_id: str) -> None:
    agora = datetime.utcnow()
    limite_carrinho = agora - timedelta(minutes=RESERVA_EXPIRACAO_CARRINHO_MINUTOS)
    limite_pendente = agora - timedelta(minutes=RESERVA_EXPIRACAO_PENDENTE_MINUTOS)

    carrinhos_expirados = (
        db.query(Pedido)
        .filter(
            Pedido.tenant_id == tenant_id,
            Pedido.status == "carrinho",
            Pedido.created_at < limite_carrinho,
        )
        .all()
    )
    for pedido in carrinhos_expirados:
        pedido.status = "expirado"

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

    if carrinhos_expirados or pendentes_expirados:
        db.flush()


def _request_hash(data: dict) -> str:
    serialized = json.dumps(data, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _pagamento_online_configurado(db: Session | None = None, tenant_id: str | None = None) -> bool:
    if db is not None and tenant_id is not None:
        return get_active_mercado_pago_runtime_config(db, tenant_id) is not None

    enabled = str(os.getenv("ECOMMERCE_PAYMENT_GATEWAY_ENABLED", "")).strip().lower()
    provider = str(os.getenv("ECOMMERCE_PAYMENT_PROVIDER", "")).strip()
    return enabled in {"1", "true", "yes", "on"} and bool(provider)


def _payment_provider() -> str:
    return str(os.getenv("ECOMMERCE_PAYMENT_PROVIDER", "") or "").strip().lower()


def _public_base_url() -> str:
    return (
        os.getenv("ECOMMERCE_PUBLIC_BASE_URL")
        or os.getenv("ECOMMERCE_BASE_URL")
        or os.getenv("FRONTEND_URL")
        or "https://corepet.com.br"
    ).strip().rstrip("/")


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


def _checkout_idempotency_payload(
    identity: EcommerceIdentity,
    payload: CheckoutFinalizarRequest,
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
        "origem": payload.origem,
    }


def _calcular_desconto(subtotal: float, cupom: str | None) -> tuple[str | None, int, float]:
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


@router.get("/formas-pagamento")
def listar_formas_pagamento(
    identity: EcommerceIdentity = Depends(_current_identity),
    db: Session = Depends(get_session),
):
    """Lista as formas de pagamento ativas cadastradas no ERP."""
    tenant_id = _activate_checkout_tenant_context(identity)
    formas = (
        db.query(FormaPagamento)
        .filter(
            FormaPagamento.tenant_id == tenant_id,
            FormaPagamento.ativo == True,
        )
        .order_by(FormaPagamento.nome)
        .all()
    )
    return {
        "formas_pagamento": [
            {"id": f.id, "nome": f.nome, "tipo": f.tipo}
            for f in formas
        ]
    }


@router.post("/calcular-frete")
def calcular_frete_local(
    payload: CheckoutCalcularFreteRequest,
    identity: EcommerceIdentity = Depends(_current_identity),
    db: Session = Depends(get_session),
):
    tenant_id = _activate_checkout_tenant_context(identity)
    return _frete_local_por_cidade(db, tenant_id, payload.cidade_destino)


@router.get("/resumo")
def resumo_checkout(
    cidade_destino: str = Query(..., min_length=2),
    cupom: str | None = Query(default=None),
    identity: EcommerceIdentity = Depends(_current_identity),
    db: Session = Depends(get_session),
):
    tenant_id = _activate_checkout_tenant_context(identity)
    _expirar_reservas_automaticamente(db, tenant_id)

    carrinho = _buscar_carrinho(db, identity)
    if not carrinho:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Carrinho vazio")

    itens = _buscar_itens(db, carrinho.pedido_id)
    if not itens:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Carrinho vazio")

    subtotal = round(sum(float(item.subtotal or 0.0) for item in itens), 2)
    frete = _frete_local_por_cidade(db, tenant_id, cidade_destino)
    cupom_codigo, cupom_percentual, desconto = _calcular_desconto(subtotal, cupom)
    total = round(max(subtotal - desconto, 0.0) + float(frete["valor_frete"]), 2)

    return {
        "pedido_id": carrinho.pedido_id,
        "itens_count": len(itens),
        "subtotal": subtotal,
        "frete": frete,
        "cupom": {
            "codigo": cupom_codigo,
            "percentual": cupom_percentual,
            "desconto": desconto,
        },
        "total": total,
    }


@router.post("/finalizar")
def finalizar_checkout(
    payload: CheckoutFinalizarRequest,
    request: Request,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    identity: EcommerceIdentity = Depends(_current_identity),
    db: Session = Depends(get_session),
):
    tenant_id = _activate_checkout_tenant_context(identity)
    _expirar_reservas_automaticamente(db, tenant_id)
    forma_pagamento_tipo = _validar_forma_pagamento_online(payload.forma_pagamento_nome)

    payment_config = get_active_mercado_pago_runtime_config(db, tenant_id)
    if not payment_config:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Mercado Pago ainda nao configurado para esta loja. "
                "Configure as credenciais em E-commerce > Configuracoes antes de finalizar pedidos."
            ),
        )

    endpoint_name = "POST /api/checkout/finalizar"
    idem_key_value = idempotency_key or request.headers.get("Idempotency-Key")
    request_data = _checkout_idempotency_payload(identity, payload)
    tenant_uuid = request_data["tenant_id"]
    request_hash = _request_hash(request_data)
    idem_row = None

    if idem_key_value:
        idem_row = (
            db.query(IdempotencyKey)
            .filter(
                IdempotencyKey.user_id == identity.user_id,
                IdempotencyKey.tenant_id == tenant_uuid,
                IdempotencyKey.endpoint == endpoint_name,
                IdempotencyKey.chave_idempotencia == idem_key_value,
            )
            .first()
        )

        if idem_row:
            if idem_row.request_hash != request_hash:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Conflito de idempotência")
            if idem_row.status == "completed" and idem_row.response_body:
                return json.loads(idem_row.response_body)
        else:
            idem_row = IdempotencyKey(
                user_id=identity.user_id,
                tenant_id=tenant_uuid,
                endpoint=endpoint_name,
                chave_idempotencia=idem_key_value,
                request_hash=request_hash,
                status="processing",
            )
            db.add(idem_row)
            db.flush()

    carrinho = _buscar_carrinho(db, identity)
    if not carrinho:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Carrinho vazio")

    origem_checkout = normalizar_canal_venda_online(payload.origem)
    carrinho.origem = origem_checkout

    itens = _buscar_itens(db, carrinho.pedido_id)
    if not itens:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Carrinho vazio")

    subtotal = round(sum(float(item.subtotal or 0.0) for item in itens), 2)

    # Retirada na loja (próprio, terceiro ou app_loja): não valida frete por cidade
    if payload.tipo_retirada in ("proprio", "terceiro", "app_loja"):
        frete = {
            "disponivel": True,
            "valor_frete": 0.0,
            "prazo_estimado": "Retirada na loja",
            "tipo": "retirada",
            "cidade_loja": None,
            "cidade_destino": payload.cidade_destino,
        }
    else:
        frete = _frete_local_por_cidade(db, tenant_id, payload.cidade_destino)

    cupom_codigo, cupom_percentual, desconto = _calcular_desconto(subtotal, payload.cupom)
    total = round(max(subtotal - desconto, 0.0) + float(frete["valor_frete"]), 2)

    carrinho.total = total
    carrinho.status = "pendente"

    # Tipo de retirada e palavra-chave para terceiro retirar
    tipo_retirada = payload.tipo_retirada  # 'proprio' | 'terceiro' | 'app_loja' | None
    palavra_chave = None
    if tipo_retirada in ("terceiro", "app_loja"):
        # app_loja: cliente comprou pelo app, vai à loja e fala a palavra no caixa
        palavra_chave = _gerar_palavra_chave_retirada()
    elif tipo_retirada == "proprio" and payload.is_drive:
        # Drive: cliente próprio, mas quer drive — usamos palavra-chave como token de chegada
        palavra_chave = _gerar_palavra_chave_retirada()
    carrinho.tipo_retirada = tipo_retirada
    carrinho.palavra_chave_retirada = palavra_chave
    carrinho.is_drive = payload.is_drive

    response = {
        "status": "pagamento_pendente_aprovacao",
        "pedido_id": carrinho.pedido_id,
        "pedido_status": carrinho.status,
        "subtotal": subtotal,
        "frete": frete,
        "cupom": {
            "codigo": cupom_codigo,
            "percentual": cupom_percentual,
            "desconto": desconto,
        },
        "total": total,
        "endereco_entrega": payload.endereco_entrega,
        "tipo_retirada": tipo_retirada,
        "is_drive": payload.is_drive,
        "forma_pagamento_tipo": forma_pagamento_tipo,
        "palavra_chave_retirada": palavra_chave,
        "origem": carrinho.origem,
    }

    provider = payment_config.provider
    response["payment_provider"] = provider
    if is_mercado_pago_provider(provider):
        tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
        storefront_ref = str(getattr(tenant, "ecommerce_slug", None) or tenant_id).strip("/")
        if origem_checkout == "app":
            return_url_base = f"{_public_base_url()}/app/retorno-pagamento"
        else:
            return_url_base = f"{_public_base_url()}/{storefront_ref}"
        preference = create_preference(
            pedido=carrinho,
            total=total,
            forma_pagamento_tipo=forma_pagamento_tipo,
            endereco_entrega=payload.endereco_entrega,
            tipo_retirada=tipo_retirada,
            access_token=payment_config.access_token,
            notification_url=payment_config.webhook_url,
            return_url_base=return_url_base,
            use_sandbox=payment_config.use_sandbox,
        )
        carrinho.payment_provider = "mercadopago"
        carrinho.payment_preference_id = preference.get("preference_id")
        carrinho.payment_url = preference.get("payment_url")
        response.update({
            "payment_provider": carrinho.payment_provider,
            "payment_preference_id": carrinho.payment_preference_id,
            "payment_url": carrinho.payment_url,
            "init_point": preference.get("init_point"),
            "sandbox_init_point": preference.get("sandbox_init_point"),
        })

    if idem_row:
        idem_row.status = "completed"
        idem_row.response_status_code = 200
        idem_row.response_body = json.dumps(response, ensure_ascii=False)
        idem_row.completed_at = datetime.utcnow()

    db.commit()

    logger.info(
        f"Checkout enviado para pagamento: carrinho #{carrinho.pedido_id} "
        f"aguardando aprovacao (tipo_retirada={tipo_retirada})"
    )
    return response


@router.get("/pedidos")
def listar_pedidos_cliente(
    limit: int = Query(default=20, ge=1, le=100),
    identity: EcommerceIdentity = Depends(_current_identity),
    db: Session = Depends(get_session),
):
    """Lista todos os pedidos finalizados do cliente logado (exclui carrinho ativo)."""
    _expirar_reservas_automaticamente(db, identity.tenant_id)

    pedidos = (
        db.query(Pedido)
        .filter(
            Pedido.cliente_id == identity.user_id,
            Pedido.tenant_id == identity.tenant_id,
            Pedido.status != "carrinho",
        )
        .order_by(Pedido.id.desc())
        .limit(limit)
        .all()
    )

    resultado = []
    for pedido in pedidos:
        itens = _buscar_itens(db, pedido.pedido_id)
        payment_info = _payment_info_for_pedido(db, pedido)
        venda_info = _venda_info_for_pedido(db, pedido)
        resultado.append({
            "pedido_id": pedido.pedido_id,
            "status": pedido.status,
            "total": float(pedido.total or 0.0),
            "origem": pedido.origem or venda_info["canal"] or '-',
            "venda_id": venda_info["venda_id"],
            "status_entrega": venda_info["status_entrega"],
            "retirado_por": venda_info["retirado_por"],
            "tem_entrega": venda_info["tem_entrega"],
            "tipo_retirada": pedido.tipo_retirada,
            "palavra_chave_retirada": pedido.palavra_chave_retirada,
            "payment_provider": payment_info["payment_provider"],
            "payment_preference_id": payment_info["payment_preference_id"],
            "payment_url": payment_info["payment_url"],
            "created_at": pedido.created_at.isoformat() if pedido.created_at else None,
            "itens_count": len(itens),
            "itens": [
                {
                    "produto_id": item.produto_id,
                    "nome": item.nome,
                    "quantidade": item.quantidade,
                    "preco_unitario": float(item.preco_unitario or 0.0),
                    "subtotal": float(item.subtotal or 0.0),
                }
                for item in itens
            ],
        })

    return {"pedidos": resultado}


@router.get("/pedido/{pedido_id}/status")
def consultar_status_pedido(
    pedido_id: str,
    identity: EcommerceIdentity = Depends(_current_identity),
    db: Session = Depends(get_session),
):
    _expirar_reservas_automaticamente(db, identity.tenant_id)

    pedido = (
        db.query(Pedido)
        .filter(
            Pedido.pedido_id == pedido_id,
            Pedido.cliente_id == identity.user_id,
            Pedido.tenant_id == identity.tenant_id,
        )
        .first()
    )
    if not pedido:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pedido não encontrado")

    payment_info = _payment_info_for_pedido(db, pedido)
    venda_info = _venda_info_for_pedido(db, pedido)
    return {
        "pedido_id": pedido.pedido_id,
        "status": pedido.status,
        "total": float(pedido.total or 0.0),
        "origem": pedido.origem or venda_info["canal"] or '-',
        "venda_id": venda_info["venda_id"],
        "status_entrega": venda_info["status_entrega"],
        "retirado_por": venda_info["retirado_por"],
        "tem_entrega": venda_info["tem_entrega"],
        "tipo_retirada": pedido.tipo_retirada,
        "is_drive": pedido.is_drive,
        "drive_chegou_at": pedido.drive_chegou_at.isoformat() if pedido.drive_chegou_at else None,
        "drive_entregue_at": pedido.drive_entregue_at.isoformat() if pedido.drive_entregue_at else None,
        "palavra_chave_retirada": pedido.palavra_chave_retirada,
        "payment_provider": payment_info["payment_provider"],
        "payment_preference_id": payment_info["payment_preference_id"],
        "payment_url": payment_info["payment_url"],
        "created_at": pedido.created_at,
    }


@router.post("/pedido/{pedido_id}/cancelar")
def cancelar_pedido(
    pedido_id: str,
    identity: EcommerceIdentity = Depends(_current_identity),
    db: Session = Depends(get_session),
):
    _expirar_reservas_automaticamente(db, identity.tenant_id)

    pedido = (
        db.query(Pedido)
        .filter(
            Pedido.pedido_id == pedido_id,
            Pedido.cliente_id == identity.user_id,
            Pedido.tenant_id == identity.tenant_id,
        )
        .first()
    )
    if not pedido:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pedido não encontrado")

    if pedido.status not in ("carrinho", "pendente"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Pedido não pode ser cancelado")

    pedido.status = "cancelado"
    db.commit()

    return {
        "pedido_id": pedido.pedido_id,
        "status": pedido.status,
        "message": "Pedido cancelado com sucesso",
    }


@router.post("/pedido/{pedido_id}/drive-cheguei")
def drive_cheguei(
    pedido_id: str,
    identity: EcommerceIdentity = Depends(_current_identity),
    db: Session = Depends(get_session),
):
    """Cliente pressiona 'Cheguei' — grava timestamp de chegada no drive."""
    pedido = (
        db.query(Pedido)
        .filter(
            Pedido.pedido_id == pedido_id,
            Pedido.cliente_id == identity.user_id,
            Pedido.tenant_id == identity.tenant_id,
        )
        .first()
    )
    if not pedido:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pedido não encontrado")

    if not pedido.is_drive:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Este pedido não é drive")

    if pedido.drive_chegou_at:
        return {"pedido_id": pedido.pedido_id, "drive_chegou_at": pedido.drive_chegou_at.isoformat(), "message": "Chegada já registrada"}

    pedido.drive_chegou_at = now_brasilia()
    db.commit()

    logger.info(f"🚗 Drive chegou: pedido #{pedido_id} (cliente {identity.user_id})")
    return {
        "pedido_id": pedido.pedido_id,
        "drive_chegou_at": pedido.drive_chegou_at.isoformat(),
        "message": "Chegada registrada! Aguarde, estamos preparando seu pedido.",
    }
