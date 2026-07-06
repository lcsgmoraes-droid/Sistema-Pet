"""Servicos de baixa de contas a pagar."""

import logging
from datetime import date, datetime

from fastapi import HTTPException
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.domain.dre.lancamento_dre_sync import atualizar_dre_por_lancamento
from app.financeiro.contas_pagar_common import _decimal_monetario
from app.financeiro.contas_pagar_recorrencia import (
    _garantir_janela_recorrencia_apos_pagamento,
)
from app.financeiro_models import (
    ContaBancaria,
    ContaPagar,
    FormaPagamento,
    LancamentoManual,
    MovimentacaoFinanceira,
    Pagamento,
)

logger = logging.getLogger(__name__)


def validar_forma_pagamento(
    db: Session,
    *,
    tenant_id: str,
    forma_pagamento_id: int | None,
) -> int | None:
    if not forma_pagamento_id:
        return None

    forma_pagamento = (
        db.query(FormaPagamento)
        .filter(
            FormaPagamento.id == forma_pagamento_id,
            FormaPagamento.tenant_id == tenant_id,
            FormaPagamento.ativo.is_(True),
        )
        .first()
    )
    if not forma_pagamento:
        raise HTTPException(
            status_code=400,
            detail=(
                "Forma de pagamento selecionada nao foi encontrada ou esta inativa. "
                "Atualize a tela e selecione uma forma valida."
            ),
        )
    return forma_pagamento.id


def validar_conta_bancaria(
    db: Session,
    *,
    tenant_id: str,
    conta_bancaria_id: int | None,
) -> ContaBancaria | None:
    if not conta_bancaria_id:
        return None

    conta_bancaria = (
        db.query(ContaBancaria)
        .filter(
            ContaBancaria.id == conta_bancaria_id,
            ContaBancaria.tenant_id == tenant_id,
        )
        .first()
    )
    if not conta_bancaria:
        raise HTTPException(
            status_code=404,
            detail=f"Conta bancaria {conta_bancaria_id} nao encontrada",
        )
    if not conta_bancaria.ativa:
        raise HTTPException(
            status_code=400,
            detail=f"Conta bancaria '{conta_bancaria.nome}' esta inativa",
        )
    return conta_bancaria


def _normalizar_valores_conta(conta: ContaPagar) -> None:
    conta.valor_original = _decimal_monetario(conta.valor_original)
    conta.valor_pago = _decimal_monetario(conta.valor_pago)
    conta.valor_juros = _decimal_monetario(conta.valor_juros)
    conta.valor_multa = _decimal_monetario(conta.valor_multa)
    conta.valor_desconto = _decimal_monetario(conta.valor_desconto)
    conta.valor_final = _decimal_monetario(conta.valor_final or conta.valor_original)


def _atualizar_lancamento_previsto(
    db: Session,
    *,
    tenant_id: str,
    conta: ContaPagar,
) -> None:
    lancamento = (
        db.query(LancamentoManual)
        .filter(
            LancamentoManual.tenant_id == tenant_id,
            LancamentoManual.tipo == "saida",
            LancamentoManual.status == "previsto",
            LancamentoManual.gerado_automaticamente.is_(True),
            or_(
                LancamentoManual.documento == f"CONTA-PAGAR-{conta.id}",
                LancamentoManual.observacoes
                == f"Gerado automaticamente da conta a pagar #{conta.id}",
                LancamentoManual.observacoes.like(
                    f"Gerado automaticamente da conta a pagar #{conta.id}.%"
                ),
                LancamentoManual.observacoes.like(
                    f"Gerado automaticamente da conta a pagar #{conta.id} (%"
                ),
            ),
        )
        .order_by(LancamentoManual.id.desc())
        .first()
    )
    if lancamento:
        lancamento.status = "realizado"
        lancamento.realizado_em = datetime.now()


def _sincronizar_recorrencia_pos_pagamento(
    db: Session,
    *,
    tenant_id: str,
    conta: ContaPagar,
) -> int:
    if conta.status != "pago":
        return 0

    contas_recorrentes = _garantir_janela_recorrencia_apos_pagamento(
        db=db,
        tenant_id=tenant_id,
        conta_paga=conta,
        hoje=date.today(),
    )
    for conta_recorrente in contas_recorrentes:
        try:
            atualizar_dre_por_lancamento(
                db=db,
                tenant_id=tenant_id,
                dre_subcategoria_id=conta_recorrente.dre_subcategoria_id,
                canal=conta_recorrente.canal,
                valor=conta_recorrente.valor_original,
                data_lancamento=conta_recorrente.data_vencimento,
                tipo_movimentacao="DESPESA",
            )
        except Exception as exc:
            logger.warning(
                "Erro ao atualizar DRE para conta recorrente #%s: %s",
                conta_recorrente.id,
                exc,
            )
    return len(contas_recorrentes)


def aplicar_pagamento_conta_pagar(
    db: Session,
    *,
    conta: ContaPagar,
    tenant_id: str,
    current_user,
    data_pagamento: date,
    forma_pagamento_validada_id: int | None,
    conta_bancaria: ContaBancaria | None,
    observacoes: str | None,
    valor_base_pagamento=None,
    valor_juros=0,
    valor_multa=0,
    valor_desconto=0,
) -> dict:
    if conta.status in {"pago", "cancelado"}:
        raise HTTPException(
            status_code=400,
            detail=f"Conta {conta.id} nao pode ser paga",
        )

    _normalizar_valores_conta(conta)
    valor_base_pagamento = _decimal_monetario(
        valor_base_pagamento
        if valor_base_pagamento is not None
        else conta.valor_final - conta.valor_pago
    )
    valor_juros = _decimal_monetario(valor_juros)
    valor_multa = _decimal_monetario(valor_multa)
    valor_desconto = _decimal_monetario(valor_desconto)
    valor_total_pagamento = (
        valor_base_pagamento + valor_juros + valor_multa - valor_desconto
    )

    if valor_base_pagamento <= 0:
        raise HTTPException(
            status_code=400,
            detail="Informe um valor de pagamento maior que zero.",
        )
    if valor_total_pagamento <= 0:
        raise HTTPException(
            status_code=400,
            detail=(
                "O valor final do pagamento precisa ser maior que zero. "
                "Revise juros, multa e desconto."
            ),
        )

    conta.valor_pago += valor_total_pagamento
    conta.valor_juros += valor_juros
    conta.valor_multa += valor_multa
    conta.valor_desconto += valor_desconto
    conta.valor_final = (
        conta.valor_original
        + conta.valor_juros
        + conta.valor_multa
        - conta.valor_desconto
    )
    conta.status = "pago" if conta.valor_pago >= conta.valor_final else "parcial"
    if conta.status == "pago":
        conta.data_pagamento = data_pagamento

    db.add(
        Pagamento(
            conta_pagar_id=conta.id,
            forma_pagamento_id=forma_pagamento_validada_id,
            valor_pago=valor_total_pagamento,
            data_pagamento=data_pagamento,
            observacoes=observacoes,
            user_id=current_user.id,
            tenant_id=tenant_id,
        )
    )

    if conta_bancaria:
        db.add(
            MovimentacaoFinanceira(
                conta_bancaria_id=conta_bancaria.id,
                tipo="saida",
                valor=valor_total_pagamento,
                descricao=f"Pagamento: {conta.descricao}",
                data_movimento=datetime.combine(data_pagamento, datetime.min.time()),
                categoria_id=conta.categoria_id,
                status="realizado",
                forma_pagamento_id=forma_pagamento_validada_id,
                documento=conta.documento,
                origem_tipo="conta_pagar",
                origem_id=conta.id,
                observacoes=observacoes,
                user_id=current_user.id,
                tenant_id=tenant_id,
            )
        )
        conta_bancaria.saldo_atual -= valor_total_pagamento

    _atualizar_lancamento_previsto(db, tenant_id=tenant_id, conta=conta)
    recorrencias_criadas = _sincronizar_recorrencia_pos_pagamento(
        db,
        tenant_id=tenant_id,
        conta=conta,
    )

    return {
        "conta_id": conta.id,
        "status": conta.status,
        "valor_pago": valor_total_pagamento,
        "valor_pago_total": conta.valor_pago,
        "valor_final": conta.valor_final,
        "saldo_restante": conta.valor_final - conta.valor_pago,
        "recorrencias_criadas": recorrencias_criadas,
    }
