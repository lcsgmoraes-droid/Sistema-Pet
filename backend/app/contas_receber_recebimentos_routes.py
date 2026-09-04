"""Rotas de baixa e recebimento de contas a receber."""

import logging
from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session, joinedload

from .auth.dependencies import get_current_user_and_tenant
from .contas_receber_encargos import (
    aplicar_encargos_automaticos,
    calcular_encargos_automaticos,
    carregar_config_encargos,
    dinheiro,
    serializar_calculo_encargos,
)
from .contas_receber_schemas import RecebimentoCreate, RecebimentoLoteCreate
from .db import get_session
from .financeiro_models import ContaReceber, FormaPagamento, Recebimento
from .idempotency import idempotent
from .utils.tenant_safe_sql import execute_tenant_safe

logger = logging.getLogger(__name__)
router = APIRouter()


def _aplicar_baixa(
    conta,
    *,
    data_recebimento,
    valor_recebido=0,
    valor_juros=0,
    valor_multa=0,
    valor_desconto=0,
    aplicar_automaticos=False,
    quitar=False,
    config=None,
):
    calculo = calcular_encargos_automaticos(conta, data_recebimento, config)
    if aplicar_automaticos:
        aplicar_encargos_automaticos(conta, calculo, data_recebimento)

    conta.valor_juros = dinheiro(conta.valor_juros) + dinheiro(valor_juros)
    conta.valor_multa = dinheiro(conta.valor_multa) + dinheiro(valor_multa)
    conta.valor_desconto = dinheiro(conta.valor_desconto) + dinheiro(valor_desconto)
    conta.valor_final = (
        dinheiro(conta.valor_original)
        + dinheiro(conta.valor_juros)
        + dinheiro(conta.valor_multa)
        - dinheiro(conta.valor_desconto)
    )

    saldo = dinheiro(conta.valor_final) - dinheiro(conta.valor_recebido)
    if saldo <= 0:
        raise HTTPException(status_code=400, detail="Conta sem saldo para receber")

    valor_baixa = saldo if quitar else dinheiro(valor_recebido)
    if valor_baixa <= 0:
        raise HTTPException(status_code=400, detail="Informe um valor maior que zero")
    if valor_baixa > saldo + Decimal("0.01"):
        raise HTTPException(
            status_code=400,
            detail=f"Valor informado supera o saldo de R$ {saldo:.2f}",
        )

    conta.valor_recebido = dinheiro(conta.valor_recebido) + valor_baixa
    if conta.valor_recebido >= conta.valor_final:
        conta.status = "recebido"
        conta.data_recebimento = data_recebimento
    else:
        conta.status = "parcial"
    return valor_baixa, calculo


def _gerar_comissao_baixa_lote(db, conta, tenant_id, forma_pagamento_id, valor_baixa):
    """Preserva na baixa em lote o mesmo efeito financeiro da baixa individual."""
    if not conta.venda_id:
        return None

    try:
        from app.comissoes_service import gerar_comissoes_venda
        from app.vendas_models import Venda

        venda = (
            db.query(Venda)
            .filter(Venda.id == conta.venda_id, Venda.tenant_id == tenant_id)
            .first()
        )
        if not venda or not venda.funcionario_id:
            return None

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
                FormaPagamento.id == forma_pagamento_id,
                FormaPagamento.tenant_id == tenant_id,
            )
            .first()
            if forma_pagamento_id
            else None
        )
        resultado = gerar_comissoes_venda(
            venda_id=venda.id,
            funcionario_id=venda.funcionario_id,
            valor_pago=Decimal(str(valor_baixa)),
            forma_pagamento=forma.nome if forma else None,
            parcela_numero=proxima_parcela,
            db=db,
            tenant_id=tenant_id,
        )
        if not resultado.get("success"):
            logger.warning(
                "Falha ao gerar comissao da baixa em lote para venda %s: %s",
                venda.id,
                resultado.get("error", "erro desconhecido"),
            )
            return None
        return {
            "venda_id": venda.id,
            "numero_venda": venda.numero_venda,
            "valor_comissao": resultado.get("total_comissao", 0),
        }
    except Exception:
        logger.exception(
            "Erro ao gerar comissao da baixa em lote para venda %s", conta.venda_id
        )
        return None


@router.get("/{conta_id}/encargos")
def consultar_encargos_conta(
    conta_id: int,
    data_calculo: date,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Prévia dos encargos automáticos, sem alterar a conta."""
    _current_user, tenant_id = user_and_tenant
    conta = (
        db.query(ContaReceber)
        .options(joinedload(ContaReceber.forma_pagamento))
        .filter(ContaReceber.id == conta_id, ContaReceber.tenant_id == tenant_id)
        .first()
    )
    if not conta:
        raise HTTPException(status_code=404, detail="Conta não encontrada")
    config = carregar_config_encargos(db, tenant_id)
    return serializar_calculo_encargos(
        calcular_encargos_automaticos(conta, data_calculo, config)
    )


@router.post("/receber-lote")
@idempotent()
async def registrar_recebimentos_lote(
    lote: RecebimentoLoteCreate,
    request: Request,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Quita, em uma única operação, todas as parcelas selecionadas."""
    current_user, tenant_id = user_and_tenant
    contas = (
        db.query(ContaReceber)
        .options(joinedload(ContaReceber.forma_pagamento))
        .filter(
            ContaReceber.id.in_(lote.conta_ids),
            ContaReceber.tenant_id == tenant_id,
        )
        .all()
    )
    contas_por_id = {conta.id: conta for conta in contas}
    faltantes = [
        conta_id for conta_id in lote.conta_ids if conta_id not in contas_por_id
    ]
    if faltantes:
        raise HTTPException(
            status_code=404,
            detail=f"Conta(s) não encontrada(s): {', '.join(map(str, faltantes))}",
        )

    config = carregar_config_encargos(db, tenant_id)
    resultados = []
    try:
        for conta_id in lote.conta_ids:
            conta = contas_por_id[conta_id]
            if str(conta.status).lower() in {
                "recebido",
                "pago",
                "cancelado",
                "cancelada",
            }:
                raise HTTPException(
                    status_code=400,
                    detail=f"Conta {conta_id} não está disponível para baixa",
                )
            valor_baixa, calculo = _aplicar_baixa(
                conta,
                data_recebimento=lote.data_recebimento,
                aplicar_automaticos=lote.aplicar_encargos_automaticos,
                quitar=True,
                config=config,
            )
            db.add(
                Recebimento(
                    conta_receber_id=conta.id,
                    forma_pagamento_id=lote.forma_pagamento_id,
                    valor_recebido=valor_baixa,
                    data_recebimento=lote.data_recebimento,
                    observacoes=lote.observacoes,
                    user_id=current_user.id,
                    tenant_id=tenant_id,
                )
            )
            resultados.append(
                {
                    "conta_id": conta.id,
                    "valor_recebido": float(valor_baixa),
                    "juros_aplicados": (
                        float(calculo["valor_juros_calculado"])
                        if lote.aplicar_encargos_automaticos
                        else 0
                    ),
                    "multa_aplicada": (
                        float(calculo["valor_multa_calculada"])
                        if lote.aplicar_encargos_automaticos
                        else 0
                    ),
                }
            )
        db.commit()
    except Exception:
        db.rollback()
        raise

    for item in resultados:
        conta = contas_por_id[item["conta_id"]]
        comissao = _gerar_comissao_baixa_lote(
            db,
            conta,
            tenant_id,
            lote.forma_pagamento_id,
            item["valor_recebido"],
        )
        if comissao:
            item["comissao"] = comissao

    return {
        "message": f"{len(resultados)} conta(s) recebida(s) com sucesso",
        "quantidade": len(resultados),
        "valor_total": round(sum(item["valor_recebido"] for item in resultados), 2),
        "itens": resultados,
    }


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
        .options(joinedload(ContaReceber.forma_pagamento))
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

    config = carregar_config_encargos(db, tenant_id)
    valor_baixa, calculo_encargos = _aplicar_baixa(
        conta,
        data_recebimento=recebimento.data_recebimento,
        valor_recebido=recebimento.valor_recebido,
        valor_juros=recebimento.valor_juros,
        valor_multa=recebimento.valor_multa,
        valor_desconto=recebimento.valor_desconto,
        aplicar_automaticos=recebimento.aplicar_encargos_automaticos,
        quitar=recebimento.quitar,
        config=config,
    )

    # Registrar recebimento
    novo_recebimento = Recebimento(
        conta_receber_id=conta.id,
        forma_pagamento_id=recebimento.forma_pagamento_id,
        valor_recebido=valor_baixa,
        data_recebimento=recebimento.data_recebimento,
        observacoes=recebimento.observacoes,
        user_id=current_user.id,
        tenant_id=tenant_id,  # ✅ Garantir isolamento multi-tenant
    )
    db.add(novo_recebimento)

    db.commit()
    db.refresh(novo_recebimento)

    logger.info(f"✅ Recebimento registrado: R$ {valor_baixa} - Conta {conta_id}")

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
                    valor_pago=Decimal(str(valor_baixa)),  # Apenas o valor DESTA baixa
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
            logger.error(f"❌ Erro ao gerar comissão para venda #{conta.venda_id}: {e}")
            # Não falha o recebimento por erro na comissão
            pass

    response = {
        "message": "Recebimento registrado com sucesso",
        "conta_id": conta.id,
        "status": conta.status,
        "valor_recebido_total": float(conta.valor_recebido),
        "valor_final": float(conta.valor_final),
        "saldo_restante": float(conta.valor_final - conta.valor_recebido),
        "encargos_automaticos": (
            serializar_calculo_encargos(calculo_encargos)
            if recebimento.aplicar_encargos_automaticos
            else None
        ),
        "recebimento": {
            "id": novo_recebimento.id,
            "valor": float(novo_recebimento.valor_recebido),
            "data": novo_recebimento.data_recebimento.isoformat(),
            "forma_pagamento_id": novo_recebimento.forma_pagamento_id,
            "observacoes": novo_recebimento.observacoes,
        },
    }

    if comissao_gerada and comissao_info:
        response["comissao"] = comissao_info

    return response


# ============================================================================
# DASHBOARD / RESUMO
# ============================================================================
