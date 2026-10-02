"""Validação e conferência de lançamentos feitos após o fechamento do caixa."""

from datetime import datetime

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.caixa.conferencia import moeda, totais_dinheiro
from app.caixa.escopo import buscar_caixa_acessivel
from app.caixa_models import Caixa, MovimentacaoCaixa
from app.utils.timezone import now_brasilia


def validar_revisao_caixa(
    db: Session,
    *,
    caixa_id: int | None,
    data_ocorrencia: datetime | None,
    motivo: str | None,
    usuario,
    tenant_id,
) -> Caixa | None:
    campos = (caixa_id, data_ocorrencia, motivo)
    if all(campo is None for campo in campos):
        return None
    if any(campo is None for campo in campos):
        raise HTTPException(400, "Informe caixa, data e motivo da revisão.")
    if not getattr(usuario, "is_admin", False):
        raise HTTPException(
            403, "Apenas administradores podem revisar caixas fechados."
        )
    if len(motivo.strip()) < 10:
        raise HTTPException(
            400, "Descreva o motivo da revisão com pelo menos 10 caracteres."
        )
    if data_ocorrencia.tzinfo is not None:
        raise HTTPException(400, "Informe a data e hora local sem fuso horário.")
    caixa, _ = buscar_caixa_acessivel(
        db, caixa_id=caixa_id, tenant_id=tenant_id, usuario_id=usuario.id
    )
    if not caixa:
        raise HTTPException(404, "Caixa não encontrado.")
    if (
        caixa.status != "fechado"
        or caixa.data_fechamento is None
        or caixa.valor_informado is None
    ):
        raise HTTPException(400, "A revisão exige um caixa fechado e conferido.")
    if not (caixa.data_abertura <= data_ocorrencia <= caixa.data_fechamento):
        raise HTTPException(
            400, "A data e hora devem estar entre a abertura e o fechamento do caixa."
        )
    if data_ocorrencia > now_brasilia():
        raise HTTPException(400, "A data informada não pode estar no futuro.")
    return caixa


def recalcular_fechamento_revisado(db: Session, *, caixa: Caixa, tenant_id) -> None:
    movimentacoes = (
        db.query(MovimentacaoCaixa)
        .filter(
            MovimentacaoCaixa.caixa_id == caixa.id,
            MovimentacaoCaixa.tenant_id == tenant_id,
        )
        .all()
    )
    caixa.valor_esperado = totais_dinheiro(caixa.valor_abertura, movimentacoes)[
        "saldo_atual"
    ]
    caixa.diferenca = float(moeda(caixa.valor_informado) - moeda(caixa.valor_esperado))
