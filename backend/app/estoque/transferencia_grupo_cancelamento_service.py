"""Cancelamento atomico de transferencia entre empresas do mesmo grupo."""

from __future__ import annotations

from datetime import datetime, timezone
import logging
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.empresa_grupo_models import EmpresaGrupoTransferencia
from app.estoque.transferencia_parceiro_entrada_service import (
    MOTIVO_ENTRADA_PARCEIRO,
)
from app.estoque.transferencia_parceiro_support import (
    _MOTIVO_TRANSFERENCIA_PARCEIRO_ESTOQUE,
    _restaurar_lotes_consumidos_transferencia,
)
from app.financeiro_models import ContaPagar, ContaReceber, Pagamento, Recebimento
from app.produtos_models import EstoqueMovimentacao, Produto
from app.services.business_audit_service import log_business_event
from app.tenancy.context import tenant_context

MOTIVO_CANCELAMENTO_GRUPO = "transf_grupo_cancelamento"
REFERENCIA_CANCELAMENTO_GRUPO = "transferencia_grupo_cancelamento"
logger = logging.getLogger(__name__)


def _texto_limpo(valor) -> str | None:
    texto = str(valor or "").strip()
    return texto or None


def _adicionar_historico_cancelamento(texto_atual: str | None, mensagem: str) -> str:
    texto_atual = _texto_limpo(texto_atual)
    return f"{texto_atual}\n\n{mensagem}" if texto_atual else mensagem


def _validar_financeiro_cancelavel(
    db: Session,
    *,
    conta_receber: ContaReceber,
    conta_pagar: ContaPagar,
    empresa_origem_id: str,
    empresa_destino_id: str,
) -> None:
    empresa_origem_uuid = UUID(empresa_origem_id)
    empresa_destino_uuid = UUID(empresa_destino_id)
    with tenant_context(empresa_origem_id):
        possui_recebimento = (
            db.query(Recebimento.id)
            .filter(
                Recebimento.tenant_id == empresa_origem_uuid,
                Recebimento.conta_receber_id == conta_receber.id,
            )
            .first()
            is not None
        )
    status_receber = str(conta_receber.status or "").strip().lower()
    if (
        float(conta_receber.valor_recebido or 0) > 0
        or possui_recebimento
        or status_receber in {"recebido", "pago", "parcial", "baixa_parcial"}
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "A transferência integrada possui recebimento na empresa de origem. "
                "Desfaça a baixa financeira antes de cancelar."
            ),
        )

    with tenant_context(empresa_destino_id):
        possui_pagamento = (
            db.query(Pagamento.id)
            .filter(
                Pagamento.tenant_id == empresa_destino_uuid,
                Pagamento.conta_pagar_id == conta_pagar.id,
            )
            .first()
            is not None
        )
    status_pagar = str(conta_pagar.status or "").strip().lower()
    if (
        float(conta_pagar.valor_pago or 0) > 0
        or possui_pagamento
        or status_pagar in {"pago", "recebido", "parcial"}
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "A transferência integrada possui pagamento na empresa de destino. "
                "Desfaça a baixa financeira antes de cancelar."
            ),
        )


def _criar_movimentacao_cancelamento(
    db: Session,
    *,
    produto: Produto,
    movimento_original: EstoqueMovimentacao,
    transferencia: EmpresaGrupoTransferencia,
    tenant_id: str,
    user_id: int,
    tipo: str,
) -> dict:
    quantidade = float(movimento_original.quantidade or 0)
    estoque_anterior = float(produto.estoque_atual or 0)
    if tipo == "saida" and estoque_anterior + 1e-9 < quantidade:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Não é possível cancelar porque o produto '{produto.nome}' não possui "
                "mais a quantidade recebida no estoque de destino. Reponha o estoque "
                "antes de cancelar."
            ),
        )
    estoque_novo = (
        estoque_anterior + quantidade
        if tipo == "entrada"
        else estoque_anterior - quantidade
    )
    produto.estoque_atual = estoque_novo
    movimento = EstoqueMovimentacao(
        produto_id=produto.id,
        tipo=tipo,
        motivo=MOTIVO_CANCELAMENTO_GRUPO,
        quantidade=quantidade,
        quantidade_anterior=estoque_anterior,
        quantidade_nova=estoque_novo,
        custo_unitario=float(movimento_original.custo_unitario or 0),
        valor_total=float(movimento_original.valor_total or 0),
        documento=transferencia.documento,
        referencia_id=transferencia.id,
        referencia_tipo=REFERENCIA_CANCELAMENTO_GRUPO,
        observacao=(
            f"Cancelamento da transferência integrada #{transferencia.id}. "
            "Estoque revertido nas duas empresas."
        ),
        user_id=user_id,
        tenant_id=tenant_id,
    )
    db.add(produto)
    db.add(movimento)
    db.flush()
    return {
        "movimentacao_id": movimento.id,
        "produto_id": produto.id,
        "estoque_novo": float(estoque_novo),
    }


def cancelar_transferencia_integrada_por_conta(
    db: Session,
    *,
    empresa_origem_id,
    usuario_origem_id: int,
    conta_receber_origem_id: int,
    sincronizar_estoque,
) -> dict | None:
    """Cancela os dois lados de uma transferência integrada, em uma transação."""
    empresa_origem_id = str(empresa_origem_id)
    empresa_origem_uuid = UUID(empresa_origem_id)
    transferencia = (
        db.query(EmpresaGrupoTransferencia)
        .filter(
            EmpresaGrupoTransferencia.empresa_origem_id == empresa_origem_id,
            EmpresaGrupoTransferencia.conta_receber_origem_id
            == int(conta_receber_origem_id),
        )
        .with_for_update()
        .first()
    )
    if transferencia is None:
        return None
    if transferencia.status == "cancelada":
        cancelamento = dict((transferencia.resultado or {}).get("cancelamento") or {})
        return {
            "sucesso": True,
            "transferencia_integrada": True,
            "transferencia_grupo_id": transferencia.id,
            "conta_receber_id": conta_receber_origem_id,
            "conta_pagar_destino_id": transferencia.conta_pagar_destino_id,
            "status": "cancelada",
            **cancelamento,
            "idempotente": True,
        }
    if transferencia.status != "concluida":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A transferência integrada não está concluída e não pode ser cancelada.",
        )
    if not transferencia.conta_pagar_destino_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A transferência integrada não possui a conta de destino vinculada.",
        )

    empresa_destino_id = str(transferencia.empresa_destino_id)
    empresa_destino_uuid = UUID(empresa_destino_id)
    with tenant_context(empresa_origem_id):
        conta_receber = (
            db.query(ContaReceber)
            .filter(
                ContaReceber.id == int(conta_receber_origem_id),
                ContaReceber.tenant_id == empresa_origem_uuid,
                ContaReceber.canal == "transferencia_parceiro",
            )
            .with_for_update()
            .first()
        )
        movimentos_origem = (
            db.query(EstoqueMovimentacao)
            .filter(
                EstoqueMovimentacao.tenant_id == empresa_origem_uuid,
                EstoqueMovimentacao.referencia_id == int(conta_receber_origem_id),
                EstoqueMovimentacao.tipo == "saida",
                EstoqueMovimentacao.motivo.in_(
                    [_MOTIVO_TRANSFERENCIA_PARCEIRO_ESTOQUE, "transferencia_parceiro"]
                ),
            )
            .order_by(EstoqueMovimentacao.id.asc())
            .all()
        )
    with tenant_context(empresa_destino_id):
        conta_pagar = (
            db.query(ContaPagar)
            .filter(
                ContaPagar.id == int(transferencia.conta_pagar_destino_id),
                ContaPagar.tenant_id == empresa_destino_uuid,
                ContaPagar.canal == "transferencia_parceiro_entrada",
            )
            .with_for_update()
            .first()
        )
        movimentos_destino = (
            db.query(EstoqueMovimentacao)
            .filter(
                EstoqueMovimentacao.tenant_id == empresa_destino_uuid,
                EstoqueMovimentacao.referencia_id
                == int(transferencia.conta_pagar_destino_id),
                EstoqueMovimentacao.tipo == "entrada",
                EstoqueMovimentacao.motivo == MOTIVO_ENTRADA_PARCEIRO,
            )
            .order_by(EstoqueMovimentacao.id.asc())
            .all()
        )

    if conta_receber is None or conta_pagar is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Os lançamentos financeiros da transferência integrada não foram encontrados.",
        )
    if not movimentos_origem or not movimentos_destino:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="As movimentações de estoque da transferência integrada não foram encontradas.",
        )
    _validar_financeiro_cancelavel(
        db,
        conta_receber=conta_receber,
        conta_pagar=conta_pagar,
        empresa_origem_id=empresa_origem_id,
        empresa_destino_id=empresa_destino_id,
    )

    quantidades_destino: dict[int, float] = {}
    for movimento in movimentos_destino:
        quantidades_destino[movimento.produto_id] = quantidades_destino.get(
            movimento.produto_id, 0.0
        ) + float(movimento.quantidade or 0)
    with tenant_context(empresa_destino_id):
        produtos_destino = (
            db.query(Produto)
            .filter(
                Produto.tenant_id == empresa_destino_uuid,
                Produto.id.in_(list(quantidades_destino)),
            )
            .with_for_update()
            .all()
        )
    produtos_destino_por_id = {produto.id: produto for produto in produtos_destino}
    for produto_id, quantidade in quantidades_destino.items():
        produto = produtos_destino_por_id.get(produto_id)
        if produto is None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Produto ID {produto_id} não foi encontrado na empresa de destino.",
            )
        if float(produto.estoque_atual or 0) + 1e-9 < quantidade:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"Não é possível cancelar porque o produto '{produto.nome}' não possui "
                    "mais a quantidade recebida no estoque de destino. Reponha o estoque "
                    "antes de cancelar."
                ),
            )

    movimentos_cancelamento_origem: list[dict] = []
    with tenant_context(empresa_origem_id):
        produtos_origem = (
            db.query(Produto)
            .filter(
                Produto.tenant_id == empresa_origem_uuid,
                Produto.id.in_([mov.produto_id for mov in movimentos_origem]),
            )
            .with_for_update()
            .all()
        )
        produtos_origem_por_id = {produto.id: produto for produto in produtos_origem}
        for movimento in movimentos_origem:
            produto = produtos_origem_por_id.get(movimento.produto_id)
            if produto is None:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Produto ID {movimento.produto_id} não foi encontrado na origem.",
                )
            _restaurar_lotes_consumidos_transferencia(db, movimento)
            movimentos_cancelamento_origem.append(
                _criar_movimentacao_cancelamento(
                    db,
                    produto=produto,
                    movimento_original=movimento,
                    transferencia=transferencia,
                    tenant_id=empresa_origem_uuid,
                    user_id=usuario_origem_id,
                    tipo="entrada",
                )
            )

    usuario_destino_id = int(transferencia.usuario_destino_id or usuario_origem_id)
    movimentos_cancelamento_destino: list[dict] = []
    with tenant_context(empresa_destino_id):
        for movimento in movimentos_destino:
            movimentos_cancelamento_destino.append(
                _criar_movimentacao_cancelamento(
                    db,
                    produto=produtos_destino_por_id[movimento.produto_id],
                    movimento_original=movimento,
                    transferencia=transferencia,
                    tenant_id=empresa_destino_uuid,
                    user_id=usuario_destino_id,
                    tipo="saida",
                )
            )

    cancelado_em = datetime.now(timezone.utc)
    mensagem_historico = (
        f"Transferência integrada #{transferencia.id} cancelada em "
        f"{cancelado_em:%d/%m/%Y %H:%M}. Estoque e financeiro revertidos nas duas empresas."
    )
    conta_receber.status = "cancelado"
    conta_receber.observacoes = _adicionar_historico_cancelamento(
        conta_receber.observacoes, mensagem_historico
    )
    conta_pagar.status = "cancelado"
    conta_pagar.observacoes = _adicionar_historico_cancelamento(
        conta_pagar.observacoes, mensagem_historico
    )
    transferencia.status = "cancelada"
    cancelamento = {
        "cancelado_em": cancelado_em.isoformat(),
        "cancelado_por_usuario_id": usuario_origem_id,
        "movimentacoes_origem": movimentos_cancelamento_origem,
        "movimentacoes_destino": movimentos_cancelamento_destino,
    }
    transferencia.resultado = {
        **dict(transferencia.resultado or {}),
        "status": "cancelada",
        "cancelamento": cancelamento,
    }
    with tenant_context(empresa_origem_id):
        log_business_event(
            db=db,
            tenant_id=empresa_origem_id,
            user_id=usuario_origem_id,
            event="transferencia_grupo_cancelada_origem",
            entity_type="empresa_grupo_transferencia",
            entity_id=transferencia.id,
            metadata={"empresa_destino_id": empresa_destino_id},
            commit=False,
        )
    with tenant_context(empresa_destino_id):
        log_business_event(
            db=db,
            tenant_id=empresa_destino_id,
            user_id=usuario_destino_id,
            event="transferencia_grupo_cancelada_destino",
            entity_type="empresa_grupo_transferencia",
            entity_id=transferencia.id,
            metadata={"empresa_origem_id": empresa_origem_id},
            commit=False,
        )
    db.commit()

    for movimento in movimentos_cancelamento_origem:
        try:
            sincronizar_estoque(
                movimento["produto_id"],
                movimento["estoque_novo"],
                "transferencia_grupo_cancelamento_origem",
            )
        except Exception:
            logger.warning(
                "Nao foi possivel agendar o Bling do cancelamento na origem",
                exc_info=True,
            )
    for movimento in movimentos_cancelamento_destino:
        try:
            sincronizar_estoque(
                movimento["produto_id"],
                movimento["estoque_novo"],
                "transferencia_grupo_cancelamento_destino",
            )
        except Exception:
            logger.warning(
                "Nao foi possivel agendar o Bling do cancelamento no destino",
                exc_info=True,
            )

    return {
        "sucesso": True,
        "transferencia_integrada": True,
        "transferencia_grupo_id": transferencia.id,
        "conta_receber_id": conta_receber.id,
        "conta_pagar_destino_id": conta_pagar.id,
        "status": "cancelada",
        **cancelamento,
        "idempotente": False,
    }
