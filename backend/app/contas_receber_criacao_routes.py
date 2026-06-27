"""Rotas de criacao de contas a receber."""

import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from .auth.dependencies import get_current_user_and_tenant
from .contas_receber_recorrencias import calcular_proxima_recorrencia
from .contas_receber_schemas import ContaReceberCreate
from .db import get_session
from .domain.dre.lancamento_dre_sync import atualizar_dre_por_lancamento
from .dre_plano_contas_models import DRESubcategoria
from .financeiro_models import ContaReceber, LancamentoManual
from .idempotency import idempotent

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/", status_code=status.HTTP_201_CREATED)
@idempotent()  # ðŸ”’ IDEMPOTÃŠNCIA: evita criaÃ§Ã£o duplicada de contas a receber
async def criar_conta_receber(
    conta: ContaReceberCreate,
    request: Request,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    Cria uma ou mais contas a receber (com parcelamento se necessÃ¡rio)
    + ATUALIZA DRE EM TEMPO REAL
    """
    current_user, tenant_id = user_and_tenant
    contas_criadas = []

    try:
        # ============================
        # VALIDAÃ‡ÃƒO DRE - CRÃTICA
        # ============================
        subcategoria = (
            db.query(DRESubcategoria)
            .filter(
                DRESubcategoria.id == conta.dre_subcategoria_id,
                DRESubcategoria.tenant_id == tenant_id,
                DRESubcategoria.ativo.is_(True),
            )
            .first()
        )

        if not subcategoria:
            raise HTTPException(
                status_code=400,
                detail=f"Subcategoria DRE {conta.dre_subcategoria_id} invÃ¡lida ou nÃ£o pertence a este tenant",
            )

        # ============================
        # CRIAÃ‡ÃƒO DE CONTAS
        # ============================
        if conta.eh_parcelado and conta.total_parcelas > 1:
            # Criar conta principal (controle)
            conta_principal = ContaReceber(
                descricao=f"{conta.descricao} (Parcelado)",
                cliente_id=conta.cliente_id,
                categoria_id=conta.categoria_id,
                dre_subcategoria_id=conta.dre_subcategoria_id,
                canal=conta.canal,
                valor_original=conta.valor_original,
                valor_final=conta.valor_original,
                data_emissao=conta.data_emissao,
                data_vencimento=conta.data_vencimento,
                status="parcelado",
                eh_parcelado=True,
                total_parcelas=conta.total_parcelas,
                venda_id=conta.venda_id,
                documento=conta.documento,
                observacoes=conta.observacoes,
                user_id=current_user.id,
            )
            db.add(conta_principal)
            db.flush()

            # Criar parcelas
            valor_parcela = conta.valor_original / conta.total_parcelas

            for i in range(1, conta.total_parcelas + 1):
                # Vencimento: soma i meses
                vencimento_parcela = conta.data_vencimento
                if i > 1:
                    mes = vencimento_parcela.month + (i - 1)
                    ano = vencimento_parcela.year
                    while mes > 12:
                        mes -= 12
                        ano += 1
                    vencimento_parcela = vencimento_parcela.replace(year=ano, month=mes)

                parcela = ContaReceber(
                    descricao=f"{conta.descricao} - Parcela {i}/{conta.total_parcelas}",
                    cliente_id=conta.cliente_id,
                    categoria_id=conta.categoria_id,
                    dre_subcategoria_id=conta.dre_subcategoria_id,
                    canal=conta.canal,
                    valor_original=valor_parcela,
                    valor_final=valor_parcela,
                    data_emissao=conta.data_emissao,
                    data_vencimento=vencimento_parcela,
                    status="pendente",
                    eh_parcelado=True,
                    numero_parcela=i,
                    total_parcelas=conta.total_parcelas,
                    conta_principal_id=conta_principal.id,
                    venda_id=conta.venda_id,
                    documento=conta.documento,
                    observacoes=f"Parcela {i} de {conta.total_parcelas}",
                    user_id=current_user.id,
                )
                db.add(parcela)
                contas_criadas.append(parcela)

        else:
            # Conta simples
            nova_conta = ContaReceber(
                descricao=conta.descricao,
                cliente_id=conta.cliente_id,
                categoria_id=conta.categoria_id,
                dre_subcategoria_id=conta.dre_subcategoria_id,
                canal=conta.canal,
                valor_original=conta.valor_original,
                valor_final=conta.valor_original,
                data_emissao=conta.data_emissao,
                data_vencimento=conta.data_vencimento,
                status="pendente",
                venda_id=conta.venda_id,
                documento=conta.documento,
                observacoes=conta.observacoes,
                # RecorrÃªncia
                eh_recorrente=conta.eh_recorrente,
                tipo_recorrencia=conta.tipo_recorrencia,
                intervalo_dias=conta.intervalo_dias,
                data_inicio_recorrencia=conta.data_inicio_recorrencia
                or conta.data_vencimento,
                data_fim_recorrencia=conta.data_fim_recorrencia,
                numero_repeticoes=conta.numero_repeticoes,
                user_id=current_user.id,
            )

            # Se Ã© recorrente, calcular prÃ³xima recorrÃªncia
            if nova_conta.eh_recorrente and nova_conta.tipo_recorrencia:
                try:
                    nova_conta.proxima_recorrencia = calcular_proxima_recorrencia(
                        nova_conta.data_vencimento,
                        nova_conta.tipo_recorrencia,
                        nova_conta.intervalo_dias,
                    )
                except Exception as e:
                    logger.warning(
                        f"âš ï¸  Erro ao calcular prÃ³xima recorrÃªncia: {e}"
                    )

            db.add(nova_conta)
            contas_criadas.append(nova_conta)

        db.commit()

        # ============================
        # ATUALIZAÃ‡ÃƒO DRE EM TEMPO REAL
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
                    tipo_movimentacao="RECEITA",  # â† Contas a RECEBER = RECEITA
                )
                logger.info(
                    f"âœ… DRE atualizado: ContaReceber #{conta_criada.id} â†’ Subcategoria {conta_criada.dre_subcategoria_id} â†’ Canal {conta_criada.canal}"
                )
            except Exception as e:
                # NÃ£o bloqueia criaÃ§Ã£o se DRE falhar (logging apenas)
                logger.warning(
                    f"âš ï¸ Erro ao atualizar DRE para ContaReceber #{conta_criada.id}: {e}"
                )

        # INTEGRAÃ‡ÃƒO REVERSA: Criar lanÃ§amentos manuais no fluxo de caixa
        for conta_criada in contas_criadas:
            try:
                lancamento = LancamentoManual(
                    tipo="entrada",
                    valor=conta_criada.valor_original,
                    descricao=conta_criada.descricao,
                    data_lancamento=conta_criada.data_emissao,
                    data_prevista=conta_criada.data_vencimento,
                    data_efetivacao=None,  # Ainda nÃ£o recebido
                    categoria_id=conta_criada.categoria_id,
                    conta_bancaria_id=None,
                    status="previsto",
                    observacoes=f"Gerado automaticamente da conta a receber #{conta_criada.id}",
                    gerado_automaticamente=True,
                    confianca_ia=None,
                )
                db.add(lancamento)
            except Exception as e:
                logger.warning(
                    f"âš ï¸  NÃ£o foi possÃ­vel criar lanÃ§amento para conta #{conta_criada.id}: {e}"
                )

        db.commit()

        logger.info(f"âœ… {len(contas_criadas)} conta(s) a receber criada(s)")

        return {
            "message": "Conta(s) criada(s) com sucesso",
            "total_contas": len(contas_criadas),
            "ids": [c.id for c in contas_criadas],
        }

    except Exception as e:
        logger.error(f"âŒ Erro ao criar conta: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# LISTAR CONTAS A RECEBER
# ============================================================================
