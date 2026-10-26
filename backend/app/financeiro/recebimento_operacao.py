"""Destino de uma baixa: caixa, banco e repasse de cartão, sem commit parcial."""

from datetime import datetime, timedelta
from decimal import Decimal

from fastapi import HTTPException

from app.caixa.escopo import buscar_caixa_para_recebimento
from app.caixa_models import MovimentacaoCaixa
from app.financeiro.crediario_parcelamento import distribuir_valor_parcelas
from app.financeiro_models import (
    ContaBancaria,
    ContaReceber,
    FormaPagamento,
    MovimentacaoFinanceira,
)
from app.ia.aba5_models import FluxoCaixa
from app.services.card_fee_service import CardFeeConfigurationError, resolve_card_fee


TIPOS_CARTAO = {"cartao_credito", "cartao_debito", "link_pagamento"}


def preparar_destino_recebimento(db, *, dados, tenant_id, usuario):
    """Bloqueia o caixa antes das vendas, na mesma ordem do fechamento/PDV."""
    caixa, _ = buscar_caixa_para_recebimento(
        db,
        tenant_id=tenant_id,
        usuario_id=usuario.id,
        caixa_id=dados.caixa_id,
        bloquear_caixa=True,
    )
    if not caixa:
        raise HTTPException(400, "Abra um caixa antes de registrar o recebimento.")
    forma = None
    if dados.forma_pagamento_id:
        forma = (
            db.query(FormaPagamento)
            .filter(
                FormaPagamento.id == dados.forma_pagamento_id,
                FormaPagamento.tenant_id == tenant_id,
                FormaPagamento.ativo.is_(True),
            )
            .first()
        )
        if not forma:
            raise HTTPException(400, "Forma de pagamento inexistente ou inativa.")
        if forma.tipo in {"crediario", "boleto", "cashback", "credito_cliente"}:
            raise HTTPException(
                400,
                "Selecione uma forma de recebimento efetivo para dar baixa nesta conta.",
            )
    tipo = forma.tipo if forma else "outro"
    if dados.numero_parcelas > 1 and tipo not in {"cartao_credito", "link_pagamento"}:
        raise HTTPException(
            400,
            "O parcelamento de recebimentos está disponível para cartão de crédito.",
        )
    banco = None
    if dados.conta_bancaria_id:
        banco = (
            db.query(ContaBancaria)
            .filter(
                ContaBancaria.id == dados.conta_bancaria_id,
                ContaBancaria.tenant_id == tenant_id,
                ContaBancaria.ativa.is_(True),
            )
            .populate_existing()
            .with_for_update()
            .first()
        )
        if not banco:
            raise HTTPException(400, "Conta bancária inexistente ou inativa.")
    return {"caixa": caixa, "forma": forma, "banco": banco, "tipo": tipo}


def registrar_efeitos_recebimento(
    db, *, conta, recebimento, dados, destino, usuario, tenant_id
):
    """O recibo quita o cliente; parcelas de cartão pertencem à operadora."""
    from app.clientes.baixas_lote_service import atualizar_previsao

    caixa, forma, banco, tipo = (
        destino[k] for k in ("caixa", "forma", "banco", "tipo")
    )
    instante = datetime.combine(recebimento.data_recebimento, datetime.min.time())
    recebimento.caixa_id = caixa.id
    recebimento.conta_bancaria_id = banco.id if banco else None
    recebimento.numero_parcelas = dados.numero_parcelas
    recebimento.operadora_id = dados.operadora_id
    recebimento.bandeira = dados.bandeira
    recebimento.nsu_cartao = dados.nsu_cartao
    db.flush()
    referencia = f"RECEBIMENTO-{recebimento.id}"
    nome_usuario = usuario.nome or getattr(usuario, "email", None) or "Usuário"
    descricao = f"Recebimento #{recebimento.id} - {conta.descricao}"
    db.add(
        MovimentacaoCaixa(
            tenant_id=tenant_id,
            caixa_id=caixa.id,
            tipo="venda" if tipo == "dinheiro" else "recebimento",
            categoria="recebimento_conta",
            valor=recebimento.valor_recebido,
            forma_pagamento="dinheiro"
            if tipo == "dinheiro"
            else (forma.nome if forma else "Outro"),
            descricao=descricao,
            documento=referencia,
            venda_id=conta.venda_id,
            usuario_id=usuario.id,
            usuario_nome=nome_usuario,
            data_movimento=instante,
        )
    )
    if tipo in TIPOS_CARTAO:
        modalidade = "debito" if tipo == "cartao_debito" else "credito"
        try:
            taxa = destino.get("taxa_cartao") or resolve_card_fee(
                db,
                tenant_id=tenant_id,
                valor=destino.get("valor_total_receber", recebimento.valor_recebido),
                forma_pagamento_id=forma.id,
                operadora_id=dados.operadora_id,
                bandeira=dados.bandeira,
                modalidade=modalidade,
                parcelas=dados.numero_parcelas,
                strict=True,
            )
        except CardFeeConfigurationError as exc:
            raise HTTPException(400, str(exc)) from exc
        recebimento.operadora_id, recebimento.bandeira = (
            taxa.operadora_id,
            taxa.bandeira,
        )
        if not destino.get("nsu_validado"):
            from app.financeiro.recebimento_nsu import validar_nsu_recebimento

            validar_nsu_recebimento(
                db,
                tenant_id=tenant_id,
                operadora_id=taxa.operadora_id,
                nsu=dados.nsu_cartao,
                recebimento_ids=(recebimento.id,),
            )
            destino["nsu_validado"] = True
        destino["taxa_cartao"] = taxa
        total = destino.get("valor_total_receber", recebimento.valor_recebido)
        recebido_antes = destino.get("valor_rateado", Decimal("0.00"))
        taxa_antes = destino.get("taxa_rateada", Decimal("0.00"))
        parcela_taxa = (
            taxa.valor_taxa - taxa_antes
            if recebido_antes + recebimento.valor_recebido >= total
            else (taxa.valor_taxa * recebimento.valor_recebido / total).quantize(
                Decimal("0.01")
            )
        )
        destino["valor_rateado"] = recebido_antes + recebimento.valor_recebido
        destino["taxa_rateada"] = taxa_antes + parcela_taxa
        valores = distribuir_valor_parcelas(
            recebimento.valor_recebido, dados.numero_parcelas
        )
        liquidos = distribuir_valor_parcelas(
            recebimento.valor_recebido - parcela_taxa, dados.numero_parcelas
        )
        primeira_data = recebimento.data_recebimento + timedelta(
            days=taxa.prazo_recebimento_dias
        )
        for indice, (valor, liquido) in enumerate(
            zip(valores, liquidos, strict=True), 1
        ):
            repasse = ContaReceber(
                tenant_id=tenant_id,
                cliente_id=conta.cliente_id,
                user_id=usuario.id,
                descricao=f"Repasse de cartão - recebimento #{recebimento.id} - {indice}/{dados.numero_parcelas}",
                forma_pagamento_id=forma.id,
                categoria_id=conta.categoria_id,
                dre_subcategoria_id=conta.dre_subcategoria_id,
                canal=conta.canal,
                valor_original=valor,
                valor_final=valor,
                valor_recebido=0,
                valor_liquido_estimado=liquido,
                data_emissao=recebimento.data_recebimento,
                data_vencimento=primeira_data + timedelta(days=30 * (indice - 1)),
                status="pendente",
                eh_parcelado=dados.numero_parcelas > 1,
                numero_parcela=indice,
                total_parcelas=dados.numero_parcelas,
                conta_principal_id=conta.id,
                documento=referencia,
                nsu=dados.nsu_cartao,
                observacoes=recebimento.observacoes,
            )
            # Sem venda_id: receber um repasse não é novo pagamento da venda.
            db.add(repasse)
            db.flush()
            atualizar_previsao(
                db,
                tenant_id=tenant_id,
                conta=repasse,
                user_id=usuario.id,
                instante=instante,
            )
    else:
        db.add(
            FluxoCaixa(
                tenant_id=tenant_id,
                usuario_id=usuario.id,
                tipo="entrada",
                categoria="Recebimento de conta",
                descricao=descricao,
                valor=recebimento.valor_recebido,
                data_movimentacao=instante,
                status="realizado",
                origem_tipo="recebimento",
                origem_id=recebimento.id,
            )
        )
        if banco and tipo != "dinheiro":
            db.add(
                MovimentacaoFinanceira(
                    tenant_id=tenant_id,
                    user_id=usuario.id,
                    conta_bancaria_id=banco.id,
                    forma_pagamento_id=forma.id if forma else None,
                    categoria_id=conta.categoria_id,
                    tipo="entrada",
                    status="realizado",
                    valor=recebimento.valor_recebido,
                    data_movimento=instante,
                    origem_tipo="recebimento",
                    origem_id=recebimento.id,
                    documento=referencia,
                    descricao=descricao,
                    observacoes=recebimento.observacoes,
                )
            )
            banco.saldo_atual = (
                Decimal(str(banco.saldo_atual or 0)) + recebimento.valor_recebido
            )
    atualizar_previsao(
        db, tenant_id=tenant_id, conta=conta, user_id=usuario.id, instante=instante
    )
