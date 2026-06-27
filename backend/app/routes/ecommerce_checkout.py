from uuid import UUID
from datetime import datetime
import json
import logging

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Header, status
from sqlalchemy.orm import Session

from app.db import get_session
from app.financeiro_models import FormaPagamento
from app.idempotency_models import IdempotencyKey
from app.models import Tenant
from app.pedido_models import Pedido
from app.routes.ecommerce_checkout_support import (
    CheckoutCalcularFreteRequest,
    CheckoutFinalizarRequest,
    EcommerceIdentity,
    _activate_checkout_tenant_context,
    _app_payment_return_url,
    _buscar_carrinho,
    _buscar_itens,
    _calcular_desconto,
    _checkout_idempotency_payload,
    _classificar_forma_pagamento_online as _classificar_forma_pagamento_online,
    _current_identity,
    _expirar_reservas_automaticamente,
    _frete_local_por_cidade,
    _gerar_palavra_chave_retirada,
    _pagamento_online_configurado as _pagamento_online_configurado,
    _public_base_url,
    _request_hash,
    _resolver_origem_checkout,
    _validar_forma_pagamento_online,
)
from app.services.ecommerce_payment_config import get_active_mercado_pago_runtime_config
from app.services.customer_order_history import list_customer_order_history
from app.services.mercado_pago_checkout import (
    create_preference,
    is_mercado_pago_provider,
)
from app.services.order_push_notifications import notify_order_event
from app.tenancy.context import (
    clear_current_tenant,
    get_current_tenant,
    set_current_tenant,
)
from app.utils.timezone import now_brasilia


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/checkout", tags=["ecommerce-checkout"])


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
                IdempotencyKey.chave_idempotencia
                == f"ecommerce-venda:{pedido.pedido_id}",
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
            venda_id = (
                int(response_body.get("venda_id"))
                if response_body.get("venda_id")
                else None
            )
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
            FormaPagamento.ativo.is_(True),
        )
        .order_by(FormaPagamento.nome)
        .all()
    )
    return {
        "formas_pagamento": [
            {"id": f.id, "nome": f.nome, "tipo": f.tipo} for f in formas
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
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Carrinho vazio"
        )

    itens = _buscar_itens(db, carrinho.pedido_id)
    if not itens:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Carrinho vazio"
        )

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
    origem_checkout = _resolver_origem_checkout(payload, request)
    request_data = _checkout_idempotency_payload(identity, payload, origem_checkout)
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
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Conflito de idempotência",
                )
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
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Carrinho vazio"
        )

    carrinho.origem = origem_checkout

    itens = _buscar_itens(db, carrinho.pedido_id)
    if not itens:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Carrinho vazio"
        )

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

    cupom_codigo, cupom_percentual, desconto = _calcular_desconto(
        subtotal, payload.cupom
    )
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
        storefront_ref = str(
            getattr(tenant, "ecommerce_slug", None) or tenant_id
        ).strip("/")
        return_url_params = None
        if origem_checkout == "app":
            return_url_base = _app_payment_return_url()
            return_url_params = {
                "loja": storefront_ref,
                "tenant": storefront_ref,
                "tenant_id": tenant_id,
                "canal": "app",
            }
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
            return_url_params=return_url_params,
            use_sandbox=payment_config.use_sandbox,
        )
        carrinho.payment_provider = "mercadopago"
        carrinho.payment_preference_id = preference.get("preference_id")
        carrinho.payment_url = preference.get("payment_url")
        response.update(
            {
                "payment_provider": carrinho.payment_provider,
                "payment_preference_id": carrinho.payment_preference_id,
                "payment_url": carrinho.payment_url,
                "init_point": preference.get("init_point"),
                "sandbox_init_point": preference.get("sandbox_init_point"),
            }
        )

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
    notify_order_event(
        db,
        tenant_id=tenant_id,
        user_id=identity.user_id,
        event="checkout_created",
        pedido_id=carrinho.pedido_id,
        canal=origem_checkout,
    )
    return response


@router.get("/pedidos")
def listar_pedidos_cliente(
    limit: int = Query(default=20, ge=1, le=100),
    identity: EcommerceIdentity = Depends(_current_identity),
    db: Session = Depends(get_session),
):
    """Lista o historico de compras do cliente logado por canal."""
    tenant_id = _activate_checkout_tenant_context(identity)
    _expirar_reservas_automaticamente(db, tenant_id)

    pedidos = list_customer_order_history(
        db,
        tenant_id=tenant_id,
        user_id=identity.user_id,
        limit=limit,
    )

    response = {"pedidos": pedidos}
    db.rollback()
    return response


@router.get("/pedido/{pedido_id}/status")
def consultar_status_pedido(
    pedido_id: str,
    identity: EcommerceIdentity = Depends(_current_identity),
    db: Session = Depends(get_session),
):
    tenant_id = _activate_checkout_tenant_context(identity)
    _expirar_reservas_automaticamente(db, tenant_id)

    pedido = (
        db.query(Pedido)
        .filter(
            Pedido.pedido_id == pedido_id,
            Pedido.cliente_id == identity.user_id,
            Pedido.tenant_id == tenant_id,
        )
        .first()
    )
    if not pedido:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Pedido não encontrado"
        )

    payment_info = _payment_info_for_pedido(db, pedido)
    venda_info = _venda_info_for_pedido(db, pedido)
    return {
        "pedido_id": pedido.pedido_id,
        "status": pedido.status,
        "total": float(pedido.total or 0.0),
        "origem": pedido.origem or venda_info["canal"] or "-",
        "venda_id": venda_info["venda_id"],
        "status_entrega": venda_info["status_entrega"],
        "retirado_por": venda_info["retirado_por"],
        "tem_entrega": venda_info["tem_entrega"],
        "tipo_retirada": pedido.tipo_retirada,
        "is_drive": pedido.is_drive,
        "drive_chegou_at": pedido.drive_chegou_at.isoformat()
        if pedido.drive_chegou_at
        else None,
        "drive_entregue_at": pedido.drive_entregue_at.isoformat()
        if pedido.drive_entregue_at
        else None,
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
    tenant_id = _activate_checkout_tenant_context(identity)
    _expirar_reservas_automaticamente(db, tenant_id)

    pedido = (
        db.query(Pedido)
        .filter(
            Pedido.pedido_id == pedido_id,
            Pedido.cliente_id == identity.user_id,
            Pedido.tenant_id == tenant_id,
        )
        .first()
    )
    if not pedido:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Pedido não encontrado"
        )

    if pedido.status not in ("carrinho", "pendente"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Pedido não pode ser cancelado",
        )

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
    tenant_id = _activate_checkout_tenant_context(identity)
    pedido = (
        db.query(Pedido)
        .filter(
            Pedido.pedido_id == pedido_id,
            Pedido.cliente_id == identity.user_id,
            Pedido.tenant_id == tenant_id,
        )
        .first()
    )
    if not pedido:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Pedido não encontrado"
        )

    if not pedido.is_drive:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Este pedido não é drive"
        )

    if pedido.drive_chegou_at:
        return {
            "pedido_id": pedido.pedido_id,
            "drive_chegou_at": pedido.drive_chegou_at.isoformat(),
            "message": "Chegada já registrada",
        }

    pedido.drive_chegou_at = now_brasilia()
    db.commit()

    logger.info(f"🚗 Drive chegou: pedido #{pedido_id} (cliente {identity.user_id})")
    return {
        "pedido_id": pedido.pedido_id,
        "drive_chegou_at": pedido.drive_chegou_at.isoformat(),
        "message": "Chegada registrada! Aguarde, estamos preparando seu pedido.",
    }
