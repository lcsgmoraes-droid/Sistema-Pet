"""Rotas financeiras e historicos legados de clientes."""

import logging
from datetime import datetime as dt, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user_and_tenant
from app.db import get_session
from app.models import Cliente
from app.services.venda_rentabilidade_snapshot_service import (
    get_or_build_venda_rentabilidade_snapshot,
)

logger = logging.getLogger(__name__)
router = APIRouter()


def _validar_tenant_e_obter_usuario(user_and_tenant):
    current_user, tenant_id = user_and_tenant
    return current_user, tenant_id


def _obter_cliente_ou_404(db: Session, cliente_id: int, tenant_id: str):
    cliente = (
        db.query(Cliente)
        .filter(Cliente.id == cliente_id, Cliente.tenant_id == tenant_id)
        .first()
    )
    if not cliente:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Cliente nÃ£o encontrado"
        )
    return cliente

@router.get("/{cliente_id}/credito/extrato")
def get_extrato_credito(
    cliente_id: int,
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Retorna o histórico de movimentações de crédito do cliente."""
    from app.models import CreditoLog
    from sqlalchemy import desc

    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)
    _obter_cliente_ou_404(db, cliente_id, tenant_id)

    logs = (
        db.query(CreditoLog)
        .filter(CreditoLog.cliente_id == cliente_id, CreditoLog.tenant_id == tenant_id)
        .order_by(desc(CreditoLog.created_at))
        .limit(limit)
        .all()
    )

    return [
        {
            "id": log.id,
            "tipo": log.tipo,
            "valor": float(log.valor),
            "saldo_anterior": float(log.saldo_anterior),
            "saldo_atual": float(log.saldo_atual),
            "motivo": log.motivo,
            "referencia_id": log.referencia_id,
            "usuario_nome": log.usuario_nome,
            "created_at": log.created_at.isoformat() if log.created_at else None,
        }
        for log in logs
    ]


@router.get("/{cliente_id}/historico-compras")
async def get_historico_compras(
    cliente_id: int,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Retorna o histÃ³rico de compras do cliente"""
    from app.vendas_models import Venda
    from sqlalchemy import desc

    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)
    cliente = _obter_cliente_ou_404(db, cliente_id, tenant_id)

    # Buscar vendas do cliente
    vendas = (
        db.query(Venda)
        .filter(Venda.cliente_id == cliente_id, Venda.tenant_id == tenant_id)
        .order_by(desc(Venda.data_venda))
        .all()
    )

    # EstatÃ­sticas
    total_compras = len(vendas)
    total_gasto = sum(float(v.total or 0) for v in vendas if v.status == "finalizada")
    ticket_medio = total_gasto / total_compras if total_compras > 0 else 0

    # Ãšltima compra
    ultima_compra = vendas[0].data_venda if vendas else None

    return {
        "cliente_id": cliente.id,
        "cliente_nome": cliente.nome,
        # Campos no nÃ­vel raiz para compatibilidade com frontend
        "total_compras": total_compras,
        "valor_total_gasto": round(total_gasto, 2),
        "ticket_medio": round(ticket_medio, 2),
        "ultima_compra": ultima_compra.isoformat() if ultima_compra else None,
        # Mantendo estatisticas tambÃ©m para compatibilidade
        "estatisticas": {
            "total_compras": total_compras,
            "total_gasto": round(total_gasto, 2),
            "ticket_medio": round(ticket_medio, 2),
            "ultima_compra": ultima_compra.isoformat() if ultima_compra else None,
        },
        "vendas": [
            {
                "id": v.id,
                "numero_venda": v.numero_venda
                if hasattr(v, "numero_venda") and v.numero_venda
                else v.id,
                "data_venda": v.data_venda.isoformat()
                if hasattr(v.data_venda, "isoformat")
                else str(v.data_venda),
                "total": float(v.total or 0),
                "subtotal": float(v.subtotal or 0)
                if hasattr(v, "subtotal")
                else float(v.total or 0),
                "desconto_valor": float(v.desconto_valor or 0)
                if hasattr(v, "desconto_valor")
                else 0,
                "taxa_entrega": float(v.taxa_entrega or 0)
                if hasattr(v, "taxa_entrega")
                else 0,
                "saldo_devedor": float(v.total or 0)
                - (
                    sum(float(pag.valor or 0) for pag in v.pagamentos)
                    if hasattr(v, "pagamentos") and v.pagamentos
                    else 0
                ),
                "status": v.status,
                "total_itens": len(v.itens) if v.itens else 0,
                "vendedor_nome": v.vendedor_nome
                if hasattr(v, "vendedor_nome")
                else None,
                "observacoes": v.observacoes if hasattr(v, "observacoes") else None,
                # Lista completa de formas de pagamento
                "pagamentos": [
                    {
                        "forma": (
                            pag.forma_pagamento.nome
                            if (
                                pag.forma_pagamento
                                and hasattr(pag.forma_pagamento, "nome")
                            )
                            else str(pag.forma_pagamento)
                            if pag.forma_pagamento
                            else "Não informado"
                        ),
                        "valor": float(pag.valor or 0),
                    }
                    for pag in (v.pagamentos or [])
                ],
                # Itens da venda
                "itens": [
                    {
                        "nome": (
                            item.produto.nome
                            if item.produto
                            else item.servico_descricao
                        )
                        or "Item",
                        "quantidade": float(item.quantidade or 0),
                        "preco_unitario": float(item.preco_unitario or 0),
                        "subtotal": float(item.subtotal or 0),
                        "tipo": item.tipo or "produto",
                    }
                    for item in (v.itens or [])
                ],
            }
            for v in vendas
        ],
    }


@router.get("/{cliente_id}/vendas-em-aberto")
async def get_vendas_em_aberto(
    cliente_id: int,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Retorna vendas em aberto (pendentes) do cliente"""
    from app.vendas_models import Venda

    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)
    cliente = _obter_cliente_ou_404(db, cliente_id, tenant_id)

    # Buscar vendas em aberto do cliente (status: aberta ou baixa_parcial)
    # Ordenar da mais ANTIGA para a mais RECENTE (ordem ascendente)
    vendas_aberto = (
        db.query(Venda)
        .filter(
            Venda.cliente_id == cliente_id,
            Venda.tenant_id == tenant_id,
            Venda.status.in_(["aberta", "baixa_parcial"]),
        )
        .order_by(Venda.data_venda.asc())
        .all()
    )

    # DEBUG: Log para verificar quantas vendas foram encontradas
    logger.info("Buscando vendas em aberto do cliente")
    logger.info("Total de vendas em aberto encontrado: %s", len(vendas_aberto))

    # Filtrar apenas vendas com saldo devedor maior que zero
    vendas_com_saldo = []
    for v in vendas_aberto:
        valor_pago = (
            sum(float(pag.valor or 0) for pag in v.pagamentos)
            if hasattr(v, "pagamentos") and v.pagamentos
            else 0
        )
        saldo = float(v.total or 0) - valor_pago

        if saldo > 0.01:  # Apenas vendas com saldo maior que 1 centavo
            vendas_com_saldo.append(v)
            logger.info(
                f"  âœ… ID: {v.id} | Status: {v.status} | Total: R$ {v.total} | Pago: R$ {valor_pago} | Saldo: R$ {saldo}"
            )
        else:
            logger.info(
                f"  âŒ ID: {v.id} | Status: {v.status} | Saldo zerado - EXCLUÃDA"
            )

    # Usar apenas vendas com saldo
    vendas_aberto = vendas_com_saldo

    # Calcular valores
    total_vendas = len(vendas_aberto)
    valor_total = sum(float(v.total or 0) for v in vendas_aberto)

    # Calcular valor pago somando os pagamentos
    valor_pago = 0
    for v in vendas_aberto:
        if hasattr(v, "pagamentos") and v.pagamentos:
            valor_pago += sum(float(pag.valor or 0) for pag in v.pagamentos)

    saldo_pendente = valor_total - valor_pago

    return {
        "cliente_id": cliente.id,
        "cliente_nome": cliente.nome,
        "tem_vendas_aberto": total_vendas > 0,
        "resumo": {
            "total_vendas": total_vendas,
            "valor_total": round(valor_total, 2),
            "valor_pago": round(valor_pago, 2),
            "saldo_pendente": round(saldo_pendente, 2),
            "total_em_aberto": round(saldo_pendente, 2),  # Compatibilidade com frontend
        },
        "vendas": [
            {
                "id": v.id,
                "numero_venda": v.numero_venda,  # NÃºmero formatado da venda (ex: 202601190004)
                "data_venda": v.data_venda.isoformat()
                if hasattr(v.data_venda, "isoformat")
                else str(v.data_venda),
                "total": float(v.total or 0),
                "total_pago": sum(float(pag.valor or 0) for pag in v.pagamentos)
                if hasattr(v, "pagamentos") and v.pagamentos
                else 0,
                "saldo_devedor": float(v.total or 0)
                - (
                    sum(float(pag.valor or 0) for pag in v.pagamentos)
                    if hasattr(v, "pagamentos") and v.pagamentos
                    else 0
                ),
                "status": v.status,
                "canal": v.canal or "loja_fisica",
            }
            for v in vendas_aberto
        ],
    }


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


@router.get("/{cliente_id}/historico")
async def get_cliente_historico(
    cliente_id: int,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    âš ï¸ **DEPRECATED** - Esta rota serÃ¡ removida em versÃ£o futura

    **Problemas desta rota:**
    - âŒ Carrega TODAS as transaÃ§Ãµes em memÃ³ria (sem paginaÃ§Ã£o)
    - âŒ Performance ruim com histÃ³rico grande (>500 transaÃ§Ãµes)
    - âŒ Alto consumo de memÃ³ria
    - âŒ Ordena tudo em Python (deveria ser no banco)

    **Migre para as novas rotas:**

    1. **Para histÃ³rico completo paginado:**
       ```
       GET /financeiro/cliente/{cliente_id}?page=1&per_page=20
       ```
       - PaginaÃ§Ã£o obrigatÃ³ria
       - Filtros: data_inicio, data_fim, tipo, status
       - Performance otimizada

    2. **Para resumo leve (uso no cadastro):**
       ```
       GET /financeiro/cliente/{cliente_id}/resumo
       ```
       - Apenas dados agregados (COUNT, SUM)
       - Muito mais rÃ¡pido (~10-50ms vs 500-2000ms)
       - Ideal para Step 6 do wizard

    **Data de remoÃ§Ã£o planejada:** Junho/2026

    ---

    Retorna o histÃ³rico completo de transaÃ§Ãµes do cliente:
    - Vendas realizadas
    - DevoluÃ§Ãµes
    - Contas a receber (em aberto e pagas)
    - Recebimentos
    """
    _, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)
    cliente = _obter_cliente_ou_404(db, cliente_id, tenant_id)

    # Importar modelos necessÃ¡rios
    from app.vendas_models import Venda
    from app.financeiro_models import ContaReceber, Recebimento

    historico = []

    # 1. Buscar vendas do cliente (excluir canceladas/devolvidas do histÃ³rico principal)
    vendas = (
        db.query(Venda)
        .filter(
            Venda.cliente_id == cliente_id,
            Venda.status.notin_(["cancelada", "devolvida"]),
        )
        .order_by(Venda.data_venda.desc())
        .all()
    )

    for venda in vendas:
        historico.append(
            {
                "tipo": "venda",
                "data": venda.data_venda.isoformat() if venda.data_venda else None,
                "descricao": f"Venda #{venda.numero_venda}",
                "valor": float(venda.total),
                "status": venda.status,
                "detalhes": {
                    "venda_id": venda.id,
                    "numero_venda": venda.numero_venda,
                    "subtotal": float(venda.subtotal),
                    "desconto": float(venda.desconto_valor)
                    if venda.desconto_valor
                    else 0,
                    "total": float(venda.total),
                    "status": venda.status,
                    "canal": venda.canal,
                    "observacoes": venda.observacoes,
                },
            }
        )

    # 2. Buscar devoluÃ§Ãµes (vendas canceladas/devolvidas)
    devolucoes = (
        db.query(Venda)
        .filter(
            Venda.cliente_id == cliente_id, Venda.status.in_(["cancelada", "devolvida"])
        )
        .order_by(Venda.data_venda.desc())
        .all()
    )

    for devolucao in devolucoes:
        historico.append(
            {
                "tipo": "devolucao",
                "data": devolucao.data_venda.isoformat()
                if devolucao.data_venda
                else None,
                "descricao": f"DevoluÃ§Ã£o - Venda #{devolucao.numero_venda}",
                "valor": -float(devolucao.total),
                "status": devolucao.status,
                "detalhes": {
                    "numero_venda": devolucao.numero_venda,
                    "total": float(devolucao.total),
                    "motivo": devolucao.observacoes,
                },
            }
        )

    # 3. Buscar contas a receber
    contas_receber = (
        db.query(ContaReceber)
        .filter(ContaReceber.cliente_id == cliente_id)
        .order_by(ContaReceber.data_vencimento.desc())
        .all()
    )

    for conta in contas_receber:
        valor_recebido = float(conta.valor_recebido) if conta.valor_recebido else 0
        valor_pendente = float(conta.valor_original) - valor_recebido

        historico.append(
            {
                "tipo": "conta_receber",
                "data": conta.data_emissao.isoformat() if conta.data_emissao else None,
                "descricao": conta.descricao,
                "valor": float(conta.valor_original),
                "status": conta.status,
                "detalhes": {
                    "vencimento": conta.data_vencimento.isoformat()
                    if conta.data_vencimento
                    else None,
                    "valor_original": float(conta.valor_original),
                    "valor_recebido": valor_recebido,
                    "valor_pendente": valor_pendente,
                    "status": conta.status,
                    "numero_parcela": conta.numero_parcela,
                    "total_parcelas": conta.total_parcelas,
                },
            }
        )

    # 4. Buscar recebimentos
    recebimentos = (
        db.query(Recebimento)
        .join(ContaReceber)
        .filter(ContaReceber.cliente_id == cliente_id)
        .order_by(Recebimento.data_recebimento.desc())
        .all()
    )

    for rec in recebimentos:
        historico.append(
            {
                "tipo": "recebimento",
                "data": rec.data_recebimento.isoformat()
                if rec.data_recebimento
                else None,
                "descricao": f"Recebimento - {rec.conta.descricao if rec.conta else 'Conta'}",
                "valor": float(rec.valor_recebido),
                "status": "efetivado",
                "detalhes": {
                    "valor": float(rec.valor_recebido),
                    "forma_pagamento": rec.forma_pagamento.nome
                    if rec.forma_pagamento
                    else None,
                    "observacoes": rec.observacoes,
                },
            }
        )

    # Ordenar histÃ³rico por data (mais recente primeiro)
    historico.sort(key=lambda x: x["data"] if x["data"] else "", reverse=True)

    # Calcular totais
    total_vendas = sum(float(v.total) for v in vendas)
    total_em_aberto = sum(
        float(c.valor_original) - float(c.valor_recebido or 0)
        for c in contas_receber
        if c.status == "pendente"
    )
    total_recebido = sum(float(r.valor_recebido) for r in recebimentos)

    return {
        "cliente": {
            "id": cliente.id,
            "codigo": cliente.codigo,
            "nome": cliente.nome,
            "credito_atual": float(cliente.credito) if cliente.credito else 0,
        },
        "resumo": {
            "total_vendas": total_vendas,
            "total_em_aberto": total_em_aberto,
            "total_recebido": total_recebido,
            "total_transacoes": len(historico),
        },
        "historico": historico,
    }
