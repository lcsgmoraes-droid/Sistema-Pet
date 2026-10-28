"""Cancelamento local do piloto DEV, sem estorno externo nem novo FIFO."""

from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import or_

from app.ifood_order_models import IfoodOrder
from app.pedido_integrado_item_models import PedidoIntegradoItem
from app.pedido_integrado_models import PedidoIntegrado
from app.produtos_models import EstoqueMovimentacao, Produto
from app.vendas_models import VendaItem, VendaPagamento

MOTIVO = "cancelamento_venda"


def _helpers():
    # O modulo publico continua sendo a interface dos servicos de venda.
    from . import pdv_pilot

    return pdv_pilot


def _reservation(db, bridge):
    p = _helpers()
    reservation = (
        db.query(PedidoIntegrado)
        .filter_by(tenant_id=bridge.tenant_id, id=bridge.reservation_id)
        .with_for_update()
        .populate_existing()
        .one_or_none()
    )
    items = (
        db.query(PedidoIntegradoItem)
        .filter_by(
            tenant_id=bridge.tenant_id, pedido_integrado_id=bridge.reservation_id
        )
        .with_for_update()
        .populate_existing()
        .all()
    )
    sold = bridge.status == "sold"
    if (
        reservation is None
        or reservation.canal != "ifood"
        or reservation.pedido_bling_id is not None
        or reservation.status != ("confirmado" if sold else "aberto")
        or len(items) != 1
        or items[0].sku != p.PILOT_SKU
        or p._decimal(items[0].quantidade) != 1
        or items[0].liberado_em is not None
        or bool(items[0].vendido_em) != sold
    ):
        p._blocked(
            "A reserva original do piloto precisa ser conferida antes de cancelar."
        )
    return reservation, items[0]


def _validate_online(db, sale, bridge, values):
    p = _helpers()
    payments = (
        db.query(VendaPagamento)
        .filter_by(tenant_id=sale.tenant_id, venda_id=sale.id)
        .with_for_update()
        .populate_existing()
        .all()
    )
    evidence = bridge.online_financial_evidence
    expected = p._online_evidence(values)
    if not isinstance(evidence, dict) or evidence.get("version") != 1:
        p._blocked("A evidencia original do pagamento online precisa ser conferida.")
    if bridge.status == "reserved":
        valid = not payments and evidence == expected
    else:
        payment = payments[0] if len(payments) == 1 else None
        recorded = evidence.get("payment") or {}
        valid = (
            evidence.get("checkout") == expected["checkout"]
            and payment is not None
            and payment.id == recorded.get("sale_payment_id")
            and payment.gateway_provider == "ifood"
            and payment.gateway_payment_id == values["payment_reference"]
            and payment.numero_transacao == values["payment_reference"]
            and payment.forma_pagamento == "iFood online"
            and payment.status == "aprovado"
            and payment.caixa_id is None
            and p._decimal(payment.valor) == values["total"]
            and recorded.get("reference") == values["payment_reference"]
            and recorded.get("status") == "approved"
            and recorded.get("quitation_basis") == "ifood_liability_order_received"
        )
    if sale.caixa_id is not None or not valid:
        p._blocked("O pagamento online diverge da conclusao externa auditada.")

    # Este piloto nunca criou caixa/banco/recebivel. Nao usar o cancelamento
    # generico para apagar ou estornar um efeito financeiro inesperado.
    from app.caixa_models import MovimentacaoCaixa
    from app.financeiro_models import (
        ContaReceber,
        LancamentoManual,
        MovimentacaoFinanceira,
    )

    if (
        db.query(ContaReceber)
        .filter_by(tenant_id=sale.tenant_id, venda_id=sale.id)
        .first()
        or db.query(MovimentacaoCaixa)
        .filter_by(tenant_id=sale.tenant_id, venda_id=sale.id)
        .first()
        or db.query(MovimentacaoFinanceira)
        .filter_by(tenant_id=sale.tenant_id, origem_tipo="venda", origem_id=sale.id)
        .first()
        or db.query(LancamentoManual)
        .filter(
            LancamentoManual.tenant_id == sale.tenant_id,
            or_(
                LancamentoManual.documento == f"VENDA-{sale.id}",
                LancamentoManual.documento.like(f"VENDA-{sale.id}-%"),
            ),
        )
        .first()
    ):
        p._blocked(
            "Ha efeitos financeiros locais inesperados; confira antes de cancelar o piloto online."
        )


def prepare_cancellation(db, sale):
    p = _helpers()
    candidate = p._sale_bridge(db, sale, lock=False)
    if candidate is None:
        return None
    # A venda ja esta bloqueada pelo servico: Sale -> Order -> Bridge -> reserva.
    order = (
        db.query(IfoodOrder)
        .filter_by(tenant_id=sale.tenant_id, ifood_order_id=candidate.ifood_order_id)
        .with_for_update()
        .populate_existing()
        .one_or_none()
    )
    if order is None:
        p._blocked("O pedido original do piloto nao foi localizado.")
    p._scope(order)
    bridge = p._sale_bridge(db, sale)
    sold = bridge.status == "sold"
    if (
        bridge.status not in {"reserved", "sold"}
        or bridge.merchant_id != order.merchant_id
        or bridge.ifood_order_id != order.ifood_order_id
        or bool(bridge.stock_decreased_at) != sold
        or sale.status != ("finalizada" if sold else "aberta")
    ):
        p._blocked(
            "O estado da venda e da ponte do piloto diverge; confira antes de cancelar."
        )
    values = p._validated_pilot_values(order)
    if values["evidence_hash"] != bridge.evidence_hash:
        p._blocked("A sacola original diverge da reserva; confira antes de cancelar.")
    items = (
        db.query(VendaItem)
        .filter_by(tenant_id=sale.tenant_id, venda_id=sale.id)
        .with_for_update()
        .populate_existing()
        .all()
    )
    if (
        len(items) != 1
        or items[0].produto_id != bridge.product_id
        or items[0].tipo != "produto"
        or items[0].product_variation_id is not None
        or items[0].estoque_origem_tenant_id is not None
        or p._decimal(items[0].quantidade) != 1
        or p._decimal(items[0].preco_unitario) != bridge.unit_price
        or p._decimal(items[0].subtotal) != bridge.unit_price
        or p._decimal(sale.subtotal) != bridge.unit_price
        or p._decimal(sale.total) != values["total"]
        or sale.cliente_id is not None
    ):
        p._blocked(
            "O cancelamento exige o unico item original do piloto, sem alteracoes."
        )
    _reservation(db, bridge)
    if values["payment_mode"] == "online":
        _validate_online(db, sale, bridge, values)
    elif bridge.online_financial_evidence is not None:
        p._blocked("O modo do pagamento diverge da evidencia original.")
    return bridge


def estornar_item_piloto(db, bridge, sale, item, user_id, motivo):
    """Recompoe o saldo e os lotes da unica saida original, na mesma transacao."""
    p = _helpers()
    from app.estoque.devolucao_lotes import (
        preparar_devolucao_lotes,
        recompor_lotes_devolucao,
    )
    from app.estoque.service import EstoqueService
    from app.vendas.devolucao_dre import custo_original_item_devolvido

    if (
        str(item.tenant_id) != str(sale.tenant_id)
        or str(bridge.tenant_id) != str(sale.tenant_id)
        or item.venda_id != sale.id
        or bridge.sale_id != sale.id
        or item.produto_id != bridge.product_id
        or p._decimal(item.quantidade) != 1
    ):
        p._blocked("O item do retorno diverge da venda e da empresa do piloto.")
    product = (
        db.query(Produto)
        .filter_by(tenant_id=sale.tenant_id, id=bridge.product_id, codigo=p.PILOT_SKU)
        .with_for_update()
        .populate_existing()
        .one_or_none()
    )
    if (
        product is None
        or product.tipo_produto != "SIMPLES"
        or not product.controlar_estoque
    ):
        p._blocked("O produto original do piloto precisa ser conferido.")
    proof = item.custo_original_saida
    if not isinstance(proof, dict) or any(
        type(proof.get(key)) is not int
        for key in (
            "versao",
            "venda_id",
            "venda_item_id",
            "produto_id",
            "movimentacao_id",
        )
    ):
        p._blocked("O cancelamento exige a identificacao original da baixa do piloto.")
    captured = proof.get("capturado_em")
    try:
        if not isinstance(captured, str) or "T" not in captured:
            raise ValueError
        datetime.fromisoformat(captured.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        p._blocked("A data da prova original da baixa precisa ser conferida.")
    cost, source, pending = custo_original_item_devolvido(
        db, sale, item, Decimal("1"), sale.tenant_id
    )
    if pending or source != "baixa_estoque_venda" or not isinstance(proof, dict):
        p._blocked("O cancelamento exige o comprovante original da baixa do piloto.")
    moves = (
        db.query(EstoqueMovimentacao)
        .filter_by(
            tenant_id=sale.tenant_id,
            produto_id=product.id,
            referencia_id=sale.id,
            referencia_tipo="venda",
        )
        .with_for_update()
        .populate_existing()
        .all()
    )
    exits = [
        move for move in moves if move.tipo == "saida" and move.status != "cancelado"
    ]
    if (
        len(exits) != 1
        or any(move.tipo == "entrada" for move in moves)
        or exits[0].id != proof.get("movimentacao_id")
        or exits[0].motivo != "venda"
        or p._decimal(exits[0].quantidade) != 1
        or p._decimal(exits[0].valor_total) != cost
    ):
        p._blocked(
            "A saida original ou um retorno anterior exige conciliacao do estoque."
        )
    plan = preparar_devolucao_lotes(
        db,
        produto_id=product.id,
        tenant_id=sale.tenant_id,
        venda_id=sale.id,
        saidas=exits,
        itens_venda=[item],
        quantidades_por_item={item.id: Decimal("1")},
        bloquear=True,
        motivo_entrada=MOTIVO,
    )
    result = EstoqueService.estornar_estoque(
        produto_id=product.id,
        quantidade=1,
        motivo=MOTIVO,
        referencia_id=sale.id,
        referencia_tipo="venda",
        user_id=user_id,
        db=db,
        tenant_id=sale.tenant_id,
        documento=sale.numero_venda,
        observacao=f"Cancelamento local do piloto iFood: {motivo}. Sem estorno financeiro externo.",
        custo_unitario_override=float(cost),
        valor_total_override=float(cost),
    )
    recompor_lotes_devolucao(
        db,
        plan,
        item.id,
        Decimal("1"),
        result["movimentacao_id"],
        motivo_entrada=MOTIVO,
    )
    bridge._pilot_stock_reversal = {
        "movement_id": result["movimentacao_id"],
        "original_movement_id": exits[0].id,
        "quantity": 1,
        "original_cost": str(cost),
    }
    return result


def complete_cancellation(db, bridge):
    if bridge is None:
        return
    p = _helpers()
    reservation, item = _reservation(db, bridge)
    sold = bridge.status == "sold"
    reversal = getattr(bridge, "_pilot_stock_reversal", None)
    if sold and not reversal:
        p._blocked(
            "A devolucao fisica do piloto precisa ser comprovada antes de cancelar."
        )
    if sold:
        entry = (
            db.query(EstoqueMovimentacao)
            .filter_by(
                id=reversal["movement_id"],
                tenant_id=bridge.tenant_id,
                produto_id=bridge.product_id,
                referencia_id=bridge.sale_id,
                referencia_tipo="venda",
                tipo="entrada",
                motivo=MOTIVO,
            )
            .one_or_none()
        )
        if (
            entry is None
            or entry.status == "cancelado"
            or p._decimal(entry.quantidade) != 1
            or p._decimal(entry.valor_total) != p._decimal(reversal["original_cost"])
        ):
            p._blocked(
                "A entrada de retorno do piloto nao corresponde a prova original."
            )
    at = datetime.now(timezone.utc)
    cancellation = {
        "scope": "local_dev",
        "cancelled_at": at.isoformat(),
        "stock_restored": sold,
        "stock_reversal": reversal,
        "provider_cancellation_confirmed": False,
        "refund_status": "pending_provider_review"
        if bridge.online_financial_evidence
        else "not_online",
        "refunded_amount": None,
    }
    item.liberado_em = datetime.utcnow()
    reservation.status = "cancelado"
    reservation.cancelado_em = datetime.utcnow()
    reservation.payload = {
        **(reservation.payload or {}),
        "pilot_cancellation": cancellation,
    }
    bridge.status = "cancelled"
    bridge.cancelled_at = at
    if bridge.online_financial_evidence:
        evidence = dict(bridge.online_financial_evidence)
        evidence["receivable"] = {
            **evidence["receivable"],
            "status": "cancelled_pending_provider_review",
        }
        evidence["cancellation"] = cancellation
        bridge.online_financial_evidence = evidence


def cancellation_summary(db, bridge):
    if bridge.status != "cancelled":
        return {"stock_restored": False, "cancellation": None}
    reservation = (
        db.query(PedidoIntegrado)
        .filter_by(tenant_id=bridge.tenant_id, id=bridge.reservation_id)
        .one_or_none()
    )
    data = (
        (reservation.payload or {}).get("pilot_cancellation") if reservation else None
    )
    return {
        "stock_restored": bool(data and data.get("stock_restored")),
        "cancellation": data,
    }
