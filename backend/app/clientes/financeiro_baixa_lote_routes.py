"""Rotas de baixa financeira em lote de clientes."""

import logging
from datetime import datetime as dt, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user_and_tenant
from app.clientes.common import _validar_tenant_e_obter_usuario
from app.db import get_session
from app.services.venda_rentabilidade_snapshot_service import (
    get_or_build_venda_rentabilidade_snapshot,
)


logger = logging.getLogger(__name__)
router = APIRouter()

__all__ = ["baixar_vendas_lote", "router"]


@router.post("/{cliente_id}/baixar-vendas-lote")
async def baixar_vendas_lote(
    cliente_id: int,
    dados: dict,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """DÃ¡ baixa em mÃºltiplas vendas de uma vez, gerando movimentaÃ§Ãµes no caixa e contas a receber"""
    try:
        current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)

        logger.info("\n=== BAIXAR VENDAS LOTE ===")
        logger.info(f"Cliente ID: {cliente_id}")
        logger.info(f"Dados recebidos: {dados}")

        from app.vendas_models import Venda, VendaPagamento
        from app.caixa_models import Caixa, MovimentacaoCaixa
        from app.financeiro_models import ContaReceber, Recebimento
        from app.ia.aba5_models import FluxoCaixa

        # Extrair dados do body
        vendas_ids = dados.get("vendas_ids", [])
        valor_total = float(dados.get("valor_total", 0))
        forma_pagamento = dados.get("forma_pagamento", "")
        numero_transacao = dados.get("numero_transacao")

        logger.info(f"Vendas IDs: {vendas_ids}")
        logger.info(f"Valor total: {valor_total}")
        logger.info(f"Forma pagamento: {forma_pagamento}")

        # Validar se hÃ¡ caixa aberto
        caixa_aberto = (
            db.query(Caixa)
            .filter(
                Caixa.usuario_id == current_user.id,
                Caixa.tenant_id == tenant_id,
                Caixa.status == "aberto",
            )
            .first()
        )

        logger.info(f"Caixa aberto: {caixa_aberto}")

        if not caixa_aberto:
            raise HTTPException(
                status_code=400,
                detail="NÃ£o hÃ¡ caixa aberto. Abra o caixa antes de dar baixa nas vendas.",
            )

        # Buscar vendas ordenadas da mais antiga para a mais nova
        vendas = (
            db.query(Venda)
            .filter(
                Venda.id.in_(vendas_ids),
                Venda.cliente_id == cliente_id,
                Venda.tenant_id == tenant_id,
                Venda.status.in_(["aberta", "baixa_parcial"]),
            )
            .order_by(Venda.data_venda.asc())
            .all()
        )  # Ordenar das mais antigas para as mais novas

        logger.info(f"Vendas encontradas: {len(vendas)}")

        if not vendas:
            raise HTTPException(status_code=404, detail="Nenhuma venda encontrada")

        if len(vendas) != len(vendas_ids):
            raise HTTPException(
                status_code=400,
                detail="Algumas vendas nÃ£o foram encontradas ou nÃ£o estÃ£o em aberto",
            )

        # Calcular saldo devedor de cada venda
        vendas_com_saldo = []
        total_saldo_devedor = 0

        for venda in vendas:
            valor_ja_pago = (
                sum(float(p.valor or 0) for p in venda.pagamentos)
                if venda.pagamentos
                else 0
            )
            saldo_devedor = float(venda.total or 0) - valor_ja_pago

            logger.info(
                f"Venda {venda.id}: Total={venda.total}, Pago={valor_ja_pago}, Saldo={saldo_devedor}"
            )

            if saldo_devedor > 0.01:  # TolerÃ¢ncia de 1 centavo
                vendas_com_saldo.append(
                    {
                        "venda": venda,
                        "saldo_devedor": saldo_devedor,
                        "valor_ja_pago": valor_ja_pago,
                    }
                )
                total_saldo_devedor += saldo_devedor

        logger.info(
            f"Vendas com saldo: {len(vendas_com_saldo)}, Total saldo: {total_saldo_devedor}"
        )

        if not vendas_com_saldo:
            raise HTTPException(
                status_code=400, detail="Todas as vendas jÃ¡ estÃ£o quitadas"
            )

        if valor_total > total_saldo_devedor + 0.01:
            raise HTTPException(
                status_code=400,
                detail=f"Valor do pagamento (R$ {valor_total:.2f}) excede o saldo devedor total (R$ {total_saldo_devedor:.2f})",
            )

        # Distribuir o valor proporcionalmente entre as vendas
        valor_restante = valor_total
        vendas_quitadas = []
        vendas_parciais = []
        eventos_campanha_enfileirados = 0

        for item in vendas_com_saldo:
            venda = item["venda"]
            saldo_devedor = item["saldo_devedor"]

            # Calcular quanto aplicar nesta venda (proporcional ao saldo)
            if valor_restante <= 0:
                break

            valor_aplicar = min(valor_restante, saldo_devedor)

            logger.info(f"Aplicando {valor_aplicar} na venda {venda.id}")

            # Criar pagamento
            # ðŸ”’ ISOLAMENTO MULTI-TENANT: tenant_id obrigatÃ³rio
            pagamento = VendaPagamento(
                venda_id=venda.id,
                tenant_id=tenant_id,  # âœ… Garantir isolamento entre empresas
                forma_pagamento=forma_pagamento,
                valor=valor_aplicar,
                numero_transacao=numero_transacao,
                status="confirmado",
                data_pagamento=dt.now(),
            )
            db.add(pagamento)

            # Atualizar status da venda
            novo_valor_pago = item["valor_ja_pago"] + valor_aplicar
            novo_saldo = float(venda.total) - novo_valor_pago

            if abs(novo_saldo) < 0.01:  # Quitada
                venda.status = "finalizada"
                vendas_quitadas.append(
                    {
                        "id": venda.id,
                        "numero_venda": venda.id,
                        "valor_baixado": valor_aplicar,
                        "saldo_anterior": saldo_devedor,
                    }
                )
                if venda.cliente_id:
                    try:
                        from app.campaigns.models import (
                            CampaignEventQueue,
                            EventOriginEnum,
                        )

                        db.add(
                            CampaignEventQueue(
                                tenant_id=tenant_id,
                                event_type="purchase_completed",
                                event_origin=EventOriginEnum.user_action,
                                event_depth=0,
                                payload={
                                    "customer_id": venda.cliente_id,
                                    "venda_id": venda.id,
                                    "venda_total": float(venda.total or 0),
                                    "canal": venda.canal or "loja_fisica",
                                },
                            )
                        )
                        eventos_campanha_enfileirados += 1
                    except Exception as e_camp:
                        logger.warning(
                            "[Campanhas] Falha ao enfileirar baixa em lote: %s", e_camp
                        )
            else:  # Baixa parcial
                venda.status = "baixa_parcial"
                vendas_parciais.append(
                    {
                        "id": venda.id,
                        "numero_venda": venda.id,
                        "valor_baixado": valor_aplicar,
                        "saldo_restante": novo_saldo,
                        "saldo_anterior": saldo_devedor,
                    }
                )

            get_or_build_venda_rentabilidade_snapshot(
                venda,
                db,
                tenant_id,
                persist_if_missing=True,
                force_refresh=True,
            )

            # Registrar movimentaÃ§Ã£o no caixa (apenas para formas que movimentam caixa)
            formas_que_movimentam_caixa = [
                "dinheiro",
                "Dinheiro",
                "pix",
                "PIX",
                "cartao_debito",
                "CartÃ£o de DÃ©bito",
            ]
            if forma_pagamento in formas_que_movimentam_caixa:
                # ðŸ”’ ISOLAMENTO MULTI-TENANT: tenant_id obrigatÃ³rio
                movimentacao = MovimentacaoCaixa(
                    caixa_id=caixa_aberto.id,
                    tipo="venda",
                    categoria="venda",
                    valor=valor_aplicar,
                    forma_pagamento=forma_pagamento,
                    descricao=f"Baixa venda #{venda.id} - {venda.cliente.nome if venda.cliente else 'Cliente avulso'}",
                    venda_id=venda.id,
                    usuario_id=current_user.id,
                    usuario_nome=current_user.nome or current_user.email,
                    data_movimento=dt.now(),
                    tenant_id=tenant_id,  # âœ… Garantir isolamento entre empresas
                )
                db.add(movimentacao)

            # Dar baixa no contas a receber (se existir)
            conta_receber = (
                db.query(ContaReceber)
                .filter(
                    ContaReceber.venda_id == venda.id,
                    ContaReceber.status.in_(["pendente", "baixa_parcial", "parcial"]),
                )
                .first()
            )

            if conta_receber:
                valor_ja_recebido = float(conta_receber.valor_recebido or 0)
                novo_valor_recebido = valor_ja_recebido + valor_aplicar

                conta_receber.valor_recebido = novo_valor_recebido
                conta_receber.data_recebimento = dt.now()

                if abs(float(conta_receber.valor_final) - novo_valor_recebido) < 0.01:
                    conta_receber.status = "pago"
                else:
                    conta_receber.status = "baixa_parcial"

                # ðŸ†• Criar registro de recebimento
                recebimento = Recebimento(
                    conta_receber_id=conta_receber.id,
                    valor_recebido=valor_aplicar,
                    data_recebimento=dt.now().date(),
                    observacoes=f"Baixa em lote - {forma_pagamento}",
                    user_id=current_user.id,
                    tenant_id=tenant_id,  # âœ… Garantir isolamento multi-tenant
                )
                db.add(recebimento)

                # ðŸ†• CRIAR LANÃ‡AMENTO REALIZADO NO FLUXO DE CAIXA
                fluxo_realizado = FluxoCaixa(
                    usuario_id=current_user.id,
                    tipo="entrada",
                    categoria="Recebimento de Venda",
                    descricao=f"Baixa venda #{venda.numero_venda} - {venda.cliente.nome if venda.cliente else 'Cliente avulso'}",
                    valor=valor_aplicar,
                    data_movimentacao=dt.now(),
                    data_prevista=None,
                    status="realizado",
                    origem_tipo="conta_receber",
                    origem_id=conta_receber.id,
                )
                db.add(fluxo_realizado)

                logger.info(
                    f"âœ… Fluxo de caixa REALIZADO criado: R$ {valor_aplicar:.2f}"
                )

                # ðŸ†• CRIAR LANÃ‡AMENTO PREVISTO NO FLUXO DE CAIXA (se houver saldo restante)
                saldo_conta = float(conta_receber.valor_final) - novo_valor_recebido
                if saldo_conta > 0.01:  # Se ainda tem saldo
                    data_previsao = dt.now() + timedelta(days=30)  # +30 dias

                    fluxo_previsto = FluxoCaixa(
                        usuario_id=current_user.id,
                        tipo="entrada",
                        categoria="Recebimento de Venda",
                        descricao=f"Saldo previsto venda #{venda.numero_venda} - {venda.cliente.nome if venda.cliente else 'Cliente avulso'}",
                        valor=saldo_conta,
                        data_movimentacao=None,
                        data_prevista=data_previsao,
                        status="previsto",
                        origem_tipo="conta_receber",
                        origem_id=conta_receber.id,
                    )
                    db.add(fluxo_previsto)

                    logger.info(
                        f"âœ… Fluxo de caixa PREVISTO criado: R$ {saldo_conta:.2f} para {data_previsao.strftime('%d/%m/%Y')}"
                    )

            valor_restante -= valor_aplicar

        db.commit()

        logger.info("Commit realizado com sucesso!")
        if eventos_campanha_enfileirados:
            logger.info(
                "[Campanhas] %d purchase_completed enfileirado(s) pela baixa em lote",
                eventos_campanha_enfileirados,
            )

        return {
            "success": True,
            "total_vendas_afetadas": len(vendas_quitadas) + len(vendas_parciais),
            "vendas_quitadas": vendas_quitadas,
            "vendas_parciais": vendas_parciais,
            "valor_total_baixado": valor_total,
            "valor_restante": valor_restante,
            "message": f"Baixa realizada com sucesso! {len(vendas_quitadas)} vendas quitadas, {len(vendas_parciais)} com baixa parcial.",
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.info(f"ERRO NO PROCESSAMENTO: {str(e)}")
        import traceback

        traceback.print_exc()
        db.rollback()
        raise HTTPException(
            status_code=500, detail=f"Erro ao processar baixa: {str(e)}"
        )
