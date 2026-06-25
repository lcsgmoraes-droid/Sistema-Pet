"""Rota consolidada de fluxo de caixa."""

from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import and_
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user_and_tenant
from app.db import get_session
from app.financeiro.common import financeiro_erp_required
from app.financeiro.fluxo_caixa_periodos import _agrupar_por_periodo
from app.financeiro.fluxo_caixa_schemas import (
    FluxoCaixaMovimentacao,
    FluxoCaixaResponse,
)

router = APIRouter()


@router.get("/fluxo-caixa", response_model=FluxoCaixaResponse)
def get_fluxo_caixa(
    data_inicio: str,  # formato: YYYY-MM-DD
    data_fim: str,  # formato: YYYY-MM-DD
    conta_bancaria_id: Optional[int] = None,
    agrupamento: str = "dia",  # dia, semana, mes
    numero_venda: Optional[str] = None,  # Filtro por número de venda
    db: Session = Depends(get_session),
    current_user_and_tenant=Depends(get_current_user_and_tenant),
    _module_access: None = financeiro_erp_required,
):
    """
    Retorna o fluxo de caixa consolidado para um período - Estilo Flua.

    Consolida com separação Previsto vs Realizado:
    - Saldo inicial das contas bancárias
    - REALIZADO: Vendas pagas, Contas recebidas/pagas, Lançamentos manuais realizados
    - PREVISTO: Contas pendentes, Lançamentos manuais previstos, Lançamentos recorrentes

    Parâmetros:
    - agrupamento: 'dia', 'semana' ou 'mes'
    """
    current_user, tenant_id = current_user_and_tenant
    from app.vendas_models import Venda
    from app.financeiro_models import (
        ContaPagar,
        ContaReceber,
        ContaBancaria,
        LancamentoManual,
    )

    # Converter strings para date
    try:
        dt_inicio = datetime.strptime(data_inicio, "%Y-%m-%d").date()
        dt_fim = datetime.strptime(data_fim, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(
            status_code=400, detail="Formato de data inválido. Use YYYY-MM-DD"
        )

    # Validar agrupamento
    if agrupamento not in ["dia", "semana", "mes"]:
        raise HTTPException(
            status_code=400, detail="Agrupamento deve ser 'dia', 'semana' ou 'mes'"
        )

    # Filtro de conta bancária
    filtro_conta = []
    if conta_bancaria_id:
        filtro_conta = [conta_bancaria_id]
    else:
        # Todas as contas do usuário e tenant
        contas = (
            db.query(ContaBancaria)
            .filter(
                ContaBancaria.user_id == current_user.id,
                ContaBancaria.tenant_id == tenant_id,
            )
            .all()
        )
        filtro_conta = [c.id for c in contas]

    # ========== SALDO INICIAL ==========
    saldo_inicial = Decimal(0)
    if filtro_conta:
        contas_obj = (
            db.query(ContaBancaria)
            .filter(
                and_(
                    ContaBancaria.id.in_(filtro_conta),
                    ContaBancaria.user_id == current_user.id,
                    ContaBancaria.tenant_id == tenant_id,
                )
            )
            .all()
        )

        for conta in contas_obj:
            saldo_inicial += Decimal(str(conta.saldo_atual or 0))

    # ========== MOVIMENTAÇÕES ==========
    movimentacoes = []

    # 1. VENDAS REALIZADAS (Entradas Realizadas)
    vendas = (
        db.query(Venda)
        .filter(
            and_(
                Venda.user_id == current_user.id,
                Venda.tenant_id == tenant_id,
                Venda.data_venda >= dt_inicio,
                Venda.data_venda <= dt_fim,
                Venda.status == "finalizada",
            )
        )
        .all()
    )

    for venda in vendas:
        movimentacoes.append(
            FluxoCaixaMovimentacao(
                data=venda.data_venda.date()
                if isinstance(venda.data_venda, datetime)
                else venda.data_venda,
                tipo="entrada",
                descricao=f"Venda #{venda.id}",
                categoria="Vendas",
                valor=float(venda.total or 0),
                origem_tipo="venda",
                origem_id=venda.id,
                status="realizado",
            )
        )

    # 2. CONTAS A RECEBER PAGAS (Entradas Realizadas)
    # Agora buscamos da tabela fluxo_caixa, então vamos PULAR esta seção para evitar duplicação
    # Os recebimentos serão buscados via fluxo_caixa mais abaixo
    """
    recebimentos = db.query(Recebimento).join(ContaReceber).filter(
        and_(
            ContaReceber.user_id == user.id,
            Recebimento.data_recebimento >= dt_inicio,
            Recebimento.data_recebimento <= dt_fim
        )
    ).all()
    
    for rec in recebimentos:
        conta_receber = db.query(ContaReceber).filter(ContaReceber.id == rec.conta_receber_id).first()
        if conta_receber:
            # Buscar número da venda se existir
            numero_venda = None
            if conta_receber.venda_id:
                from app.vendas_models import Venda
                venda = db.query(Venda).filter(Venda.id == conta_receber.venda_id).first()
                if venda:
                    numero_venda = venda.numero_venda
            
            movimentacoes.append(FluxoCaixaMovimentacao(
                data=rec.data_recebimento if isinstance(rec.data_recebimento, date) else rec.data_recebimento.date(),
                tipo='entrada',
                descricao=f'Recebimento - {conta_receber.cliente.nome if conta_receber.cliente else "Cliente"}',
                categoria='Recebimentos',
                valor=float(rec.valor_recebido or 0),
                origem_tipo='conta_receber',
                origem_id=conta_receber.id,
                numero_venda=numero_venda,
                status='realizado'
            ))
    """

    # 3. CONTAS A PAGAR PAGAS (Saídas Realizadas)
    contas_pagas = (
        db.query(ContaPagar)
        .filter(
            and_(
                ContaPagar.user_id == current_user.id,
                ContaPagar.data_pagamento >= dt_inicio,
                ContaPagar.data_pagamento <= dt_fim,
                ContaPagar.status == "pago",
            )
        )
        .all()
    )

    for conta in contas_pagas:
        fornecedor_nome = conta.fornecedor.nome if conta.fornecedor else "Fornecedor"
        movimentacoes.append(
            FluxoCaixaMovimentacao(
                data=conta.data_pagamento
                if isinstance(conta.data_pagamento, date)
                else conta.data_pagamento.date(),
                tipo="saida",
                descricao=f"Pagamento - {fornecedor_nome}",
                categoria="Fornecedores",
                valor=float(conta.valor_pago or 0),
                origem_tipo="conta_pagar",
                origem_id=conta.id,
                status="realizado",
            )
        )

    # 4. LANÇAMENTOS MANUAIS REALIZADOS
    lancamentos_realizados = (
        db.query(LancamentoManual)
        .filter(
            and_(
                LancamentoManual.data_lancamento >= dt_inicio,
                LancamentoManual.data_lancamento <= dt_fim,
                LancamentoManual.status == "realizado",
            )
        )
        .all()
    )

    for lanc in lancamentos_realizados:
        movimentacoes.append(
            FluxoCaixaMovimentacao(
                data=lanc.data_lancamento
                if isinstance(lanc.data_lancamento, date)
                else lanc.data_lancamento.date(),
                tipo=lanc.tipo,
                descricao=lanc.descricao,
                categoria=lanc.categoria.nome if lanc.categoria else "Sem Categoria",
                valor=float(lanc.valor),
                origem_tipo="lancamento_manual",
                origem_id=lanc.id,
                status="realizado",
            )
        )

    # 🆕 LANÇAMENTOS DA TABELA FLUXO_CAIXA (REALIZADOS)
    from app.ia.aba5_models import FluxoCaixa

    # Converter para datetime para pegar horário completo
    dt_inicio_datetime = datetime.combine(dt_inicio, datetime.min.time())
    dt_fim_datetime = datetime.combine(dt_fim, datetime.max.time())

    fluxos_realizados = (
        db.query(FluxoCaixa)
        .filter(
            and_(
                FluxoCaixa.usuario_id == current_user.id,
                FluxoCaixa.data_movimentacao >= dt_inicio_datetime,
                FluxoCaixa.data_movimentacao <= dt_fim_datetime,
                FluxoCaixa.status == "realizado",
            )
        )
        .all()
    )

    for fluxo in fluxos_realizados:
        # Buscar número da venda se a origem for conta_receber
        numero_venda_fluxo = None
        if fluxo.origem_tipo == "conta_receber" and fluxo.origem_id:
            conta = (
                db.query(ContaReceber)
                .filter(ContaReceber.id == fluxo.origem_id)
                .first()
            )
            if conta and conta.venda_id:
                venda = db.query(Venda).filter(Venda.id == conta.venda_id).first()
                if venda:
                    numero_venda_fluxo = venda.numero_venda

        movimentacoes.append(
            FluxoCaixaMovimentacao(
                data=fluxo.data_movimentacao.date()
                if isinstance(fluxo.data_movimentacao, datetime)
                else fluxo.data_movimentacao,
                tipo="entrada" if fluxo.tipo == "entrada" else "saida",
                descricao=fluxo.descricao or "Movimentação",
                categoria=fluxo.categoria or "Sem Categoria",
                valor=float(fluxo.valor),
                origem_tipo=fluxo.origem_tipo or "fluxo_caixa",
                origem_id=fluxo.origem_id,
                numero_venda=numero_venda_fluxo,
                status="realizado",
            )
        )

    # ========== PREVISÕES ==========

    # 5. CONTAS A RECEBER PENDENTES (Entradas Previstas)
    # Agora buscamos da tabela fluxo_caixa, então vamos PULAR esta seção para evitar duplicação
    """
    contas_receber_pendentes = db.query(ContaReceber).filter(
        and_(
            ContaReceber.user_id == user.id,
            ContaReceber.data_vencimento >= dt_inicio,
            ContaReceber.data_vencimento <= dt_fim,
            ContaReceber.status.in_(['pendente', 'parcial'])
        )
    ).all()
    
    for conta in contas_receber_pendentes:
        valor_restante = (conta.valor_original or 0) - (conta.valor_recebido or 0)
        if valor_restante > 0:
            # Buscar número da venda se existir
            numero_venda = None
            if conta.venda_id:
                from app.vendas_models import Venda
                venda = db.query(Venda).filter(Venda.id == conta.venda_id).first()
                if venda:
                    numero_venda = venda.numero_venda
            
            movimentacoes.append(FluxoCaixaMovimentacao(
                data=conta.data_vencimento,
                tipo='entrada',
                descricao=f'A Receber - {conta.cliente.nome if conta.cliente else "Cliente"}',
                categoria='Recebimentos',
                valor=float(valor_restante),
                origem_tipo='conta_receber',
                origem_id=conta.id,
                numero_venda=numero_venda,
                status='previsto'
            ))
    """

    # 6. CONTAS A PAGAR PENDENTES (Saídas Previstas)
    contas_pagar_pendentes = (
        db.query(ContaPagar)
        .filter(
            and_(
                ContaPagar.user_id == current_user.id,
                ContaPagar.data_vencimento >= dt_inicio,
                ContaPagar.data_vencimento <= dt_fim,
                ContaPagar.status.in_(["pendente", "atrasado"]),
            )
        )
        .all()
    )

    for conta in contas_pagar_pendentes:
        valor_restante = (conta.valor_original or 0) - (conta.valor_pago or 0)
        if valor_restante > 0:
            fornecedor_nome = (
                conta.fornecedor.nome if conta.fornecedor else "Fornecedor"
            )
            movimentacoes.append(
                FluxoCaixaMovimentacao(
                    data=conta.data_vencimento,
                    tipo="saida",
                    descricao=f"A Pagar - {fornecedor_nome}",
                    categoria="Fornecedores",
                    valor=float(valor_restante),
                    origem_tipo="conta_pagar",
                    origem_id=conta.id,
                    status="previsto",
                )
            )

    # 7. LANÇAMENTOS MANUAIS PREVISTOS
    lancamentos_previstos = (
        db.query(LancamentoManual)
        .filter(
            and_(
                LancamentoManual.data_lancamento >= dt_inicio,
                LancamentoManual.data_lancamento <= dt_fim,
                LancamentoManual.status == "previsto",
            )
        )
        .all()
    )

    for lanc in lancamentos_previstos:
        movimentacoes.append(
            FluxoCaixaMovimentacao(
                data=lanc.data_lancamento,
                tipo=lanc.tipo,
                descricao=lanc.descricao,
                categoria=lanc.categoria.nome if lanc.categoria else "Sem Categoria",
                valor=float(lanc.valor),
                origem_tipo="lancamento_manual",
                origem_id=lanc.id,
                status="previsto",
            )
        )

    # 🆕 LANÇAMENTOS DA TABELA FLUXO_CAIXA (PREVISTOS)
    fluxos_previstos = (
        db.query(FluxoCaixa)
        .filter(
            and_(
                FluxoCaixa.usuario_id == current_user.id,
                FluxoCaixa.data_prevista >= dt_inicio_datetime,
                FluxoCaixa.data_prevista <= dt_fim_datetime,
                FluxoCaixa.status == "previsto",
            )
        )
        .all()
    )

    for fluxo in fluxos_previstos:
        # Buscar número da venda se a origem for conta_receber
        numero_venda_fluxo = None
        if fluxo.origem_tipo == "conta_receber" and fluxo.origem_id:
            conta = (
                db.query(ContaReceber)
                .filter(ContaReceber.id == fluxo.origem_id)
                .first()
            )
            if conta and conta.venda_id:
                venda = db.query(Venda).filter(Venda.id == conta.venda_id).first()
                if venda:
                    numero_venda_fluxo = venda.numero_venda

        movimentacoes.append(
            FluxoCaixaMovimentacao(
                data=fluxo.data_prevista.date()
                if isinstance(fluxo.data_prevista, datetime)
                else fluxo.data_prevista,
                tipo="entrada" if fluxo.tipo == "entrada" else "saida",
                descricao=fluxo.descricao or "Movimentação",
                categoria=fluxo.categoria or "Sem Categoria",
                valor=float(fluxo.valor),
                origem_tipo=fluxo.origem_tipo or "fluxo_caixa",
                origem_id=fluxo.origem_id,
                numero_venda=numero_venda_fluxo,
                status="previsto",
            )
        )

    # ========== FILTRAR POR NÚMERO DE VENDA (se fornecido) ==========
    if numero_venda:
        # Buscar IDs das vendas que correspondem ao número
        vendas_filtro = (
            db.query(Venda.id)
            .filter(
                and_(
                    Venda.user_id == current_user.id,
                    Venda.numero_venda.like(f"%{numero_venda}%"),
                )
            )
            .all()
        )

        vendas_ids = [v[0] for v in vendas_filtro]

        if vendas_ids:
            # Filtrar movimentações para apenas as que estão relacionadas a essas vendas
            movimentacoes_filtradas = []
            for mov in movimentacoes:
                # Incluir se é relacionado a venda diretamente
                if mov.origem_tipo == "venda" and mov.origem_id in vendas_ids:
                    movimentacoes_filtradas.append(mov)
                # Ou se é conta a receber/recebimento de venda
                elif mov.numero_venda and mov.numero_venda == numero_venda:
                    movimentacoes_filtradas.append(mov)
                # Ou se é conta a receber vinculada à venda
                elif mov.origem_tipo == "conta_receber":
                    # Buscar a conta para verificar venda_id
                    conta = (
                        db.query(ContaReceber)
                        .filter(ContaReceber.id == mov.origem_id)
                        .first()
                    )
                    if conta and conta.venda_id in vendas_ids:
                        movimentacoes_filtradas.append(mov)

            movimentacoes = movimentacoes_filtradas

    # ========== AGRUPAR POR PERÍODO ==========
    periodos = _agrupar_por_periodo(
        movimentacoes, dt_inicio, dt_fim, agrupamento, float(saldo_inicial)
    )

    # ========== TOTALIZADORES ==========
    total_previsto_entradas = sum(
        m.valor for m in movimentacoes if m.tipo == "entrada" and m.status == "previsto"
    )
    total_previsto_saidas = sum(
        m.valor for m in movimentacoes if m.tipo == "saida" and m.status == "previsto"
    )

    total_realizado_entradas = sum(
        m.valor
        for m in movimentacoes
        if m.tipo == "entrada" and m.status == "realizado"
    )
    total_realizado_saidas = sum(
        m.valor for m in movimentacoes if m.tipo == "saida" and m.status == "realizado"
    )

    saldo_final = (
        float(saldo_inicial) + total_realizado_entradas - total_realizado_saidas
    )
    saldo_previsto_final = saldo_final + total_previsto_entradas - total_previsto_saidas

    return FluxoCaixaResponse(
        periodos=periodos,
        movimentacoes=sorted(movimentacoes, key=lambda x: x.data),
        total_previsto_entradas=total_previsto_entradas,
        total_previsto_saidas=total_previsto_saidas,
        total_realizado_entradas=total_realizado_entradas,
        total_realizado_saidas=total_realizado_saidas,
        saldo_inicial=float(saldo_inicial),
        saldo_final=saldo_final,
        saldo_previsto_final=saldo_previsto_final,
    )
