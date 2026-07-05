"""Rotas de criacao de contas a pagar."""

import logging
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user_and_tenant
from app.db import get_session
from app.domain.dre.lancamento_dre_sync import atualizar_dre_por_lancamento
from app.financeiro.contas_pagar_classificacao import (
    aplicar_classificacao_aprendida_conta_pagar,
)
from app.financeiro.contas_pagar_common import (
    _obter_tipo_produto_revenda_id,
    _resolver_dre_subcategoria_conta_pagar,
)
from app.financeiro.contas_pagar_recorrencia import (
    _gerar_contas_recorrentes_ate_janela,
    calcular_limite_janela_recorrencia,
    calcular_proxima_recorrencia,
)
from app.financeiro.contas_pagar_schemas import ContaPagarCreate
from app.financeiro_models import CategoriaFinanceira, ContaPagar, LancamentoManual
from app.idempotency import idempotent
from app.services.reconciliacao_provisao_service import reconciliar_provisao
from app.services.reconciliacao_simples_service import reconciliar_das_simples

logger = logging.getLogger(__name__)
router = APIRouter()


# CRIAR CONTA A PAGAR
# ============================================================================


@router.post("/", status_code=status.HTTP_201_CREATED)
@idempotent()  # 🔒 IDEMPOTÊNCIA: evita criação duplicada de contas a pagar
async def criar_conta_pagar(
    conta: ContaPagarCreate,
    request: Request,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    Cria uma ou mais contas a pagar (com parcelamento se necessário)
    + ATUALIZA DRE EM TEMPO REAL
    """
    current_user, tenant_id = user_and_tenant
    contas_criadas = []

    try:
        conta_pre_classificacao = ContaPagar(
            descricao=conta.descricao,
            fornecedor_id=conta.fornecedor_id,
            categoria_id=conta.categoria_id,
            dre_subcategoria_id=conta.dre_subcategoria_id,
            canal=conta.canal,
            tipo_despesa_id=conta.tipo_despesa_id,
            valor_original=conta.valor_original,
            valor_final=conta.valor_original,
            data_emissao=conta.data_emissao,
            data_vencimento=conta.data_vencimento,
            user_id=current_user.id,
            tenant_id=tenant_id,
        )
        if aplicar_classificacao_aprendida_conta_pagar(
            db, tenant_id, conta_pre_classificacao
        ):
            conta.categoria_id = conta_pre_classificacao.categoria_id
            conta.dre_subcategoria_id = conta_pre_classificacao.dre_subcategoria_id
            conta.canal = conta_pre_classificacao.canal or conta.canal
            conta.tipo_despesa_id = conta_pre_classificacao.tipo_despesa_id

        # ============================
        # CLASSIFICACAO DRE
        # ============================
        conta.dre_subcategoria_id = _resolver_dre_subcategoria_conta_pagar(
            db,
            tenant_id,
            dre_subcategoria_id=conta.dre_subcategoria_id,
            categoria_id=conta.categoria_id,
        )

        tipo_despesa_id = conta.tipo_despesa_id
        if conta.nota_entrada_id and not tipo_despesa_id:
            tipo_despesa_id = _obter_tipo_produto_revenda_id(db, tenant_id)

        # ============================
        # CRIAÇÃO DE CONTAS
        # ============================
        if conta.eh_parcelado and conta.total_parcelas > 1:
            # Criar conta principal (controle)
            conta_principal = ContaPagar(
                descricao=f"{conta.descricao} (Parcelado)",
                fornecedor_id=conta.fornecedor_id,
                categoria_id=conta.categoria_id,
                dre_subcategoria_id=conta.dre_subcategoria_id,
                canal=conta.canal,
                tipo_despesa_id=tipo_despesa_id,
                valor_original=conta.valor_original,
                valor_final=conta.valor_original,
                data_emissao=conta.data_emissao,
                data_vencimento=conta.data_vencimento,
                status="parcelado",
                eh_parcelado=True,
                total_parcelas=conta.total_parcelas,
                nota_entrada_id=conta.nota_entrada_id,
                documento=conta.documento,
                observacoes=conta.observacoes,
                user_id=current_user.id,
                tenant_id=tenant_id,
            )
            db.add(conta_principal)
            db.flush()

            # Criar parcelas
            valor_parcela = conta.valor_original / conta.total_parcelas

            for i in range(1, conta.total_parcelas + 1):
                # Vencimento: soma i meses
                vencimento_parcela = conta.data_vencimento
                if i > 1:
                    # Adiciona meses
                    mes = vencimento_parcela.month + (i - 1)
                    ano = vencimento_parcela.year
                    while mes > 12:
                        mes -= 12
                        ano += 1
                    vencimento_parcela = vencimento_parcela.replace(year=ano, month=mes)

                parcela = ContaPagar(
                    descricao=f"{conta.descricao} - Parcela {i}/{conta.total_parcelas}",
                    fornecedor_id=conta.fornecedor_id,
                    categoria_id=conta.categoria_id,
                    dre_subcategoria_id=conta.dre_subcategoria_id,
                    canal=conta.canal,
                    tipo_despesa_id=tipo_despesa_id,
                    valor_original=valor_parcela,
                    valor_final=valor_parcela,
                    data_emissao=conta.data_emissao,
                    data_vencimento=vencimento_parcela,
                    status="pendente",
                    eh_parcelado=True,
                    numero_parcela=i,
                    total_parcelas=conta.total_parcelas,
                    conta_principal_id=conta_principal.id,
                    nota_entrada_id=conta.nota_entrada_id,
                    documento=conta.documento,
                    observacoes=f"Parcela {i} de {conta.total_parcelas}",
                    user_id=current_user.id,
                    tenant_id=tenant_id,
                )
                db.add(parcela)
                contas_criadas.append(parcela)

        else:
            # Conta simples (não parcelada)
            nova_conta = ContaPagar(
                descricao=conta.descricao,
                fornecedor_id=conta.fornecedor_id,
                categoria_id=conta.categoria_id,
                dre_subcategoria_id=conta.dre_subcategoria_id,
                canal=conta.canal,
                tipo_despesa_id=tipo_despesa_id,
                valor_original=conta.valor_original,
                valor_final=conta.valor_original,
                data_emissao=conta.data_emissao,
                data_vencimento=conta.data_vencimento,
                status="pendente",
                nota_entrada_id=conta.nota_entrada_id,
                documento=conta.documento,
                observacoes=conta.observacoes,
                # Recorrência
                eh_recorrente=conta.eh_recorrente,
                tipo_recorrencia=conta.tipo_recorrencia,
                intervalo_dias=conta.intervalo_dias,
                data_inicio_recorrencia=conta.data_inicio_recorrencia
                or conta.data_vencimento,
                data_fim_recorrencia=conta.data_fim_recorrencia,
                numero_repeticoes=conta.numero_repeticoes,
                user_id=current_user.id,
                tenant_id=tenant_id,
            )

            # Se é recorrente, calcular próxima recorrência
            if nova_conta.eh_recorrente and nova_conta.tipo_recorrencia:
                try:
                    nova_conta.proxima_recorrencia = calcular_proxima_recorrencia(
                        nova_conta.data_vencimento,
                        nova_conta.tipo_recorrencia,
                        nova_conta.intervalo_dias,
                    )
                except Exception as e:
                    logger.warning(f"⚠️  Erro ao calcular próxima recorrência: {e}")

            db.add(nova_conta)
            contas_criadas.append(nova_conta)

            if (
                nova_conta.eh_recorrente
                and nova_conta.tipo_recorrencia
                and nova_conta.proxima_recorrencia
            ):
                db.flush()
                limite_recorrencia = calcular_limite_janela_recorrencia(date.today())
                contas_criadas.extend(
                    _gerar_contas_recorrentes_ate_janela(
                        db=db,
                        tenant_id=tenant_id,
                        conta_origem=nova_conta,
                        limite_recorrencia=limite_recorrencia,
                    )
                )

        db.commit()

        # ============================
        # ATUALIZAR DRE EM TEMPO REAL
        # ============================
        for conta_criada in contas_criadas:
            try:
                atualizar_dre_por_lancamento(
                    db=db,
                    tenant_id=tenant_id,
                    dre_subcategoria_id=conta_criada.dre_subcategoria_id,
                    canal=conta_criada.canal,
                    valor=conta_criada.valor_original,
                    data_lancamento=conta_criada.data_vencimento,
                    tipo_movimentacao="DESPESA",
                )
            except Exception as e:
                logger.warning(
                    f"⚠️ Erro ao atualizar DRE para conta #{conta_criada.id}: {e}"
                )

        # ============================
        # RECONCILIAÇÃO DAS SIMPLES NACIONAL
        # ============================
        for conta_criada in contas_criadas:
            try:
                # Verificar se é DAS Simples Nacional
                categoria = (
                    db.query(CategoriaFinanceira)
                    .filter(CategoriaFinanceira.id == conta_criada.categoria_id)
                    .first()
                )

                if (
                    categoria
                    and "DAS" in categoria.nome.upper()
                    and "SIMPLES" in categoria.nome.upper()
                ):
                    # Determinar competência pela data de emissão
                    mes_competencia = conta_criada.data_emissao.month
                    ano_competencia = conta_criada.data_emissao.year

                    resultado = reconciliar_das_simples(
                        db=db,
                        tenant_id=tenant_id,
                        valor_das=conta_criada.valor_original,
                        mes_competencia=mes_competencia,
                        ano_competencia=ano_competencia,
                        usuario_id=current_user.id,
                    )

                    if resultado.get("sucesso"):
                        logger.info(
                            f"✅ DAS reconciliado: R$ {resultado['valor_das_real']:.2f} "
                            f"(Ajuste: R$ {abs(resultado['diferenca']):.2f})"
                        )
                        if resultado.get("sugestao_aliquota"):
                            logger.info(
                                f"💡 Nova alíquota sugerida: {resultado['sugestao_aliquota']}%"
                            )
                    else:
                        logger.warning(
                            f"⚠️ Reconciliação falhou: {resultado.get('motivo')}"
                        )
            except Exception as e:
                logger.warning(
                    f"⚠️ Erro ao reconciliar DAS para conta #{conta_criada.id}: {e}"
                )
                import traceback

                traceback.print_exc()

        # ============================
        # RECONCILIAÇÃO DE PROVISÕES TRABALHISTAS
        # ============================
        for conta_criada in contas_criadas:
            try:
                categoria = (
                    db.query(CategoriaFinanceira)
                    .filter(CategoriaFinanceira.id == conta_criada.categoria_id)
                    .first()
                )

                if not categoria:
                    continue

                # Determinar competência pela data de emissão (ou vencimento)
                mes_competencia = conta_criada.data_emissao.month
                ano_competencia = conta_criada.data_emissao.year

                # Reconciliar INSS
                if categoria.nome == "INSS Patronal":
                    reconciliar_provisao(
                        db=db,
                        tenant_id=tenant_id,
                        nome_provisao="Provisão INSS Patronal",
                        nome_real="INSS Patronal",
                        valor_real=conta_criada.valor_original,
                        mes=mes_competencia,
                        ano=ano_competencia,
                        observacao_real="INSS Patronal (valor real)",
                    )
                    logger.info(
                        f"✅ INSS reconciliado: R$ {conta_criada.valor_original:.2f}"
                    )
                    db.commit()

                # Reconciliar FGTS
                elif categoria.nome == "FGTS":
                    reconciliar_provisao(
                        db=db,
                        tenant_id=tenant_id,
                        nome_provisao="Provisão FGTS",
                        nome_real="FGTS",
                        valor_real=conta_criada.valor_original,
                        mes=mes_competencia,
                        ano=ano_competencia,
                        observacao_real="FGTS (valor real)",
                    )
                    logger.info(
                        f"✅ FGTS reconciliado: R$ {conta_criada.valor_original:.2f}"
                    )
                    db.commit()

                # Reconciliar Folha de Pagamento
                elif categoria.nome == "Folha de Pagamento":
                    reconciliar_provisao(
                        db=db,
                        tenant_id=tenant_id,
                        nome_provisao="Provisão Folha de Pagamento",
                        nome_real="Folha de Pagamento",
                        valor_real=conta_criada.valor_original,
                        mes=mes_competencia,
                        ano=ano_competencia,
                        observacao_real="Folha de Pagamento (valor real)",
                    )
                    logger.info(
                        f"✅ Folha reconciliada: R$ {conta_criada.valor_original:.2f}"
                    )
                    db.commit()

            except Exception as e:
                logger.warning(
                    f"⚠️ Erro ao reconciliar provisão para conta #{conta_criada.id}: {e}"
                )
                import traceback

                traceback.print_exc()

        # INTEGRAÇÃO REVERSA: Criar lançamentos manuais no fluxo de caixa
        for conta_criada in contas_criadas:
            try:
                lancamento = LancamentoManual(
                    tipo="saida",
                    valor=conta_criada.valor_original,
                    descricao=conta_criada.descricao,
                    data_lancamento=conta_criada.data_emissao,
                    data_competencia=conta_criada.data_vencimento,
                    categoria_id=conta_criada.categoria_id,
                    conta_bancaria_id=None,
                    status="previsto",
                    documento=f"CONTA-PAGAR-{conta_criada.id}",
                    observacoes=f"Gerado automaticamente da conta a pagar #{conta_criada.id}",
                    gerado_automaticamente=True,
                    confianca_ia=None,
                    user_id=current_user.id,
                    tenant_id=tenant_id,
                )
                db.add(lancamento)
            except Exception as e:
                logger.warning(
                    f"⚠️  Não foi possível criar lançamento para conta #{conta_criada.id}: {e}"
                )

        db.commit()

        logger.info(f"✅ {len(contas_criadas)} conta(s) a pagar criada(s)")

        return {
            "message": "Conta(s) criada(s) com sucesso",
            "total_contas": len(contas_criadas),
            "ids": [c.id for c in contas_criadas],
        }

    except HTTPException as e:
        logger.warning(f"Erro validado ao criar conta: {e.detail}")
        db.rollback()
        raise
    except Exception as e:
        logger.error(f"❌ Erro ao criar conta: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
