"""Rotas de baixa e recebimento de contas a receber."""

import logging
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from .auth.dependencies import get_current_user_and_tenant
from .contas_receber_schemas import RecebimentoCreate
from .db import get_session
from .financeiro_models import ContaReceber, FormaPagamento, Recebimento
from .idempotency import idempotent
from .utils.tenant_safe_sql import execute_tenant_safe

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/{conta_id}/receber")
@idempotent()  # 🔒 IDEMPOTÊNCIA: evita recebimento duplicado
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
    current_user, tenant_id = user_and_tenant
    conta = (
        db.query(ContaReceber)
        .filter(
            ContaReceber.id == conta_id,
            ContaReceber.tenant_id == tenant_id,
        )
        .first()
    )

    if not conta:
        raise HTTPException(status_code=404, detail="Conta não encontrada")

    if conta.status == "recebido":
        raise HTTPException(status_code=400, detail="Conta já está recebida")

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
    novo_recebimento = Recebimento(
        conta_receber_id=conta.id,
        forma_pagamento_id=recebimento.forma_pagamento_id,
        valor_recebido=recebimento.valor_recebido,
        data_recebimento=recebimento.data_recebimento,
        observacoes=recebimento.observacoes,
        user_id=current_user.id,
        tenant_id=tenant_id,  # ✅ Garantir isolamento multi-tenant
    )
    db.add(novo_recebimento)

    db.commit()

    logger.info(
        f"✅ Recebimento registrado: R$ {recebimento.valor_recebido} - Conta {conta_id}"
    )

    # ============================================================================
    # 💰 GERAR COMISSÃO SE CONTA VINCULADA A VENDA
    # ============================================================================
    comissao_gerada = False
    comissao_info = None

    if conta.venda_id:
        try:
            from app.comissoes_service import gerar_comissoes_venda
            from app.vendas_models import Venda

            # Buscar venda para verificar se tem funcionário
            venda = (
                db.query(Venda)
                .filter(Venda.id == conta.venda_id, Venda.tenant_id == tenant_id)
                .first()
            )

            if venda and venda.funcionario_id:
                logger.info(
                    f"💰 Gerando comissão para venda #{venda.numero_venda} (baixa de conta a receber)"
                )

                # Gerar comissão proporcional ao valor recebido NESTA baixa
                proxima_parcela = int(
                    execute_tenant_safe(
                        db,
                        """
                        SELECT COALESCE(MAX(parcela_numero), 0) + 1
                        FROM comissoes_itens
                        WHERE venda_id = :venda_id
                          AND funcionario_id = :funcionario_id
                          AND {tenant_filter}
                        """,
                        {
                            "venda_id": venda.id,
                            "funcionario_id": venda.funcionario_id,
                        },
                        tenant_id=tenant_id,
                    ).scalar()
                    or 1
                )
                forma = (
                    db.query(FormaPagamento)
                    .filter(
                        FormaPagamento.id == recebimento.forma_pagamento_id,
                        FormaPagamento.tenant_id == tenant_id,
                    )
                    .first()
                    if recebimento.forma_pagamento_id
                    else None
                )

                resultado = gerar_comissoes_venda(
                    venda_id=venda.id,
                    funcionario_id=venda.funcionario_id,
                    valor_pago=Decimal(
                        str(recebimento.valor_recebido)
                    ),  # Apenas o valor DESTA baixa
                    forma_pagamento=forma.nome if forma else None,
                    parcela_numero=proxima_parcela,
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
                        f"✅ Comissão gerada com sucesso: R$ {resultado.get('total_comissao', 0):.2f}"
                    )
                else:
                    logger.warning(
                        f"⚠️ Falha ao gerar comissão: {resultado.get('error', 'Erro desconhecido')}"
                    )
            else:
                logger.info(
                    f"ℹ️ Venda #{conta.venda_id} sem funcionário configurado, comissão não gerada"
                )

        except Exception as e:
            logger.error(
                f"❌ Erro ao gerar comissão para venda #{conta.venda_id}: {e}"
            )
            # Não falha o recebimento por erro na comissão
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
