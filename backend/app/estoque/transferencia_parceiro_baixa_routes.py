"""Rotas de baixa e exclusao da transferencia para parceiro."""

import logging
from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user_and_tenant
from app.bling_estoque_sync import sincronizar_bling_background
from app.db import get_session
from app.estoque.service import EstoqueService
from app.estoque.transferencia_parceiro_documents import (
    _saldo_conta_receber,
    _status_transferencia_parceiro,
)
from app.estoque.transferencia_parceiro_schemas import (
    TransferenciaParceiroContaPagarCompensacaoItem,
    TransferenciaParceiroContaPagarCompensacaoResponse,
    TransferenciaParceiroRecebimentoRequest,
)
from app.estoque.transferencia_parceiro_support import (
    _MOTIVO_TRANSFERENCIA_PARCEIRO_ESTOQUE,
    _MOTIVO_TRANSFERENCIA_PARCEIRO_EXCLUSAO,
    _REFERENCIA_TRANSFERENCIA_PARCEIRO_EXCLUSAO,
    _aplicar_compensacoes_contas_pagar_transferencia,
    _buscar_conta_transferencia_parceiro,
    _buscar_contas_pagar_compensacao_transferencia,
    _buscar_forma_pagamento_transferencia,
    _formatar_resumo_compensacoes_transferencia,
    _label_modo_baixa_transferencia,
    _normalizar_modo_baixa_transferencia,
    _obter_ou_criar_forma_pagamento_acerto,
    _origem_conta_pagar_compensacao,
    _restaurar_lotes_consumidos_transferencia,
    _saldo_conta_pagar,
    _status_conta_pagar_compensacao,
    _texto_limpo,
)
from app.financeiro_models import Recebimento
from app.produtos_models import EstoqueMovimentacao
from app.security.permissions_decorator import require_permission


logger = logging.getLogger(__name__)
router = APIRouter()

_MOTIVO_DEVOLUCAO_TRANSFERENCIA_PARCEIRO = "transf_dev"
_REFERENCIA_DEVOLUCAO_TRANSFERENCIA_PARCEIRO = "transf_devolucao"


def _estornar_estoque_transferencia_devolvida(
    db: Session,
    *,
    conta,
    user_id: int,
    tenant_id,
    observacao: str,
) -> list[int]:
    movimentacoes = (
        db.query(EstoqueMovimentacao)
        .filter(
            EstoqueMovimentacao.tenant_id == str(tenant_id),
            EstoqueMovimentacao.referencia_id == conta.id,
            EstoqueMovimentacao.tipo == "saida",
            EstoqueMovimentacao.motivo.in_(
                [_MOTIVO_TRANSFERENCIA_PARCEIRO_ESTOQUE, "transferencia_parceiro"]
            ),
        )
        .order_by(EstoqueMovimentacao.id.asc())
        .all()
    )

    movimentos_criados: list[int] = []
    for movimentacao in movimentacoes:
        resultado = EstoqueService.estornar_estoque(
            produto_id=movimentacao.produto_id,
            quantidade=float(movimentacao.quantidade or 0),
            motivo=_MOTIVO_DEVOLUCAO_TRANSFERENCIA_PARCEIRO,
            referencia_id=conta.id,
            referencia_tipo=_REFERENCIA_DEVOLUCAO_TRANSFERENCIA_PARCEIRO,
            user_id=user_id,
            db=db,
            tenant_id=str(tenant_id),
            documento=conta.documento,
            observacao=observacao,
            custo_unitario_override=float(movimentacao.custo_unitario or 0),
            valor_total_override=float(movimentacao.valor_total or 0),
        )
        movimentos_criados.append(resultado["movimentacao_id"])

    return movimentos_criados


@router.get(
    "/transferencia-parceiro/{conta_receber_id}/contas-pagar-compensacao",
    response_model=TransferenciaParceiroContaPagarCompensacaoResponse,
)
@require_permission("produtos.visualizar")
def listar_contas_pagar_compensacao_transferencia(
    conta_receber_id: int,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Lista contas a pagar em aberto da mesma pessoa para realizar compensacao."""
    _current_user, tenant_id = user_and_tenant
    conta = _buscar_conta_transferencia_parceiro(db, tenant_id, conta_receber_id)
    contas = _buscar_contas_pagar_compensacao_transferencia(
        db,
        tenant_id=tenant_id,
        cliente_id=getattr(conta, "cliente_id", None),
    )

    items = []
    total_disponivel = 0.0
    for conta_pagar in contas:
        saldo_aberto = _saldo_conta_pagar(conta_pagar)
        status_conta, status_label = _status_conta_pagar_compensacao(conta_pagar)
        origem_acerto, origem_label = _origem_conta_pagar_compensacao(conta_pagar)
        total_disponivel += saldo_aberto
        items.append(
            TransferenciaParceiroContaPagarCompensacaoItem(
                conta_pagar_id=conta_pagar.id,
                descricao=conta_pagar.descricao,
                documento=conta_pagar.documento,
                canal=conta_pagar.canal,
                origem_acerto=origem_acerto,
                origem_label=origem_label,
                data_emissao=conta_pagar.data_emissao,
                data_vencimento=conta_pagar.data_vencimento,
                status=status_conta,
                status_label=status_label,
                valor_original=float(conta_pagar.valor_original or 0),
                valor_pago=float(conta_pagar.valor_pago or 0),
                saldo_aberto=saldo_aberto,
                observacoes=conta_pagar.observacoes,
            )
        )

    return TransferenciaParceiroContaPagarCompensacaoResponse(
        items=items,
        total=len(items),
        total_disponivel=round(total_disponivel, 2),
    )


@router.post("/transferencia-parceiro/{conta_receber_id}/receber")
@require_permission("produtos.editar")
def registrar_recebimento_transferencia_parceiro(
    conta_receber_id: int,
    payload: TransferenciaParceiroRecebimentoRequest,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Registra baixa financeira de uma transferencia com ressarcimento."""
    current_user, tenant_id = user_and_tenant
    conta = _buscar_conta_transferencia_parceiro(db, tenant_id, conta_receber_id)
    modo_baixa = _normalizar_modo_baixa_transferencia(payload.modo_baixa)
    devolver_estoque = bool(getattr(payload, "devolver_estoque", False))
    compensacoes_payload = [
        item
        for item in (payload.compensacoes or [])
        if round(float(item.valor_compensado or 0), 2) > 0
    ]

    status_atual = str(getattr(conta, "status", "") or "").strip().lower()
    if status_atual in {"cancelado", "cancelada"}:
        raise HTTPException(
            status_code=400,
            detail="Transferencia cancelada nao pode receber baixa",
        )

    saldo_aberto = _saldo_conta_receber(conta)
    valor_recebido = round(float(payload.valor_recebido or 0), 2)

    if valor_recebido <= 0:
        raise HTTPException(
            status_code=400,
            detail="Informe um valor recebido maior que zero",
        )

    if valor_recebido - saldo_aberto > 0.01:
        raise HTTPException(
            status_code=400,
            detail=(
                f"O valor recebido ultrapassa o saldo da transferencia. "
                f"Saldo atual: R$ {saldo_aberto:.2f}"
            ),
        )

    observacao_recebimento = _texto_limpo(payload.observacao)
    if modo_baixa == "produto_devolvido" and devolver_estoque:
        if saldo_aberto - valor_recebido > 0.01:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Produto devolvido com volta ao estoque exige baixa integral "
                    "da transferencia."
                ),
            )
    if (
        modo_baixa == "produto_devolvido"
        and not devolver_estoque
        and not observacao_recebimento
    ):
        raise HTTPException(
            status_code=400,
            detail=(
                "Informe uma observacao quando produto devolvido nao volta "
                "para o estoque."
            ),
        )

    total_compensado = round(
        sum(float(item.valor_compensado or 0) for item in compensacoes_payload),
        2,
    )
    if modo_baixa == "acerto" and not compensacoes_payload:
        raise HTTPException(
            status_code=400,
            detail=(
                "No acerto, selecione uma conta a pagar ou lance uma divida "
                "para compensar."
            ),
        )
    if modo_baixa == "acerto" and abs(total_compensado - valor_recebido) > 0.01:
        raise HTTPException(
            status_code=400,
            detail=(
                "O total compensado nas contas a pagar deve ser igual ao valor da baixa "
                "quando houver titulos selecionados para compensacao."
            ),
        )

    valor_recebido_total = round(float(conta.valor_recebido or 0) + valor_recebido, 2)
    conta.valor_recebido = Decimal(str(valor_recebido_total))
    conta.data_recebimento = payload.data_recebimento or date.today()
    conta.status = (
        "recebido"
        if abs(float(conta.valor_final or 0) - valor_recebido_total) < 0.01
        else "parcial"
    )

    forma_pagamento = None
    if modo_baixa == "acerto":
        forma_pagamento = _obter_ou_criar_forma_pagamento_acerto(
            db,
            tenant_id=tenant_id,
            user_id=current_user.id,
        )
    elif modo_baixa == "recebimento" and payload.forma_pagamento_id:
        forma_pagamento = _buscar_forma_pagamento_transferencia(
            db,
            tenant_id=tenant_id,
            forma_pagamento_id=payload.forma_pagamento_id,
        )

    if forma_pagamento:
        conta.forma_pagamento_id = forma_pagamento.id

    modo_label = _label_modo_baixa_transferencia(modo_baixa) or "Recebimento"
    compensacoes_processadas: list[dict] = []
    movimentacoes_estoque: list[int] = []
    if modo_baixa == "acerto" and compensacoes_payload:
        compensacoes_processadas = _aplicar_compensacoes_contas_pagar_transferencia(
            db,
            conta_receber=conta,
            tenant_id=tenant_id,
            user_id=current_user.id,
            data_pagamento=conta.data_recebimento,
            forma_pagamento=forma_pagamento,
            compensacoes_payload=compensacoes_payload,
        )

    detalhe_forma = (
        f" | Forma: {forma_pagamento.nome}"
        if forma_pagamento and _texto_limpo(forma_pagamento.nome)
        else ""
    )
    detalhe_compensacao = ""
    resumo_compensacao = _formatar_resumo_compensacoes_transferencia(
        compensacoes_processadas
    )
    if resumo_compensacao:
        detalhe_compensacao = f" | {resumo_compensacao}"
    detalhe_observacao = (
        f" - {observacao_recebimento}" if observacao_recebimento else ""
    )
    historico = (
        f"{modo_label} {conta.data_recebimento.strftime('%d/%m/%Y')}: "
        f"R$ {valor_recebido:.2f}{detalhe_forma}{detalhe_compensacao}{detalhe_observacao}"
    )
    conta.observacoes = (
        f"{conta.observacoes}\n\n{historico}".strip()
        if conta.observacoes
        else historico
    )

    if modo_baixa in {"recebimento", "acerto"}:
        recebimento = Recebimento(
            conta_receber_id=conta.id,
            forma_pagamento_id=forma_pagamento.id if forma_pagamento else None,
            valor_recebido=Decimal(str(valor_recebido)),
            data_recebimento=conta.data_recebimento,
            observacoes=historico,
            user_id=current_user.id,
            tenant_id=str(tenant_id),
        )
        db.add(recebimento)

    if modo_baixa == "produto_devolvido" and devolver_estoque:
        movimentacoes_estoque = _estornar_estoque_transferencia_devolvida(
            db,
            conta=conta,
            user_id=current_user.id,
            tenant_id=tenant_id,
            observacao=historico,
        )

    db.commit()
    db.refresh(conta)

    status_resolvido, status_label = _status_transferencia_parceiro(conta)

    return {
        "sucesso": True,
        "conta_receber_id": conta.id,
        "status": status_resolvido,
        "status_label": status_label,
        "valor_recebido": float(conta.valor_recebido or 0),
        "saldo_aberto": _saldo_conta_receber(conta),
        "data_recebimento": conta.data_recebimento.isoformat()
        if conta.data_recebimento
        else None,
        "modo_baixa": modo_baixa,
        "modo_baixa_label": modo_label,
        "forma_pagamento_id": forma_pagamento.id if forma_pagamento else None,
        "forma_pagamento_nome": _texto_limpo(getattr(forma_pagamento, "nome", None)),
        "compensacoes": compensacoes_processadas,
        "devolver_estoque": devolver_estoque,
        "movimentacoes_estoque": movimentacoes_estoque,
    }


@router.delete("/transferencia-parceiro/{conta_receber_id}")
@require_permission("produtos.editar")
def excluir_transferencia_parceiro(
    conta_receber_id: int,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Exclui uma transferencia ainda sem baixa, estornando o estoque."""
    current_user, tenant_id = user_and_tenant
    conta = _buscar_conta_transferencia_parceiro(db, tenant_id, conta_receber_id)

    if float(conta.valor_recebido or 0) > 0:
        raise HTTPException(
            status_code=400,
            detail=(
                "Esta transferencia ja possui recebimento registrado. "
                "Remova ou trate a baixa financeira antes de excluir o lancamento."
            ),
        )

    movimentacoes = (
        db.query(EstoqueMovimentacao)
        .filter(
            EstoqueMovimentacao.tenant_id == str(tenant_id),
            EstoqueMovimentacao.referencia_id == conta.id,
            EstoqueMovimentacao.tipo == "saida",
            EstoqueMovimentacao.motivo.in_(
                [_MOTIVO_TRANSFERENCIA_PARCEIRO_ESTOQUE, "transferencia_parceiro"]
            ),
        )
        .order_by(EstoqueMovimentacao.id.asc())
        .all()
    )

    try:
        estoques_finais: dict[int, float] = {}
        lotes_restaurados = 0

        for movimentacao in movimentacoes:
            lotes_restaurados += _restaurar_lotes_consumidos_transferencia(
                db, movimentacao
            )
            resultado_estorno = EstoqueService.estornar_estoque(
                produto_id=movimentacao.produto_id,
                quantidade=float(movimentacao.quantidade or 0),
                motivo=_MOTIVO_TRANSFERENCIA_PARCEIRO_EXCLUSAO,
                referencia_id=conta.id,
                referencia_tipo=_REFERENCIA_TRANSFERENCIA_PARCEIRO_EXCLUSAO,
                user_id=current_user.id,
                db=db,
                tenant_id=str(tenant_id),
                documento=conta.documento,
                observacao=(
                    f"Estorno por exclusao da transferencia "
                    f"{conta.documento or conta.id}"
                ),
                custo_unitario_override=float(movimentacao.custo_unitario or 0),
                valor_total_override=float(movimentacao.valor_total or 0),
            )
            estoques_finais[movimentacao.produto_id] = resultado_estorno["estoque_novo"]
            db.delete(movimentacao)

        recebimentos = (
            db.query(Recebimento)
            .filter(
                Recebimento.conta_receber_id == conta.id,
                Recebimento.tenant_id == str(tenant_id),
            )
            .all()
        )
        for recebimento in recebimentos:
            db.delete(recebimento)

        db.delete(conta)
        db.commit()

        for produto_id, estoque_novo in estoques_finais.items():
            try:
                sincronizar_bling_background(
                    produto_id,
                    estoque_novo,
                    "transferencia_parceiro_exclusao",
                )
            except Exception as e_sync:
                logger.warning(
                    f"[BLING-SYNC] Erro ao agendar sync (exclusao transferencia-parceiro): {e_sync}"
                )

        return {
            "sucesso": True,
            "conta_receber_id": conta_receber_id,
            "documento": conta.documento,
            "lotes_restaurados": lotes_restaurados,
        }
    except HTTPException:
        db.rollback()
        raise
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        db.rollback()
        logger.exception("Erro ao excluir transferencia para parceiro: %s", exc)
        raise HTTPException(
            status_code=500,
            detail="Nao foi possivel excluir a transferencia para parceiro",
        )
