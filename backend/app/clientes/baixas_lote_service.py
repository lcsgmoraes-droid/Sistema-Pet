"""Identidade do recebimento e contrapartidas do estorno, numa só transação.

Os originais permanecem no caixa/data de origem. A correção registra valores
negativos no caixa atual; assim não reescreve um fechamento já conferido.
"""

from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from uuid import UUID, uuid4

from fastapi import HTTPException
from sqlalchemy import func, or_
from sqlalchemy.orm import selectinload

from app.audit_log import log_action
from app.caixa.escopo import buscar_caixa_aberto
from app.caixa.service import CaixaService
from app.caixa_models import MovimentacaoCaixa
from app.financeiro_models import ContaReceber, MovimentacaoFinanceira, Recebimento
from app.ia.aba5_models import FluxoCaixa
from app.services.venda_rentabilidade_snapshot_service import (
    invalidate_venda_rentabilidade_snapshot,
)
from app.utils.timezone import now_brasilia
from app.vendas.status_pagamento import calcular_resumo_pagamento_venda
from app.vendas_models import Venda, VendaBaixaLote, VendaBaixaLoteItem, VendaPagamento


def moeda(value):
    return Decimal(str(value or 0)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def nome_usuario(user):
    return (
        user.nome
        or getattr(user, "username", None)
        or getattr(user, "email", None)
        or "Usuário"
    )[:200]


def normalizar_requisicao(dados):
    try:
        ids = dados.get("vendas_ids")
        if not isinstance(ids, list) or not 1 <= len(ids) <= 200:
            raise ValueError()
        if any(type(i) is not int or i <= 0 for i in ids) or len(set(ids)) != len(ids):
            raise ValueError()
        valor = Decimal(str(dados.get("valor_total", 0)))
        if not valor.is_finite() or valor <= 0 or valor > Decimal("99999999.99"):
            raise ValueError()
        valor = moeda(valor)
        forma = str(dados.get("forma_pagamento") or "").strip()
        if (
            not forma
            or len(forma) > 50
            or forma.casefold()
            in {"cashback", "credito_cliente", "crediario", "crediário", "boleto"}
        ):
            raise ValueError()
        transacao = str(dados.get("numero_transacao") or "").strip() or None
        if transacao and len(transacao) > 100:
            raise ValueError()
        observacoes = str(dados.get("observacoes") or "").strip() or None
        if observacoes and len(observacoes) > 2000:
            raise ValueError()
        request_id = (
            str(UUID(str(dados["request_id"])))
            if dados.get("request_id")
            else str(uuid4())
        )
    except (ValueError, TypeError, InvalidOperation):
        raise HTTPException(
            422,
            "Informe vendas válidas, valor positivo, forma de recebimento e uma identificação válida da operação.",
        )
    return request_id, {
        "vendas_ids": sorted(ids),
        "valor_total": str(valor),
        "forma_pagamento": forma,
        "numero_transacao": transacao,
        "observacoes": observacoes,
    }


def buscar_repeticao(db, *, tenant_id, cliente_id, request_id, requisicao):
    anterior = (
        db.query(VendaBaixaLote)
        .filter_by(tenant_id=tenant_id, request_id=request_id)
        .first()
    )
    if anterior:
        if anterior.cliente_id != cliente_id or anterior.requisicao != requisicao:
            raise HTTPException(
                409, "Esta identificação já foi utilizada para outro recebimento."
            )
        return anterior
    return None


def preparar_lote(
    db, *, tenant_id, cliente_id, current_user, caixa, request_id, requisicao
):
    anterior = buscar_repeticao(
        db,
        tenant_id=tenant_id,
        cliente_id=cliente_id,
        request_id=request_id,
        requisicao=requisicao,
    )
    if anterior:
        return anterior, True
    lote = VendaBaixaLote(
        tenant_id=tenant_id,
        cliente_id=cliente_id,
        caixa_id=caixa.id,
        usuario_id=current_user.id,
        usuario_nome=nome_usuario(current_user),
        request_id=request_id,
        requisicao=requisicao,
        valor_total=moeda(requisicao["valor_total"]),
        forma_pagamento=requisicao["forma_pagamento"],
        numero_transacao=requisicao["numero_transacao"],
        observacoes=requisicao["observacoes"],
        data=now_brasilia(),
        status="confirmado",
    )
    db.add(lote)
    db.flush()
    return lote, False


def atualizar_previsao(db, *, tenant_id, conta, user_id, instante):
    """Uma previsão por saldo, sem acumular previsões de baixas parciais."""
    anteriores = (
        db.query(FluxoCaixa)
        .filter_by(
            tenant_id=tenant_id,
            origem_tipo="conta_receber",
            origem_id=conta.id,
            status="previsto",
        )
        .order_by(FluxoCaixa.id)
        .with_for_update()
        .all()
    )
    data = next((f.data_prevista for f in anteriores if f.data_prevista), None)
    for fluxo in anteriores:
        fluxo.status = "cancelado"
    saldo = moeda(conta.valor_final) - moeda(conta.valor_recebido)
    if saldo <= 0:
        return None
    if data is None:
        vencimento = conta.data_vencimento
        data = (
            datetime.combine(vencimento, datetime.min.time())
            if vencimento
            else instante + timedelta(days=30)
        )
    fluxo = FluxoCaixa(
        tenant_id=tenant_id,
        usuario_id=user_id,
        tipo="entrada",
        categoria="Recebimento de Venda",
        descricao=f"Saldo previsto - {conta.descricao}",
        valor=saldo,
        data_movimentacao=None,
        data_prevista=data,
        status="previsto",
        origem_tipo="conta_receber",
        origem_id=conta.id,
    )
    db.add(fluxo)
    return fluxo


def registrar_item(
    db,
    *,
    lote,
    venda,
    pagamento,
    conta,
    recebimento,
    movimento,
    fluxo,
    previsao,
    evento,
    status_anterior,
):
    pagamento.baixa_lote_id = lote.id
    db.flush()
    soma_recibos = (
        db.query(func.sum(Recebimento.valor_recebido))
        .filter_by(tenant_id=lote.tenant_id, conta_receber_id=conta.id)
        .scalar()
    )
    db.add(
        VendaBaixaLoteItem(
            tenant_id=lote.tenant_id,
            lote_id=lote.id,
            venda_id=venda.id,
            numero_venda=venda.numero_venda,
            valor=pagamento.valor,
            pagamento_id=pagamento.id,
            efeitos={
                "venda_total": str(moeda(venda.total)),
                "status_venda_anterior": status_anterior,
                "conta_id": conta.id,
                "recebimento_id": recebimento.id,
                "saldo_sem_recibos": str(
                    moeda(conta.valor_recebido) - moeda(soma_recibos)
                ),
                "movimento_id": movimento.id if movimento else None,
                "fluxo_id": fluxo.id,
                "previsao_id": previsao.id if previsao else None,
                "evento_id": evento.id if evento else None,
            },
        )
    )


def auditar_lote(db, lote, user, action):
    log_action(
        db=db,
        tenant_id=lote.tenant_id,
        user_id=user.id,
        action=action,
        entity_type="vendas_baixas_lotes",
        entity_id=lote.id,
        commit=False,
        new_value=lote.to_dict(),
        details=f"{action}: baixa em lote #{lote.id}",
    )


def listar_lotes(db, tenant_id, cliente_id, page, per_page):
    query = db.query(VendaBaixaLote).filter_by(
        tenant_id=tenant_id, cliente_id=cliente_id
    )
    total = query.count()
    lotes = (
        query.options(selectinload(VendaBaixaLote.itens))
        .order_by(VendaBaixaLote.id.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )
    return {
        "itens": [lote.to_dict() for lote in lotes],
        "total": total,
        "page": page,
        "per_page": per_page,
    }


def _bloquear(motivo):
    raise HTTPException(
        409,
        f"Não foi possível estornar o lançamento: {motivo}. Nenhum valor foi alterado.",
    )


def _obter_efeitos(db, lote, item, venda):
    """Valida os vínculos e todos os saldos antes da primeira contrapartida."""
    e = item.efeitos
    if (
        not venda
        or venda.cliente_id != lote.cliente_id
        or moeda(venda.total) != moeda(e["venda_total"])
    ):
        _bloquear("a venda foi alterada; confira seus itens e valores")
    if venda.status not in {"aberta", "baixa_parcial", "finalizada", "pago_nf"}:
        _bloquear("há venda cancelada ou devolvida; confira os lançamentos posteriores")
    pagamento = (
        db.query(VendaPagamento)
        .filter_by(
            id=item.pagamento_id,
            tenant_id=lote.tenant_id,
            venda_id=item.venda_id,
            baixa_lote_id=lote.id,
        )
        .populate_existing()
        .with_for_update()
        .first()
    )
    if (
        not pagamento
        or moeda(pagamento.valor) != moeda(item.valor)
        or pagamento.status in {"estornado", "cancelado", "recusado"}
    ):
        _bloquear("o pagamento original está ausente ou divergente")
    if (
        pagamento.gateway_payment_id
        or pagamento.gateway_provider
        or pagamento.status_conciliacao == "conciliado"
        or moeda(pagamento.valor_taxa_prevista) > 0
    ):
        _bloquear(
            "o pagamento tem conciliação, taxa ou operadora vinculada; desfaça esse vínculo no financeiro primeiro"
        )
    from app.comissoes_models import ComissaoItem

    ids_pagamentos = [
        ident
        for (ident,) in db.query(VendaPagamento.id)
        .filter_by(tenant_id=lote.tenant_id, venda_id=venda.id)
        .order_by(VendaPagamento.data_pagamento, VendaPagamento.id)
        .all()
    ]
    parcela = ids_pagamentos.index(pagamento.id) + 1
    comissao = (
        db.query(ComissaoItem.id)
        .filter(
            ComissaoItem.tenant_id == lote.tenant_id,
            ComissaoItem.venda_id == venda.id,
            or_(
                ComissaoItem.parcela_numero == parcela,
                ComissaoItem.parcela_numero.is_(None),
            ),
            ComissaoItem.status != "estornado",
        )
        .first()
    )
    if comissao:
        _bloquear(
            "foi gerada comissão sobre esse pagamento; estorne essa comissão antes da baixa"
        )
    conta = (
        db.query(ContaReceber)
        .filter_by(id=e["conta_id"], tenant_id=lote.tenant_id, venda_id=venda.id)
        .populate_existing()
        .with_for_update()
        .first()
    )
    if not conta or conta.status in {"cancelado", "cancelada"}:
        _bloquear("a conta a receber original foi cancelada ou removida")
    if (
        conta.conciliado
        or conta.conciliacao_recebimento_id
        or conta.conciliacao_lote_id
        or conta.validacao_id
        or conta.data_liquidacao
        or conta.status_conciliacao not in (None, "prevista")
    ):
        _bloquear(
            "o recebimento já participou de conciliação financeira; desfaça a conciliação primeiro"
        )
    bancaria = (
        db.query(MovimentacaoFinanceira.id)
        .filter(
            MovimentacaoFinanceira.tenant_id == lote.tenant_id,
            MovimentacaoFinanceira.status != "cancelado",
            or_(
                (MovimentacaoFinanceira.origem_tipo == "conta_receber")
                & (MovimentacaoFinanceira.origem_id == conta.id),
                (MovimentacaoFinanceira.origem_tipo == "venda")
                & (MovimentacaoFinanceira.origem_id == venda.id),
            ),
        )
        .first()
    )
    if bancaria:
        _bloquear(
            "há movimento bancário posterior vinculado; estorne esse movimento no financeiro primeiro"
        )
    recebimento = (
        db.query(Recebimento)
        .filter_by(
            id=e["recebimento_id"], tenant_id=lote.tenant_id, conta_receber_id=conta.id
        )
        .with_for_update()
        .first()
    )
    recebido = (
        db.query(func.sum(Recebimento.valor_recebido))
        .filter_by(tenant_id=lote.tenant_id, conta_receber_id=conta.id)
        .scalar()
    )
    if (
        not recebimento
        or moeda(recebimento.valor_recebido) != moeda(item.valor)
        or moeda(conta.valor_recebido)
        != moeda(recebido) + moeda(e.get("saldo_sem_recibos"))
        or moeda(conta.valor_recebido) < moeda(item.valor)
    ):
        _bloquear("o saldo da conta não corresponde aos recebimentos registrados")
    fluxo = (
        db.query(FluxoCaixa)
        .filter_by(
            id=e["fluxo_id"],
            tenant_id=lote.tenant_id,
            origem_tipo="conta_receber",
            origem_id=conta.id,
            status="realizado",
        )
        .with_for_update()
        .first()
    )
    if not fluxo or moeda(fluxo.valor) != moeda(item.valor) or fluxo.tipo != "entrada":
        _bloquear("o movimento original no fluxo de caixa está ausente ou divergente")
    if e.get("movimento_id"):
        movimento = (
            db.query(MovimentacaoCaixa)
            .filter_by(
                id=e["movimento_id"],
                tenant_id=lote.tenant_id,
                caixa_id=lote.caixa_id,
                venda_id=venda.id,
                tipo="venda",
            )
            .with_for_update()
            .first()
        )
        if not movimento or moeda(movimento.valor) != moeda(item.valor):
            _bloquear("a entrada original no caixa está ausente ou divergente")
    return pagamento, conta, recebimento


def estornar_lote(db, *, tenant_id, cliente_id, lote_id, current_user, motivo):
    motivo = str(motivo or "").strip()
    if not 5 <= len(motivo) <= 500:
        raise HTTPException(422, "Informe o motivo do estorno com 5 a 500 caracteres.")
    # Idempotência também após o caixa ter sido fechado: consulta antes do lock.
    lote = (
        db.query(VendaBaixaLote)
        .filter_by(id=lote_id, tenant_id=tenant_id, cliente_id=cliente_id)
        .first()
    )
    if not lote:
        raise HTTPException(404, "Lançamento em lote não encontrado.")
    if lote.status == "estornado":
        return lote.to_dict()
    caixa, _ = buscar_caixa_aberto(
        db, tenant_id=tenant_id, usuario_id=current_user.id, bloquear_caixa=True
    )
    if not caixa:
        raise HTTPException(
            400,
            "Abra o caixa para registrar o estorno. O fechamento original será preservado.",
        )
    # Ordem comum aos recebimentos: Caixa -> Lote -> Vendas -> Clientes/campanhas.
    lote = (
        db.query(VendaBaixaLote)
        .filter_by(id=lote_id, tenant_id=tenant_id, cliente_id=cliente_id)
        .populate_existing()
        .with_for_update()
        .one()
    )
    if lote.status == "estornado":
        return lote.to_dict()
    itens = (
        db.query(VendaBaixaLoteItem)
        .filter_by(tenant_id=tenant_id, lote_id=lote.id)
        .order_by(VendaBaixaLoteItem.venda_id)
        .all()
    )
    if not itens or sum((moeda(i.valor) for i in itens), Decimal("0")) != moeda(
        lote.valor_total
    ):
        _bloquear("o rateio do lançamento não corresponde ao valor recebido")
    vendas = {
        v.id: v
        for v in db.query(Venda)
        .filter(Venda.tenant_id == tenant_id, Venda.id.in_([i.venda_id for i in itens]))
        .order_by(Venda.id)
        .populate_existing()
        .with_for_update()
        .all()
    }
    efeitos = [
        (i, vendas.get(i.venda_id), _obter_efeitos(db, lote, i, vendas.get(i.venda_id)))
        for i in itens
    ]
    from app.campaigns.baixa_lote_reversal import estornar_beneficios_baixa_lote

    instante = now_brasilia()
    for item, venda, (pagamento, conta, recebimento) in efeitos:
        if item.efeitos.get("evento_id"):
            estornar_beneficios_baixa_lote(
                db, tenant_id, venda.id, item.efeitos["evento_id"], motivo
            )
        contraparte = VendaPagamento(
            tenant_id=tenant_id,
            venda_id=venda.id,
            baixa_lote_id=lote.id,
            caixa_id=caixa.id,
            forma_pagamento=pagamento.forma_pagamento,
            forma_pagamento_id=pagamento.forma_pagamento_id,
            valor=-moeda(item.valor),
            status="confirmado",
            data_pagamento=instante,
            numero_transacao=f"ESTORNO-LOTE-{lote.id}",
        )
        db.add(contraparte)
        if CaixaService.eh_forma_dinheiro(pagamento.forma_pagamento):
            db.add(
                MovimentacaoCaixa(
                    tenant_id=tenant_id,
                    caixa_id=caixa.id,
                    venda_id=venda.id,
                    tipo="devolucao",
                    categoria="estorno_baixa_lote",
                    valor=moeda(item.valor),
                    forma_pagamento=pagamento.forma_pagamento,
                    documento=f"ESTORNO-LOTE-{lote.id}",
                    descricao=f"Estorno da baixa em lote #{lote.id} - venda {venda.numero_venda}: {motivo}",
                    usuario_id=current_user.id,
                    usuario_nome=nome_usuario(current_user),
                    data_movimento=instante,
                )
            )
        db.add(
            Recebimento(
                tenant_id=tenant_id,
                conta_receber_id=conta.id,
                forma_pagamento_id=recebimento.forma_pagamento_id,
                valor_recebido=-moeda(item.valor),
                data_recebimento=instante.date(),
                observacoes=f"Estorno da baixa em lote #{lote.id}: {motivo}",
                user_id=current_user.id,
            )
        )
        db.add(
            FluxoCaixa(
                tenant_id=tenant_id,
                usuario_id=current_user.id,
                tipo="entrada",
                categoria="Estorno de recebimento",
                descricao=f"Estorno da baixa em lote #{lote.id} - venda {venda.numero_venda}",
                valor=-moeda(item.valor),
                data_movimentacao=instante,
                status="realizado",
                origem_tipo="conta_receber",
                origem_id=conta.id,
            )
        )
        conta.valor_recebido = moeda(conta.valor_recebido) - moeda(item.valor)
        conta.status = "parcial" if conta.valor_recebido > 0 else "pendente"
        conta.data_recebimento = instante.date() if conta.valor_recebido > 0 else None
        atualizar_previsao(
            db,
            tenant_id=tenant_id,
            conta=conta,
            user_id=current_user.id,
            instante=instante,
        )
        db.flush()
        item.pagamento_estorno_id = contraparte.id
        pagamentos = (
            db.query(VendaPagamento)
            .filter_by(venda_id=venda.id, tenant_id=tenant_id)
            .all()
        )
        resumo = calcular_resumo_pagamento_venda(
            total=venda.total,
            pagamentos=pagamentos,
            contas_receber=venda.contas_receber,
        )
        # Documento fiscal e venda permanecem; somente a situação do recebimento muda.
        if venda.status != "pago_nf":
            venda.status = "baixa_parcial" if resumo["valor_pago"] > 0 else "aberta"
        invalidate_venda_rentabilidade_snapshot(venda)
    lote.status = "estornado"
    lote.estornado_em = instante
    lote.estornado_por_id = current_user.id
    lote.estornado_por_nome = nome_usuario(current_user)
    lote.caixa_estorno_id = caixa.id
    lote.motivo_estorno = motivo
    db.flush()
    db.expire(lote, ["itens"])
    auditar_lote(db, lote, current_user, "estornar_baixa_lote")
    return lote.to_dict()
