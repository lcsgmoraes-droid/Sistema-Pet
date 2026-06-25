# -*- coding: utf-8 -*-
"""Publicacao de eventos emitidos apos a finalizacao de venda."""

import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

__all__ = ["publicar_eventos_finalizacao"]


def publicar_eventos_finalizacao(
    *,
    venda: Any,
    pagamentos: List[Dict[str, Any]],
    estoque_baixado: List[Dict[str, Any]],
    movimentacoes_caixa_ids: List[int],
    contas_baixadas: List[Dict[str, Any]],
    total_pagamentos: float,
    user_id: int,
    user_nome: str,
) -> None:
    # ETAPA 7: EMITIR EVENTOS DE DOMÍNIO
    # ============================================================

    # Evento principal: Venda finalizada (sistema legado)
    # 🔒 EVENTOS DESABILITADOS TEMPORARIAMENTE (publish_event não exportado)
    # try:
    #     from app.domain.events import VendaFinalizada, publish_event as publish_legacy
    #
    #     evento = VendaFinalizada(
    #         venda_id=venda.id,
    #         numero_venda=venda.numero_venda,
    #         user_id=user_id,
    #         user_nome=user_nome,
    #         cliente_id=venda.cliente_id,
    #         funcionario_id=venda.funcionario_id,
    #         total=float(venda.total),
    #         total_pago=total_pagamentos,
    #         status=venda.status,
    #         formas_pagamento=[p['forma_pagamento'] for p in pagamentos],
    #         estoque_baixado=(len(estoque_baixado) > 0),
    #         caixa_movimentado=(len(movimentacoes_caixa_ids) > 0),
    #         contas_baixadas=len(contas_baixadas),
    #         metadados={
    #             'quantidade_itens': len(venda.itens),
    #             'tem_entrega': venda.tem_entrega
    #         }
    #     )
    #
    #     publish_legacy(evento)
    #     logger.debug(f"📢 Evento VendaFinalizada publicado (venda_id={venda.id})")
    #
    # except Exception as e:
    #     logger.error(f"⚠️  Erro ao publicar evento VendaFinalizada: {str(e)}", exc_info=True)

    try:
        from app.domain.events import VendaFinalizada, publish_event

        publish_event(
            VendaFinalizada(
                venda_id=venda.id,
                numero_venda=venda.numero_venda,
                user_id=user_id,
                user_nome=user_nome,
                cliente_id=venda.cliente_id,
                funcionario_id=venda.funcionario_id,
                total=float(venda.total),
                total_pago=total_pagamentos,
                status=venda.status,
                formas_pagamento=[p["forma_pagamento"] for p in pagamentos],
                estoque_baixado=(len(estoque_baixado) > 0),
                caixa_movimentado=(len(movimentacoes_caixa_ids) > 0),
                contas_baixadas=len(contas_baixadas),
                metadados={
                    "quantidade_itens": len(venda.itens),
                    "tem_entrega": venda.tem_entrega,
                },
            )
        )
        logger.debug("Evento VendaFinalizada publicado (venda_id=%s)", venda.id)
    except Exception as e:
        logger.error(
            "Erro ao publicar evento VendaFinalizada: %s",
            str(e),
            exc_info=True,
        )

    # Novos eventos: VendaRealizadaEvent + eventos por produto/KIT
    try:
        from app.events import (
            VendaRealizadaEvent,
            ProdutoVendidoEvent,
            KitVendidoEvent,
            publish_event,
        )

        # 1. Evento principal da venda
        forma_pagamento_principal = (
            pagamentos[0]["forma_pagamento"] if pagamentos else "Não especificado"
        )
        tem_kit = any(
            resultado.get("kit_origem") or resultado.get("tipo_kit")
            for resultado in estoque_baixado
        )

        evento_venda = VendaRealizadaEvent(
            venda_id=venda.id,
            numero_venda=venda.numero_venda,
            total=float(venda.total),
            forma_pagamento=forma_pagamento_principal,
            quantidade_itens=len(venda.itens),
            cliente_id=venda.cliente_id,
            vendedor_id=venda.vendedor_id,
            funcionario_id=venda.funcionario_id,
            tem_kit=tem_kit,
            user_id=user_id,
            metadados={
                "status": venda.status,
                "total_pago": total_pagamentos,
                "formas_pagamento": [p["forma_pagamento"] for p in pagamentos],
                "tem_entrega": venda.tem_entrega,
            },
        )
        publish_event(evento_venda)
        logger.debug(f"📢 VendaRealizadaEvent publicado (venda_id={venda.id})")

        # 2. Eventos por produto/KIT vendido
        # Agrupar resultados por produto (pode ter múltiplas entradas para KIT VIRTUAL)
        produtos_processados = {}
        kits_processados = {}

        for resultado in estoque_baixado:
            produto_id = resultado.get("produto_id")

            # Se é componente de KIT VIRTUAL
            if resultado.get("kit_origem"):
                kit_id = resultado.get("kit_id")
                kit_nome = resultado.get("kit_origem")

                # Acumular componentes do KIT
                if kit_id not in kits_processados:
                    kits_processados[kit_id] = {
                        "kit_nome": kit_nome,
                        "tipo_kit": "VIRTUAL",
                        "componentes": [],
                    }

                kits_processados[kit_id]["componentes"].append(
                    {
                        "produto_id": produto_id,
                        "nome": resultado.get("produto"),
                        "quantidade": resultado.get("quantidade"),
                        "estoque_anterior": resultado.get("estoque_anterior"),
                        "estoque_novo": resultado.get("estoque_novo"),
                    }
                )

            # Se é KIT FÍSICO
            elif resultado.get("tipo_kit") == "FISICO":
                kit_id = produto_id
                kit_nome = resultado.get("produto")

                kits_processados[kit_id] = {
                    "kit_nome": kit_nome,
                    "tipo_kit": "FISICO",
                    "quantidade": resultado.get("quantidade"),
                    "estoque_anterior": resultado.get("estoque_anterior"),
                    "estoque_novo": resultado.get("estoque_novo"),
                    "componentes": [],
                }

            # Se é produto SIMPLES/VARIACAO (não é componente de KIT)
            elif not resultado.get("kit_origem"):
                produtos_processados[produto_id] = resultado

        # Publicar eventos de produtos SIMPLES/VARIACAO
        for produto_id, resultado in produtos_processados.items():
            # Buscar item da venda para obter preços
            item_venda = next(
                (item for item in venda.itens if item.produto_id == produto_id),
                None,
            )

            if item_venda:
                evento_produto = ProdutoVendidoEvent(
                    venda_id=venda.id,
                    produto_id=produto_id,
                    produto_nome=resultado.get("produto"),
                    tipo_produto=resultado.get("tipo_produto", "SIMPLES"),
                    quantidade=float(resultado.get("quantidade")),
                    preco_unitario=float(item_venda.preco_unitario or 0),
                    preco_total=float(item_venda.subtotal or 0),
                    estoque_anterior=float(resultado.get("estoque_anterior")),
                    estoque_novo=float(resultado.get("estoque_novo")),
                    user_id=user_id,
                )
                publish_event(evento_produto)
                logger.debug(
                    f"📢 ProdutoVendidoEvent publicado (produto_id={produto_id})"
                )

        # Publicar eventos de KITs
        for kit_id, kit_info in kits_processados.items():
            # Buscar item da venda para obter preços
            item_venda = next(
                (item for item in venda.itens if item.produto_id == kit_id),
                None,
            )

            if item_venda:
                evento_kit = KitVendidoEvent(
                    venda_id=venda.id,
                    kit_id=kit_id,
                    kit_nome=kit_info["kit_nome"],
                    tipo_kit=kit_info["tipo_kit"],
                    quantidade=float(kit_info.get("quantidade", item_venda.quantidade)),
                    preco_unitario=float(item_venda.preco_unitario or 0),
                    preco_total=float(item_venda.preco_total or 0),
                    componentes_baixados=kit_info.get("componentes", []),
                    estoque_kit_anterior=float(kit_info.get("estoque_anterior"))
                    if kit_info.get("estoque_anterior")
                    else None,
                    estoque_kit_novo=float(kit_info.get("estoque_novo"))
                    if kit_info.get("estoque_novo")
                    else None,
                    user_id=user_id,
                )
                publish_event(evento_kit)
                logger.debug(
                    f"📢 KitVendidoEvent publicado (kit_id={kit_id}, tipo={kit_info['tipo_kit']})"
                )

        logger.info(
            f"📢 Eventos publicados: 1 VendaRealizadaEvent, "
            f"{len(produtos_processados)} ProdutoVendidoEvent, "
            f"{len(kits_processados)} KitVendidoEvent"
        )

    except Exception as e:
        logger.error(
            f"⚠️  Erro ao publicar novos eventos de domínio: {str(e)}",
            exc_info=True,
        )
        # Não aborta a finalização

    # ============================================================
