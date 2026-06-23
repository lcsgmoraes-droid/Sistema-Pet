"""Rotas de devolução de vendas."""

import logging
from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.audit_log import log_action
from app.auth.dependencies import get_current_user_and_tenant
from app.caixa.service import CaixaService
from app.db import get_session
from app.estoque.service import EstoqueService
from app.utils.security_helpers import safe_get_cliente
from app.vendas.routes_common import _validar_tenant_e_obter_usuario
from app.vendas_models import Venda, VendaItem

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/{venda_id}/devolucao")
def registrar_devolucao(
    venda_id: int,
    dados: dict,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Registrar devolução de itens de uma venda"""
    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)

    try:
        logger.info(f"\n{'=' * 80}")
        logger.info(f"🔄 INICIANDO DEVOLUÇÃO - Venda #{venda_id}")
        logger.info("=" * 80)
        logger.info("Dados de devolucao recebidos")
        logger.info("Usuario autenticado para devolucao")
        logger.info("Tenant validado para devolucao")

        # Buscar a venda
        venda = db.query(Venda).filter_by(id=venda_id, tenant_id=tenant_id).first()

        if not venda:
            logger.info(f"❌ Venda #{venda_id} não encontrada")
            raise HTTPException(status_code=404, detail="Venda não encontrada")

        logger.info(
            f"✅ Venda encontrada: #{venda.numero_venda} - Total: R$ {venda.total}"
        )

        caixa_id = dados.get("caixa_id")
        itens_devolucao = dados.get("itens", [])
        motivo = dados.get("motivo", "")
        gerar_credito = dados.get("gerar_credito", False)  # 🆕 Nova opção

        logger.info(f"💰 Modo: {'CRÉDITO ao cliente' if gerar_credito else 'DINHEIRO'}")
        logger.info(f"📝 Motivo: {motivo}")
        logger.info(f"📦 Itens para devolução: {len(itens_devolucao)}")

        if not caixa_id and not gerar_credito:
            logger.info("❌ Caixa ID não fornecido para devolução em dinheiro")
            raise HTTPException(
                status_code=400,
                detail="ID do caixa é obrigatório para devolução em dinheiro",
            )

        if not itens_devolucao:
            logger.info("❌ Nenhum item selecionado")
            raise HTTPException(
                status_code=400, detail="Nenhum item selecionado para devolução"
            )

        if not motivo:
            logger.info("❌ Motivo não fornecido")
            raise HTTPException(
                status_code=400, detail="Motivo da devolução é obrigatório"
            )

        # Verificar se o caixa existe e está aberto (apenas se for devolução em dinheiro)
        from app.caixa_models import Caixa

        caixa = None
        if not gerar_credito:
            caixa = db.query(Caixa).filter_by(id=caixa_id, status="aberto").first()

            if not caixa:
                raise HTTPException(
                    status_code=400, detail="Caixa não encontrado ou não está aberto"
                )

        valor_total_devolucao = 0
        itens_devolvidos = []

        # Processar cada item devolvido
        for item_dev in itens_devolucao:
            # 🆕 Verificar se é componente de KIT
            is_componente_kit = item_dev.get("is_componente_kit", False)

            if is_componente_kit:
                # 🔥 DEVOLUÇÃO DE COMPONENTE DE KIT
                produto_id = item_dev.get("produto_id")
                quantidade_devolvida = float(item_dev.get("quantidade", 0))
                preco_unitario_componente = float(item_dev.get("preco_unitario", 0))
                kit_item_id = item_dev.get("kit_item_id")

                if quantidade_devolvida <= 0:
                    continue

                logger.info(
                    f"📦 Devolvendo componente do KIT - Produto ID: {produto_id}, Quantidade: {quantidade_devolvida}"
                )

                # Devolver componente ao estoque
                try:
                    EstoqueService.estornar_estoque(
                        produto_id=produto_id,
                        quantidade=quantidade_devolvida,
                        motivo="devolucao",
                        referencia_id=venda_id,
                        referencia_tipo="venda",
                        user_id=current_user.id,
                        tenant_id=tenant_id,
                        db=db,
                        documento=None,
                        observacao=f"{motivo} - Componente de KIT (Item #{kit_item_id})",
                    )

                    # Buscar nome do produto
                    from app.produtos_models import Produto

                    produto = db.query(Produto).filter_by(id=produto_id).first()
                    produto_nome = produto.nome if produto else f"Produto #{produto_id}"

                    logger.info(
                        f"  ✅ Componente estornado: {produto_nome} +{quantidade_devolvida}"
                    )

                    # Registrar auditoria
                    log_action(
                        db=db,
                        user_id=current_user.id,
                        action="update",
                        entity_type="produtos",
                        entity_id=produto_id,
                        details=f"Devolução de componente de KIT (+{quantidade_devolvida}) - Venda #{venda_id} - Motivo: {motivo}",
                    )
                except ValueError as e:
                    logger.error(f"Erro ao devolver componente de KIT: {e}")

                # Calcular valor devolvido do componente
                valor_componente = Decimal(str(preco_unitario_componente)) * Decimal(
                    str(quantidade_devolvida)
                )
                valor_total_devolucao += valor_componente

                itens_devolvidos.append(
                    {
                        "produto_id": produto_id,
                        "produto_nome": produto_nome,
                        "quantidade": quantidade_devolvida,
                        "valor_unitario": preco_unitario_componente,
                        "valor_total": valor_componente,
                        "tipo": "componente_kit",
                    }
                )

            else:
                # 🔹 DEVOLUÇÃO NORMAL (Item inteiro - pode ser KIT inteiro ou produto simples)
                item_id = item_dev.get("item_id")
                quantidade_devolvida = float(item_dev.get("quantidade", 0))

                if quantidade_devolvida <= 0:
                    continue

                # Buscar o item da venda
                item_venda = (
                    db.query(VendaItem).filter_by(id=item_id, venda_id=venda_id).first()
                )

                if not item_venda:
                    raise HTTPException(
                        status_code=404,
                        detail=f"Item {item_id} não encontrado na venda",
                    )

                if quantidade_devolvida > item_venda.quantidade:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Quantidade devolvida ({quantidade_devolvida}) maior que quantidade vendida ({item_venda.quantidade})",
                    )

                # Devolver ao estoque
                if item_venda.produto_id:
                    try:
                        EstoqueService.estornar_estoque(
                            produto_id=item_venda.produto_id,
                            quantidade=quantidade_devolvida,
                            motivo="devolucao",
                            referencia_id=venda_id,
                            referencia_tipo="venda",
                            user_id=current_user.id,
                            tenant_id=tenant_id,
                            db=db,
                            documento=None,
                            observacao=motivo,
                        )
                        # Registrar auditoria
                        log_action(
                            db=db,
                            user_id=current_user.id,
                            action="update",
                            entity_type="produtos",
                            entity_id=item_venda.produto_id,
                            details=f"Devolução de estoque (+{quantidade_devolvida}) - Venda #{venda_id} - Motivo: {motivo}",
                        )
                    except ValueError as e:
                        logger.error(f"Erro ao devolver estoque: {e}")

                # Calcular valor devolvido
                valor_item = item_venda.preco_unitario * Decimal(
                    str(quantidade_devolvida)
                )
                valor_total_devolucao += valor_item

                itens_devolvidos.append(
                    {
                        "produto_id": item_venda.produto_id,
                        "produto_nome": item_venda.produto.nome
                        if item_venda.produto
                        else item_venda.servico_descricao,
                        "quantidade": quantidade_devolvida,
                        "valor_unitario": item_venda.preco_unitario,
                        "valor_total": valor_item,
                        "tipo": "item_normal",
                    }
                )

        # 💰 OPÇÃO 1: GERAR CRÉDITO PARA O CLIENTE
        if gerar_credito:
            if not venda.cliente_id:
                raise HTTPException(
                    status_code=400,
                    detail="Não é possível gerar crédito para venda sem cliente cadastrado",
                )

            # 🔒 SEGURANÇA: Validar que o cliente pertence ao usuário
            cliente = safe_get_cliente(db, venda.cliente_id, current_user.id)

            # Adicionar crédito ao cliente
            cliente.credito = (cliente.credito or Decimal("0")) + Decimal(
                str(valor_total_devolucao)
            )
            logger.info(
                f"💰 Crédito adicionado ao cliente {cliente.nome}: +R$ {valor_total_devolucao:.2f} (Total: R$ {cliente.credito:.2f})"
            )

            # Não cria MovimentacaoCaixa nem LancamentoManual (apenas crédito)

        # 💵 OPÇÃO 2: DEVOLUÇÃO EM DINHEIRO
        else:
            # Verificar se o caixa existe e está aberto
            from app.caixa_models import Caixa

            caixa = db.query(Caixa).filter_by(id=caixa_id, status="aberto").first()

            if not caixa:
                raise HTTPException(
                    status_code=400, detail="Caixa não encontrado ou não está aberto"
                )

            # Registrar devolução no caixa usando o service
            movimentacao = CaixaService.registrar_devolucao(
                caixa_id=caixa_id,
                venda_id=venda_id,
                venda_numero=venda.numero_venda,
                valor=valor_total_devolucao,
                motivo=motivo,
                user_id=current_user.id,
                user_nome=current_user.nome,
                tenant_id=tenant_id,  # 🔒 Isolamento multi-tenant
                db=db,
            )

            # Criar lançamento manual de saída (estorno no fluxo de caixa)
            from app.financeiro_models import LancamentoManual, CategoriaFinanceira

            categoria_devolucoes = (
                db.query(CategoriaFinanceira)
                .filter(
                    CategoriaFinanceira.nome.ilike("%devolução%"),
                    CategoriaFinanceira.tipo == "despesa",
                    CategoriaFinanceira.tenant_id == tenant_id,
                )
                .first()
            )

            if not categoria_devolucoes:
                categoria_devolucoes = CategoriaFinanceira(
                    nome="Devoluções de Vendas",
                    tipo="despesa",
                    user_id=current_user.id,
                    tenant_id=tenant_id,
                )
                db.add(categoria_devolucoes)
                db.flush()

            lancamento_devolucao = LancamentoManual(
                tipo="saida",
                valor=Decimal(str(valor_total_devolucao)),
                descricao=f"Devolução venda {venda.numero_venda} - {motivo}",
                data_lancamento=date.today(),
                status="realizado",
                categoria_id=categoria_devolucoes.id,
                documento=f"DEVOLUCAO-{venda_id}",
                fornecedor_cliente=venda.cliente.nome
                if venda.cliente
                else "Cliente Avulso",
                user_id=current_user.id,
                tenant_id=tenant_id,
            )
            db.add(lancamento_devolucao)
            logger.info(
                f"📊 Lançamento de devolução criado: R$ {valor_total_devolucao:.2f}"
            )

        # 🆕 AJUSTAR CONTAS A RECEBER (sempre, independente de crédito ou dinheiro)
        from app.financeiro_models import (
            ContaReceber,
            LancamentoManual,
            CategoriaFinanceira,
        )

        contas_receber = db.query(ContaReceber).filter_by(venda_id=venda_id).all()
        if contas_receber:
            # Reduzir proporcionalmente o valor das contas pendentes ou estornar pagas
            for conta in contas_receber:
                if conta.status in ["pendente", "parcial"]:
                    proporcao = float(valor_total_devolucao) / float(venda.total)
                    reducao = float(conta.valor_original) * proporcao

                    conta.valor_original -= Decimal(str(reducao))
                    conta.valor_final -= Decimal(str(reducao))

                    # Se ficou zerada, marcar como cancelada
                    if conta.valor_final <= 0:
                        conta.status = "cancelada"

                    logger.info(
                        f"💳 Ajustando ContaReceber #{conta.id}: -R$ {reducao:.2f}"
                    )
                elif conta.status == "pago":
                    # Cancelar a conta paga (estorno)
                    conta.status = "estornada"
                    logger.info(f"💳 Estornando ContaReceber #{conta.id} (paga)")

        # 🆕 MARCAR LANÇAMENTOS MANUAIS REALIZADOS COMO ESTORNADOS (Fluxo de Caixa)
        # Não criar novos lançamentos de estorno — o DEVOLUCAO acima já registra a saída.
        # Apenas marcar os lançamentos de entrada da venda como estornados para controle.
        lancamentos_entrada = (
            db.query(LancamentoManual)
            .filter(
                LancamentoManual.documento == f"VENDA-{venda_id}",
                LancamentoManual.tipo == "entrada",
                LancamentoManual.status == "realizado",
            )
            .all()
        )
        for lanc in lancamentos_entrada:
            lanc.status = "estornado"
            logger.info(f"💸 LancamentoManual #{lanc.id} marcado como estornado")

        # 🆕 ATUALIZAR STATUS DA VENDA
        if (
            float(valor_total_devolucao) >= float(venda.total) * 0.99
        ):  # 99% devolvido = total
            venda.status = "devolvida_total"
        else:
            venda.status = "finalizada_devolucao"

        # 📝 GERAR HISTÓRICO DE DEVOLUÇÃO NA OBSERVAÇÃO
        from datetime import datetime

        # Determinar tipo de devolução
        if float(valor_total_devolucao) >= float(venda.total) * 0.99:
            tipo_desc = "Devolução total"
        else:
            # Verificar se tem componentes de KIT
            tem_componentes = any(
                item.get("tipo") == "componente_kit" for item in itens_devolvidos
            )
            if tem_componentes:
                tipo_desc = "Devolução parcial por componentes de KIT"
            else:
                tipo_desc = "Devolução parcial"

        # Montar histórico
        historico = f"\n\n{'=' * 60}\n"
        historico += f"[DEVOLUÇÃO | {datetime.now().strftime('%d/%m/%Y %H:%M')}]\n"
        historico += f"Usuário: {current_user.nome}\n"
        historico += f"Tipo: {tipo_desc}\n"

        # Agrupar itens por tipo
        itens_kit = [i for i in itens_devolvidos if i.get("tipo") == "componente_kit"]
        itens_normais = [
            i for i in itens_devolvidos if i.get("tipo") != "componente_kit"
        ]

        # Listar itens normais
        if itens_normais:
            historico += "Itens devolvidos:\n"
            for item in itens_normais:
                historico += f"  • {item['produto_nome']} → {item['quantidade']} un (R$ {float(item['valor_total']):.2f})\n"

        # Listar componentes de KIT
        if itens_kit:
            historico += "Componentes de KIT devolvidos:\n"
            for item in itens_kit:
                historico += f"  • {item['produto_nome']} → {item['quantidade']} un (R$ {float(item['valor_total']):.2f})\n"

        historico += f"Motivo: {motivo}\n"
        historico += "Forma de estorno:\n"

        if gerar_credito:
            historico += (
                f"  • Crédito em cliente → R$ {float(valor_total_devolucao):.2f}\n"
            )
        else:
            historico += (
                f"  • Dinheiro (Caixa) → R$ {float(valor_total_devolucao):.2f}\n"
            )

        historico += f"Valor total estornado: R$ {float(valor_total_devolucao):.2f}\n"
        historico += f"{'=' * 60}"

        # Anexar histórico à observação (APPEND, nunca sobrescrever)
        if venda.observacoes:
            venda.observacoes = venda.observacoes + historico
        else:
            venda.observacoes = historico.lstrip()

        logger.info("📝 Histórico de devolução adicionado às observações da venda")

        # Registrar auditoria da devolução
        tipo_devolucao = "Crédito ao cliente" if gerar_credito else "Dinheiro"
        log_action(
            db=db,
            user_id=current_user.id,
            action="devolucao",
            entity_type="vendas",
            entity_id=venda_id,
            details=f"Devolução registrada ({tipo_devolucao}) - Venda #{venda_id} - R$ {valor_total_devolucao:.2f} - Motivo: {motivo}",
        )

        db.commit()

        resultado = {
            "message": "Devolução registrada com sucesso",
            "venda_id": venda_id,
            "valor_total_devolucao": float(valor_total_devolucao),
            "tipo_devolucao": tipo_devolucao,
            "status_venda": venda.status,
            "itens_devolvidos": itens_devolvidos,
        }

        if gerar_credito:
            # 🔒 SEGURANÇA: Validar que o cliente pertence ao usuário
            cliente = safe_get_cliente(db, venda.cliente_id, current_user.id)
            resultado["credito_cliente"] = float(cliente.credito)
            resultado["cliente_nome"] = cliente.nome
        else:
            resultado["movimentacao_caixa_id"] = movimentacao["movimentacao_id"]

        logger.info("✅ Devolução concluída com sucesso!")
        logger.info(f"{'=' * 80}\n")
        return resultado

    except HTTPException:
        raise
    except Exception as e:
        logger.info(f"\n{'=' * 80}")
        logger.info("🚨 ERRO CRÍTICO NA DEVOLUÇÃO:")
        logger.info(f"{'=' * 80}")
        logger.info(f"Tipo: {type(e).__name__}")
        logger.info(f"Mensagem: {str(e)}")
        import traceback

        logger.info("Traceback completo:")
        traceback.print_exc()
        logger.info(f"{'=' * 80}\n")
        db.rollback()
        raise HTTPException(
            status_code=500, detail=f"Erro ao processar devolução: {str(e)}"
        )


# ============================================================================
# ENDPOINTS - RELATÓRIOS
