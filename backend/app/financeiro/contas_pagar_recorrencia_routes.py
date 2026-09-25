"""Rotas de recorrencia de contas a pagar."""

import logging
from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import and_, func, or_
from sqlalchemy.orm import Session, joinedload

from app.auth.dependencies import get_current_user_and_tenant
from app.db import get_session
from app.domain.dre.lancamento_dre_sync import atualizar_dre_por_lancamento
from app.financeiro.contas_pagar_recorrencia import (
    _gerar_contas_recorrentes_ate_janela,
    _obter_origem_recorrencia,
    _query_contas_recorrencia,
    calcular_limite_janela_recorrencia,
)
from app.financeiro.contas_pagar_schemas import ContaPagarRecorrenciaBulkDelete
from app.financeiro_models import ContaPagar, LancamentoManual

logger = logging.getLogger(__name__)
router = APIRouter()


def _tem_pagamento(conta: ContaPagar) -> bool:
    return bool(
        conta.status in ("pago", "parcial")
        or (conta.valor_pago or Decimal("0")) > 0
        or conta.pagamentos
    )


def _remover_previsoes_conta(db: Session, tenant_id, conta: ContaPagar) -> None:
    """Remove apenas previsoes automaticas vinculadas a esta conta."""
    prefixo = f"Gerado automaticamente da conta a pagar #{conta.id}"
    previsoes = (
        db.query(LancamentoManual)
        .filter(
            LancamentoManual.tenant_id == tenant_id,
            LancamentoManual.tipo == "saida",
            LancamentoManual.status == "previsto",
            LancamentoManual.gerado_automaticamente.is_(True),
            or_(
                LancamentoManual.documento == f"CONTA-PAGAR-{conta.id}",
                LancamentoManual.observacoes == prefixo,
                LancamentoManual.observacoes.like(f"{prefixo}.%"),
                LancamentoManual.observacoes.like(f"{prefixo} (%"),
            ),
        )
        .all()
    )
    for previsao in previsoes:
        db.delete(previsao)


def _excluir_contas_sem_pagamento(
    db: Session, tenant_id, contas: list[ContaPagar]
) -> None:
    for conta in sorted(contas, key=lambda item: 1 if item.eh_recorrente else 0):
        _remover_previsoes_conta(db, tenant_id, conta)
        db.delete(conta)


@router.get("/{conta_id}/recorrencia")
def listar_recorrencia_conta_pagar(
    conta_id: int,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Lista a cadeia recorrente de uma conta para manutencao seletiva."""
    _, tenant_id = user_and_tenant

    conta = (
        db.query(ContaPagar)
        .filter(
            ContaPagar.id == conta_id,
            ContaPagar.tenant_id == tenant_id,
        )
        .first()
    )
    if not conta:
        raise HTTPException(status_code=404, detail="Conta nao encontrada")

    conta_origem = _obter_origem_recorrencia(db, tenant_id, conta)
    if not conta_origem:
        conta_origem = conta

    itens = (
        _query_contas_recorrencia(db, tenant_id, conta_origem.id)
        .order_by(
            ContaPagar.data_vencimento.asc(),
            ContaPagar.id.asc(),
        )
        .all()
    )

    return {
        "conta_origem_id": conta_origem.id,
        "itens": [
            {
                "id": item.id,
                "descricao": item.descricao,
                "data_vencimento": item.data_vencimento,
                "valor_final": float(item.valor_final or 0),
                "valor_pago": float(item.valor_pago or 0),
                "status": item.status,
                "eh_origem": item.id == conta_origem.id,
                "pode_excluir": not _tem_pagamento(item),
                "motivo_bloqueio": (
                    "Conta com pagamento registrado" if _tem_pagamento(item) else None
                ),
            }
            for item in itens
        ],
    }


@router.post("/recorrencias/excluir")
def excluir_recorrencias_contas_pagar(
    payload: ContaPagarRecorrenciaBulkDelete,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Exclui lancamentos recorrentes selecionados, desde que nao tenham pagamentos."""
    _, tenant_id = user_and_tenant
    ids = sorted({int(item_id) for item_id in payload.ids if item_id})
    if not ids:
        raise HTTPException(
            status_code=422, detail="Selecione pelo menos um lancamento para excluir"
        )

    contas = (
        db.query(ContaPagar)
        .options(joinedload(ContaPagar.pagamentos))
        .filter(
            ContaPagar.tenant_id == tenant_id,
            ContaPagar.id.in_(ids),
        )
        .all()
    )
    if len(contas) != len(ids):
        raise HTTPException(
            status_code=404, detail="Uma ou mais contas nao foram encontradas"
        )

    contas_por_id = {conta.id: conta for conta in contas}
    for conta in contas:
        if _tem_pagamento(conta):
            raise HTTPException(
                status_code=400,
                detail=f"Conta #{conta.id} possui pagamento registrado e nao pode ser excluida",
            )

    ids_set = set(ids)
    for conta in contas:
        if not conta.eh_recorrente:
            continue
        filhas_nao_selecionadas = (
            db.query(func.count(ContaPagar.id))
            .filter(
                ContaPagar.tenant_id == tenant_id,
                ContaPagar.conta_recorrencia_origem_id == conta.id,
                ~ContaPagar.id.in_(ids_set),
            )
            .scalar()
            or 0
        )
        if filhas_nao_selecionadas:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Para excluir a conta origem da recorrencia, selecione tambem "
                    "todos os lancamentos futuros sem pagamento."
                ),
            )

    _excluir_contas_sem_pagamento(
        db, tenant_id, [contas_por_id[conta_id] for conta_id in ids]
    )

    db.commit()

    return {
        "ok": True,
        "mensagem": "Lancamentos recorrentes excluidos com sucesso",
        "ids": ids,
        "total": len(ids),
    }


# ============================================================================
# PROCESSAR RECORRÊNCIAS
# ============================================================================


@router.post("/processar-recorrencias")
async def processar_recorrencias_contas_pagar(
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    Processa contas recorrentes e cria novas contas quando necessário
    Esta rota deve ser executada periodicamente (diariamente recomendado)
    """
    current_user, tenant_id = user_and_tenant
    hoje = date.today()
    limite_recorrencia = calcular_limite_janela_recorrencia(hoje)
    contas_criadas = []

    # Buscar contas recorrentes que precisam manter a janela futura preenchida
    contas_recorrentes = (
        db.query(ContaPagar)
        .filter(
            and_(
                ContaPagar.eh_recorrente.is_(True),
                ContaPagar.proxima_recorrencia <= limite_recorrencia,
                or_(
                    ContaPagar.data_fim_recorrencia.is_(None),
                    ContaPagar.data_fim_recorrencia >= hoje,
                ),
            )
        )
        .all()
    )

    for conta_origem in contas_recorrentes:
        try:
            novas_contas = _gerar_contas_recorrentes_ate_janela(
                db=db,
                tenant_id=tenant_id,
                conta_origem=conta_origem,
                limite_recorrencia=limite_recorrencia,
            )
            contas_criadas.extend(novas_contas)
            logger.info(
                f"Recorrencia #{conta_origem.id}: {len(novas_contas)} conta(s) gerada(s)"
            )

        except Exception as e:
            logger.error(
                f"Erro ao processar recorrencia da conta #{conta_origem.id}: {e}"
            )
            continue

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
                f"Erro ao atualizar DRE para conta recorrente #{conta_criada.id}: {e}"
            )

    db.commit()

    return {
        "message": f"{len(contas_criadas)} conta(s) recorrente(s) processada(s) com sucesso",
        "contas_criadas": len(contas_criadas),
        "ids": [c.id for c in contas_criadas],
    }
