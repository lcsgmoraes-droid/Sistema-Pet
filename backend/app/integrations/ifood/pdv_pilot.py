"""Piloto DEV assistido: pedido de teste -> reserva -> baixa normal do PDV.

Nao consulta o provedor, nao confirma pedido remoto e nunca habilita producao.
O registro de reserva usa o mesmo PedidoIntegradoItem dos demais pedidos.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import hashlib
import json
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import or_, text

from app.config import _is_strict_runtime_environment, settings
from app.ifood_order_models import IfoodEvent, IfoodOrder, IfoodPdvBridge

PILOT_SKU = "018631.1"
_ACTIVE_STATUSES = {
    "PLACED",
    "CONFIRMED",
    "PREPARATION_STARTED",
    "SEPARATION_STARTED",
    "SEPARATION_ENDED",
    "READY_TO_PICKUP",
}


def _blocked(reason: str):
    raise HTTPException(409, reason)


def _object(value, field: str) -> dict:
    if not isinstance(value, dict):
        _blocked(f"Estrutura invalida no pedido de teste: {field}.")
    return value


def _decimal(value) -> Decimal:
    if isinstance(value, bool):
        _blocked("Quantidade ou valor invalido no pedido de teste.")
    try:
        result = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        _blocked("Quantidade ou valor ausente no pedido de teste.")
    if not result.is_finite():
        _blocked("Quantidade ou valor invalido no pedido de teste.")
    return result


def _money(value, field: str) -> Decimal:
    money = _object(value, field)
    cents = _decimal(money.get("value"))
    if (
        money.get("currency", "BRL") != "BRL"
        or cents < 0
        or cents > Decimal("9999999999")
        or cents != cents.to_integral_value()
    ):
        _blocked("O piloto exige valores nao negativos em centavos de reais (BRL).")
    return cents / 100


def _zero_money(value, field: str):
    if _money(value, field) != 0:
        _blocked("Este piloto aceita somente taxas e descontos explicitamente zerados.")


def _pilot_operation(payload: dict) -> tuple[str, Decimal]:
    operation = _object(payload.get("operationMode"), "operationMode")
    mode = operation.get("type")
    if mode in {"TAKEOUT", "TAKE-OUT"}:
        return "TAKEOUT", Decimal(0)
    if mode != "DELIVERY":
        _blocked("A modalidade do pedido nao e suportada pelo piloto DEV.")
    delivery = _object(operation.get("delivery"), "operationMode.delivery")
    prices = _object(delivery.get("prices"), "operationMode.delivery.prices")
    shipping = _money(
        prices.get("grossValue"), "operationMode.delivery.prices.grossValue"
    )
    if "discount" in prices:
        _zero_money(prices["discount"], "operationMode.delivery.prices.discount")
    if (
        "netValue" in prices
        and _money(prices["netValue"], "operationMode.delivery.prices.netValue")
        != shipping
    ):
        _blocked("O frete liquido diverge do frete bruto; confira a cobranca do iFood.")
    return "DELIVERY", shipping


def _validate_pilot_fees_and_benefits(payload: dict, bag: dict):
    if "fees" in payload:
        fees = payload["fees"]
        if not isinstance(fees, list):
            _blocked("Confira as taxas do pedido; estrutura desconhecida no piloto.")
        for fee in fees:
            fee = _object(fee, "fees[]")
            prices = _object(fee.get("prices"), "fees[].prices")
            for key in ("grossValue", "discount", "netValue"):
                _zero_money(prices.get(key), f"fees[].prices.{key}")
    nested = payload.get("benefit")
    if nested is not None:
        nested = _object(nested, "benefit")
        if nested.get("benefits"):
            _blocked("Cupons e beneficios nao fazem parte deste piloto de estoque.")
    if payload.get("benefits") or payload.get("coupons") or bag.get("benefits"):
        _blocked("Cupons e beneficios nao fazem parte deste piloto de estoque.")


def pilot_settings_reason(
    *, tenant_id=None, merchant_id=None, order_id=None, require_order=True
) -> str | None:
    if _is_strict_runtime_environment() or str(
        settings.ENVIRONMENT
    ).strip().lower() not in {"development", "dev", "test", "local"}:
        return "O piloto do PDV iFood e exclusivo do DEV; producao e staging estao bloqueados."
    if not settings.IFOOD_PDV_PILOT_ENABLED:
        return "O piloto DEV do PDV iFood esta desabilitado."
    try:
        configured_tenant = str(UUID(settings.IFOOD_PDV_PILOT_TENANT_ID))
        configured_merchant = str(UUID(settings.IFOOD_PDV_PILOT_MERCHANT_ID))
    except (ValueError, TypeError, AttributeError):
        return "Configure explicitamente a empresa e a loja de testes do piloto."
    if settings.IFOOD_PDV_PILOT_SKU != PILOT_SKU or (
        require_order and not str(settings.IFOOD_PDV_PILOT_ORDER_ID or "").strip()
    ):
        return "Configure o pedido de teste e o SKU 018631.1 antes de importar."
    if tenant_id is not None and str(tenant_id) != configured_tenant:
        return "Esta empresa nao esta autorizada no piloto DEV."
    if merchant_id is not None and str(merchant_id) != configured_merchant:
        return "Esta loja nao esta autorizada no piloto DEV."
    if (
        order_id is not None
        and str(order_id) != settings.IFOOD_PDV_PILOT_ORDER_ID.strip()
    ):
        return "Somente o pedido de teste configurado pode entrar no PDV."
    return None


def _scope(order: IfoodOrder):
    reason = pilot_settings_reason(
        tenant_id=order.tenant_id,
        merchant_id=order.merchant_id,
        order_id=order.ifood_order_id,
    )
    if reason:
        _blocked(reason)


def validate_pilot_payload(order: IfoodOrder) -> dict:
    """Contrato Groceries Virtual Bag; desconhecidos falham sem movimentacao."""
    _scope(order)
    if str(order.status or "").upper() not in _ACTIVE_STATUSES:
        _blocked(
            "Pedido encerrado, cancelado ou com estado desconhecido nao pode criar reserva retroativa."
        )
    return _validated_pilot_values(order)


def pilot_order_display_total(order: IfoodOrder) -> Decimal:
    """Exibe valores conferidos mesmo apos encerrar, sem autorizar movimentacao."""
    _scope(order)
    return _validated_pilot_values(order)["total"]


def _validated_pilot_values(order: IfoodOrder) -> dict:
    payload = _object(order.payload, "pedido")
    if payload.get("test") is not True:
        _blocked("Somente pedidos oficiais marcados test=true podem entrar neste DEV.")
    if (
        str(_object(payload.get("merchant"), "merchant").get("id") or "")
        != order.merchant_id
    ):
        _blocked("A loja do pedido diverge da loja de teste autorizada.")
    if str(payload.get("id") or "") != order.ifood_order_id:
        _blocked("O identificador da sacola diverge do pedido autorizado.")
    operation_type, shipping_price = _pilot_operation(payload)
    bag = _object(payload.get("bag"), "bag")
    _validate_pilot_fees_and_benefits(payload, bag)
    items = bag.get("items")
    if not isinstance(items, list) or len(items) != 1 or not isinstance(items[0], dict):
        _blocked("O pedido de teste deve conter somente um item do SKU 018631.1.")
    item = items[0]
    product_info = _object(item.get("product"), "item.product")
    if (
        not isinstance(item.get("uniqueId"), str)
        or not item["uniqueId"].strip()
        or product_info.get("isVariableWeight") is not False
    ):
        _blocked(
            "O piloto exige identificador do item e unidade fixa, sem pesagem variavel."
        )
    if item.get("unavailable") is not False:
        _blocked("O item deve estar explicitamente disponivel na sacola de teste.")
    if _decimal(item.get("quantity")) != 1:
        _blocked("Este piloto aceita exatamente uma unidade do SKU 018631.1.")
    ean = str(item.get("ean") or "").strip()
    if len(ean) != 13 or not ean.isdigit():
        _blocked("O item do pedido precisa informar o mesmo EAN do cadastro.")
    unit_value = _object(
        _object(item.get("prices"), "item.prices").get("unitValue"), "unitValue"
    )
    gross_value = _object(
        _object(bag.get("prices"), "bag.prices").get("grossValue"), "grossValue"
    )
    price = _money(unit_value, "unitValue")
    gross = _money(gross_value, "grossValue")
    total = gross + shipping_price
    if price <= 0 or gross != price or total > Decimal("99999999.99"):
        _blocked(
            "Este piloto exige preco unitario positivo e subtotal igual ao unico item, sem desconto."
        )
    methods = _object(payload.get("payment"), "payment").get("methods")
    if not isinstance(methods, list) or len(methods) != 1:
        _blocked("Confira a forma de pagamento presencial do pedido de teste.")
    total_payment = Decimal(0)
    for method in methods:
        if (
            not isinstance(method, dict)
            or method.get("inPerson") is not True
            or str(method.get("name") or "").strip().lower() not in {"cash", "dinheiro"}
        ):
            _blocked(
                "Este piloto aceita somente dinheiro presencial; online, cartao, misto ou desconhecido esta bloqueado."
            )
        payment_amount = _object(method.get("amount"), "payment.amount")
        amount = _money(payment_amount, "payment.amount")
        if amount <= 0:
            _blocked("Valor de pagamento presencial invalido.")
        total_payment += amount
    if total_payment != total:
        _blocked("O pagamento precisa corresponder aos itens mais o frete do pedido.")
    evidence = {
        "order_id": order.ifood_order_id,
        "merchant_id": order.merchant_id,
        "item_id": item["uniqueId"],
        "ean": ean,
        "sku": PILOT_SKU,
        "quantity": "1",
        "price": str(price.quantize(Decimal(".01"))),
        "shipping_price": str(shipping_price.quantize(Decimal(".01"))),
        "total": str(total.quantize(Decimal(".01"))),
        "type": operation_type,
        "payment": methods,
    }
    evidence_hash = hashlib.sha256(
        json.dumps(evidence, sort_keys=True, ensure_ascii=False).encode()
    ).hexdigest()
    return {
        "ean": ean,
        "quantity": Decimal(1),
        "price": price,
        "shipping_price": shipping_price,
        "total": total,
        "operation_type": operation_type,
        "evidence_hash": evidence_hash,
    }


def _product(db, order, validated, *, lock=False):
    from app.produtos_models import Produto

    query = db.query(Produto).filter(
        Produto.tenant_id == order.tenant_id, Produto.codigo == PILOT_SKU
    )
    if lock:
        query = query.with_for_update().populate_existing()
    products = query.all()
    if len(products) != 1:
        _blocked(
            "O SKU do piloto precisa corresponder a um unico produto desta empresa."
        )
    product = products[0]
    if (
        product.tipo_produto != "SIMPLES"
        or str(product.unidade or "").upper() != "UN"
        or not product.controlar_estoque
        or not product.ativo
        or not product.is_sellable
        or product.deleted_at is not None
    ):
        _blocked(
            "O piloto aceita somente produto simples, ativo e controlado em unidade UN."
        )
    eans = {
        str(getattr(product, name, None) or "").strip()
        for name in ("codigo_barras", "gtin_ean", "gtin_ean_tributario")
    }
    if validated["ean"] not in eans:
        _blocked("O EAN do pedido nao corresponde ao SKU 018631.1 nesta empresa.")
    return product


def _bridge(db, *, tenant_id, sale_id=None, order_id=None, lock=False):
    query = db.query(IfoodPdvBridge).filter(IfoodPdvBridge.tenant_id == tenant_id)
    query = (
        query.filter(IfoodPdvBridge.sale_id == sale_id)
        if sale_id is not None
        else query.filter(IfoodPdvBridge.ifood_order_id == order_id)
    )
    if lock:
        query = query.with_for_update().populate_existing()
    return query.first()


def _aware(value):
    if value is None:
        return None
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value


def pilot_bag_review_reason(db, order, bridge=None):
    """Eventos de alteracao nao tornam um hash anterior prova de sacola atual."""
    reason = "A sacola recebeu alteracao ou terminou a separacao. Consulte novamente Orders Virtual Bag e confira o mesmo item antes de finalizar o piloto."
    if order.last_action == "pdv_bag_review_required":
        return reason
    query = db.query(IfoodEvent).filter(
        IfoodEvent.tenant_id == order.tenant_id,
        IfoodEvent.ifood_order_id == order.ifood_order_id,
        or_(
            IfoodEvent.code.in_(("OPA", "SPE", "ORDER_PATCHED", "SEPARATION_ENDED")),
            IfoodEvent.full_code.in_(("ORDER_PATCHED", "PATCHED", "SEPARATION_ENDED")),
        ),
    )
    if bridge is not None:
        query = query.filter(
            or_(
                IfoodEvent.processed_at.is_(None),
                IfoodEvent.processed_at >= bridge.created_at,
            )
        )
    events = query.all()
    reviewed_at = (
        _aware(order.last_action_at)
        if order.last_action == "pdv_bag_reviewed"
        else None
    )
    if any(
        event.processed_at is None
        or reviewed_at is None
        or _aware(event.processed_at) > reviewed_at
        for event in events
    ):
        return reason
    return None


def confirm_pilot_bag_review(db, order):
    """Somente o GET fresco sob lock pode aprovar o espelho, sem mudar reserva."""
    if pilot_settings_reason(
        tenant_id=order.tenant_id,
        merchant_id=order.merchant_id,
        order_id=order.ifood_order_id,
    ):
        return
    bridge = _bridge(db, tenant_id=order.tenant_id, order_id=order.ifood_order_id)
    try:
        validated = validate_pilot_payload(order)
        if bridge is not None and (
            bridge.status != "reserved"
            or validated["evidence_hash"] != bridge.evidence_hash
        ):
            _blocked("A sacola atual diverge do item reservado no PDV de teste.")
    except HTTPException:
        order.last_action = "pdv_bag_review_required"
    else:
        order.last_action = "pdv_bag_reviewed"
    order.last_action_at = datetime.now(timezone.utc)


def pdv_bridge_summary(db, order: IfoodOrder) -> dict:
    reason = pilot_settings_reason(
        tenant_id=order.tenant_id,
        merchant_id=order.merchant_id,
        order_id=order.ifood_order_id,
    )
    summary = {
        "enabled": pilot_settings_reason(
            tenant_id=order.tenant_id, merchant_id=order.merchant_id
        )
        is None,
        "eligible": False,
        "status": "blocked" if reason else "not_imported",
        "sale_id": None,
        "reserved_quantity": 0,
        "stock_decreased": False,
        "reason": reason,
    }
    if reason:
        return summary
    bridge = _bridge(db, tenant_id=order.tenant_id, order_id=order.ifood_order_id)
    if bridge:
        return {
            **summary,
            "status": bridge.status,
            "sale_id": bridge.sale_id,
            "reserved_quantity": (
                float(bridge.quantity) if bridge.status == "reserved" else 0
            ),
            "stock_decreased": bridge.stock_decreased_at is not None,
            "reason": pilot_bag_review_reason(db, order, bridge)
            or "Pedido ja vinculado ao PDV de teste.",
        }
    try:
        validated = validate_pilot_payload(order)
        _product(db, order, validated)
        review_reason = pilot_bag_review_reason(db, order)
        if review_reason:
            _blocked(review_reason)
    except HTTPException as exc:
        return {**summary, "reason": str(exc.detail), "status": "blocked"}
    return {**summary, "eligible": True, "reason": None}


def import_pdv_pilot(db, *, tenant_id, order_id: str, actor_id: int) -> IfoodOrder:
    """Uma transacao: venda reservada + pedido integrado + vinculo, sem baixa."""
    from app.estoque_reserva_service import EstoqueReservaService
    from app.models import User
    from app.pedido_integrado_models import PedidoIntegrado
    from app.pedido_integrado_item_models import PedidoIntegradoItem
    from app.vendas_models import Venda, VendaItem
    from app.vendas.numeracao import gerar_numero_venda
    from app.utils.timezone import now_brasilia

    reason = pilot_settings_reason(tenant_id=tenant_id, order_id=order_id)
    if reason:
        _blocked(reason)
    order = (
        db.query(IfoodOrder)
        .filter(
            IfoodOrder.tenant_id == tenant_id, IfoodOrder.ifood_order_id == order_id
        )
        .with_for_update()
        .populate_existing()
        .first()
    )
    if not order:
        raise HTTPException(404, "Pedido de teste iFood nao encontrado nesta empresa.")
    _scope(order)
    from app.ifood_integration_models import IfoodMerchantConfig

    config = (
        db.query(IfoodMerchantConfig)
        .filter(
            IfoodMerchantConfig.tenant_id == tenant_id,
            IfoodMerchantConfig.active.is_(True),
            IfoodMerchantConfig.merchant_id == order.merchant_id,
        )
        .first()
    )
    if config is None:
        _blocked("Confira o vinculo ativo desta empresa com a loja de teste.")
    # A linha do pedido serializa importacoes; uma repeticao nao altera o
    # vinculo e nao deve inverter Order->Bridge contra a finalizacao.
    if _bridge(db, tenant_id=tenant_id, order_id=order_id):
        return order
    validated = validate_pilot_payload(order)
    review_reason = pilot_bag_review_reason(db, order)
    if review_reason:
        _blocked(review_reason)
    product = _product(db, order, validated, lock=True)
    actor = (
        db.query(User).filter(User.id == actor_id, User.tenant_id == tenant_id).first()
    )
    if actor is None:
        _blocked("O responsavel pelo piloto deve pertencer a esta empresa DEV.")
    reserved = EstoqueReservaService.quantidade_reservada_produto(
        db, tenant_id, product
    )
    if Decimal(str(product.estoque_atual or 0)) - Decimal(str(reserved)) < 1:
        _blocked("Saldo disponivel insuficiente para reservar uma unidade no piloto.")
    # Serializa a numeracao deste importador sem depender de um ID externo falso.
    if db.bind.dialect.name == "postgresql":
        db.execute(
            text("SELECT pg_advisory_xact_lock(hashtextextended(:key, 0))"),
            {"key": f"ifood-pdv-sale-number:{tenant_id}"},
        )
    reservation = PedidoIntegrado(
        tenant_id=tenant_id,
        pedido_bling_id=None,
        pedido_bling_numero=None,
        canal="ifood",
        status="aberto",
        expira_em=PedidoIntegrado.calcular_expiracao(),
        payload={
            "source": "ifood",
            "test": True,
            "ifood_order_id": order_id,
            "merchant_id": order.merchant_id,
        },
    )
    db.add(reservation)
    db.flush()
    reservation_item = PedidoIntegradoItem(
        tenant_id=tenant_id,
        pedido_integrado_id=reservation.id,
        sku=product.codigo,
        descricao=product.nome,
        quantidade=1,
    )
    sale = Venda(
        tenant_id=tenant_id,
        numero_venda=gerar_numero_venda(db, tenant_id, actor_id),
        vendedor_id=actor_id,
        user_id=actor_id,
        subtotal=validated["price"],
        total=validated["total"],
        desconto_valor=0,
        desconto_venda_valor=0,
        desconto_percentual=0,
        canal="ifood",
        status="aberta",
        tem_entrega=validated["operation_type"] == "DELIVERY",
        taxa_entrega=validated["shipping_price"],
        tipo_retirada="proprio" if validated["operation_type"] == "TAKEOUT" else None,
        status_entrega="pendente",
        nao_gerar_beneficios=True,
        justificativa_nao_gerar_beneficios="Pedido oficial de teste iFood em DEV.",
        observacoes=f"TESTE iFood {order.display_id or order_id}. Estoque reservado; baixa unica na finalizacao do PDV.",
        data_venda=now_brasilia(),
    )
    db.add_all([reservation_item, sale])
    db.flush()
    sale_item = VendaItem(
        tenant_id=tenant_id,
        venda_id=sale.id,
        tipo="produto",
        produto_id=product.id,
        quantidade=1,
        preco_unitario=validated["price"],
        subtotal=validated["price"],
        desconto_item=0,
        ignorar_recorrencia=True,
    )
    bridge = IfoodPdvBridge(
        tenant_id=tenant_id,
        merchant_id=order.merchant_id,
        ifood_order_id=order_id,
        sale_id=sale.id,
        reservation_id=reservation.id,
        product_id=product.id,
        quantity=1,
        unit_price=validated["price"],
        evidence_hash=validated["evidence_hash"],
        status="reserved",
        actor_id=actor_id,
    )
    db.add_all([sale_item, bridge])
    db.flush()
    return order


def block_pilot_picking_edit(db, order):
    # Sem consulta nova para instalacoes e origens fora do piloto DEV.
    if pilot_settings_reason(
        tenant_id=order.tenant_id,
        merchant_id=order.merchant_id,
        order_id=order.ifood_order_id,
    ):
        return
    if _bridge(db, tenant_id=order.tenant_id, order_id=order.ifood_order_id):
        _blocked(
            "O item ja esta reservado no PDV de teste. A sacola nao pode ser alterada neste piloto."
        )


def _sale_bridge(db, sale, *, lock=True):
    if str(getattr(sale, "canal", None) or "").lower() != "ifood":
        return None
    # Nao permite usar o canal como atalho de criacao/finalizacao em producao.
    reason = pilot_settings_reason(tenant_id=sale.tenant_id)
    if reason:
        _blocked(reason)
    bridge = _bridge(db, tenant_id=sale.tenant_id, sale_id=sale.id, lock=lock)
    if bridge is None:
        _blocked("Venda iFood sem o vinculo auditavel do piloto DEV.")
    return bridge


def block_pilot_sale_edit(db, sale):
    if str(getattr(sale, "canal", None) or "").lower() == "ifood":
        _sale_bridge(db, sale)
        _blocked(
            "Itens, precos e status da venda iFood de teste sao preservados. Use Finalizar ou Cancelar."
        )


def is_pilot_external_delivery(db, sale) -> bool:
    """Dispensa apenas entregador LOCAL; a modalidade verdadeira e preservada.

    Nao autoriza operacoes logisticas, nem enfraquece os locks/validacoes feitos
    novamente pelo finalizador antes da baixa fisica.
    """
    if str(getattr(sale, "canal", None) or "").lower() != "ifood":
        return False
    bridge = _sale_bridge(db, sale, lock=False)
    if bridge.status != "reserved":
        return False
    order = (
        db.query(IfoodOrder)
        .filter(
            IfoodOrder.tenant_id == sale.tenant_id,
            IfoodOrder.ifood_order_id == bridge.ifood_order_id,
        )
        .populate_existing()
        .first()
    )
    if order is None:
        return False
    validated = validate_pilot_payload(order)
    review_reason = pilot_bag_review_reason(db, order, bridge)
    if review_reason:
        _blocked(review_reason)
    return (
        validated["operation_type"] == "DELIVERY"
        and validated["evidence_hash"] == bridge.evidence_hash
        and bool(sale.tem_entrega)
        and not sale.entregador_id
    )


def prepare_pilot_finalization(db, sale, pagamentos, *, cupom_code=None):
    candidate = _sale_bridge(db, sale, lock=False)
    if candidate is None:
        return None
    order = (
        db.query(IfoodOrder)
        .filter(
            IfoodOrder.tenant_id == sale.tenant_id,
            IfoodOrder.ifood_order_id == candidate.ifood_order_id,
        )
        .with_for_update()
        .populate_existing()
        .first()
    )
    if not order:
        _blocked("O pedido de origem do piloto nao foi localizado.")
    # A venda ja foi travada pelo finalizador: Sale -> Order -> Bridge -> Item.
    # Polling que altera/cancela Order espera o mesmo limite de commit da baixa.
    bridge = _sale_bridge(db, sale)
    if bridge.status != "reserved" or bridge.stock_decreased_at is not None:
        _blocked(
            "A reserva deste pedido ja foi encerrada; nao e permitida uma nova baixa."
        )
    from app.pedido_integrado_item_models import PedidoIntegradoItem
    from app.pedido_integrado_models import PedidoIntegrado

    reservation = (
        db.query(PedidoIntegrado)
        .filter(
            PedidoIntegrado.tenant_id == sale.tenant_id,
            PedidoIntegrado.id == bridge.reservation_id,
        )
        .with_for_update()
        .populate_existing()
        .one()
    )
    reservation_items = (
        db.query(PedidoIntegradoItem)
        .filter(
            PedidoIntegradoItem.tenant_id == sale.tenant_id,
            PedidoIntegradoItem.pedido_integrado_id == bridge.reservation_id,
        )
        .with_for_update()
        .populate_existing()
        .all()
    )
    if (
        reservation.canal != "ifood"
        or reservation.pedido_bling_id is not None
        or reservation.status != "aberto"
        or len(reservation_items) != 1
        or reservation_items[0].sku != PILOT_SKU
        or reservation_items[0].quantidade != 1
        or reservation_items[0].vendido_em is not None
        or reservation_items[0].liberado_em is not None
    ):
        _blocked(
            "A reserva ativa deste unico item precisa ser conferida antes da baixa."
        )
    validated = validate_pilot_payload(order)
    review_reason = pilot_bag_review_reason(db, order, bridge)
    if review_reason:
        _blocked(review_reason)
    if validated["evidence_hash"] != bridge.evidence_hash:
        _blocked(
            "A sacola do iFood mudou depois da reserva; confira antes de finalizar."
        )
    product = _product(db, order, validated, lock=True)
    from app.vendas_models import VendaItem

    items = (
        db.query(VendaItem)
        .filter(VendaItem.tenant_id == sale.tenant_id, VendaItem.venda_id == sale.id)
        .with_for_update()
        .populate_existing()
        .all()
    )
    if (
        len(items) != 1
        or items[0].produto_id != bridge.product_id
        or items[0].product_variation_id
        or items[0].estoque_origem_tenant_id
        or _decimal(items[0].quantidade) != 1
        or _decimal(items[0].preco_unitario) != bridge.unit_price
        or _decimal(items[0].subtotal) != bridge.unit_price
        or _decimal(sale.subtotal) != bridge.unit_price
        or _decimal(sale.total) != validated["total"]
        or bool(sale.tem_entrega) != (validated["operation_type"] == "DELIVERY")
        or (
            validated["operation_type"] == "DELIVERY" and sale.tipo_retirada is not None
        )
        or _decimal(sale.taxa_entrega or 0) != validated["shipping_price"]
        or sale.entregador_id is not None
        or cupom_code
        or sale.cupom_code
        or _decimal(sale.desconto_valor or 0) != 0
    ):
        _blocked("A venda do piloto diverge do unico item reservado.")
    from app.estoque_reserva_service import EstoqueReservaService

    # A reserva atual ja inclui este pedido; toda a cobertura precisa existir.
    if Decimal(str(product.estoque_atual or 0)) < Decimal(
        str(
            EstoqueReservaService.quantidade_reservada_produto(
                db, sale.tenant_id, product
            )
        )
    ):
        _blocked("O saldo fisico nao cobre as reservas atuais do produto.")
    if (
        len(pagamentos or []) != 1
        or sum((_decimal(p.get("valor")) for p in pagamentos), Decimal(0))
        != validated["total"]
        or str(pagamentos[0].get("forma_pagamento") or "").strip().lower()
        not in {"cash", "dinheiro"}
    ):
        _blocked(
            "Registre exatamente o pagamento presencial do pedido de teste, sem excedente ou credito."
        )
    if pagamentos[0].get("forma_pagamento_id"):
        from app.financeiro_models import FormaPagamento

        form = (
            db.query(FormaPagamento)
            .filter(
                FormaPagamento.tenant_id == sale.tenant_id,
                FormaPagamento.id == pagamentos[0]["forma_pagamento_id"],
                FormaPagamento.ativo.is_(True),
            )
            .first()
        )
        if form is None or form.tipo != "dinheiro":
            _blocked(
                "A forma de pagamento do PDV deve ser dinheiro, como no pedido iFood de teste."
            )
    return bridge


def complete_pilot_finalization(db, bridge):
    """Chamado antes do MESMO commit que confirma a baixa FIFO normal."""
    if bridge is None:
        return
    from app.pedido_integrado_item_models import PedidoIntegradoItem
    from app.pedido_integrado_models import PedidoIntegrado

    item = (
        db.query(PedidoIntegradoItem)
        .filter(
            PedidoIntegradoItem.tenant_id == bridge.tenant_id,
            PedidoIntegradoItem.pedido_integrado_id == bridge.reservation_id,
        )
        .with_for_update()
        .one()
    )
    if item.vendido_em or item.liberado_em:
        _blocked("A reserva do piloto ja foi encerrada.")
    item.vendido_em = datetime.utcnow()
    reservation = (
        db.query(PedidoIntegrado)
        .filter(
            PedidoIntegrado.tenant_id == bridge.tenant_id,
            PedidoIntegrado.id == bridge.reservation_id,
        )
        .one()
    )
    reservation.status = "confirmado"
    reservation.confirmado_em = datetime.utcnow()
    bridge.status = "sold"
    bridge.stock_decreased_at = datetime.now(timezone.utc)


def prepare_pilot_cancellation(db, sale):
    bridge = _sale_bridge(db, sale)
    if bridge is None:
        return None
    if bridge.status not in {"reserved", "sold"}:
        _blocked("O vinculo deste pedido ja esta cancelado.")
    return bridge


def complete_pilot_cancellation(db, bridge):
    if bridge is None:
        return
    from app.pedido_integrado_item_models import PedidoIntegradoItem
    from app.pedido_integrado_models import PedidoIntegrado

    item = (
        db.query(PedidoIntegradoItem)
        .filter(
            PedidoIntegradoItem.tenant_id == bridge.tenant_id,
            PedidoIntegradoItem.pedido_integrado_id == bridge.reservation_id,
        )
        .with_for_update()
        .one()
    )
    if not item.liberado_em:
        item.liberado_em = datetime.utcnow()
    reservation = (
        db.query(PedidoIntegrado)
        .filter(
            PedidoIntegrado.tenant_id == bridge.tenant_id,
            PedidoIntegrado.id == bridge.reservation_id,
        )
        .one()
    )
    reservation.status = "cancelado"
    reservation.cancelado_em = datetime.utcnow()
    bridge.status = "cancelled"
    bridge.cancelled_at = datetime.now(timezone.utc)
