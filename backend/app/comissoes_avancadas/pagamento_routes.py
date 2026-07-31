"""Pagamento seguro de comissões já provisionadas."""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import bindparam, text
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user_and_tenant
from app.comissoes_avancadas.common import logger, struct_logger
from app.comissoes_avancadas_models import (
    FecharComissaoComPagamento,
    FecharComPagamentoResponse,
    ListaFormasPagamento,
)
from app.db import get_session
from app.financeiro.contas_pagar_pagamento_service import (
    aplicar_pagamento_conta_pagar,
    validar_conta_bancaria,
    validar_forma_pagamento,
)
from app.financeiro_models import ContaPagar, FormaPagamento
from app.security.permissions_decorator import require_permission_dependency
from app.utils.tenant_safe_sql import execute_tenant_safe

router = APIRouter(
    dependencies=[Depends(require_permission_dependency("comissoes.fechamentos"))]
)

CENTAVO = Decimal("0.01")


def _dinheiro(valor) -> Decimal:
    return Decimal(str(valor or 0)).quantize(CENTAVO, rounding=ROUND_HALF_UP)


@router.get("/formas-pagamento", summary="Lista de formas de pagamento disponíveis")
def listar_formas_pagamento(
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
) -> ListaFormasPagamento:
    """Lista as formas financeiras ativas da empresa atual."""
    _current_user, tenant_id = user_and_tenant
    formas = (
        db.query(FormaPagamento)
        .filter(
            FormaPagamento.tenant_id == tenant_id,
            FormaPagamento.ativo.is_(True),
        )
        .order_by(FormaPagamento.nome)
        .all()
    )
    return ListaFormasPagamento(
        success=True,
        formas=[
            {
                "id": forma.id,
                "nome": forma.nome,
                "descricao": forma.nome,
                "ativo": True,
            }
            for forma in formas
        ],
    )


def _resolver_forma_pagamento(
    db: Session,
    *,
    tenant_id,
    referencia: str,
) -> FormaPagamento | None:
    valor = str(referencia or "").strip()
    if not valor or valor == "nao_informado":
        return None

    query = db.query(FormaPagamento).filter(
        FormaPagamento.tenant_id == tenant_id,
        FormaPagamento.ativo.is_(True),
    )
    forma = (
        query.filter(FormaPagamento.id == int(valor)).first()
        if valor.isdigit()
        else None
    )
    if not forma:
        forma = query.filter(FormaPagamento.nome.ilike(valor)).first()
    if not forma:
        raise HTTPException(
            status_code=400,
            detail="Forma de pagamento não encontrada ou inativa.",
        )
    return forma


@router.post(
    "/fechar-com-pagamento",
    summary="Fechar comissões com pagamento total ou parcial",
)
async def fechar_com_pagamento_parcial(
    payload: FecharComissaoComPagamento,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
) -> FecharComPagamentoResponse:
    """Aplica o pagamento nas contas já provisionadas, sem duplicar despesas."""
    current_user, tenant_id = user_and_tenant
    ids_solicitados = list(dict.fromkeys(payload.comissoes_ids))
    if not ids_solicitados:
        raise HTTPException(status_code=400, detail="Nenhuma comissão selecionada")

    try:
        lock_clause = (
            " FOR UPDATE" if db.bind and db.bind.dialect.name == "postgresql" else ""
        )
        stmt = text(
            f"""
            SELECT
                id,
                funcionario_id,
                valor_comissao_gerada,
                COALESCE(valor_pago, 0) AS valor_pago,
                status,
                conta_pagar_id
            FROM comissoes_itens
            WHERE id IN :ids
              AND {{tenant_filter}}
            {lock_clause}
            """
        ).bindparams(bindparam("ids", expanding=True))
        rows = execute_tenant_safe(
            db,
            stmt,
            {"ids": tuple(ids_solicitados)},
            tenant_id=tenant_id,
        ).fetchall()
        rows_por_id = {row.id: row for row in rows}

        ignoradas = [
            item_id for item_id in ids_solicitados if item_id not in rows_por_id
        ]
        candidatas = []
        for item_id in ids_solicitados:
            row = rows_por_id.get(item_id)
            if not row:
                continue
            if row.status not in {"pendente", "fechada"}:
                ignoradas.append(item_id)
                continue
            candidatas.append(row)

        if not candidatas:
            raise HTTPException(
                status_code=400, detail="Nenhuma comissão válida para pagar"
            )

        funcionarios = {row.funcionario_id for row in candidatas}
        if len(funcionarios) != 1:
            raise HTTPException(
                status_code=400,
                detail="Selecione comissões de apenas um funcionário por pagamento.",
            )

        contas_ids = {row.conta_pagar_id for row in candidatas if row.conta_pagar_id}
        contas = (
            db.query(ContaPagar)
            .filter(
                ContaPagar.id.in_(contas_ids),
                ContaPagar.tenant_id == tenant_id,
            )
            .with_for_update()
            .all()
            if contas_ids
            else []
        )
        contas_por_id = {conta.id: conta for conta in contas}

        itens = []
        for row in candidatas:
            conta = contas_por_id.get(row.conta_pagar_id)
            if not conta or conta.status in {"pago", "cancelado"}:
                raise HTTPException(
                    status_code=409,
                    detail=(
                        f"A comissão {row.id} não possui uma conta a pagar válida. "
                        "Reprovisione ou confira o financeiro antes de pagar."
                    ),
                )

            valor_comissao = _dinheiro(row.valor_comissao_gerada)
            valor_ja_pago = max(_dinheiro(row.valor_pago), _dinheiro(conta.valor_pago))
            saldo = max(Decimal("0"), valor_comissao - valor_ja_pago)
            saldo_conta = max(
                Decimal("0"),
                _dinheiro(conta.valor_final) - _dinheiro(conta.valor_pago),
            )
            if saldo == 0:
                ignoradas.append(row.id)
                continue
            if saldo_conta == 0:
                raise HTTPException(
                    status_code=409,
                    detail=(
                        f"A conta a pagar da comissão {row.id} não possui saldo, "
                        "mas a comissão ainda está aberta. Faça a conciliação "
                        "financeira antes de pagar."
                    ),
                )
            itens.append(
                {
                    "row": row,
                    "conta": conta,
                    "valor_comissao": valor_comissao,
                    "valor_ja_pago": valor_ja_pago,
                    "saldo": saldo,
                    "saldo_liquidavel": min(saldo, saldo_conta),
                }
            )

        if not itens:
            raise HTTPException(
                status_code=400, detail="As comissões selecionadas já estão pagas"
            )

        valor_solicitado = _dinheiro(payload.valor_pago)
        saldo_total_antes = sum((item["saldo"] for item in itens), Decimal("0"))
        limite_pagamento = sum(
            (item["saldo_liquidavel"] for item in itens), Decimal("0")
        )
        if valor_solicitado <= 0:
            raise HTTPException(
                status_code=400, detail="Valor pago deve ser maior que zero"
            )
        if valor_solicitado > limite_pagamento:
            raise HTTPException(
                status_code=400,
                detail=(
                    "O valor informado excede o saldo liquidável das contas "
                    f"provisionadas (R$ {limite_pagamento:.2f})."
                ),
            )

        forma = _resolver_forma_pagamento(
            db,
            tenant_id=tenant_id,
            referencia=payload.forma_pagamento,
        )
        forma_id = validar_forma_pagamento(
            db,
            tenant_id=tenant_id,
            forma_pagamento_id=forma.id if forma else None,
        )
        conta_bancaria = validar_conta_bancaria(
            db,
            tenant_id=tenant_id,
            conta_bancaria_id=payload.conta_bancaria_id,
        )

        restante = valor_solicitado
        total_processadas = 0
        saldos_finais = {item["row"].id: item["saldo"] for item in itens}
        for item in itens:
            if restante <= 0:
                break
            valor_aplicar = min(restante, item["saldo_liquidavel"])
            aplicar_pagamento_conta_pagar(
                db,
                conta=item["conta"],
                tenant_id=tenant_id,
                current_user=current_user,
                data_pagamento=payload.data_pagamento,
                forma_pagamento_validada_id=forma_id,
                conta_bancaria=conta_bancaria,
                observacoes=payload.observacoes,
                valor_base_pagamento=valor_aplicar,
            )

            novo_pago = item["valor_ja_pago"] + valor_aplicar
            if item["conta"].status == "pago":
                novo_pago = item["valor_comissao"]
            novo_saldo = max(Decimal("0"), item["valor_comissao"] - novo_pago)
            novo_status = "pago" if novo_saldo == 0 else "fechada"
            execute_tenant_safe(
                db,
                """
                UPDATE comissoes_itens
                SET status = :status,
                    data_fechamento = COALESCE(data_fechamento, :data_pagamento),
                    data_pagamento = :data_pagamento,
                    forma_pagamento = :forma_pagamento,
                    valor_pago = :valor_pago,
                    saldo_restante = :saldo_restante,
                    observacao_pagamento = :observacao,
                    data_atualizacao = CURRENT_TIMESTAMP
                WHERE id = :id
                  AND {tenant_filter}
                """,
                {
                    "status": novo_status,
                    "data_pagamento": payload.data_pagamento,
                    "forma_pagamento": forma.nome if forma else "Não informado",
                    "valor_pago": novo_pago,
                    "saldo_restante": novo_saldo,
                    "observacao": payload.observacoes,
                    "id": item["row"].id,
                },
                tenant_id=tenant_id,
            )
            restante -= valor_aplicar
            total_processadas += 1
            saldos_finais[item["row"].id] = novo_saldo

        saldo_total_restante = sum(saldos_finais.values(), Decimal("0"))
        comissoes_com_saldo = sum(1 for saldo in saldos_finais.values() if saldo > 0)
        db.commit()

        mensagem = (
            f"{total_processadas} comissão(ões) atualizada(s). "
            f"Pagamento: R$ {valor_solicitado:.2f}."
        )
        struct_logger.info(
            "COMMISSION_PAYMENT_APPLIED",
            mensagem,
            extra={
                "total_processadas": total_processadas,
                "total_ignoradas": len(set(ignoradas)),
                "valor_pago": float(valor_solicitado),
                "saldo_restante": float(saldo_total_restante),
                "funcionario_id": next(iter(funcionarios)),
            },
        )
        return FecharComPagamentoResponse(
            success=True,
            total_processadas=total_processadas,
            total_ignoradas=len(set(ignoradas)),
            valor_total_fechado=float(saldo_total_antes),
            valor_total_pago=float(valor_solicitado),
            saldo_total_restante=float(saldo_total_restante),
            comissoes_com_saldo=comissoes_com_saldo,
            forma_pagamento=forma.nome if forma else "Não informado",
            data_pagamento=str(payload.data_pagamento),
            observacoes=payload.observacoes,
            mensagem=mensagem,
        )
    except HTTPException:
        db.rollback()
        raise
    except Exception as exc:
        db.rollback()
        logger.exception("Erro ao pagar comissões")
        raise HTTPException(
            status_code=500,
            detail="Não foi possível concluir o pagamento das comissões.",
        ) from exc


__all__ = ["fechar_com_pagamento_parcial", "listar_formas_pagamento", "router"]
