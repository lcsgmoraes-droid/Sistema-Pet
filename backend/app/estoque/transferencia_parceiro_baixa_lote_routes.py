from __future__ import annotations

from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user_and_tenant
from app.db import get_session
from app.estoque.transferencia_parceiro_baixa_lote_schemas import (
    TransferenciaParceiroBaixaLotePreviewItem,
    TransferenciaParceiroBaixaLotePreviewRequest,
    TransferenciaParceiroBaixaLotePreviewResponse,
    TransferenciaParceiroBaixaLoteRequest,
    TransferenciaParceiroBaixaLoteResponse,
)
from app.estoque.transferencia_parceiro_baixa_lote_service import (
    aplicar_baixa_lote_transferencia,
    atualizar_dre_baixa_lote,
    buscar_transferencias_abertas_para_baixa,
    decimal_monetario,
    distribuir_baixa_transferencias,
    saldo_conta_receber_decimal,
)
from app.security.permissions_decorator import require_permission


router = APIRouter()


@router.post(
    "/transferencia-parceiro/baixa-lote/preview",
    response_model=TransferenciaParceiroBaixaLotePreviewResponse,
)
@require_permission("produtos.visualizar")
def preview_baixa_lote_transferencia_parceiro(
    payload: TransferenciaParceiroBaixaLotePreviewRequest,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    _current_user, tenant_id = user_and_tenant
    contas = buscar_transferencias_abertas_para_baixa(
        db,
        tenant_id=tenant_id,
        parceiro_id=payload.parceiro_id,
        data_inicio=payload.data_inicio,
        data_fim=payload.data_fim,
        ordem=payload.ordem,
    )
    distribuicao = distribuir_baixa_transferencias(
        contas,
        payload.valor_total,
        ordem=payload.ordem,
    )
    valores_por_conta = {
        item["conta_receber_id"]: item["valor_baixado"] for item in distribuicao
    }
    total_aberto = sum(
        (saldo_conta_receber_decimal(conta) for conta in contas),
        Decimal("0.00"),
    )
    total_sugerido = sum(
        (item["valor_baixado"] for item in distribuicao),
        Decimal("0.00"),
    )
    valor_restante = max(
        decimal_monetario(payload.valor_total) - total_sugerido,
        Decimal("0.00"),
    )

    return TransferenciaParceiroBaixaLotePreviewResponse(
        items=[
            TransferenciaParceiroBaixaLotePreviewItem(
                conta_receber_id=conta.id,
                documento=conta.documento,
                data_emissao=conta.data_emissao,
                data_vencimento=conta.data_vencimento,
                valor_original=float(conta.valor_original or 0),
                valor_recebido=float(conta.valor_recebido or 0),
                saldo_aberto=float(saldo_conta_receber_decimal(conta)),
                valor_sugerido=float(valores_por_conta.get(conta.id, Decimal("0.00"))),
            )
            for conta in contas
        ],
        total_aberto=float(total_aberto),
        total_sugerido=float(total_sugerido),
        valor_restante=float(valor_restante),
    )


@router.post(
    "/transferencia-parceiro/baixa-lote",
    response_model=TransferenciaParceiroBaixaLoteResponse,
)
@require_permission("produtos.editar")
def registrar_baixa_lote_transferencia_parceiro(
    payload: TransferenciaParceiroBaixaLoteRequest,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    current_user, tenant_id = user_and_tenant
    try:
        resultado = aplicar_baixa_lote_transferencia(
            db,
            tenant_id=tenant_id,
            user_id=current_user.id,
            payload=payload,
        )
        dre_lancamentos = resultado.pop("_dre_lancamentos", [])
        db.commit()
        atualizar_dre_baixa_lote(
            db,
            tenant_id=tenant_id,
            lancamentos=dre_lancamentos,
        )
        return resultado
    except HTTPException:
        db.rollback()
        raise
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Nao foi possivel registrar a baixa por valor.",
        )
