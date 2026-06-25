"""Cupons, cashback e beneficios previstos para o PDV mobile."""

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.campaigns.channel_scope import (
    campaign_allows_sale_channel,
    normalize_benefit_channel,
)
from app.campaigns.coupon_service import preview_coupon_redemption
from app.campaigns.models import (
    Campaign,
    CampaignStatusEnum,
    CampaignTypeEnum,
    CashbackTransaction,
    Coupon,
    CouponChannelEnum,
    CouponStatusEnum,
)
from app.db import get_session
from app.models import User
from app.produtos_models import Produto
from app.routes.ecommerce_auth import (
    _cashback_disponivel_clause,
    _get_current_ecommerce_user,
)

from .auth import _get_funcionario_operacional_or_403
from .clientes import _buscar_cliente_pdv_funcionario
from .common import _round_money_funcionario_pdv
from .schemas import (
    FuncionarioPdvBeneficiosPreviewRequest,
    FuncionarioPdvBeneficiosPreviewResponse,
    FuncionarioPdvItemRequest,
)

router = APIRouter()


def _listar_cupons_disponiveis_funcionario_pdv(
    db: Session,
    *,
    tenant_id: str,
    cliente_id: Optional[int],
    subtotal: float,
) -> list[dict]:
    filtros_cliente = [Coupon.customer_id.is_(None)]
    if cliente_id:
        filtros_cliente.append(Coupon.customer_id == cliente_id)

    cupons = (
        db.query(Coupon)
        .filter(
            Coupon.tenant_id == tenant_id,
            Coupon.status == CouponStatusEnum.active,
            Coupon.channel.in_([CouponChannelEnum.pdv, CouponChannelEnum.all]),
            or_(*filtros_cliente),
        )
        .order_by(Coupon.created_at.desc())
        .limit(20)
        .all()
    )

    disponiveis = []
    for cupom in cupons:
        try:
            preview = preview_coupon_redemption(
                db,
                tenant_id=tenant_id,
                code=cupom.code,
                venda_total=subtotal,
                customer_id=cliente_id,
            )
        except HTTPException:
            continue

        disponiveis.append(
            {
                "code": preview["code"],
                "coupon_type": preview["coupon_type"],
                "discount_value": preview.get("discount_value"),
                "discount_percent": preview.get("discount_percent"),
                "discount_applied": _round_money_funcionario_pdv(
                    preview.get("discount_applied")
                ),
                "min_purchase_value": (
                    float(cupom.min_purchase_value)
                    if cupom.min_purchase_value
                    else None
                ),
                "valid_until": cupom.valid_until.isoformat()
                if cupom.valid_until
                else None,
            }
        )
    return disponiveis


def _saldo_cashback_funcionario_pdv(
    db: Session,
    *,
    tenant_id: str,
    cliente_id: Optional[int],
) -> float:
    if not cliente_id:
        return 0.0
    saldo_raw = (
        db.query(func.sum(CashbackTransaction.amount))
        .filter(
            CashbackTransaction.tenant_id == tenant_id,
            CashbackTransaction.customer_id == cliente_id,
            _cashback_disponivel_clause(
                CashbackTransaction, datetime.now(timezone.utc)
            ),
        )
        .scalar()
    )
    return max(0.0, _round_money_funcionario_pdv(saldo_raw))


def _cashback_bonus_param_key_funcionario_pdv(sale_channel: str) -> str:
    channel = normalize_benefit_channel(sale_channel)
    if channel == "app":
        return "app_bonus_percent"
    if channel == "ecommerce":
        return "ecommerce_bonus_percent"
    return "pdv_bonus_percent"


def _param_float_funcionario_pdv(params: dict, *keys: str, default: float = 0) -> float:
    for key in keys:
        valor = params.get(key)
        if valor is None or valor == "":
            continue
        try:
            return float(valor)
        except (TypeError, ValueError):
            continue
    return default


def _param_int_funcionario_pdv(params: dict, *keys: str, default: int = 0) -> int:
    for key in keys:
        valor = params.get(key)
        if valor is None or valor == "":
            continue
        try:
            return int(float(valor))
        except (TypeError, ValueError):
            continue
    return default


def _calcular_beneficios_gerados_funcionario_pdv(
    db: Session,
    *,
    tenant_id: str,
    cliente_id: Optional[int],
    total_venda: float,
) -> list[dict]:
    if total_venda <= 0:
        return []

    sale_channel = "loja_fisica"
    campanhas = (
        db.query(Campaign)
        .filter(
            Campaign.tenant_id == tenant_id,
            Campaign.status == CampaignStatusEnum.active,
            Campaign.campaign_type.in_(
                [
                    CampaignTypeEnum.cashback,
                    CampaignTypeEnum.loyalty_stamp,
                    CampaignTypeEnum.quick_repurchase,
                ]
            ),
        )
        .order_by(Campaign.priority.asc(), Campaign.id.asc())
        .all()
    )

    beneficios: list[dict] = []
    for campanha in campanhas:
        if not campaign_allows_sale_channel(campanha, sale_channel):
            continue

        params = campanha.params or {}
        min_purchase_value = _param_float_funcionario_pdv(
            params,
            "min_purchase_value",
            "valor_minimo",
            "minimum_purchase",
            default=0,
        )
        if min_purchase_value and total_venda + 0.01 < min_purchase_value:
            continue

        tipo_campanha = campanha.campaign_type
        if tipo_campanha == CampaignTypeEnum.cashback:
            percentual = _param_float_funcionario_pdv(
                params,
                "cashback_percent",
                "percentual_cashback",
                "percentual",
                default=0,
            )
            percentual += _param_float_funcionario_pdv(
                params,
                _cashback_bonus_param_key_funcionario_pdv(sale_channel),
                default=0,
            )
            valor_cashback = _round_money_funcionario_pdv(
                total_venda * percentual / 100
            )
            if valor_cashback > 0:
                beneficios.append(
                    {
                        "tipo": "cashback",
                        "titulo": campanha.name or "Cashback",
                        "valor": valor_cashback,
                        "descricao": f"{percentual:.2f}% sobre a venda",
                        "cliente_id": cliente_id,
                    }
                )
            continue

        if tipo_campanha == CampaignTypeEnum.loyalty_stamp:
            stamps_per_purchase = max(
                1,
                _param_int_funcionario_pdv(
                    params,
                    "stamps_per_purchase",
                    "carimbos_por_compra",
                    "stamp_count",
                    default=1,
                ),
            )
            if min_purchase_value > 0:
                quantidade = (
                    max(1, int(total_venda // min_purchase_value)) * stamps_per_purchase
                )
            else:
                quantidade = stamps_per_purchase
            beneficios.append(
                {
                    "tipo": "fidelidade",
                    "titulo": campanha.name or "Cartao fidelidade",
                    "quantidade": quantidade,
                    "descricao": f"{quantidade} carimbo(s) previstos",
                    "cliente_id": cliente_id,
                }
            )
            continue

        if tipo_campanha == CampaignTypeEnum.quick_repurchase:
            valor_cupom = _param_float_funcionario_pdv(
                params,
                "coupon_value",
                "valor_cupom",
                "discount_value",
                default=0,
            )
            percentual_cupom = _param_float_funcionario_pdv(
                params,
                "coupon_percent",
                "percentual_cupom",
                "discount_percent",
                default=0,
            )
            if valor_cupom > 0 or percentual_cupom > 0:
                beneficios.append(
                    {
                        "tipo": "cupom",
                        "titulo": campanha.name or "Cupom de recompra",
                        "valor": valor_cupom,
                        "percentual": percentual_cupom,
                        "descricao": "Cupom previsto apos a venda",
                        "cliente_id": cliente_id,
                    }
                )

    return beneficios


def _aplicar_desconto_cupom_nos_itens_funcionario_pdv(
    itens_payload: list[dict],
    desconto_total: float,
) -> list[dict]:
    desconto_total = min(
        _round_money_funcionario_pdv(desconto_total),
        sum(item["subtotal"] for item in itens_payload),
    )
    if desconto_total <= 0:
        return itens_payload

    total_bruto = sum(item["subtotal"] for item in itens_payload)
    restante = desconto_total
    itens_com_desconto = []
    for indice, item in enumerate(itens_payload):
        item_ajustado = dict(item)
        if indice == len(itens_payload) - 1:
            desconto_item = restante
        else:
            desconto_item = _round_money_funcionario_pdv(
                desconto_total * item["subtotal"] / total_bruto
            )
            desconto_item = min(desconto_item, item["subtotal"], restante)
            restante = _round_money_funcionario_pdv(restante - desconto_item)

        item_ajustado["desconto_item"] = _round_money_funcionario_pdv(
            float(item_ajustado.get("desconto_item") or 0) + desconto_item
        )
        item_ajustado["subtotal"] = _round_money_funcionario_pdv(
            item_ajustado["subtotal"] - desconto_item
        )
        itens_com_desconto.append(item_ajustado)

    return itens_com_desconto


def _calcular_beneficios_funcionario_pdv(
    db: Session,
    *,
    tenant_id: str,
    cliente_id: Optional[int],
    itens: list[FuncionarioPdvItemRequest],
    cupom_codigo: Optional[str] = None,
    cashback_valor: Optional[float] = None,
) -> dict:
    if not itens:
        raise HTTPException(
            status_code=400, detail="Adicione ao menos um item para vender."
        )

    _buscar_cliente_pdv_funcionario(db, tenant_id, cliente_id)

    itens_payload = []
    subtotal_bruto = 0.0
    for item in itens:
        produto = (
            db.query(Produto)
            .filter(
                Produto.id == item.produto_id,
                Produto.tenant_id == tenant_id,
                Produto.ativo.is_(True),
                Produto.situacao.is_not(False),
                Produto.tipo_produto.in_(["SIMPLES", "VARIACAO", "KIT"]),
            )
            .first()
        )
        if not produto:
            raise HTTPException(
                status_code=404, detail=f"Produto ID {item.produto_id} nao encontrado."
            )

        preco_unitario = float(produto.preco_venda or item.preco_unitario or 0)
        if preco_unitario <= 0:
            raise HTTPException(
                status_code=400,
                detail=f"Produto '{produto.nome}' esta sem preco de venda.",
            )

        quantidade = float(item.quantidade)
        subtotal_item = _round_money_funcionario_pdv(quantidade * preco_unitario)
        subtotal_bruto = _round_money_funcionario_pdv(subtotal_bruto + subtotal_item)
        itens_payload.append(
            {
                "tipo": "produto",
                "produto_id": produto.id,
                "quantidade": quantidade,
                "preco_unitario": preco_unitario,
                "desconto_item": 0,
                "subtotal": subtotal_item,
            }
        )

    cupom_code = None
    desconto_cupom = 0.0
    if cupom_codigo:
        preview_cupom = preview_coupon_redemption(
            db,
            tenant_id=tenant_id,
            code=cupom_codigo,
            venda_total=subtotal_bruto,
            customer_id=cliente_id,
        )
        cupom_code = preview_cupom["code"]
        desconto_cupom = _round_money_funcionario_pdv(
            preview_cupom.get("discount_applied")
        )

    itens_payload = _aplicar_desconto_cupom_nos_itens_funcionario_pdv(
        itens_payload, desconto_cupom
    )
    total_venda = _round_money_funcionario_pdv(
        sum(item["subtotal"] for item in itens_payload)
    )

    cashback_disponivel = _saldo_cashback_funcionario_pdv(
        db,
        tenant_id=tenant_id,
        cliente_id=cliente_id,
    )
    cashback_solicitado = _round_money_funcionario_pdv(cashback_valor)
    mensagens: list[str] = []
    if cashback_solicitado > 0 and not cliente_id:
        raise HTTPException(
            status_code=400, detail="Selecione um cliente para usar cashback."
        )
    if cashback_solicitado > cashback_disponivel + 0.01:
        raise HTTPException(
            status_code=400, detail="Cashback solicitado maior que o saldo disponivel."
        )

    cashback_usado = min(cashback_solicitado, total_venda)
    if cashback_solicitado > total_venda:
        mensagens.append("Cashback limitado ao total da venda apos descontos.")
    cashback_usado = _round_money_funcionario_pdv(cashback_usado)
    valor_pagamento = _round_money_funcionario_pdv(total_venda - cashback_usado)

    cupons_disponiveis = _listar_cupons_disponiveis_funcionario_pdv(
        db,
        tenant_id=tenant_id,
        cliente_id=cliente_id,
        subtotal=subtotal_bruto,
    )
    beneficios_gerados = _calcular_beneficios_gerados_funcionario_pdv(
        db,
        tenant_id=tenant_id,
        cliente_id=cliente_id,
        total_venda=total_venda,
    )

    return {
        "itens_payload": itens_payload,
        "subtotal": subtotal_bruto,
        "desconto_cupom": desconto_cupom,
        "cupom_code": cupom_code,
        "cashback_disponivel": cashback_disponivel,
        "cashback_valor": cashback_usado,
        "total_venda": total_venda,
        "valor_pagamento": valor_pagamento,
        "cupons_disponiveis": cupons_disponiveis,
        "beneficios_gerados": beneficios_gerados,
        "mensagens": mensagens,
    }


@router.post(
    "/funcionario/pdv/beneficios/preview",
    response_model=FuncionarioPdvBeneficiosPreviewResponse,
)
def preview_beneficios_funcionario_pdv(
    dados: FuncionarioPdvBeneficiosPreviewRequest,
    current_user: User = Depends(_get_current_ecommerce_user),
    db: Session = Depends(get_session),
):
    _funcionario, tenant_id = _get_funcionario_operacional_or_403(db, current_user)
    beneficios = _calcular_beneficios_funcionario_pdv(
        db,
        tenant_id=tenant_id,
        cliente_id=dados.cliente_id,
        itens=dados.itens,
        cupom_codigo=dados.cupom_codigo,
        cashback_valor=dados.cashback_valor,
    )
    return {
        "subtotal": beneficios["subtotal"],
        "desconto_cupom": beneficios["desconto_cupom"],
        "cupom_code": beneficios["cupom_code"],
        "cashback_disponivel": beneficios["cashback_disponivel"],
        "cashback_valor": beneficios["cashback_valor"],
        "total_venda": beneficios["total_venda"],
        "valor_pagamento": beneficios["valor_pagamento"],
        "cupons_disponiveis": beneficios["cupons_disponiveis"],
        "beneficios_gerados": beneficios["beneficios_gerados"],
        "mensagens": beneficios["mensagens"],
    }
