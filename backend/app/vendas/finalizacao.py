# -*- coding: utf-8 -*-
"""Finalizacao de vendas.

Mantem a orquestracao critica de pagamento, estoque, caixa, financeiro e
eventos fora da fachada ``VendaService`` sem alterar o comportamento publico.
"""

import logging
from datetime import date, timedelta
from decimal import Decimal
from typing import Any, Callable, Dict, List, Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.services.venda_rentabilidade_snapshot_service import (
    get_or_build_venda_rentabilidade_snapshot,
    invalidate_venda_rentabilidade_snapshot,
)
from app.utils.timezone import now_brasilia
from app.vendas.finalizacao_eventos import publicar_eventos_finalizacao
from app.vendas.finalizacao_pagamentos import (
    _calcular_pagamentos_finalizacao,
    consumir_cupom_finalizacao,
    processar_pagamentos_finalizacao,
)
from app.vendas.finalizacao_pos_commit import processar_pos_commit_finalizacao
from app.vendas.pos_processamento import gerar_dre_competencia_venda

logger = logging.getLogger(__name__)

__all__ = [
    "_calcular_pagamentos_finalizacao",
    "finalizar_venda",
]


def finalizar_venda(
    venda_id: int,
    pagamentos: List[Dict[str, Any]],
    user_id: int,
    user_nome: str,
    tenant_id: str,
    db: Session,
    cupom_code: Optional[str] = None,
    cupom_discount_applied: Optional[float] = None,
    caixa_id: Optional[int] = None,
    permitir_caixa_tenant: bool = False,
    *,
    processar_baixa_estoque_item: Callable[..., List[Dict[str, Any]]],
) -> Dict[str, Any]:
    """
    Finaliza uma venda com transação atômica.

    Esta é a operação MAIS CRÍTICA do sistema. Executa em ordem:
    1. Validações (venda, caixa, status, pagamentos)
    2. Processamento de pagamentos (crédito cliente, caixa)
    3. Atualização de status da venda
    4. Baixa de estoque
    5. Vinculação ao caixa
    6. Baixa de contas a receber existentes
    7. COMMIT ÚNICO ✅
    8. Operações pós-commit (contas novas, comissões, lembretes)

    TRANSAÇÃO ATÔMICA:
    - Se qualquer etapa 1-6 falhar → ROLLBACK completo
    - Apenas após commit bem-sucedido → etapa 8
    - Erros na etapa 8 não abortam a venda (já commitada)

    Args:
        venda_id: ID da venda a ser finalizada
        pagamentos: Lista de dicts com forma_pagamento, valor, numero_parcelas
        user_id: ID do usuário que está finalizando
        user_nome: Nome do usuário (para auditoria)
        db: Sessão do SQLAlchemy (será commitada AQUI)

    Returns:
        Dict com resultado completo:
        {
            'venda': {
                'id': int,
                'numero_venda': str,
                'status': str,
                'total': float,
                'total_pago': float
            },
            'operacoes': {
                'estoque_baixado': List[dict],
                'caixa_movimentacoes': List[int],
                'contas_baixadas': List[dict],
                'contas_criadas': List[int]
            },
            'pos_commit': {
                'contas_novas': int,
                'comissoes_geradas': bool,
                'lembretes_criados': int
            }
        }

    Raises:
        HTTPException(404): Venda não encontrada
        HTTPException(400): Status inválido, pagamento inválido, estoque insuficiente

    Exemplo:
        >>> resultado = VendaService.finalizar_venda(
        ...     venda_id=120,
        ...     pagamentos=[
        ...         {'forma_pagamento': 'Dinheiro', 'valor': 50.0},
        ...         {'forma_pagamento': 'PIX', 'valor': 50.0}
        ...     ],
        ...     user_id=1,
        ...     user_nome="João Silva",
        ...     db=db
        ... )
        >>> logger.info(f"Venda {resultado['venda']['numero_venda']} finalizada!")
    """
    # Imports locais
    from app.vendas_models import Venda, VendaPagamento
    from app.caixa.service import CaixaService
    from app.financeiro import ContasReceberService
    from app.financeiro_models import LancamentoManual, CategoriaFinanceira
    from app.services.business_audit_service import (
        build_sale_coupon_redeemed_metadata,
        calculate_manual_discount_amount,
        log_business_event,
    )

    logger.info(
        f"🚀 Iniciando finalização da venda #{venda_id} - {len(pagamentos)} pagamento(s)"
    )

    try:
        # ============================================================
        # ETAPA 1: VALIDAÇÕES INICIAIS
        # ============================================================

        # Validar caixa aberto
        caixa_info = CaixaService.validar_caixa_aberto(
            user_id=user_id,
            db=db,
            tenant_id=tenant_id,
            caixa_id=caixa_id,
            permitir_caixa_tenant=permitir_caixa_tenant,
        )
        caixa_aberto_id = caixa_info["caixa_id"]
        logger.debug(f"✅ Caixa validado: ID={caixa_aberto_id}")

        # Buscar venda
        venda = db.query(Venda).filter_by(id=venda_id, tenant_id=tenant_id).first()
        if not venda:
            raise HTTPException(status_code=404, detail="Venda não encontrada")

        # Validar status
        if venda.status not in ["aberta", "baixa_parcial"]:
            raise HTTPException(
                status_code=400,
                detail=f"Apenas vendas abertas ou com baixa parcial podem receber pagamentos (status atual: {venda.status})",
            )

        # Calcular totais
        pagamentos_existentes = (
            db.query(VendaPagamento).filter_by(venda_id=venda.id).all()
        )
        total_venda = float(venda.total)
        totais_pagamento = _calcular_pagamentos_finalizacao(
            total_venda=total_venda,
            pagamentos_existentes=pagamentos_existentes,
            pagamentos_novos=pagamentos,
        )
        total_ja_pago = totais_pagamento["total_ja_pago"]
        total_novos_pagamentos = totais_pagamento["total_novos_pagamentos"]
        total_pagamentos = totais_pagamento["total_pagamentos"]

        logger.info(
            f"💰 Totais: Venda=R$ {total_venda:.2f}, "
            f"Já pago=R$ {total_ja_pago:.2f}, "
            f"Novos=R$ {total_novos_pagamentos:.2f}"
        )

        cupom_consumido = consumir_cupom_finalizacao(
            venda=venda,
            cupom_code=cupom_code,
            cupom_discount_applied=cupom_discount_applied,
            tenant_id=tenant_id,
            db=db,
        )
        # ============================================================
        # ETAPA 2: PROCESSAR PAGAMENTOS
        # ============================================================

        movimentacoes_caixa_ids = processar_pagamentos_finalizacao(
            venda=venda,
            pagamentos=pagamentos,
            user_id=user_id,
            user_nome=user_nome,
            tenant_id=tenant_id,
            db=db,
            caixa_aberto_id=caixa_aberto_id,
        )
        # ============================================================
        # ETAPA 3: ATUALIZAR STATUS DA VENDA
        # ============================================================

        # 🎯 GUARDAR STATUS ANTERIOR (para decisão de baixa de estoque)
        status_anterior = venda.status
        logger.info(f"📋 Status anterior: {status_anterior}")

        if total_pagamentos >= total_venda - 0.01:
            # Pagamento completo
            venda.status = "finalizada"
            venda.data_finalizacao = now_brasilia()
            logger.info("✅ Venda FINALIZADA - Pagamento completo")
        elif total_pagamentos > 0:
            # Pagamento parcial
            venda.status = "baixa_parcial"
            logger.info(
                f"📊 Venda BAIXA PARCIAL - R$ {total_pagamentos:.2f} de R$ {total_venda:.2f}"
            )

            # Criar lançamento previsto para saldo em aberto
            saldo_em_aberto = total_venda - total_pagamentos
            if saldo_em_aberto > 0.01:
                categoria_receitas = (
                    db.query(CategoriaFinanceira)
                    .filter(
                        CategoriaFinanceira.nome.ilike("%vendas%"),
                        CategoriaFinanceira.tipo == "receita",
                        CategoriaFinanceira.tenant_id == tenant_id,
                    )
                    .first()
                )

                if not categoria_receitas:
                    categoria_receitas = CategoriaFinanceira(
                        nome="Receitas de Vendas",
                        tipo="receita",
                        user_id=user_id,
                        tenant_id=tenant_id,  # ✅ Garantir isolamento multi-tenant
                    )
                    db.add(categoria_receitas)
                    db.flush()

                data_prevista = date.today() + timedelta(days=30)
                lancamento_saldo = LancamentoManual(
                    tipo="entrada",
                    valor=Decimal(str(saldo_em_aberto)),
                    descricao=f"Venda {venda.numero_venda} - Saldo em aberto",
                    data_lancamento=data_prevista,
                    status="previsto",
                    categoria_id=categoria_receitas.id,
                    documento=f"VENDA-{venda.id}-SALDO",
                    fornecedor_cliente=venda.cliente.nome
                    if venda.cliente
                    else "Cliente Avulso",
                    user_id=user_id,
                    tenant_id=tenant_id,  # ✅ Garantir isolamento multi-tenant
                )
                db.add(lancamento_saldo)
                logger.info(
                    f"📝 Lançamento previsto criado: R$ {saldo_em_aberto:.2f} em {data_prevista}"
                )
        else:
            venda.status = "aberta"

        venda.updated_at = now_brasilia()

        if venda.status in ["baixa_parcial", "finalizada"]:
            get_or_build_venda_rentabilidade_snapshot(
                venda,
                db,
                tenant_id,
                persist_if_missing=True,
                force_refresh=True,
            )
        else:
            invalidate_venda_rentabilidade_snapshot(venda)

        # ============================================================
        # ETAPA 3.5: GERAR DRE POR COMPETÊNCIA (PASSO 1 - Sprint 5)
        # ============================================================

        # 🎯 EVENTO DE EFETIVAÇÃO: Venda passou de 'aberta' para qualquer status com pagamento
        # Condições para gerar DRE:
        # 1. Venda tem pagamento (parcial ou total)
        # 2. DRE ainda não foi gerada (venda.dre_gerada == False)
        # 3. Status é 'baixa_parcial' ou 'finalizada' (não 'aberta')

        if venda.status in ["baixa_parcial", "finalizada"] and not venda.dre_gerada:
            logger.info(
                f"🎯 EVENTO DE EFETIVAÇÃO DETECTADO: Venda #{venda.numero_venda} "
                f"mudou para status '{venda.status}' - Gerando DRE por competência..."
            )

            try:
                resultado_dre = gerar_dre_competencia_venda(
                    venda_id=venda.id, user_id=user_id, tenant_id=tenant_id, db=db
                )

                if resultado_dre["success"]:
                    logger.info(
                        f"✅ DRE gerada com sucesso: {resultado_dre['lancamentos_criados']} lançamentos "
                        f"(Receita: R$ {resultado_dre['receita_gerada']:.2f}, "
                        f"CMV: R$ {resultado_dre['cmv_gerado']:.2f}, "
                        f"Desconto: R$ {resultado_dre['desconto_gerado']:.2f})"
                    )
                else:
                    logger.info(f"ℹ️  DRE: {resultado_dre['message']}")

            except Exception as e:
                # ⚠️  Erro na DRE NÃO deve abortar a venda
                logger.error(
                    f"⚠️  Erro ao gerar DRE por competência (venda {venda.id}): {str(e)}",
                    exc_info=True,
                )
                # Continua a finalização da venda normalmente

        # ============================================================
        # ETAPA 4: BAIXAR ESTOQUE (COM SUPORTE A KIT)
        # ============================================================
        # 🎯 LÓGICA CRÍTICA: Só baixa estoque se venda NÃO veio de status 'aberta'
        # - Se status_anterior = 'aberta': estoque JÁ foi baixado na criação
        # - Se status_anterior != 'aberta': venda criada direto como finalizada, baixar agora

        estoque_baixado = []
        deve_baixar_estoque = status_anterior != "aberta"

        if deve_baixar_estoque:
            logger.info("📦 Baixando estoque (venda não veio de status aberta)")
        else:
            logger.info(
                "ℹ️  Estoque NÃO será baixado (já foi baixado quando venda estava aberta)"
            )

        for item in venda.itens:
            if item.tipo == "produto":
                # Determinar se é produto simples ou variação
                produto_id = item.produto_id
                product_variation_id = item.product_variation_id

                # Buscar produto (simples ou da variação)
                from app.produtos_models import Produto

                if product_variation_id:
                    # Item com variação: buscar o produto da variação
                    variacao = (
                        db.query(Produto)
                        .filter(
                            Produto.id == product_variation_id,
                            Produto.tipo_produto == "VARIACAO",
                        )
                        .first()
                    )

                    if not variacao:
                        raise ValueError(
                            f"Variação ID {product_variation_id} não encontrada"
                        )

                    produto = variacao
                elif produto_id:
                    # Item com produto simples
                    produto = (
                        db.query(Produto)
                        .filter(
                            Produto.id == produto_id, Produto.tenant_id == tenant_id
                        )
                        .first()
                    )

                    if not produto:
                        raise ValueError(f"Produto ID {produto_id} não encontrado")
                else:
                    continue  # Item sem produto (serviço)

                # 🎯 Só baixar se deve_baixar_estoque=True
                if deve_baixar_estoque:
                    # Baixar estoque conforme tipo do produto
                    resultados = processar_baixa_estoque_item(
                        produto=produto,
                        quantidade_vendida=float(item.quantidade),
                        venda_id=venda.id,
                        user_id=user_id,
                        tenant_id=tenant_id,
                        db=db,
                        product_variation_id=product_variation_id,
                        venda_codigo=venda.numero_venda,
                    )

                    # Acumular resultados
                    estoque_baixado.extend(resultados)

        # ============================================================
        # ETAPA 5: VINCULAR AO CAIXA
        # ============================================================

        if not venda.caixa_id:
            CaixaService.vincular_venda_ao_caixa(
                venda_id=venda.id, caixa_id=caixa_aberto_id, db=db
            )
            logger.info(f"🔗 Venda vinculada ao caixa #{caixa_aberto_id}")

        # ============================================================
        # ETAPA 6: BAIXAR CONTAS A RECEBER EXISTENTES
        # ============================================================

        contas_baixadas = []
        if total_novos_pagamentos > 0.01:
            forma_pag_nome = (
                pagamentos[0]["forma_pagamento"] if pagamentos else "Diversos"
            )

            resultado_baixa = ContasReceberService.baixar_contas_da_venda(
                venda_id=venda.id,
                venda_numero=venda.numero_venda,
                valor_total_pagamento=total_novos_pagamentos,
                forma_pagamento_nome=forma_pag_nome,
                user_id=user_id,
                tenant_id=tenant_id,
                db=db,
            )

            contas_baixadas = resultado_baixa["contas_baixadas"]

            if contas_baixadas:
                logger.info(
                    f"💰 Contas baixadas: {len(contas_baixadas)} conta(s), "
                    f"R$ {float(resultado_baixa['valor_distribuido']):.2f} distribuído"
                )

            # Atualizar lançamentos manuais
            total_recebido_venda = total_ja_pago + total_novos_pagamentos
            resultado_lancamentos = ContasReceberService.atualizar_lancamentos_venda(
                venda_id=venda.id,
                venda_numero=venda.numero_venda,
                total_venda=total_venda,
                total_recebido=total_recebido_venda,
                user_id=user_id,
                tenant_id=tenant_id,
                db=db,
            )

            logger.info(
                f"📝 Lançamentos: {len(resultado_lancamentos['lancamentos_atualizados'])} atualizado(s), "
                f"Status: {resultado_lancamentos['status']}"
            )

        # ============================================================
        # 🔥 COMMIT ÚNICO - TRANSAÇÃO ATÔMICA 🔥
        # ============================================================

        if cupom_consumido:
            log_business_event(
                db=db,
                tenant_id=tenant_id,
                user_id=user_id,
                event="sale.coupon_redeemed",
                entity_type="vendas",
                entity_id=venda.id,
                metadata=build_sale_coupon_redeemed_metadata(
                    venda=venda,
                    coupon_consumed=cupom_consumido,
                ),
                details=f"Cupom consumido na venda #{venda.numero_venda}",
                commit=False,
            )

        manual_discount_amount = calculate_manual_discount_amount(venda)
        if manual_discount_amount > 0:
            log_business_event(
                db=db,
                tenant_id=tenant_id,
                user_id=user_id,
                event="sale.manual_discount_finalized",
                entity_type="vendas",
                entity_id=venda.id,
                metadata={
                    "sale_number": venda.numero_venda,
                    "discount_amount": manual_discount_amount,
                    "gross_discount": float(venda.desconto_valor or 0),
                    "coupon_discount": float(venda.cupom_discount_applied or 0),
                    "customer_id": venda.cliente_id,
                    "sale_total": float(venda.total or 0),
                },
                details=f"Desconto manual efetivado na venda #{venda.numero_venda}",
                commit=False,
            )

        db.commit()
        logger.info(
            f"✅ ✅ ✅ COMMIT REALIZADO - Venda #{venda.numero_venda} finalizada com sucesso! ✅ ✅ ✅"
        )

        pendencias_estoque_finalizadas = 0
        recurrence_result = {"created": [], "completed": [], "skipped": []}
        if venda.status == "finalizada":
            try:
                from app.services.pendencia_estoque_service import (
                    finalizar_pendencias_por_venda,
                )

                resultado_pendencias_estoque = finalizar_pendencias_por_venda(
                    db=db,
                    tenant_id=tenant_id,
                    venda=venda,
                    commit=True,
                )
                pendencias_estoque_finalizadas = int(
                    resultado_pendencias_estoque.get("finalizadas", 0) or 0
                )
            except Exception:
                logger.exception(
                    "Erro ao finalizar pendencias de estoque da venda %s",
                    venda.id,
                )
                db.rollback()

            try:
                from app.services.product_recurrence import (
                    process_finalized_sale_recurrence,
                )

                with db.begin_nested():
                    recurrence_result = process_finalized_sale_recurrence(
                        db,
                        venda=venda,
                        tenant_id=tenant_id,
                        user_id=user_id,
                    )
                db.commit()
            except Exception:
                logger.exception(
                    "Erro ao processar recorrencia da venda %s",
                    venda.id,
                )
                db.rollback()

        # ============================================================
        publicar_eventos_finalizacao(
            venda=venda,
            pagamentos=pagamentos,
            estoque_baixado=estoque_baixado,
            movimentacoes_caixa_ids=movimentacoes_caixa_ids,
            contas_baixadas=contas_baixadas,
            total_pagamentos=total_pagamentos,
            user_id=user_id,
            user_nome=user_nome,
        )

        contas_criadas_ids = processar_pos_commit_finalizacao(
            venda=venda,
            pagamentos=pagamentos,
            user_id=user_id,
            tenant_id=tenant_id,
            db=db,
        )

        # Preparar retorno
        return {
            "venda": {
                "id": venda.id,
                "numero_venda": venda.numero_venda,
                "status": venda.status,
                "total": float(venda.total),
                "total_pago": total_pagamentos,
                "data_finalizacao": venda.data_finalizacao.isoformat()
                if venda.data_finalizacao
                else None,
            },
            "operacoes": {
                "estoque_baixado": estoque_baixado,
                "caixa_movimentacoes": movimentacoes_caixa_ids,
                "contas_baixadas": contas_baixadas,
                "contas_criadas": contas_criadas_ids,
                "cupom_consumido": cupom_consumido,
                "pendencias_estoque_finalizadas": pendencias_estoque_finalizadas,
            },
            "pos_commit": {
                "contas_novas": len(contas_criadas_ids),
                "comissoes_geradas": False,  # Será processado na rota
                "lembretes_criados": len(recurrence_result["created"]),
                "lembretes_concluidos": len(recurrence_result["completed"]),
                "lembretes": recurrence_result,
            },
        }

    except HTTPException:
        # Re-lançar HTTPException (já tem mensagem amigável)
        db.rollback()
        logger.error(
            f"❌ HTTPException na finalização da venda #{venda_id} - Rollback executado"
        )
        raise

    except Exception as e:
        # Rollback em caso de erro inesperado
        db.rollback()
        logger.error(
            f"❌ ERRO CRÍTICO na finalização da venda #{venda_id}: {str(e)}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=500, detail=f"Erro ao finalizar venda: {str(e)}"
        )
