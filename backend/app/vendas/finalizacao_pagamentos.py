# -*- coding: utf-8 -*-
"""Pagamentos da finalizacao de vendas.

Concentra validacoes de saldo, cupom, cartao, credito, cashback e caixa para
deixar ``finalizacao.py`` focado na transacao principal da venda.
"""

import logging
from datetime import date as _date
from decimal import Decimal
from typing import Any, Dict, List, Optional

from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

__all__ = [
    "_calcular_pagamentos_finalizacao",
    "consumir_cupom_finalizacao",
    "processar_pagamentos_finalizacao",
]


def _calcular_pagamentos_finalizacao(
    *,
    total_venda: Any,
    pagamentos_existentes: List[Any],
    pagamentos_novos: List[Dict[str, Any]],
) -> Dict[str, float]:
    total_venda_float = float(total_venda or 0)
    total_ja_pago = sum(float(p.valor) for p in pagamentos_existentes)
    total_novos_pagamentos = sum(float(p.get("valor") or 0) for p in pagamentos_novos)
    valor_restante_bruto = total_venda_float - total_ja_pago

    if not pagamentos_novos and total_ja_pago < total_venda_float - 0.01:
        raise HTTPException(
            status_code=400, detail="Informe pelo menos uma forma de pagamento"
        )

    if valor_restante_bruto <= 0.01 and total_novos_pagamentos > 0.01:
        raise HTTPException(status_code=400, detail="Venda já está totalmente paga")

    if total_novos_pagamentos > valor_restante_bruto + 0.01:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Valor dos pagamentos excede o saldo da venda. "
                f"Saldo: R$ {max(0, valor_restante_bruto):.2f}, "
                f"informado: R$ {total_novos_pagamentos:.2f}."
            ),
        )

    return {
        "total_ja_pago": total_ja_pago,
        "total_novos_pagamentos": total_novos_pagamentos,
        "total_pagamentos": total_ja_pago + total_novos_pagamentos,
        "valor_restante": max(0, valor_restante_bruto),
    }


def consumir_cupom_finalizacao(
    *,
    venda: Any,
    cupom_code: Optional[str],
    cupom_discount_applied: Optional[float],
    tenant_id: str,
    db: Session,
) -> Optional[Dict[str, Any]]:
    from app.campaigns.coupon_service import consume_coupon_redemption

    cupom_code_resolvido = (
        str(cupom_code).strip().upper() if cupom_code else venda.cupom_code
    )
    cupom_discount_resolvido = (
        cupom_discount_applied
        if cupom_discount_applied is not None
        else float(venda.cupom_discount_applied or 0)
        if venda.cupom_discount_applied is not None
        else None
    )

    if not cupom_code_resolvido:
        return None

    venda_total_para_cupom = float(venda.total or 0)
    if cupom_discount_resolvido:
        venda_total_para_cupom += float(cupom_discount_resolvido or 0)

    cupom_consumido = consume_coupon_redemption(
        db,
        tenant_id=tenant_id,
        code=cupom_code_resolvido,
        venda_total=venda_total_para_cupom,
        customer_id=venda.cliente_id,
        venda_id=venda.id,
        expected_discount_applied=cupom_discount_resolvido,
    )
    venda.cupom_code = cupom_code_resolvido
    venda.cupom_discount_applied = cupom_consumido.get("discount_applied")
    return cupom_consumido


def processar_pagamentos_finalizacao(
    *,
    venda: Any,
    pagamentos: List[Dict[str, Any]],
    user_id: int,
    user_nome: str,
    tenant_id: str,
    db: Session,
    caixa_aberto_id: int,
) -> List[int]:
    from app.caixa.service import CaixaService
    from app.campaigns.models import (
        CashbackSourceTypeEnum,
        CashbackTransaction,
    )
    from app.financeiro_models import CategoriaFinanceira, LancamentoManual
    from app.models import Cliente
    from app.operadoras_models import OperadoraCartao
    from app.vendas_models import Venda, VendaPagamento

    movimentacoes_caixa_ids: List[int] = []

    for pag_data in pagamentos:
        operadora_id = pag_data.get("operadora_id")
        numero_parcelas = pag_data.get("numero_parcelas", 1)

        if operadora_id and numero_parcelas > 1:
            operadora = (
                db.query(OperadoraCartao)
                .filter(
                    OperadoraCartao.id == operadora_id,
                    OperadoraCartao.tenant_id == tenant_id,
                )
                .first()
            )
            if not operadora:
                raise HTTPException(
                    status_code=400,
                    detail=f"❌ Operadora não encontrada (ID: {operadora_id})",
                )

            if numero_parcelas > operadora.max_parcelas:
                raise HTTPException(
                    status_code=400,
                    detail=f"❌ PARCELAS EXCEDIDAS: {operadora.nome} permite no máximo "
                    f"{operadora.max_parcelas}x. Você tentou {numero_parcelas}x.",
                )

        nsu_informado = pag_data.get("nsu_cartao")
        if nsu_informado and operadora_id:
            nsu_duplicado = (
                db.query(VendaPagamento)
                .filter(
                    VendaPagamento.tenant_id == tenant_id,
                    VendaPagamento.nsu_cartao == nsu_informado,
                    VendaPagamento.operadora_id == operadora_id,
                )
                .first()
            )

            if nsu_duplicado:
                venda_duplicada = (
                    db.query(Venda).filter_by(id=nsu_duplicado.venda_id).first()
                )
                raise HTTPException(
                    status_code=400,
                    detail=f"❌ NSU DUPLICADO: O NSU '{nsu_informado}' já está vinculado à "
                    f"Venda {venda_duplicada.numero_venda if venda_duplicada else nsu_duplicado.venda_id}. "
                    f"Cada NSU deve ser usado apenas uma vez por operadora.",
                )

        pagamento = VendaPagamento(
            venda_id=venda.id,
            tenant_id=tenant_id,
            forma_pagamento=pag_data["forma_pagamento"],
            valor=pag_data["valor"],
            numero_parcelas=numero_parcelas,
            bandeira=pag_data.get("bandeira"),
            nsu_cartao=pag_data.get("nsu_cartao"),
            operadora_id=operadora_id,
        )
        db.add(pagamento)
        db.flush()

        forma_eh_credito = (
            pag_data["forma_pagamento"].lower() == "credito_cliente"
            or pag_data["forma_pagamento"] == "Crédito Cliente"
        )

        if forma_eh_credito:
            if not venda.cliente_id:
                raise HTTPException(
                    status_code=400,
                    detail="Crédito só pode ser usado em vendas com cliente vinculado",
                )

            cliente = db.query(Cliente).filter_by(id=venda.cliente_id).first()
            if not cliente:
                raise HTTPException(status_code=404, detail="Cliente não encontrado")

            credito_disponivel = float(cliente.credito or 0)
            if pag_data["valor"] > credito_disponivel + 0.01:
                raise HTTPException(
                    status_code=400,
                    detail=f"Crédito insuficiente. Disponível: R$ {credito_disponivel:.2f}",
                )

            cliente.credito = Decimal(str(credito_disponivel - pag_data["valor"]))
            db.add(cliente)
            logger.info(
                f"🎁 Crédito utilizado: R$ {pag_data['valor']:.2f} - "
                f"Saldo restante: R$ {float(cliente.credito):.2f}"
            )
            continue

        forma_eh_cashback = (
            pag_data["forma_pagamento"].lower() == "cashback"
            or pag_data["forma_pagamento"] == "Cashback"
        )

        if forma_eh_cashback:
            if not venda.cliente_id:
                raise HTTPException(
                    status_code=400,
                    detail="Cashback só pode ser usado em vendas com cliente vinculado",
                )

            saldo_raw = (
                db.query(func.sum(CashbackTransaction.amount))
                .filter(
                    CashbackTransaction.tenant_id == tenant_id,
                    CashbackTransaction.customer_id == venda.cliente_id,
                )
                .scalar()
            )
            saldo_disponivel = float(saldo_raw or 0)

            if pag_data["valor"] > saldo_disponivel + 0.01:
                raise HTTPException(
                    status_code=400,
                    detail=f"Cashback insuficiente. Disponível: R$ {saldo_disponivel:.2f}",
                )

            debit = CashbackTransaction(
                tenant_id=tenant_id,
                customer_id=venda.cliente_id,
                amount=-Decimal(str(pag_data["valor"])),
                source_type=CashbackSourceTypeEnum.redemption,
                source_id=venda.id,
                description=f"Resgate em venda {venda.numero_venda}",
                tx_type="debit",
            )
            db.add(debit)

            cat_campanha = (
                db.query(CategoriaFinanceira)
                .filter(
                    CategoriaFinanceira.nome.ilike("%campanha%"),
                    CategoriaFinanceira.tipo == "despesa",
                    CategoriaFinanceira.tenant_id == tenant_id,
                )
                .first()
            )
            if not cat_campanha:
                cat_campanha = CategoriaFinanceira(
                    nome="Campanhas / Marketing",
                    tipo="despesa",
                    user_id=user_id,
                    tenant_id=tenant_id,
                )
                db.add(cat_campanha)
                db.flush()

            cliente_nome = venda.cliente.nome if venda.cliente else "Cliente"
            lancamento_campanha = LancamentoManual(
                tipo="saida",
                valor=Decimal(str(pag_data["valor"])),
                descricao=f"Cashback resgatado — {cliente_nome} — Venda {venda.numero_venda}",
                data_lancamento=venda.data_venda.date()
                if hasattr(venda.data_venda, "date")
                else _date.today(),
                status="realizado",
                categoria_id=cat_campanha.id,
                conta_bancaria_id=None,
                fornecedor_cliente=cliente_nome,
                documento=f"CASHBACK-{venda.numero_venda}",
                gerado_automaticamente=True,
                user_id=user_id,
                tenant_id=tenant_id,
            )
            db.add(lancamento_campanha)
            logger.info(
                "💰 Cashback utilizado: R$ %.2f — DRE despesa campanha criada — venda=%s",
                pag_data["valor"],
                venda.numero_venda,
            )
            continue

        if CaixaService.eh_forma_dinheiro(pag_data["forma_pagamento"]):
            mov_info = CaixaService.registrar_movimentacao_venda(
                caixa_id=caixa_aberto_id,
                venda_id=venda.id,
                venda_numero=venda.numero_venda,
                valor=pag_data["valor"],
                user_id=user_id,
                user_nome=user_nome,
                tenant_id=tenant_id,
                db=db,
            )
            movimentacoes_caixa_ids.append(mov_info["movimentacao_id"])
            logger.info(f"💵 Caixa: Movimentação #{mov_info['movimentacao_id']} criada")

    return movimentacoes_caixa_ids
