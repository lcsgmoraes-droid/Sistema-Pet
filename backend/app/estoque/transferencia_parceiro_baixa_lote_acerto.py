from __future__ import annotations

from datetime import date
from decimal import Decimal, ROUND_HALF_UP

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.estoque.transferencia_parceiro_support import _texto_limpo
from app.financeiro_models import ContaPagar

CENTAVO = Decimal("0.01")


def _payload_get(payload, campo: str, default=None):
    if isinstance(payload, dict):
        return payload.get(campo, default)
    return getattr(payload, campo, default)


def valor_conta_pagar_acerto_payload(payload) -> Decimal:
    return Decimal(str(_payload_get(payload, "valor", 0) or 0)).quantize(
        CENTAVO,
        rounding=ROUND_HALF_UP,
    )


def criar_conta_pagar_acerto_lote(
    db: Session,
    *,
    tenant_id,
    parceiro_id: int,
    user_id: int,
    data_emissao: date,
    payload,
    documento_lote: str,
) -> ContaPagar:
    valor = valor_conta_pagar_acerto_payload(payload)
    if valor <= 0:
        raise HTTPException(
            status_code=400,
            detail="Informe um valor maior que zero para a nova conta a pagar do acerto.",
        )

    descricao = (
        _texto_limpo(_payload_get(payload, "descricao"))
        or f"Acerto transferencia parceiro {documento_lote}"
    )
    documento = _texto_limpo(_payload_get(payload, "documento")) or documento_lote
    observacao_usuario = _texto_limpo(_payload_get(payload, "observacao"))
    observacoes = (
        f"Conta criada pela baixa por valor de transferencia parceiro {documento_lote}."
    )
    if observacao_usuario:
        observacoes = f"{observacoes}\n\n{observacao_usuario}"

    conta = ContaPagar(
        tenant_id=str(tenant_id),
        descricao=descricao,
        fornecedor_id=parceiro_id,
        categoria_id=_payload_get(payload, "categoria_id"),
        tipo_despesa_id=_payload_get(payload, "tipo_despesa_id"),
        dre_subcategoria_id=_payload_get(payload, "dre_subcategoria_id"),
        canal="transferencia_parceiro",
        valor_original=valor,
        valor_pago=Decimal("0.00"),
        valor_final=valor,
        data_emissao=data_emissao,
        data_vencimento=_payload_get(payload, "data_vencimento") or data_emissao,
        status="pendente",
        documento=documento,
        observacoes=observacoes,
        user_id=user_id,
    )
    db.add(conta)
    db.flush()
    return conta
