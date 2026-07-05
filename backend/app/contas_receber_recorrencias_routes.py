"""Rotas de processamento de recorrencias de contas a receber."""

import logging
from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy import and_, func, or_
from sqlalchemy.orm import Session

from .auth.dependencies import get_current_user_and_tenant
from .contas_receber_recorrencias import calcular_proxima_recorrencia
from .db import get_session
from .financeiro_models import ContaReceber, LancamentoManual

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/processar-recorrencias")
async def processar_recorrencias_contas_receber(
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    Processa contas recorrentes e cria novas contas quando necessÃ¡rio
    Esta rota deve ser executada periodicamente (diariamente recomendado)
    """
    current_user, tenant_id = user_and_tenant
    hoje = date.today()
    contas_criadas = []

    # Buscar contas recorrentes que precisam gerar nova conta
    contas_recorrentes = (
        db.query(ContaReceber)
        .filter(
            and_(
                ContaReceber.eh_recorrente.is_(True),
                ContaReceber.tenant_id == tenant_id,
                ContaReceber.proxima_recorrencia <= hoje,
                or_(
                    ContaReceber.data_fim_recorrencia.is_(None),
                    ContaReceber.data_fim_recorrencia >= hoje,
                ),
            )
        )
        .all()
    )

    for conta_origem in contas_recorrentes:
        try:
            # Verificar se jÃ¡ atingiu o nÃºmero mÃ¡ximo de repetiÃ§Ãµes
            if conta_origem.numero_repeticoes:
                # Contar quantas contas jÃ¡ foram geradas
                count_geradas = (
                    db.query(func.count(ContaReceber.id))
                    .filter(
                        ContaReceber.conta_recorrencia_origem_id == conta_origem.id,
                        ContaReceber.tenant_id == tenant_id,
                    )
                    .scalar()
                )

                if count_geradas >= conta_origem.numero_repeticoes:
                    logger.info(
                        f"ðŸ“… Conta #{conta_origem.id} atingiu o nÃºmero mÃ¡ximo de repetiÃ§Ãµes ({conta_origem.numero_repeticoes})"
                    )
                    continue

            # Criar nova conta baseada na recorrÃªncia
            nova_data_vencimento = conta_origem.proxima_recorrencia

            nova_conta = ContaReceber(
                descricao=f"{conta_origem.descricao} (RecorrÃªncia {nova_data_vencimento.strftime('%m/%Y')})",
                cliente_id=conta_origem.cliente_id,
                categoria_id=conta_origem.categoria_id,
                dre_subcategoria_id=conta_origem.dre_subcategoria_id,  # Herdar da conta origem
                canal=conta_origem.canal,  # Herdar da conta origem
                valor_original=conta_origem.valor_original,
                valor_final=conta_origem.valor_original,
                data_emissao=hoje,
                data_vencimento=nova_data_vencimento,
                status="pendente",
                documento=conta_origem.documento,
                observacoes=f"Gerada automaticamente da recorrÃªncia #{conta_origem.id}",
                conta_recorrencia_origem_id=conta_origem.id,
                user_id=conta_origem.user_id,
                tenant_id=tenant_id,
            )

            db.add(nova_conta)
            db.flush()
            contas_criadas.append(nova_conta)

            # Atualizar prÃ³xima recorrÃªncia da conta origem
            conta_origem.proxima_recorrencia = calcular_proxima_recorrencia(
                nova_data_vencimento,
                conta_origem.tipo_recorrencia,
                conta_origem.intervalo_dias,
            )

            # Criar lanÃ§amento no fluxo de caixa
            try:
                lancamento = LancamentoManual(
                    tipo="entrada",
                    valor=nova_conta.valor_original,
                    descricao=nova_conta.descricao,
                    data_lancamento=hoje,
                    data_competencia=nova_data_vencimento,
                    categoria_id=nova_conta.categoria_id,
                    status="previsto",
                    documento=f"CONTA-RECEBER-{nova_conta.id}",
                    observacoes=f"Gerado automaticamente da recorrÃªncia #{conta_origem.id}",
                    gerado_automaticamente=True,
                    user_id=current_user.id,
                    tenant_id=tenant_id,
                )
                db.add(lancamento)
            except Exception as e:
                logger.warning(
                    f"âš ï¸  Erro ao criar lanÃ§amento para conta recorrente: {e}"
                )

            logger.info(
                f"âœ… Nova conta recorrente criada: #{nova_conta.id} - Vencimento: {nova_data_vencimento}"
            )

        except Exception as e:
            logger.error(
                f"âŒ Erro ao processar recorrÃªncia da conta #{conta_origem.id}: {e}"
            )
            continue

    db.commit()

    return {
        "message": f"{len(contas_criadas)} conta(s) recorrente(s) processada(s) com sucesso",
        "contas_criadas": len(contas_criadas),
        "ids": [c.id for c in contas_criadas],
    }
