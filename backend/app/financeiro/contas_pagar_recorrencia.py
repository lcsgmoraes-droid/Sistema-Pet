"""Helpers de recorrencia das contas a pagar."""

import calendar
import logging
from datetime import date, timedelta
from typing import List, Optional

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.financeiro_models import ContaPagar, LancamentoManual


logger = logging.getLogger(__name__)

RECORRENCIA_JANELA_MESES_PADRAO = 12


def calcular_proxima_recorrencia(
    data_base: date, tipo_recorrencia: str, intervalo_dias: Optional[int] = None
) -> date:
    """Calcula a proxima data de recorrencia baseado no tipo."""
    if tipo_recorrencia == "semanal":
        return data_base + timedelta(days=7)
    if tipo_recorrencia == "quinzenal":
        return data_base + timedelta(days=15)
    if tipo_recorrencia == "mensal":
        mes = data_base.month + 1
        ano = data_base.year
        if mes > 12:
            mes = 1
            ano += 1
        try:
            return data_base.replace(year=ano, month=mes)
        except ValueError:
            ultimo_dia = calendar.monthrange(ano, mes)[1]
            return date(ano, mes, ultimo_dia)
    if tipo_recorrencia == "personalizado" and intervalo_dias:
        return data_base + timedelta(days=intervalo_dias)
    raise ValueError(f"Tipo de recorrencia invalido: {tipo_recorrencia}")


def adicionar_meses(data_base: date, meses_adicionar: int) -> date:
    mes = data_base.month + meses_adicionar
    ano = data_base.year
    while mes > 12:
        mes -= 12
        ano += 1

    try:
        return data_base.replace(year=ano, month=mes)
    except ValueError:
        ultimo_dia = calendar.monthrange(ano, mes)[1]
        return date(ano, mes, ultimo_dia)


def calcular_limite_janela_recorrencia(
    hoje: date,
    meses: int = RECORRENCIA_JANELA_MESES_PADRAO,
) -> date:
    return adicionar_meses(hoje, meses)


def _gerar_contas_recorrentes_ate_janela(
    db: Session,
    tenant_id,
    conta_origem: ContaPagar,
    limite_recorrencia: date,
) -> List[ContaPagar]:
    contas_criadas: List[ContaPagar] = []

    while (
        conta_origem.proxima_recorrencia
        and conta_origem.proxima_recorrencia <= limite_recorrencia
    ):
        nova_data_vencimento = conta_origem.proxima_recorrencia

        if (
            conta_origem.data_fim_recorrencia
            and nova_data_vencimento > conta_origem.data_fim_recorrencia
        ):
            break

        if conta_origem.numero_repeticoes:
            count_geradas = (
                db.query(func.count(ContaPagar.id))
                .filter(ContaPagar.conta_recorrencia_origem_id == conta_origem.id)
                .scalar()
            )
            if count_geradas >= conta_origem.numero_repeticoes:
                logger.info(
                    "Conta #%s atingiu o numero maximo de repeticoes (%s)",
                    conta_origem.id,
                    conta_origem.numero_repeticoes,
                )
                break

        conta_existente = (
            db.query(ContaPagar)
            .filter(
                ContaPagar.conta_recorrencia_origem_id == conta_origem.id,
                ContaPagar.data_vencimento == nova_data_vencimento,
            )
            .first()
        )
        if conta_existente:
            conta_origem.proxima_recorrencia = calcular_proxima_recorrencia(
                nova_data_vencimento,
                conta_origem.tipo_recorrencia,
                conta_origem.intervalo_dias,
            )
            continue

        nova_conta = ContaPagar(
            descricao=(
                f"{conta_origem.descricao} "
                f"(Recorrencia {nova_data_vencimento.strftime('%m/%Y')})"
            ),
            fornecedor_id=conta_origem.fornecedor_id,
            categoria_id=conta_origem.categoria_id,
            dre_subcategoria_id=conta_origem.dre_subcategoria_id,
            canal=conta_origem.canal,
            tipo_despesa_id=conta_origem.tipo_despesa_id,
            valor_original=conta_origem.valor_original,
            valor_final=conta_origem.valor_original,
            data_emissao=nova_data_vencimento,
            data_vencimento=nova_data_vencimento,
            status="pendente",
            nota_entrada_id=conta_origem.nota_entrada_id,
            documento=conta_origem.documento,
            observacoes=f"Gerada automaticamente da recorrencia #{conta_origem.id}",
            conta_recorrencia_origem_id=conta_origem.id,
            user_id=conta_origem.user_id,
            tenant_id=tenant_id,
        )

        db.add(nova_conta)
        contas_criadas.append(nova_conta)

        lancamento = LancamentoManual(
            tipo="saida",
            valor=nova_conta.valor_original,
            descricao=nova_conta.descricao,
            data_lancamento=nova_conta.data_vencimento,
            data_competencia=nova_conta.data_vencimento,
            categoria_id=nova_conta.categoria_id,
            status="previsto",
            documento=nova_conta.documento,
            observacoes=f"Gerado automaticamente da recorrencia #{conta_origem.id}",
            gerado_automaticamente=True,
            user_id=conta_origem.user_id,
            tenant_id=tenant_id,
        )
        db.add(lancamento)

        conta_origem.proxima_recorrencia = calcular_proxima_recorrencia(
            nova_data_vencimento,
            conta_origem.tipo_recorrencia,
            conta_origem.intervalo_dias,
        )
        db.flush()

    return contas_criadas


def _garantir_janela_recorrencia_apos_pagamento(
    db: Session,
    tenant_id,
    conta_paga: ContaPagar,
    hoje: Optional[date] = None,
) -> List[ContaPagar]:
    conta_origem = conta_paga
    if not conta_paga.eh_recorrente and conta_paga.conta_recorrencia_origem_id:
        conta_origem = (
            db.query(ContaPagar)
            .filter(
                ContaPagar.id == conta_paga.conta_recorrencia_origem_id,
                ContaPagar.tenant_id == tenant_id,
            )
            .first()
        )

    if not conta_origem:
        return []

    if (
        not conta_origem.eh_recorrente
        or not conta_origem.tipo_recorrencia
        or not conta_origem.proxima_recorrencia
    ):
        return []

    data_referencia = hoje or date.today()
    if (
        conta_origem.data_fim_recorrencia
        and conta_origem.data_fim_recorrencia < data_referencia
    ):
        return []

    limite_recorrencia = calcular_limite_janela_recorrencia(data_referencia)
    return _gerar_contas_recorrentes_ate_janela(
        db=db,
        tenant_id=tenant_id,
        conta_origem=conta_origem,
        limite_recorrencia=limite_recorrencia,
    )


def _obter_origem_recorrencia(
    db: Session,
    tenant_id,
    conta: ContaPagar,
) -> Optional[ContaPagar]:
    if conta.conta_recorrencia_origem_id:
        return (
            db.query(ContaPagar)
            .filter(
                ContaPagar.id == conta.conta_recorrencia_origem_id,
                ContaPagar.tenant_id == tenant_id,
            )
            .first()
        )
    return conta if conta.eh_recorrente else None


def _query_contas_recorrencia(db: Session, tenant_id, origem_id: int):
    return db.query(ContaPagar).filter(
        ContaPagar.tenant_id == tenant_id,
        or_(
            ContaPagar.id == origem_id,
            ContaPagar.conta_recorrencia_origem_id == origem_id,
        ),
    )


def _garantir_janela_recorrencia_conta(
    db: Session,
    tenant_id,
    conta: ContaPagar,
    hoje: Optional[date] = None,
) -> List[ContaPagar]:
    conta_origem = _obter_origem_recorrencia(db, tenant_id, conta)
    if (
        not conta_origem
        or not conta_origem.eh_recorrente
        or not conta_origem.tipo_recorrencia
    ):
        return []

    if not conta_origem.proxima_recorrencia:
        ultima_data = (
            db.query(func.max(ContaPagar.data_vencimento))
            .filter(
                ContaPagar.tenant_id == tenant_id,
                ContaPagar.conta_recorrencia_origem_id == conta_origem.id,
            )
            .scalar()
        )
        data_base = ultima_data or conta_origem.data_vencimento
        conta_origem.proxima_recorrencia = calcular_proxima_recorrencia(
            data_base,
            conta_origem.tipo_recorrencia,
            conta_origem.intervalo_dias,
        )

    data_referencia = hoje or date.today()
    if (
        conta_origem.data_fim_recorrencia
        and conta_origem.data_fim_recorrencia < data_referencia
    ):
        return []

    return _gerar_contas_recorrentes_ate_janela(
        db=db,
        tenant_id=tenant_id,
        conta_origem=conta_origem,
        limite_recorrencia=calcular_limite_janela_recorrencia(data_referencia),
    )


def _aplicar_edicao_recorrencia_futura(
    db: Session,
    tenant_id,
    conta: ContaPagar,
    campos,
) -> int:
    conta_origem = _obter_origem_recorrencia(db, tenant_id, conta)
    if not conta_origem:
        return 0

    campos_replicaveis = {
        "descricao",
        "fornecedor_id",
        "categoria_id",
        "dre_subcategoria_id",
        "tipo_despesa_id",
        "canal",
        "valor_original",
        "documento",
        "observacoes",
    }
    if not campos_replicaveis.intersection(campos):
        return 0

    futuras = (
        db.query(ContaPagar)
        .filter(
            ContaPagar.tenant_id == tenant_id,
            ContaPagar.conta_recorrencia_origem_id == conta_origem.id,
            ContaPagar.id != conta.id,
            ContaPagar.data_vencimento > conta.data_vencimento,
            ContaPagar.status != "pago",
            func.coalesce(ContaPagar.valor_pago, 0) <= 0,
        )
        .all()
    )

    atualizadas = 0
    for futura in futuras:
        if "descricao" in campos:
            futura.descricao = (
                f"{conta.descricao} "
                f"(Recorrencia {futura.data_vencimento.strftime('%m/%Y')})"
            )
        if "fornecedor_id" in campos:
            futura.fornecedor_id = conta.fornecedor_id
        if "categoria_id" in campos:
            futura.categoria_id = conta.categoria_id
        if "dre_subcategoria_id" in campos:
            futura.dre_subcategoria_id = conta.dre_subcategoria_id
        if "tipo_despesa_id" in campos:
            futura.tipo_despesa_id = conta.tipo_despesa_id
        if "canal" in campos:
            futura.canal = conta.canal
        if "valor_original" in campos:
            futura.valor_original = conta.valor_original
            futura.valor_final = conta.valor_final
        if "documento" in campos:
            futura.documento = conta.documento
        if "observacoes" in campos:
            futura.observacoes = conta.observacoes
        atualizadas += 1

    return atualizadas
