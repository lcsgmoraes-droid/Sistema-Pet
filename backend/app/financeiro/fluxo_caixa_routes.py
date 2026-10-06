"""Rota consolidada de fluxo de caixa."""

from datetime import date, datetime
from decimal import Decimal
import re
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import and_, or_
from sqlalchemy.orm import Session, joinedload

from app.auth.dependencies import get_current_user_and_tenant
from app.db import get_session
from app.financeiro.common import financeiro_erp_required
from app.financeiro.fluxo_caixa_pagamentos import movimentacoes_pagamentos_contas_pagar
from app.financeiro.fluxo_caixa_periodos import _agrupar_por_periodo
from app.financeiro.fluxo_caixa_vendas import (
    lancamentos_cashback_sem_saida_caixa,
    valores_nao_monetarios_por_venda,
    valores_entradas_venda_realizadas,
    vendas_com_lancamento,
    vendas_devolvidas_com_entrada_integral,
)
from app.financeiro.fluxo_caixa_schemas import (
    FluxoCaixaMovimentacao,
    FluxoCaixaResponse,
)
from app.tenancy.context import set_current_tenant

router = APIRouter()


def _conta_pagar_de_lancamento_automatico(lancamento) -> int | None:
    """Identifica o espelho criado pelo cadastro da conta, inclusive recorrências."""
    if not lancamento.gerado_automaticamente or lancamento.tipo != "saida":
        return None

    documento = re.fullmatch(r"CONTA-PAGAR-(\d+)", lancamento.documento or "")
    if documento:
        return int(documento.group(1))

    observacao = re.match(
        r"Gerado automaticamente da conta a pagar #(\d+)(?:$|[ .(])",
        lancamento.observacoes or "",
    )
    return int(observacao.group(1)) if observacao else None


def _mapa_numeros_venda_por_conta(db: Session, tenant_id, conta_ids) -> dict[int, str]:
    """Busca os numeros de venda de varias contas em uma unica consulta."""
    ids = {int(conta_id) for conta_id in conta_ids if conta_id is not None}
    if not ids:
        return {}
    tenant_uuid = tenant_id if isinstance(tenant_id, UUID) else UUID(str(tenant_id))

    from app.financeiro_models import ContaReceber
    from app.vendas_models import Venda

    return {
        conta_id: numero_venda
        for conta_id, numero_venda in db.query(ContaReceber.id, Venda.numero_venda)
        .outerjoin(
            Venda,
            and_(Venda.id == ContaReceber.venda_id, Venda.tenant_id == tenant_uuid),
        )
        .filter(ContaReceber.tenant_id == tenant_uuid, ContaReceber.id.in_(ids))
        .all()
    }


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
    _current_user, tenant_id = current_user_and_tenant
    set_current_tenant(tenant_id)
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

    # Filtro de conta bancária e saldo inicial na mesma consulta.
    contas_query = db.query(ContaBancaria).filter(ContaBancaria.tenant_id == tenant_id)
    if conta_bancaria_id:
        contas_query = contas_query.filter(ContaBancaria.id == conta_bancaria_id)
    contas_obj = contas_query.all()

    # ========== SALDO INICIAL ==========
    saldo_inicial = sum(
        (Decimal(str(conta.saldo_atual or 0)) for conta in contas_obj), Decimal(0)
    )

    # ========== MOVIMENTAÇÕES ==========
    movimentacoes = []

    # 1. VENDAS REALIZADAS (Entradas Realizadas)
    vendas = (
        db.query(Venda)
        .filter(
            and_(
                Venda.tenant_id == tenant_id,
                Venda.data_venda >= dt_inicio,
                Venda.data_venda <= dt_fim,
                or_(
                    Venda.status == "finalizada",
                    and_(Venda.status == "pago_nf", Venda.data_finalizacao.isnot(None)),
                    Venda.status.in_(
                        [
                            "finalizada_devolucao",
                            "finalizada_devolucao_parcial",
                            "devolvida_total",
                        ]
                    ),
                ),
            )
        )
        .all()
    )

    devolvidas_com_entrada = vendas_devolvidas_com_entrada_integral(
        db, tenant_id, vendas
    )
    vendas = [
        venda
        for venda in vendas
        if venda.status
        not in {
            "finalizada_devolucao",
            "finalizada_devolucao_parcial",
            "devolvida_total",
        }
        or venda.id in devolvidas_com_entrada
    ]
    venda_ids = {venda.id for venda in vendas}
    vendas_com_lancamento_manual = vendas_com_lancamento(db, tenant_id, venda_ids)
    pagamentos_nao_monetarios = valores_nao_monetarios_por_venda(
        db, tenant_id, venda_ids
    )

    for venda in vendas:
        if venda.id in vendas_com_lancamento_manual:
            continue
        valor_entrada = max(
            Decimal(str(venda.total or 0))
            - pagamentos_nao_monetarios.get(venda.id, Decimal("0")),
            Decimal("0"),
        )
        if valor_entrada == 0:
            continue

        movimentacoes.append(
            FluxoCaixaMovimentacao(
                data=venda.data_venda.date()
                if isinstance(venda.data_venda, datetime)
                else venda.data_venda,
                tipo="entrada",
                descricao=f"Venda #{venda.id}",
                categoria="Vendas",
                valor=float(valor_entrada),
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

    # 3. PAGAMENTOS DE CONTAS A PAGAR (Saídas Realizadas)
    from app.financeiro_models import Pagamento

    movimentacoes.extend(
        movimentacoes_pagamentos_contas_pagar(db, tenant_id, dt_inicio, dt_fim)
    )

    # 4. LANÇAMENTOS MANUAIS REALIZADOS
    from app.ia.aba5_models import FluxoCaixa

    lancamentos_realizados = (
        db.query(LancamentoManual)
        .options(joinedload(LancamentoManual.categoria))
        .filter(
            and_(
                LancamentoManual.tenant_id == tenant_id,
                LancamentoManual.data_lancamento >= dt_inicio,
                LancamentoManual.data_lancamento <= dt_fim,
                LancamentoManual.status == "realizado",
            )
        )
        .all()
    )
    lancamentos_previstos = (
        db.query(LancamentoManual)
        .options(joinedload(LancamentoManual.categoria))
        .filter(
            LancamentoManual.tenant_id == tenant_id,
            LancamentoManual.data_lancamento >= dt_inicio,
            LancamentoManual.data_lancamento <= dt_fim,
            LancamentoManual.status == "previsto",
        )
        .all()
    )
    valores_entrada_venda = valores_entradas_venda_realizadas(
        db, tenant_id, lancamentos_realizados, dt_fim
    )
    espelhos_cashback = lancamentos_cashback_sem_saida_caixa(
        db, tenant_id, lancamentos_realizados
    )
    ids_espelhos = {
        conta_id
        for lancamento in (*lancamentos_realizados, *lancamentos_previstos)
        if (conta_id := _conta_pagar_de_lancamento_automatico(lancamento)) is not None
    }
    contas_espelhadas = {}
    espelhos_com_pagamento = set()
    espelhos_com_fluxo_realizado = set()
    if ids_espelhos:
        contas_espelhadas = {
            conta.id: conta
            for conta in db.query(ContaPagar)
            .filter(ContaPagar.tenant_id == tenant_id, ContaPagar.id.in_(ids_espelhos))
            .all()
        }
        espelhos_com_pagamento = {
            conta_id
            for (conta_id,) in db.query(Pagamento.conta_pagar_id)
            .filter(
                Pagamento.tenant_id == tenant_id,
                Pagamento.conta_pagar_id.in_(contas_espelhadas),
            )
            .all()
        }
        espelhos_com_fluxo_realizado = {
            conta_id
            for (conta_id,) in db.query(FluxoCaixa.origem_id)
            .filter(
                FluxoCaixa.tenant_id == tenant_id,
                FluxoCaixa.origem_tipo == "conta_pagar",
                FluxoCaixa.origem_id.in_(contas_espelhadas),
                FluxoCaixa.status == "realizado",
                FluxoCaixa.tipo != "entrada",
            )
            .all()
        }

    for lanc in lancamentos_realizados:
        if lanc.id in espelhos_cashback:
            continue
        conta_id = _conta_pagar_de_lancamento_automatico(lanc)
        conta_espelhada = contas_espelhadas.get(conta_id)
        # Sem baixa rastreável, preservamos o lançamento realizado legado.
        if conta_espelhada and (
            conta_id in espelhos_com_pagamento
            or conta_id in espelhos_com_fluxo_realizado
            or (conta_espelhada.status == "pago" and conta_espelhada.data_pagamento)
        ):
            continue
        valor_entrada = valores_entrada_venda.get(lanc.id, Decimal(str(lanc.valor)))
        if valor_entrada <= 0:
            continue
        movimentacoes.append(
            FluxoCaixaMovimentacao(
                data=lanc.data_lancamento
                if isinstance(lanc.data_lancamento, date)
                else lanc.data_lancamento.date(),
                tipo=lanc.tipo,
                descricao=lanc.descricao,
                categoria=lanc.categoria.nome if lanc.categoria else "Sem Categoria",
                valor=float(valor_entrada),
                origem_tipo="lancamento_manual",
                origem_id=lanc.id,
                status="realizado",
            )
        )

    # 🆕 LANÇAMENTOS DA TABELA FLUXO_CAIXA (REALIZADOS)
    # Converter para datetime para pegar horário completo
    dt_inicio_datetime = datetime.combine(dt_inicio, datetime.min.time())
    dt_fim_datetime = datetime.combine(dt_fim, datetime.max.time())

    fluxos_realizados = (
        db.query(FluxoCaixa)
        .filter(
            and_(
                FluxoCaixa.tenant_id == tenant_id,
                FluxoCaixa.data_movimentacao >= dt_inicio_datetime,
                FluxoCaixa.data_movimentacao <= dt_fim_datetime,
                FluxoCaixa.status == "realizado",
            )
        )
        .all()
    )
    numeros_venda_por_conta = _mapa_numeros_venda_por_conta(
        db,
        tenant_id,
        (
            fluxo.origem_id
            for fluxo in fluxos_realizados
            if fluxo.origem_tipo == "conta_receber"
        ),
    )

    ids_fluxo_cp_realizado = {
        fluxo.origem_id
        for fluxo in fluxos_realizados
        if fluxo.origem_tipo == "conta_pagar" and fluxo.origem_id is not None
    }
    contas_fluxo_realizado = {}
    contas_fluxo_com_pagamento = set()
    if ids_fluxo_cp_realizado:
        contas_fluxo_realizado = {
            conta.id: conta
            for conta in db.query(ContaPagar)
            .filter(
                ContaPagar.tenant_id == tenant_id,
                ContaPagar.id.in_(ids_fluxo_cp_realizado),
            )
            .all()
        }
        contas_fluxo_com_pagamento = {
            conta_id
            for (conta_id,) in db.query(Pagamento.conta_pagar_id)
            .filter(
                Pagamento.tenant_id == tenant_id,
                Pagamento.conta_pagar_id.in_(contas_fluxo_realizado),
            )
            .all()
        }

    for fluxo in fluxos_realizados:
        conta_fluxo = (
            contas_fluxo_realizado.get(fluxo.origem_id)
            if fluxo.origem_tipo == "conta_pagar"
            else None
        )
        if conta_fluxo and (
            (conta_fluxo.status == "pago" and conta_fluxo.data_pagamento is not None)
            or conta_fluxo.id in contas_fluxo_com_pagamento
        ):
            # O fluxo é espelho da baixa. Mantemos um fluxo legado sem baixa.
            continue
        numero_venda_fluxo = numeros_venda_por_conta.get(fluxo.origem_id)

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
    # Recebiveis e pagaveis abaixo usam tenant_id e pulam titulos ja previstos.
    fluxos_previstos = (
        db.query(FluxoCaixa)
        .filter(
            and_(
                FluxoCaixa.tenant_id == tenant_id,
                FluxoCaixa.data_prevista >= dt_inicio_datetime,
                FluxoCaixa.data_prevista <= dt_fim_datetime,
                FluxoCaixa.status == "previsto",
                FluxoCaixa.origem_tipo.in_(["conta_receber", "conta_pagar"]),
                FluxoCaixa.origem_id.isnot(None),
            )
        )
        .all()
    )
    contas_receber_com_fluxo_previsto = {
        fluxo.origem_id
        for fluxo in fluxos_previstos
        if fluxo.origem_tipo == "conta_receber"
    }
    ids_contas_fluxo_previsto = {
        fluxo.origem_id
        for fluxo in fluxos_previstos
        if fluxo.origem_tipo == "conta_pagar" and fluxo.origem_id is not None
    }
    contas_pagar_com_fluxo_previsto = set()
    if ids_contas_fluxo_previsto:
        contas_pagar_com_fluxo_previsto = {
            conta_id
            for (conta_id,) in db.query(ContaPagar.id)
            .filter(
                ContaPagar.tenant_id == tenant_id,
                ContaPagar.id.in_(ids_contas_fluxo_previsto),
            )
            .all()
        }

    contas_receber_pendentes = (
        db.query(ContaReceber)
        .options(joinedload(ContaReceber.cliente))
        .filter(
            and_(
                ContaReceber.tenant_id == tenant_id,
                ContaReceber.data_vencimento >= dt_inicio,
                ContaReceber.data_vencimento <= dt_fim,
                ContaReceber.status.notin_(
                    ["recebido", "pago", "cancelado", "cancelada"]
                ),
            )
        )
        .all()
    )
    numeros_venda_por_conta.update(
        _mapa_numeros_venda_por_conta(
            db,
            tenant_id,
            (conta.id for conta in contas_receber_pendentes if conta.venda_id),
        )
    )

    for conta in contas_receber_pendentes:
        if conta.id in contas_receber_com_fluxo_previsto:
            continue

        valor_restante = (conta.valor_final or 0) - (conta.valor_recebido or 0)
        if valor_restante > 0:
            numero_venda_conta = numeros_venda_por_conta.get(conta.id)

            cliente_nome = conta.cliente.nome if conta.cliente else "Cliente"
            movimentacoes.append(
                FluxoCaixaMovimentacao(
                    data=conta.data_vencimento,
                    tipo="entrada",
                    descricao=f"A Receber - {cliente_nome}",
                    categoria="Recebimentos",
                    valor=float(valor_restante),
                    origem_tipo="conta_receber",
                    origem_id=conta.id,
                    numero_venda=numero_venda_conta,
                    status="previsto",
                )
            )

    contas_pagar_pendentes = (
        db.query(ContaPagar)
        .options(joinedload(ContaPagar.fornecedor))
        .filter(
            and_(
                ContaPagar.tenant_id == tenant_id,
                ContaPagar.data_vencimento >= dt_inicio,
                ContaPagar.data_vencimento <= dt_fim,
                ContaPagar.status.in_(["pendente", "atrasado", "vencido", "parcial"]),
            )
        )
        .all()
    )

    for conta in contas_pagar_pendentes:
        valor_restante = (conta.valor_final or 0) - (conta.valor_pago or 0)
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
    for lanc in lancamentos_previstos:
        if _conta_pagar_de_lancamento_automatico(lanc) in contas_espelhadas:
            continue
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
    numeros_venda_por_conta.update(
        _mapa_numeros_venda_por_conta(
            db,
            tenant_id,
            (
                fluxo.origem_id
                for fluxo in fluxos_previstos
                if fluxo.origem_tipo == "conta_receber"
            ),
        )
    )

    for fluxo in fluxos_previstos:
        if (
            fluxo.origem_tipo == "conta_pagar"
            and fluxo.origem_id in contas_pagar_com_fluxo_previsto
        ):
            continue
        numero_venda_fluxo = numeros_venda_por_conta.get(fluxo.origem_id)

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
                    Venda.tenant_id == tenant_id,
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
                    numero_movimento = numeros_venda_por_conta.get(mov.origem_id)
                    if (
                        numero_movimento
                        and str(numero_venda).lower() in str(numero_movimento).lower()
                    ):
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
