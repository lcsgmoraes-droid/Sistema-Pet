"""Rotas de baixa e recebimento de contas a receber."""

import logging
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from .auth.dependencies import get_current_user_and_tenant
from .contas_receber_schemas import RecebimentoCreate
from .db import get_session
from .financeiro_models import ContaReceber, Recebimento
from .idempotency import idempotent

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/{conta_id}/receber")
@idempotent()  # ðŸ”’ IDEMPOTÃŠNCIA: evita recebimento duplicado
async def registrar_recebimento(
    conta_id: int,
    recebimento: RecebimentoCreate,
    request: Request,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    Registra um recebimento (baixa) de conta a receber
    """
    conta = db.query(ContaReceber).filter(ContaReceber.id == conta_id).first()

    if not conta:
        raise HTTPException(status_code=404, detail="Conta nÃ£o encontrada")

    if conta.status == "recebido":
        raise HTTPException(status_code=400, detail="Conta jÃ¡ estÃ¡ recebida")

    # Atualizar valores
    conta.valor_recebido += Decimal(str(recebimento.valor_recebido))
    conta.valor_juros += Decimal(str(recebimento.valor_juros))
    conta.valor_multa += Decimal(str(recebimento.valor_multa))
    conta.valor_desconto += Decimal(str(recebimento.valor_desconto))

    # Recalcular valor final
    conta.valor_final = (
        conta.valor_original
        + conta.valor_juros
        + conta.valor_multa
        - conta.valor_desconto
    )

    # Verificar se recebeu tudo
    if conta.valor_recebido >= conta.valor_final:
        conta.status = "recebido"
        conta.data_recebimento = recebimento.data_recebimento
    else:
        conta.status = "parcial"

    # Registrar recebimento
    current_user, tenant_id = user_and_tenant
    novo_recebimento = Recebimento(
        conta_receber_id=conta.id,
        forma_pagamento_id=recebimento.forma_pagamento_id,
        valor_recebido=recebimento.valor_recebido,
        data_recebimento=recebimento.data_recebimento,
        observacoes=recebimento.observacoes,
        user_id=current_user.id,
        tenant_id=tenant_id,  # âœ… Garantir isolamento multi-tenant
    )
    db.add(novo_recebimento)

    db.commit()

    logger.info(
        f"âœ… Recebimento registrado: R$ {recebimento.valor_recebido} - Conta {conta_id}"
    )

    # ============================================================================
    # ðŸ’° GERAR COMISSÃƒO SE CONTA VINCULADA A VENDA
    # ============================================================================
    comissao_gerada = False
    comissao_info = None

    if conta.venda_id:
        try:
            from app.comissoes_service import gerar_comissoes_venda
            from app.vendas_models import Venda

            # Buscar venda para verificar se tem funcionÃ¡rio
            venda = db.query(Venda).filter(Venda.id == conta.venda_id).first()

            if venda and venda.funcionario_id:
                logger.info(
                    f"ðŸ’° Gerando comissÃ£o para venda #{venda.numero_venda} (baixa de conta a receber)"
                )

                # Gerar comissÃ£o proporcional ao valor recebido NESTA baixa
                resultado = gerar_comissoes_venda(
                    venda_id=venda.id,
                    funcionario_id=venda.funcionario_id,
                    valor_pago=Decimal(
                        str(recebimento.valor_recebido)
                    ),  # Apenas o valor DESTA baixa
                    parcela_numero=1,  # Usar parcela 1 para pagamentos via contas a receber
                    db=db,
                )

                if resultado.get("success"):
                    comissao_gerada = True
                    comissao_info = {
                        "venda_id": venda.id,
                        "numero_venda": venda.numero_venda,
                        "valor_comissao": resultado.get("total_comissao", 0),
                    }
                    logger.info(
                        f"âœ… ComissÃ£o gerada com sucesso: R$ {resultado.get('total_comissao', 0):.2f}"
                    )
                else:
                    logger.warning(
                        f"âš ï¸ Falha ao gerar comissÃ£o: {resultado.get('error', 'Erro desconhecido')}"
                    )
            else:
                logger.info(
                    f"â„¹ï¸ Venda #{conta.venda_id} sem funcionÃ¡rio configurado, comissÃ£o nÃ£o gerada"
                )

        except Exception as e:
            logger.error(
                f"âŒ Erro ao gerar comissÃ£o para venda #{conta.venda_id}: {e}"
            )
            # NÃ£o falha o recebimento por erro na comissÃ£o
            pass

    response = {
        "message": "Recebimento registrado com sucesso",
        "conta_id": conta.id,
        "status": conta.status,
        "valor_recebido_total": float(conta.valor_recebido),
        "valor_final": float(conta.valor_final),
        "saldo_restante": float(conta.valor_final - conta.valor_recebido),
    }

    if comissao_gerada and comissao_info:
        response["comissao"] = comissao_info

    return response


# ============================================================================
# DASHBOARD / RESUMO
# ============================================================================
