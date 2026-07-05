"""Rotas de pagamento e resumo de contas a pagar."""

import logging
from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import and_, func, or_
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user_and_tenant
from app.db import get_session
from app.domain.dre.lancamento_dre_sync import atualizar_dre_por_lancamento
from app.financeiro.contas_pagar_common import (
    _decimal_monetario,
    _valor_reais_para_centavos,
)
from app.financeiro.contas_pagar_recorrencia import (
    _garantir_janela_recorrencia_apos_pagamento,
)
from app.financeiro.contas_pagar_schemas import PagamentoCreate
from app.financeiro_models import (
    ContaBancaria,
    ContaPagar,
    FormaPagamento,
    LancamentoManual,
    MovimentacaoFinanceira,
    Pagamento,
)
from app.idempotency import idempotent

logger = logging.getLogger(__name__)
router = APIRouter()


# REGISTRAR PAGAMENTO
# ============================================================================


@router.post("/{conta_id}/pagar")
@idempotent()  # 🔒 IDEMPOTÊNCIA: evita pagamento duplicado
async def registrar_pagamento(
    conta_id: int,
    pagamento: PagamentoCreate,
    request: Request,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    Registra um pagamento (baixa) de conta a pagar
    """
    current_user, tenant_id = user_and_tenant

    conta = (
        db.query(ContaPagar)
        .filter(
            ContaPagar.id == conta_id,
            ContaPagar.tenant_id == tenant_id,
        )
        .first()
    )

    if not conta:
        raise HTTPException(status_code=404, detail="Conta não encontrada")

    if conta.status == "pago":
        raise HTTPException(status_code=400, detail="Conta já está paga")

    conta.valor_original = _decimal_monetario(conta.valor_original)
    conta.valor_pago = _decimal_monetario(conta.valor_pago)
    conta.valor_juros = _decimal_monetario(conta.valor_juros)
    conta.valor_multa = _decimal_monetario(conta.valor_multa)
    conta.valor_desconto = _decimal_monetario(conta.valor_desconto)
    conta.valor_final = _decimal_monetario(conta.valor_final or conta.valor_original)

    valor_base_pagamento = _decimal_monetario(pagamento.valor_pago)
    valor_juros = _decimal_monetario(pagamento.valor_juros)
    valor_multa = _decimal_monetario(pagamento.valor_multa)
    valor_desconto = _decimal_monetario(pagamento.valor_desconto)
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
            detail="O valor final do pagamento precisa ser maior que zero. Revise juros, multa e desconto.",
        )

    forma_pagamento_validada_id = None
    if pagamento.forma_pagamento_id:
        forma_pagamento = (
            db.query(FormaPagamento)
            .filter(
                FormaPagamento.id == pagamento.forma_pagamento_id,
                FormaPagamento.tenant_id == tenant_id,
                FormaPagamento.ativo.is_(True),
            )
            .first()
        )

        if not forma_pagamento:
            raise HTTPException(
                status_code=400,
                detail="Forma de pagamento selecionada nao foi encontrada ou esta inativa. Atualize a tela e selecione uma forma valida.",
            )

        forma_pagamento_validada_id = forma_pagamento.id

    # Atualizar valores
    conta.valor_pago += valor_total_pagamento
    conta.valor_juros += valor_juros
    conta.valor_multa += valor_multa
    conta.valor_desconto += valor_desconto

    # Recalcular valor final
    conta.valor_final = (
        conta.valor_original
        + conta.valor_juros
        + conta.valor_multa
        - conta.valor_desconto
    )

    # Verificar se pagou tudo
    if conta.valor_pago >= conta.valor_final:
        conta.status = "pago"
        conta.data_pagamento = pagamento.data_pagamento
    else:
        conta.status = "parcial"

    # Registrar pagamento
    novo_pagamento = Pagamento(
        conta_pagar_id=conta.id,
        forma_pagamento_id=forma_pagamento_validada_id,
        valor_pago=valor_total_pagamento,
        data_pagamento=pagamento.data_pagamento,
        observacoes=pagamento.observacoes,
        user_id=current_user.id,
        tenant_id=tenant_id,
    )
    db.add(novo_pagamento)

    # ========================================
    # CRIAR MOVIMENTAÇÃO FINANCEIRA E ATUALIZAR SALDO
    # ========================================

    if pagamento.conta_bancaria_id:
        # Buscar conta bancária
        conta_bancaria = (
            db.query(ContaBancaria)
            .filter(
                ContaBancaria.id == pagamento.conta_bancaria_id,
                ContaBancaria.tenant_id == tenant_id,
            )
            .first()
        )

        if not conta_bancaria:
            raise HTTPException(
                status_code=404,
                detail=f"Conta bancária {pagamento.conta_bancaria_id} não encontrada",
            )

        if not conta_bancaria.ativa:
            raise HTTPException(
                status_code=400,
                detail=f"Conta bancária '{conta_bancaria.nome}' está inativa",
            )

        # Converter valor para centavos
        valor_centavos = _valor_reais_para_centavos(valor_total_pagamento)

        # Criar movimentação financeira (SAÍDA)
        movimentacao = MovimentacaoFinanceira(
            conta_bancaria_id=conta_bancaria.id,
            tipo="saida",
            valor=valor_centavos,
            descricao=f"Pagamento: {conta.descricao}",
            data_movimento=datetime.combine(
                pagamento.data_pagamento, datetime.min.time()
            ),
            categoria_id=conta.categoria_id,
            status="realizado",
            forma_pagamento_id=forma_pagamento_validada_id,
            documento=conta.documento,
            origem_tipo="conta_pagar",
            origem_id=conta.id,
            observacoes=pagamento.observacoes,
            user_id=current_user.id,
            tenant_id=tenant_id,
        )
        db.add(movimentacao)

        # Atualizar saldo da conta bancária (DÉBITO)
        conta_bancaria.saldo_atual -= valor_centavos

        logger.info(
            f"🏦 Movimentação bancária criada: {conta_bancaria.nome} "
            f"-R$ {valor_total_pagamento:.2f} (Saldo: R$ {conta_bancaria.saldo_atual / 100:.2f})"
        )

    # ========================================
    # ATUALIZAR LANÇAMENTO MANUAL PREVISTO
    # ========================================

    # Buscar lançamento manual previsto relacionado a esta conta
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
        logger.info(
            f"📊 Lançamento manual #{lancamento.id} atualizado para 'realizado'"
        )

    contas_recorrentes_criadas = []
    if conta.status == "pago":
        contas_recorrentes_criadas = _garantir_janela_recorrencia_apos_pagamento(
            db=db,
            tenant_id=tenant_id,
            conta_paga=conta,
            hoje=date.today(),
        )

        for conta_recorrente in contas_recorrentes_criadas:
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
            except Exception as e:
                logger.warning(
                    f"Erro ao atualizar DRE para conta recorrente #{conta_recorrente.id}: {e}"
                )

    db.commit()

    logger.info(
        f"✅ Pagamento registrado: R$ {pagamento.valor_pago} - Conta {conta_id}"
    )

    return {
        "message": "Pagamento registrado com sucesso",
        "conta_id": conta.id,
        "status": conta.status,
        "valor_pago_total": float(conta.valor_pago),
        "valor_final": float(conta.valor_final),
        "saldo_restante": float(conta.valor_final - conta.valor_pago),
        "recorrencias_criadas": len(contas_recorrentes_criadas),
    }


# ============================================================================
# DASHBOARD / RESUMO
# ============================================================================


@router.get("/dashboard/resumo")
def dashboard_contas_pagar(
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    Resumo financeiro de contas a pagar
    """
    current_user, tenant_id = user_and_tenant

    hoje = date.today()

    # Total pendente
    total_pendente = (
        db.query(func.sum(ContaPagar.valor_final - ContaPagar.valor_pago))
        .filter(
            ContaPagar.tenant_id == tenant_id,
            ContaPagar.status.in_(["pendente", "parcial", "vencido"]),
        )
        .scalar()
        or 0
    )

    # Vencidas
    total_vencido = (
        db.query(func.sum(ContaPagar.valor_final - ContaPagar.valor_pago))
        .filter(
            and_(
                ContaPagar.tenant_id == tenant_id,
                ContaPagar.status == "pendente",
                ContaPagar.data_vencimento < hoje,
            )
        )
        .scalar()
        or 0
    )

    count_vencidas = (
        db.query(func.count(ContaPagar.id))
        .filter(
            and_(
                ContaPagar.tenant_id == tenant_id,
                ContaPagar.status == "pendente",
                ContaPagar.data_vencimento < hoje,
            )
        )
        .scalar()
    )

    # Vence hoje
    total_vence_hoje = (
        db.query(func.sum(ContaPagar.valor_final - ContaPagar.valor_pago))
        .filter(
            and_(
                ContaPagar.tenant_id == tenant_id,
                ContaPagar.status == "pendente",
                ContaPagar.data_vencimento == hoje,
            )
        )
        .scalar()
        or 0
    )

    # Próximos 7 dias
    data_7dias = hoje + timedelta(days=7)
    total_7dias = (
        db.query(func.sum(ContaPagar.valor_final - ContaPagar.valor_pago))
        .filter(
            and_(
                ContaPagar.tenant_id == tenant_id,
                ContaPagar.status == "pendente",
                ContaPagar.data_vencimento.between(hoje, data_7dias),
            )
        )
        .scalar()
        or 0
    )

    # Próximos 30 dias
    data_30dias = hoje + timedelta(days=30)
    total_30dias = (
        db.query(func.sum(ContaPagar.valor_final - ContaPagar.valor_pago))
        .filter(
            and_(
                ContaPagar.tenant_id == tenant_id,
                ContaPagar.status == "pendente",
                ContaPagar.data_vencimento.between(hoje, data_30dias),
            )
        )
        .scalar()
        or 0
    )

    # Pago no mês
    primeiro_dia_mes = hoje.replace(day=1)
    total_pago_mes = (
        db.query(func.sum(ContaPagar.valor_pago))
        .filter(
            and_(
                ContaPagar.tenant_id == tenant_id,
                ContaPagar.data_pagamento >= primeiro_dia_mes,
                ContaPagar.data_pagamento <= hoje,
            )
        )
        .scalar()
        or 0
    )

    return {
        "total_pendente": float(total_pendente),
        "vencidas": {"total": float(total_vencido), "quantidade": count_vencidas},
        "vence_hoje": float(total_vence_hoje),
        "proximos_7_dias": float(total_7dias),
        "proximos_30_dias": float(total_30dias),
        "pago_mes_atual": float(total_pago_mes),
    }
