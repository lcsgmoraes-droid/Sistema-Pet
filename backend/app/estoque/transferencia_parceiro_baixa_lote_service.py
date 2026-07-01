from __future__ import annotations

import logging
import unicodedata
from datetime import date, datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP

from fastapi import HTTPException
from sqlalchemy.orm import Session, joinedload

from app.domain.dre.lancamento_dre_sync import atualizar_dre_por_lancamento
from app.estoque.service import EstoqueService
from app.estoque.transferencia_parceiro_baixa_lote_acerto import (
    criar_conta_pagar_acerto_lote,
    valor_conta_pagar_acerto_payload,
)
from app.estoque.transferencia_parceiro_documents import (
    _saldo_conta_receber,
    _status_transferencia_parceiro,
)
from app.estoque.transferencia_parceiro_support import (
    _MOTIVO_TRANSFERENCIA_PARCEIRO_ESTOQUE,
    _buscar_forma_pagamento_transferencia,
    _obter_ou_criar_forma_pagamento_acerto,
    _saldo_conta_pagar,
    _texto_limpo,
)
from app.financeiro_models import (
    ContaPagar,
    ContaReceber,
    LancamentoManual,
    Pagamento,
    Recebimento,
)
from app.produtos_models import EstoqueMovimentacao


CENTAVO = Decimal("0.01")
logger = logging.getLogger(__name__)

_MODOS_BAIXA_LOTE = {
    "recebimento": "Recebimento financeiro",
    "acerto": "Acerto / compensacao",
    "produto_devolvido": "Produto devolvido",
}
_MOTIVO_DEVOLUCAO_TRANSFERENCIA_PARCEIRO = "transf_dev"
_REFERENCIA_DEVOLUCAO_TRANSFERENCIA_PARCEIRO = "transf_devolucao"


def _texto_ascii(valor) -> str:
    texto = str(valor or "").strip().lower()
    return (
        unicodedata.normalize("NFD", texto)
        .encode("ascii", "ignore")
        .decode("ascii")
    )


def decimal_monetario(valor) -> Decimal:
    return Decimal(str(valor or 0)).quantize(CENTAVO, rounding=ROUND_HALF_UP)


def saldo_conta_receber_decimal(conta) -> Decimal:
    valor_final = decimal_monetario(getattr(conta, "valor_final", None))
    valor_recebido = decimal_monetario(getattr(conta, "valor_recebido", None))
    saldo = valor_final - valor_recebido
    return max(saldo, Decimal("0.00")).quantize(CENTAVO)


def _data_ordem_conta(conta) -> tuple[date, int]:
    data_ref = (
        getattr(conta, "data_emissao", None)
        or getattr(conta, "data_vencimento", None)
        or date.min
    )
    return data_ref, int(getattr(conta, "id", 0) or 0)


def distribuir_baixa_transferencias(
    contas,
    valor_total,
    *,
    ordem: str = "antiga",
) -> list[dict]:
    valor_disponivel = decimal_monetario(valor_total)
    if valor_disponivel <= 0:
        return []

    ordem_normalizada = str(ordem or "antiga").strip().lower()
    reverse = ordem_normalizada in {"nova", "mais_nova", "desc", "descendente"}
    contas_ordenadas = sorted(contas or [], key=_data_ordem_conta, reverse=reverse)

    distribuicao: list[dict] = []
    for conta in contas_ordenadas:
        if valor_disponivel <= 0:
            break

        saldo_anterior = saldo_conta_receber_decimal(conta)
        if saldo_anterior <= 0:
            continue

        valor_baixado = min(valor_disponivel, saldo_anterior).quantize(CENTAVO)
        saldo_restante = (saldo_anterior - valor_baixado).quantize(CENTAVO)
        distribuicao.append(
            {
                "conta_receber_id": int(conta.id),
                "valor_baixado": valor_baixado,
                "saldo_anterior": saldo_anterior,
                "saldo_restante": saldo_restante,
            }
        )
        valor_disponivel = (valor_disponivel - valor_baixado).quantize(CENTAVO)

    return distribuicao


def validar_devolucao_estoque_integral(conta, valor_baixado: Decimal) -> None:
    saldo_aberto = saldo_conta_receber_decimal(conta)
    valor = decimal_monetario(valor_baixado)
    if saldo_aberto - valor > CENTAVO:
        raise HTTPException(
            status_code=400,
            detail=(
                "Devolucao com entrada no estoque exige baixa integral da "
                "transferencia selecionada."
            ),
        )


def normalizar_modo_baixa_lote(valor: str | None) -> str:
    modo = str(valor or "recebimento").strip().lower()
    if modo not in _MODOS_BAIXA_LOTE:
        raise HTTPException(
            status_code=400,
            detail=(
                "Modo de baixa invalido. Use recebimento, acerto ou "
                "produto_devolvido."
            ),
        )
    return modo


def resolver_data_recebimento_financeiro(data_base: date, forma_pagamento) -> date:
    if not forma_pagamento:
        return data_base

    tipo = _texto_ascii(getattr(forma_pagamento, "tipo", ""))
    gera_recebivel = bool(getattr(forma_pagamento, "gera_contas_receber", False))
    if "cartao" not in tipo and not gera_recebivel:
        return data_base

    dias_antecipado = getattr(
        forma_pagamento, "dias_recebimento_antecipado", None
    )
    if dias_antecipado is not None:
        dias = int(dias_antecipado or 0)
    else:
        dias = int(
            getattr(forma_pagamento, "prazo_recebimento", None)
            or getattr(forma_pagamento, "prazo_dias", None)
            or 0
        )

    return data_base + timedelta(days=max(dias, 0))


def buscar_transferencias_abertas_para_baixa(
    db: Session,
    *,
    tenant_id,
    parceiro_id: int,
    data_inicio: date | None = None,
    data_fim: date | None = None,
    ordem: str = "antiga",
) -> list[ContaReceber]:
    query = (
        db.query(ContaReceber)
        .options(joinedload(ContaReceber.cliente))
        .filter(
            ContaReceber.tenant_id == str(tenant_id),
            ContaReceber.canal == "transferencia_parceiro",
            ContaReceber.cliente_id == parceiro_id,
            ContaReceber.status.notin_(
                ["recebido", "pago", "cancelado", "cancelada"]
            ),
        )
    )

    if data_inicio:
        query = query.filter(ContaReceber.data_emissao >= data_inicio)
    if data_fim:
        query = query.filter(ContaReceber.data_emissao <= data_fim)

    contas = query.all()
    reverse = str(ordem or "").strip().lower() in {
        "nova",
        "mais_nova",
        "desc",
        "descendente",
    }
    return [
        conta
        for conta in sorted(contas, key=_data_ordem_conta, reverse=reverse)
        if saldo_conta_receber_decimal(conta) > 0
    ]


def _buscar_contas_aplicacao(
    db: Session,
    *,
    tenant_id,
    parceiro_id: int,
    conta_ids: list[int],
) -> dict[int, ContaReceber]:
    contas = (
        db.query(ContaReceber)
        .options(joinedload(ContaReceber.cliente))
        .filter(
            ContaReceber.tenant_id == str(tenant_id),
            ContaReceber.canal == "transferencia_parceiro",
            ContaReceber.cliente_id == parceiro_id,
            ContaReceber.id.in_(conta_ids),
        )
        .all()
    )
    contas_por_id = {int(conta.id): conta for conta in contas}
    faltantes = [conta_id for conta_id in conta_ids if conta_id not in contas_por_id]
    if faltantes:
        raise HTTPException(
            status_code=404,
            detail="Uma ou mais transferencias selecionadas nao foram encontradas.",
        )
    return contas_por_id


def _valor_compensacao_payload(item) -> Decimal:
    valor = (
        item.get("valor_compensado")
        if isinstance(item, dict)
        else getattr(item, "valor_compensado", 0)
    )
    return decimal_monetario(valor)


def _id_compensacao_payload(item) -> int:
    valor = (
        item.get("conta_pagar_id")
        if isinstance(item, dict)
        else getattr(item, "conta_pagar_id", 0)
    )
    return int(valor or 0)


def aplicar_compensacoes_acerto_lote(
    db: Session,
    *,
    tenant_id,
    parceiro_id: int,
    user_id: int,
    data_pagamento: date,
    forma_pagamento,
    compensacoes_payload: list,
    total_baixa: Decimal,
    documento_lote: str,
) -> list[int]:
    compensacoes_validas = [
        item for item in (compensacoes_payload or []) if _valor_compensacao_payload(item) > 0
    ]
    if not compensacoes_validas:
        return []

    total_compensado = sum(
        (_valor_compensacao_payload(item) for item in compensacoes_validas),
        Decimal("0.00"),
    ).quantize(CENTAVO)
    if abs(total_compensado - total_baixa) > CENTAVO:
        raise HTTPException(
            status_code=400,
            detail=(
                "O total compensado nas contas a pagar deve ser igual ao valor "
                "total da baixa em lote."
            ),
        )

    ids = [_id_compensacao_payload(item) for item in compensacoes_validas]
    contas = (
        db.query(ContaPagar)
        .filter(
            ContaPagar.tenant_id == str(tenant_id),
            ContaPagar.fornecedor_id == parceiro_id,
            ContaPagar.id.in_(ids),
        )
        .all()
    )
    contas_por_id = {int(conta.id): conta for conta in contas}
    pagamentos_criados: list[int] = []

    for item in compensacoes_validas:
        conta_pagar_id = _id_compensacao_payload(item)
        conta_pagar = contas_por_id.get(conta_pagar_id)
        if not conta_pagar:
            raise HTTPException(
                status_code=404,
                detail=f"Conta a pagar #{conta_pagar_id} nao encontrada para essa pessoa.",
            )

        valor = _valor_compensacao_payload(item)
        saldo = decimal_monetario(_saldo_conta_pagar(conta_pagar))
        if valor - saldo > CENTAVO:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"O valor compensado ultrapassa o saldo da conta a pagar "
                    f"#{conta_pagar.id}. Saldo atual: R$ {float(saldo):.2f}"
                ),
            )

        novo_pago = decimal_monetario(conta_pagar.valor_pago) + valor
        conta_pagar.valor_pago = novo_pago
        conta_pagar.status = (
            "pago"
            if abs(decimal_monetario(conta_pagar.valor_final) - novo_pago) <= CENTAVO
            else "parcial"
        )
        if conta_pagar.status == "pago":
            conta_pagar.data_pagamento = data_pagamento

        observacao = (
            f"Compensacao via baixa em lote de transferencia parceiro "
            f"{documento_lote} - R$ {float(valor):.2f}"
        )
        pagamento = Pagamento(
            conta_pagar_id=conta_pagar.id,
            forma_pagamento_id=getattr(forma_pagamento, "id", None),
            valor_pago=valor,
            data_pagamento=data_pagamento,
            observacoes=observacao,
            user_id=user_id,
            tenant_id=str(tenant_id),
        )
        db.add(pagamento)
        db.flush()
        pagamentos_criados.append(pagamento.id)
        conta_pagar.observacoes = (
            f"{conta_pagar.observacoes}\n\n{observacao}".strip()
            if conta_pagar.observacoes
            else observacao
        )

    return pagamentos_criados


def _append_observacao(conta: ContaReceber, linha: str) -> None:
    conta.observacoes = (
        f"{conta.observacoes}\n\n{linha}".strip() if conta.observacoes else linha
    )


def _registrar_lancamento_financeiro(
    db: Session,
    *,
    conta: ContaReceber,
    valor: Decimal,
    data_recebimento: date,
    forma_pagamento,
    user_id: int,
    tenant_id,
    historico: str,
) -> int:
    lancamento = LancamentoManual(
        tipo="entrada",
        valor=valor,
        descricao=f"Transferencia parceiro - {conta.documento or conta.id}",
        data_lancamento=data_recebimento,
        status="realizado" if data_recebimento <= date.today() else "previsto",
        categoria_id=conta.categoria_id,
        conta_bancaria_id=getattr(forma_pagamento, "conta_bancaria_destino_id", None),
        documento=f"TRP-BAIXA-{conta.id}",
        fornecedor_cliente=getattr(conta.cliente, "nome", None),
        observacoes=historico,
        gerado_automaticamente=True,
        user_id=user_id,
        tenant_id=str(tenant_id),
    )
    db.add(lancamento)
    db.flush()
    return lancamento.id


def _estornar_estoque_transferencia(
    db: Session,
    *,
    conta: ContaReceber,
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


def aplicar_baixa_lote_transferencia(
    db: Session,
    *,
    tenant_id,
    user_id: int,
    payload,
) -> dict:
    modo_baixa = normalizar_modo_baixa_lote(payload.modo_baixa)
    nova_conta_pagar_acerto = getattr(payload, "nova_conta_pagar_acerto", None)
    if nova_conta_pagar_acerto and modo_baixa != "acerto":
        raise HTTPException(
            status_code=400,
            detail="Nova conta a pagar de acerto so pode ser usada no modo acerto.",
        )

    aplicacoes = [
        item
        for item in (payload.aplicacoes or [])
        if decimal_monetario(getattr(item, "valor_baixado", 0)) > 0
    ]
    if not aplicacoes:
        raise HTTPException(
            status_code=400,
            detail="Informe ao menos uma transferencia para baixar.",
        )

    conta_ids = [int(item.conta_receber_id) for item in aplicacoes]
    contas_por_id = _buscar_contas_aplicacao(
        db,
        tenant_id=tenant_id,
        parceiro_id=int(payload.parceiro_id),
        conta_ids=conta_ids,
    )

    forma_pagamento = None
    if modo_baixa == "acerto":
        forma_pagamento = _obter_ou_criar_forma_pagamento_acerto(
            db,
            tenant_id=tenant_id,
            user_id=user_id,
        )
    elif modo_baixa == "recebimento" and payload.forma_pagamento_id:
        forma_pagamento = _buscar_forma_pagamento_transferencia(
            db,
            tenant_id=tenant_id,
            forma_pagamento_id=payload.forma_pagamento_id,
        )

    if modo_baixa == "produto_devolvido" and not payload.devolver_estoque:
        if not _texto_limpo(payload.observacao):
            raise HTTPException(
                status_code=400,
                detail=(
                    "Informe uma observacao quando produto devolvido nao volta "
                    "para o estoque."
                ),
            )

    total_baixado = Decimal("0.00")
    recebimentos_criados: list[int] = []
    movimentacoes_estoque: list[int] = []
    lancamentos_dre: list[tuple[int | None, Decimal, date, str]] = []
    resultados = []

    data_financeira = resolver_data_recebimento_financeiro(
        payload.data_recebimento,
        forma_pagamento,
    )
    documento_lote = f"TRP-LOTE-{datetime.now().strftime('%Y%m%d%H%M%S')}"

    for item in aplicacoes:
        conta = contas_por_id[int(item.conta_receber_id)]
        valor_baixado = decimal_monetario(item.valor_baixado)
        saldo_anterior = saldo_conta_receber_decimal(conta)
        if valor_baixado - saldo_anterior > CENTAVO:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"O valor informado ultrapassa o saldo da transferencia "
                    f"{conta.documento or conta.id}."
                ),
            )

        if modo_baixa == "produto_devolvido" and payload.devolver_estoque:
            validar_devolucao_estoque_integral(conta, valor_baixado)

        novo_recebido = decimal_monetario(conta.valor_recebido) + valor_baixado
        conta.valor_recebido = novo_recebido
        conta.status = (
            "recebido"
            if abs(decimal_monetario(conta.valor_final) - novo_recebido) <= CENTAVO
            else "parcial"
        )
        conta.data_recebimento = (
            data_financeira if modo_baixa == "recebimento" else payload.data_recebimento
        )
        if forma_pagamento:
            conta.forma_pagamento_id = forma_pagamento.id

        modo_label = _MODOS_BAIXA_LOTE[modo_baixa]
        detalhe_forma = (
            f" | Forma: {forma_pagamento.nome}" if forma_pagamento else ""
        )
        detalhe_obs = f" - {payload.observacao.strip()}" if _texto_limpo(payload.observacao) else ""
        historico = (
            f"{modo_label} em lote {payload.data_recebimento.strftime('%d/%m/%Y')}: "
            f"R$ {float(valor_baixado):.2f}{detalhe_forma}{detalhe_obs}"
        )
        _append_observacao(conta, historico)

        if modo_baixa in {"recebimento", "acerto"}:
            recebimento = Recebimento(
                conta_receber_id=conta.id,
                forma_pagamento_id=getattr(forma_pagamento, "id", None),
                valor_recebido=valor_baixado,
                data_recebimento=conta.data_recebimento,
                observacoes=historico,
                user_id=user_id,
                tenant_id=str(tenant_id),
            )
            db.add(recebimento)
            db.flush()
            recebimentos_criados.append(recebimento.id)

        if modo_baixa == "recebimento":
            _registrar_lancamento_financeiro(
                db,
                conta=conta,
                valor=valor_baixado,
                data_recebimento=conta.data_recebimento,
                forma_pagamento=forma_pagamento,
                user_id=user_id,
                tenant_id=tenant_id,
                historico=historico,
            )
            lancamentos_dre.append(
                (
                    conta.dre_subcategoria_id,
                    valor_baixado,
                    conta.data_recebimento,
                    conta.canal,
                )
            )

        if modo_baixa == "produto_devolvido" and payload.devolver_estoque:
            movimentacoes_estoque.extend(
                _estornar_estoque_transferencia(
                    db,
                    conta=conta,
                    user_id=user_id,
                    tenant_id=tenant_id,
                    observacao=historico,
                )
            )

        status_resolvido, status_label = _status_transferencia_parceiro(conta)
        total_baixado += valor_baixado
        resultados.append(
            {
                "conta_receber_id": conta.id,
                "documento": conta.documento,
                "valor_baixado": float(valor_baixado),
                "saldo_restante": _saldo_conta_receber(conta),
                "status": status_resolvido,
                "status_label": status_label,
            }
        )

    pagamentos_criados = []
    contas_pagar_criadas = []
    if modo_baixa == "acerto":
        compensacoes_payload = list(payload.compensacoes or [])
        if nova_conta_pagar_acerto:
            conta_pagar_criada = criar_conta_pagar_acerto_lote(
                db,
                tenant_id=tenant_id,
                parceiro_id=int(payload.parceiro_id),
                user_id=user_id,
                data_emissao=payload.data_recebimento,
                payload=nova_conta_pagar_acerto,
                documento_lote=documento_lote,
            )
            contas_pagar_criadas.append(conta_pagar_criada.id)
            compensacoes_payload.append(
                {
                    "conta_pagar_id": conta_pagar_criada.id,
                    "valor_compensado": float(
                        valor_conta_pagar_acerto_payload(nova_conta_pagar_acerto)
                    ),
                }
            )

        pagamentos_criados = aplicar_compensacoes_acerto_lote(
            db,
            tenant_id=tenant_id,
            parceiro_id=int(payload.parceiro_id),
            user_id=user_id,
            data_pagamento=payload.data_recebimento,
            forma_pagamento=forma_pagamento,
            compensacoes_payload=compensacoes_payload,
            total_baixa=total_baixado.quantize(CENTAVO),
            documento_lote=documento_lote,
        )

    return {
        "sucesso": True,
        "modo_baixa": modo_baixa,
        "total_baixado": float(total_baixado.quantize(CENTAVO)),
        "total_itens": len(resultados),
        "items": resultados,
        "recebimentos_criados": recebimentos_criados,
        "pagamentos_criados": pagamentos_criados,
        "contas_pagar_criadas": contas_pagar_criadas,
        "movimentacoes_estoque": movimentacoes_estoque,
        "_dre_lancamentos": lancamentos_dre,
    }


def atualizar_dre_baixa_lote(db: Session, *, tenant_id, lancamentos: list[tuple]) -> None:
    for dre_subcategoria_id, valor, data_lancamento, canal in lancamentos:
        if not dre_subcategoria_id:
            continue
        try:
            atualizar_dre_por_lancamento(
                db=db,
                tenant_id=tenant_id,
                dre_subcategoria_id=dre_subcategoria_id,
                canal=canal,
                valor=valor,
                data_lancamento=data_lancamento,
                tipo_movimentacao="RECEITA",
            )
        except Exception as exc:
            logger.warning("Erro ao atualizar DRE da baixa em lote: %s", exc)
