"""Registra o pagamento rateado com as regras de cartão do próprio PDV."""

from fastapi import HTTPException

from app.vendas_models import VendaPagamento
from app.clientes.baixas_lote_service import moeda as _money


def registrar_pagamento_lote(
    *,
    db,
    venda,
    requisicao,
    valor_aplicar,
    valor_total,
    valor_restante,
    taxa_total_lote,
    taxa_distribuida,
    caixa_aberto,
    lote,
    current_user,
    tenant_id,
    instante_recebimento,
    forma_pagamento,
    numero_transacao,
):
    dados_cartao = requisicao.get("forma_pagamento_id") is not None
    if dados_cartao:
        from app.financeiro_models import FormaPagamento

        forma = (
            db.query(FormaPagamento)
            .filter(
                FormaPagamento.id == requisicao["forma_pagamento_id"],
                FormaPagamento.tenant_id == tenant_id,
                FormaPagamento.ativo.is_(True),
            )
            .first()
        )
        if not forma or forma.tipo in {
            "crediario",
            "boleto",
            "cashback",
            "credito_cliente",
        }:
            raise HTTPException(400, "Selecione uma forma de recebimento ativa.")
        dados_cartao = forma.tipo in {
            "cartao_credito",
            "cartao_debito",
            "link_pagamento",
        }
    if requisicao.get("numero_parcelas", 1) > 1 and not dados_cartao:
        raise HTTPException(
            400, "O parcelamento de recebimentos exige cartão de crédito."
        )
    if dados_cartao:
        from app.vendas.finalizacao_pagamentos import (
            processar_pagamentos_finalizacao,
        )

        processar_pagamentos_finalizacao(
            venda=venda,
            pagamentos=[
                {
                    **{
                        k: requisicao.get(k)
                        for k in (
                            "forma_pagamento_id",
                            "operadora_id",
                            "bandeira",
                            "nsu_cartao",
                        )
                    },
                    "forma_pagamento": forma.nome,
                    "valor": valor_aplicar,
                    "numero_parcelas": requisicao.get("numero_parcelas", 1),
                }
            ],
            user_id=current_user.id,
            user_nome=current_user.nome or current_user.email,
            tenant_id=tenant_id,
            db=db,
            caixa_aberto_id=caixa_aberto.id,
            data_ocorrencia=instante_recebimento,
            baixa_lote_id=lote.id,
        )
        pagamento = (
            db.query(VendaPagamento)
            .filter_by(venda_id=venda.id, tenant_id=tenant_id)
            .order_by(VendaPagamento.id.desc())
            .first()
        )
        pagamento.baixa_lote_id = lote.id
        pagamento.status = "confirmado"
        # Uma transação rateada entre vendas paga a taxa fixa uma vez.
        if taxa_total_lote is None:
            from app.services.card_fee_service import resolve_card_fee

            taxa_total_lote = resolve_card_fee(
                db,
                tenant_id=tenant_id,
                valor=valor_total,
                forma_pagamento_id=forma.id,
                operadora_id=pagamento.operadora_id,
                bandeira=pagamento.bandeira,
                modalidade=pagamento.modalidade_cartao,
                parcelas=pagamento.numero_parcelas,
                strict=True,
            )
        valor_taxa = (
            taxa_total_lote.valor_taxa - taxa_distribuida
            if valor_restante <= valor_aplicar
            else _money(taxa_total_lote.valor_taxa * valor_aplicar / valor_total)
        )
        taxa_distribuida += valor_taxa
        pagamento.valor_taxa_prevista = valor_taxa
        pagamento.valor_liquido_previsto = valor_aplicar - valor_taxa
        pagamento.taxa_fixa_aplicada = _money(
            taxa_total_lote.taxa_fixa * valor_aplicar / valor_total
        )
    else:
        pagamento = VendaPagamento(
            venda_id=venda.id,
            caixa_id=caixa_aberto.id,
            tenant_id=tenant_id,  # ✅ Garantir isolamento entre empresas
            forma_pagamento=forma_pagamento,
            forma_pagamento_id=requisicao.get("forma_pagamento_id"),
            valor=valor_aplicar,
            numero_transacao=numero_transacao,
            status="confirmado",
            data_pagamento=instante_recebimento,
            baixa_lote_id=lote.id,
        )
        db.add(pagamento)

    return pagamento, dados_cartao, taxa_total_lote, taxa_distribuida
