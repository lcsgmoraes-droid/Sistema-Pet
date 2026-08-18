"""Validação, prévia e criação idempotente da venda iniciada no WhatsApp."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import Any, Callable, Literal, Optional

from fastapi import HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import or_, text
from sqlalchemy.orm import Session


class WhatsAppOrderItemData(BaseModel):
    product_id: int
    quantity: float = Field(gt=0)


class WhatsAppOrderPreviewData(BaseModel):
    phone: str = Field(min_length=8, max_length=30)
    items: list[WhatsAppOrderItemData]


class WhatsAppOrderCreateData(WhatsAppOrderPreviewData):
    fulfillment: Literal["delivery", "pickup"]
    payment_method: dict[str, Any]
    delivery_address: Optional[str] = Field(default=None, max_length=1000)
    cash_change_for: Optional[float] = Field(default=None, gt=0)


def phone_digits(value: str) -> str:
    return "".join(character for character in str(value or "") if character.isdigit())


def resolve_customer(db: Session, tenant_id, *, phone: str):
    from app.models import Cliente

    digits = phone_digits(phone)
    if len(digits) < 8:
        return None
    last_four = digits[-4:]
    candidates = (
        db.query(Cliente)
        .filter(
            Cliente.tenant_id == tenant_id,
            or_(
                Cliente.celular.ilike(f"%{last_four}%"),
                Cliente.telefone.ilike(f"%{last_four}%"),
            ),
        )
        .limit(20)
        .all()
    )
    matches = [
        candidate
        for candidate in candidates
        if any(
            phone_digits(value).endswith(digits[-8:])
            for value in (candidate.celular, candidate.telefone)
            if value
        )
    ]
    return matches[0] if len(matches) == 1 else None


def customer_delivery_address(customer) -> str:
    if str(getattr(customer, "endereco_entrega", None) or "").strip():
        return str(customer.endereco_entrega).strip()
    parts = [
        getattr(customer, "endereco", None),
        getattr(customer, "numero", None),
        getattr(customer, "complemento", None),
        getattr(customer, "bairro", None),
        getattr(customer, "cidade", None),
        getattr(customer, "estado", None),
        getattr(customer, "cep", None),
    ]
    return ", ".join(str(part).strip() for part in parts if str(part or "").strip())


def payment_methods(db: Session, tenant_id) -> list[dict[str, Any]]:
    from app.financeiro_models import FormaPagamento
    from app.routes.app_mobile_funcionario_pdv.pagamentos import (
        _forma_pagamento_key_funcionario_pdv,
    )

    labels = {
        "pix": "PIX",
        "dinheiro": "Dinheiro",
        "debito": "Cartão de débito",
        "credito": "Cartão de crédito",
    }
    priority = {"pix": 0, "dinheiro": 1, "debito": 2, "credito": 3}
    methods: dict[str, dict[str, Any]] = {}
    rows = (
        db.query(FormaPagamento)
        .filter(
            FormaPagamento.tenant_id == tenant_id,
            FormaPagamento.ativo.is_(True),
        )
        .order_by(FormaPagamento.nome.asc())
        .all()
    )
    for row in rows:
        key = _forma_pagamento_key_funcionario_pdv(row)
        if key and key not in methods:
            methods[key] = {"key": key, "name": labels[key]}
    return sorted(methods.values(), key=lambda item: priority[item["key"]])


def default_delivery_person_id(db: Session, tenant_id) -> Optional[int]:
    from app.models import Cliente
    from app.models_operacionais import ConfiguracaoEntrega

    config = (
        db.query(ConfiguracaoEntrega)
        .filter(ConfiguracaoEntrega.tenant_id == tenant_id)
        .first()
    )
    if config and config.entregador_padrao_id:
        return int(config.entregador_padrao_id)
    delivery_person = (
        db.query(Cliente)
        .filter(
            Cliente.tenant_id == tenant_id,
            Cliente.is_entregador.is_(True),
            Cliente.entregador_ativo.is_(True),
            Cliente.entregador_padrao.is_(True),
        )
        .order_by(Cliente.id.asc())
        .first()
    )
    return int(delivery_person.id) if delivery_person else None


def build_order_preview(
    db: Session,
    tenant_id,
    *,
    phone: str,
    requested_items: list[WhatsAppOrderItemData],
) -> dict[str, Any]:
    from app.produtos_models import Produto
    from app.routes.app_mobile_funcionario_pdv.beneficios import (
        _calcular_beneficios_gerados_funcionario_pdv,
    )

    if not requested_items:
        raise HTTPException(status_code=400, detail="O pedido está sem produtos.")
    customer = resolve_customer(db, tenant_id, phone=phone)
    if not customer:
        raise HTTPException(
            status_code=404,
            detail="Não encontrei um único cliente vinculado a este WhatsApp.",
        )

    product_ids = {item.product_id for item in requested_items}
    products = (
        db.query(Produto)
        .filter(
            Produto.tenant_id == tenant_id,
            Produto.id.in_(product_ids),
            Produto.situacao.is_(True),
            Produto.tipo_produto != "PAI",
        )
        .all()
    )
    products_by_id = {int(product.id): product for product in products}
    preview_items: list[dict[str, Any]] = []
    total = 0.0
    for requested in requested_items:
        product = products_by_id.get(requested.product_id)
        if not product:
            raise HTTPException(
                status_code=404,
                detail=f"Produto ID {requested.product_id} não encontrado.",
            )
        quantity = float(requested.quantity)
        stock = float(product.estoque_atual or 0)
        if stock + 0.0001 < quantity:
            raise HTTPException(
                status_code=409,
                detail=f"Estoque insuficiente para {product.nome}.",
            )
        unit_price = float(product.preco_venda or 0)
        if unit_price <= 0:
            raise HTTPException(
                status_code=409,
                detail=f"O produto {product.nome} está sem preço de venda.",
            )
        subtotal = round(quantity * unit_price, 2)
        total = round(total + subtotal, 2)
        preview_items.append(
            {
                "product_id": int(product.id),
                "name": product.nome,
                "quantity": quantity,
                "unit_price": unit_price,
                "subtotal": subtotal,
                "image_url": product.imagem_principal or "",
            }
        )

    benefits = _calcular_beneficios_gerados_funcionario_pdv(
        db,
        tenant_id=tenant_id,
        cliente_id=customer.id,
        total_venda=total,
        sale_channel="ecommerce",
    )
    return {
        "success": True,
        "customer": {
            "id": int(customer.id),
            "name": customer.nome or "",
            "delivery_address": customer_delivery_address(customer),
        },
        "items": preview_items,
        "subtotal": total,
        "total": total,
        "payment_methods": payment_methods(db, tenant_id),
        "benefits": benefits,
        "delivery": {
            "default_delivery_person_id": default_delivery_person_id(db, tenant_id),
        },
    }


def _request_hash(data: WhatsAppOrderCreateData) -> str:
    payload = data.model_dump() if hasattr(data, "model_dump") else data.dict()
    serialized = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _mark_failed_registry(
    db: Session,
    *,
    tenant_id,
    endpoint: str,
    idempotency_key: str,
    error: str,
) -> None:
    from app.idempotency_models import IdempotencyKey

    db.rollback()
    registry = (
        db.query(IdempotencyKey)
        .filter(
            IdempotencyKey.tenant_id == tenant_id,
            IdempotencyKey.endpoint == endpoint,
            IdempotencyKey.chave_idempotencia == idempotency_key,
        )
        .first()
    )
    if registry and registry.status == "processing":
        registry.status = "failed"
        registry.error_message = error[:1000]
        registry.completed_at = datetime.utcnow()
        db.commit()


def create_order(
    db: Session,
    tenant_id,
    *,
    data: WhatsAppOrderCreateData,
    idempotency_key: str,
    preview_builder: Callable[..., dict[str, Any]] = build_order_preview,
) -> dict[str, Any]:
    from app.idempotency_models import IdempotencyKey
    from app.models import User
    from app.vendas import VendaService
    from app.vendas_models import Venda

    endpoint = "POST /internal/whatsapp-orchestrator/order-create-data"
    request_hash = _request_hash(data)
    order_marker = f"[WhatsApp-ID:{idempotency_key}]"
    try:
        bind = db.get_bind() if hasattr(db, "get_bind") else None
        if bind is not None and bind.dialect.name == "postgresql":
            db.execute(
                text("SELECT pg_advisory_xact_lock(hashtext(:lock_key))"),
                {"lock_key": f"{tenant_id}:{idempotency_key}"},
            )
        existing = (
            db.query(IdempotencyKey)
            .filter(
                IdempotencyKey.tenant_id == tenant_id,
                IdempotencyKey.endpoint == endpoint,
                IdempotencyKey.chave_idempotencia == idempotency_key,
            )
            .first()
        )
        if existing:
            if existing.request_hash != request_hash:
                raise HTTPException(
                    status_code=422,
                    detail="Esta confirmação já foi usada para um pedido diferente.",
                )
            if existing.status == "completed" and existing.response_body:
                return json.loads(existing.response_body)
            if existing.status == "failed":
                recovered_sale = (
                    db.query(Venda)
                    .filter(
                        Venda.tenant_id == tenant_id,
                        Venda.observacoes.contains(order_marker),
                    )
                    .first()
                )
                if recovered_sale:
                    recovered_response = {
                        "success": True,
                        "sale_id": int(recovered_sale.id),
                        "number": recovered_sale.numero_venda,
                        "status": recovered_sale.status or "aberta",
                        "total": float(recovered_sale.total or 0),
                        "payment_method": data.payment_method,
                        "fulfillment": data.fulfillment,
                        "benefits": [],
                    }
                    existing.status = "completed"
                    existing.response_status_code = 200
                    existing.response_body = json.dumps(
                        recovered_response, ensure_ascii=False
                    )
                    existing.completed_at = datetime.utcnow()
                    db.commit()
                    return recovered_response
                db.delete(existing)
                db.commit()
                existing = None
            if existing is not None:
                raise HTTPException(
                    status_code=409,
                    detail="Este pedido já está sendo processado.",
                )

        preview = preview_builder(
            db,
            tenant_id,
            phone=data.phone,
            requested_items=data.items,
        )
        payment_key = str(data.payment_method.get("key") or "").strip().lower()
        available_payment = next(
            (
                method
                for method in preview["payment_methods"]
                if method["key"] == payment_key
            ),
            None,
        )
        if not available_payment:
            raise HTTPException(
                status_code=409,
                detail="A forma de pagamento escolhida não está disponível.",
            )

        delivery_address = (
            str(data.delivery_address or "").strip()
            or str(preview["customer"].get("delivery_address") or "").strip()
        )
        delivery_person_id = preview["delivery"].get("default_delivery_person_id")
        if data.fulfillment == "delivery" and not delivery_address:
            raise HTTPException(
                status_code=409,
                detail="Informe o endereço antes de confirmar a entrega.",
            )
        if data.fulfillment == "delivery" and not delivery_person_id:
            raise HTTPException(
                status_code=409,
                detail="A loja ainda não possui entregador padrão configurado.",
            )

        seller = (
            db.query(User)
            .filter(User.tenant_id == tenant_id, User.is_active.is_(True))
            .order_by(User.is_admin.desc(), User.id.asc())
            .first()
        )
        if not seller:
            raise HTTPException(
                status_code=409,
                detail="A loja não possui usuário ativo para registrar a venda.",
            )

        registry = IdempotencyKey(
            user_id=seller.id,
            tenant_id=tenant_id,
            endpoint=endpoint,
            chave_idempotencia=idempotency_key,
            request_hash=request_hash,
            status="processing",
        )
        db.add(registry)
        db.commit()

        fulfillment_label = (
            "Entrega" if data.fulfillment == "delivery" else "Retirada na loja"
        )
        observations = (
            f"{order_marker} Pedido recebido pelo WhatsApp. "
            f"Modalidade: {fulfillment_label}. "
            f"Forma de pagamento informada: {available_payment['name']}. "
            + (
                f"Troco para R$ {float(data.cash_change_for):.2f}. "
                if payment_key == "dinheiro" and data.cash_change_for is not None
                else "Sem necessidade de troco. "
                if payment_key == "dinheiro"
                else ""
            )
            + "Venda em aberto para conferência e recebimento."
        )
        sale_payload = {
            "cliente_id": preview["customer"]["id"],
            "vendedor_id": seller.id,
            "funcionario_id": None,
            "itens": [
                {
                    "tipo": "produto",
                    "produto_id": item["product_id"],
                    "quantidade": item["quantity"],
                    "preco_unitario": item["unit_price"],
                    "desconto_item": 0,
                    "subtotal": item["subtotal"],
                }
                for item in preview["items"]
            ],
            "desconto_valor": 0,
            "desconto_percentual": 0,
            "observacoes": observations,
            "tem_entrega": data.fulfillment == "delivery",
            "taxa_entrega": 0,
            "percentual_taxa_loja": 0,
            "percentual_taxa_entregador": 0,
            "entregador_id": (
                delivery_person_id if data.fulfillment == "delivery" else None
            ),
            "loja_origem": "whatsapp",
            "endereco_entrega": (
                delivery_address if data.fulfillment == "delivery" else None
            ),
            "observacoes_entrega": (
                "Pedido confirmado pelo cliente no WhatsApp. "
                + (
                    f"Levar troco para R$ {float(data.cash_change_for):.2f}."
                    if payment_key == "dinheiro" and data.cash_change_for is not None
                    else "Não precisa de troco."
                    if payment_key == "dinheiro"
                    else ""
                )
            ).strip(),
            "canal": "whatsapp",
            "tenant_id": str(tenant_id),
        }
        sale = VendaService.criar_venda(
            payload=sale_payload,
            user_id=seller.id,
            db=db,
        )
        sale_row = (
            db.query(Venda)
            .filter(Venda.tenant_id == tenant_id, Venda.id == sale["id"])
            .first()
        )
        if sale_row and data.fulfillment == "pickup":
            sale_row.tipo_retirada = "proprio"
            sale_row.loja_origem = "whatsapp"
            db.commit()

        response = {
            "success": True,
            "sale_id": int(sale["id"]),
            "number": sale.get("numero_venda") or str(sale["id"]),
            "status": "aberta",
            "total": float(sale.get("total") or preview["total"]),
            "payment_method": available_payment,
            "fulfillment": data.fulfillment,
            "benefits": preview["benefits"],
        }
        registry = (
            db.query(IdempotencyKey).filter(IdempotencyKey.id == registry.id).first()
        )
        if registry:
            registry.status = "completed"
            registry.response_status_code = 200
            registry.response_body = json.dumps(response, ensure_ascii=False)
            registry.completed_at = datetime.utcnow()
            db.commit()
        return response
    except HTTPException as error:
        _mark_failed_registry(
            db,
            tenant_id=tenant_id,
            endpoint=endpoint,
            idempotency_key=idempotency_key,
            error=str(error.detail),
        )
        raise
    except Exception as error:
        _mark_failed_registry(
            db,
            tenant_id=tenant_id,
            endpoint=endpoint,
            idempotency_key=idempotency_key,
            error=str(error),
        )
        raise
