# -*- coding: utf-8 -*-
# ⚠️ ARQUIVO CRÍTICO DE PRODUÇÃO
# Este arquivo impacta diretamente operações reais (PDV / Financeiro / Estoque).
# NÃO alterar sem:
# 1. Entender o fluxo completo
# 2. Testar cenário real
# 3. Validar impacto financeiro

"""
Serviço de Vendas - Orquestrador Central do Domínio de Vendas
==============================================================

Este serviço centraliza TODA a lógica de negócio de vendas,
orquestrando os services especializados em transações atômicas.

RESPONSABILIDADES:
------------------
1. Criar vendas (com validações e geração de número)
2. Finalizar vendas (orquestração atômica)
3. Cancelar vendas (estorno completo)
4. Coordenar EstoqueService, CaixaService, ContasReceberService, ComissoesService
5. Gerenciar transações (commit/rollback)
6. Validar regras de negócio de vendas
7. Atualizar status de vendas
8. Auditoria completa

IMPORTANTE - DECISÕES DE ARQUITETURA:
-------------------------------------
✅ Este é o ÚNICO lugar onde commits de venda acontecem
✅ Transação atômica: tudo ou nada
✅ Services não fazem commit (apenas flush)
✅ Rollback automático em caso de erro
✅ Operações secundárias (comissões, lembretes) FORA da transação crítica
✅ TODAS as regras de negócio concentradas aqui

FLUXO COMPLETO:
---------------

CRIAR VENDA:
1. Validar payload (itens, cliente, etc)
2. Gerar número sequencial da venda
3. Calcular totais (subtotal, desconto, frete)
4. Criar venda + itens
5. Criar lançamento previsto e conta a receber
6. COMMIT
7. Retornar venda criada

FINALIZAR VENDA:
1. Validar venda e caixa
2. Processar pagamentos
3. Atualizar status
4. Baixar estoque
5. Vincular ao caixa
6. Baixar contas a receber
7. COMMIT
8. Operações pós-commit (comissões, lembretes)

CANCELAR VENDA:
1. Validar venda e permissões
2. Estornar estoque
3. Cancelar contas a receber
4. Remover movimentações
5. Estornar comissões
6. Marcar como cancelada
7. COMMIT
8. Auditoria

PADRÃO DE USO:
--------------
```python
from app.vendas import VendaService

# Criar venda
venda_dict = VendaService.criar_venda(
    payload={
        'cliente_id': 10,
        'itens': [...],
        'desconto_valor': 0,
        'taxa_entrega': 0
    },
    user_id=1,
    db=db
)

# Finalizar venda
resultado = VendaService.finalizar_venda(
    venda_id=120,
    pagamentos=[{'forma_pagamento': 'Dinheiro', 'valor': 100.0}],
    user_id=1,
    user_nome="João Silva",
    db=db
)

# Cancelar venda
resultado_cancelamento = VendaService.cancelar_venda(
    venda_id=120,
    motivo="Cliente desistiu",
    user_id=1,
    db=db
)
```

AUTOR: Sistema Pet Shop - Refatoração DDD Completa
DATA: 2025-01-23
"""

import logging
from typing import Any, Dict, List, Optional
from decimal import Decimal
from datetime import date, timedelta
from fastapi import HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc, or_, func
from uuid import UUID

from app.produtos_models import Produto as Produto
from app.vendas_models import (
    Venda as Venda,
    VendaItem as VendaItem,
    VendaPagamento as VendaPagamento,
)

# Timezone Brasília
from app.utils.timezone import now_brasilia
from app.services.venda_rentabilidade_snapshot_service import (
    get_or_build_venda_rentabilidade_snapshot,
    invalidate_venda_rentabilidade_snapshot,
)

# Services
from app.estoque.service import EstoqueService
from app.db.transaction import transactional_session
from app.vendas.pos_processamento import (
    gerar_dre_competencia_venda,
    processar_comissoes_venda,
    processar_contas_pagar_entrega,
    processar_contas_pagar_taxas,
    processar_lembretes_venda,
)

# Logger
logger = logging.getLogger(__name__)

__all__ = [
    "VendaService",
    "_calcular_pagamentos_finalizacao",
    "gerar_dre_competencia_venda",
    "processar_comissoes_venda",
    "processar_contas_pagar_entrega",
    "processar_contas_pagar_taxas",
    "processar_lembretes_venda",
]


def _calcular_pagamentos_finalizacao(
    *,
    total_venda: Any,
    pagamentos_existentes: List[Any],
    pagamentos_novos: List[Dict[str, Any]],
) -> Dict[str, float]:
    total_venda_float = float(total_venda or 0)
    total_ja_pago = sum(float(p.valor) for p in pagamentos_existentes)
    total_novos_pagamentos = sum(float(p.get("valor") or 0) for p in pagamentos_novos)
    valor_restante_bruto = total_venda_float - total_ja_pago

    if not pagamentos_novos and total_ja_pago < total_venda_float - 0.01:
        raise HTTPException(
            status_code=400, detail="Informe pelo menos uma forma de pagamento"
        )

    if valor_restante_bruto <= 0.01 and total_novos_pagamentos > 0.01:
        raise HTTPException(status_code=400, detail="Venda já está totalmente paga")

    if total_novos_pagamentos > valor_restante_bruto + 0.01:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Valor dos pagamentos excede o saldo da venda. "
                f"Saldo: R$ {max(0, valor_restante_bruto):.2f}, "
                f"informado: R$ {total_novos_pagamentos:.2f}."
            ),
        )

    return {
        "total_ja_pago": total_ja_pago,
        "total_novos_pagamentos": total_novos_pagamentos,
        "total_pagamentos": total_ja_pago + total_novos_pagamentos,
        "valor_restante": max(0, valor_restante_bruto),
    }


class VendaService:
    """
    Serviço orquestrador para vendas com transação atômica.

    Este serviço coordena EstoqueService, CaixaService, ContasReceberService e ComissoesService
    em transações únicas, garantindo atomicidade (tudo ou nada).

    Métodos principais:
    - criar_venda: Cria uma nova venda com validações e cálculos
    - finalizar_venda: Finaliza venda com pagamentos e baixa de estoque
    - cancelar_venda: Cancela venda com estorno completo
    """

    @staticmethod
    def criar_venda(
        payload: Dict[str, Any], user_id: int, db: Session
    ) -> Dict[str, Any]:
        """
        Cria uma nova venda com todas as validações e cálculos necessários.

        Operações executadas:
        1. Validar payload (itens obrigatórios, cliente, etc)
        2. Gerar número sequencial da venda
        3. Calcular totais (subtotal, desconto, frete)
        4. Criar registro de venda
        5. Criar itens da venda
        6. Criar lançamento financeiro previsto
        7. Criar conta a receber inicial
        8. COMMIT
        9. Retornar venda criada

        Args:
            payload: Dict com dados da venda:
                - cliente_id: Optional[int]
                - vendedor_id: Optional[int]
                - funcionario_id: Optional[int]
                - itens: List[dict] (obrigatório)
                - desconto_valor: float
                - desconto_percentual: float
                - observacoes: Optional[str]
                - tem_entrega: bool
                - taxa_entrega: float
                - entregador_id: Optional[int]
                - loja_origem: Optional[str]
                - endereco_entrega: Optional[str]
            user_id: ID do usuário criando a venda
            db: Sessão do SQLAlchemy

        Returns:
            Dict com venda criada (formato to_dict())

        Raises:
            HTTPException(400): Validação falhou (sem itens, etc)
        """
        from app.vendas_models import Venda, VendaItem
        from app.financeiro_models import LancamentoManual, CategoriaFinanceira
        from app.audit_log import log_action

        logger.info(f"📝 Criando nova venda para user_id={user_id}")

        try:
            # ============================================================
            # ETAPA 1: VALIDAÇÕES
            # ============================================================

            itens = payload.get("itens", [])
            if not itens or len(itens) == 0:
                raise HTTPException(
                    status_code=400, detail="A venda deve ter pelo menos um item"
                )

            logger.debug(f"✅ Validação OK: {len(itens)} itens")

            # ============================================================
            # ETAPA 2: GERAR NÚMERO DA VENDA
            # ============================================================

            numero_venda = VendaService._gerar_numero_venda(
                db,
                tenant_id=payload.get("tenant_id"),
                user_id=user_id,
            )
            logger.debug(f"✅ Número gerado: {numero_venda}")

            # ============================================================
            # ETAPA 3: CALCULAR TOTAIS
            # ============================================================

            subtotal_itens = sum(item["subtotal"] for item in itens)
            desconto_itens = sum(
                float(item.get("desconto_item") or 0) for item in itens
            )
            desconto_valor = (
                desconto_itens
                if desconto_itens > 0
                else float(payload.get("desconto_valor", 0) or 0)
            )
            tem_entrega = bool(payload.get("tem_entrega", False))
            taxa_entrega = (payload.get("taxa_entrega", 0) or 0) if tem_entrega else 0
            total = subtotal_itens + taxa_entrega

            # 🚚 Calcular distribuição da taxa de entrega
            percentual_taxa_entregador = (
                (payload.get("percentual_taxa_entregador", 0) or 0)
                if tem_entrega
                else 0
            )
            percentual_taxa_loja = (
                (
                    payload.get("percentual_taxa_loja", 100 if taxa_entrega > 0 else 0)
                    or 0
                )
                if tem_entrega
                else 0
            )

            logger.info(
                f"📥 PAYLOAD RECEBIDO - percentual_taxa_entregador: {percentual_taxa_entregador}, percentual_taxa_loja: {percentual_taxa_loja}"
            )

            # Se não foi informado percentual mas tem taxa, assumir 100% para loja (compatibilidade)
            if (
                taxa_entrega > 0
                and percentual_taxa_entregador == 0
                and percentual_taxa_loja == 0
            ):
                percentual_taxa_loja = 100

            # Calcular valores baseados nos percentuais
            valor_taxa_entregador = (
                (taxa_entrega * percentual_taxa_entregador / 100)
                if taxa_entrega > 0
                else 0
            )
            valor_taxa_loja = (
                (taxa_entrega * percentual_taxa_loja / 100) if taxa_entrega > 0 else 0
            )

            logger.info(
                f"💰 Totais: Subtotal=R$ {subtotal_itens:.2f}, "
                f"Frete=R$ {taxa_entrega:.2f}, Total=R$ {total:.2f}"
            )
            if taxa_entrega > 0:
                logger.info(
                    f"🚚 Taxa entrega: Loja {percentual_taxa_loja}% (R$ {valor_taxa_loja:.2f}), "
                    f"Entregador {percentual_taxa_entregador}% (R$ {valor_taxa_entregador:.2f})"
                )

            # ============================================================
            # ETAPA 4: CRIAR VENDA
            # ============================================================

            venda = Venda(
                numero_venda=numero_venda,
                cliente_id=payload.get("cliente_id"),
                vendedor_id=payload.get("vendedor_id") or user_id,
                funcionario_id=payload.get("funcionario_id"),
                subtotal=float(subtotal_itens),
                desconto_valor=float(desconto_valor),  # Desconto aplicado na venda
                desconto_percentual=payload.get("desconto_percentual", 0) or 0,
                cupom_code=(
                    str(payload.get("cupom_code")).strip().upper()
                    if payload.get("cupom_code")
                    else None
                ),
                cupom_discount_applied=payload.get("cupom_discount_applied"),
                total=float(total),
                observacoes=payload.get("observacoes"),
                tem_entrega=tem_entrega,
                taxa_entrega=float(taxa_entrega),
                percentual_taxa_entregador=float(percentual_taxa_entregador),
                percentual_taxa_loja=float(percentual_taxa_loja),
                valor_taxa_entregador=float(valor_taxa_entregador),
                valor_taxa_loja=float(valor_taxa_loja),
                entregador_id=payload.get("entregador_id") if tem_entrega else None,
                loja_origem=payload.get("loja_origem") if tem_entrega else None,
                endereco_entrega=payload.get("endereco_entrega")
                if tem_entrega
                else None,
                distancia_km=payload.get("distancia_km") if tem_entrega else None,
                valor_por_km=payload.get("valor_por_km") if tem_entrega else None,
                observacoes_entrega=payload.get("observacoes_entrega")
                if tem_entrega
                else None,
                status_entrega="pendente" if tem_entrega else None,
                canal=payload.get("canal", "loja_fisica"),  # Canal de venda para DRE
                status="aberta",
                data_venda=now_brasilia(),
                user_id=user_id,
                tenant_id=payload.get("tenant_id"),
            )

            # 🔒 BLINDAGEM FINAL (obrigatória) - Garante que PostgreSQL gere o ID
            venda.id = None

            db.add(venda)
            db.flush()  # Para obter o ID

            logger.info(f"✅ Venda criada: ID={venda.id}, Número={numero_venda}")

            # ============================================================
            # ETAPA 5: CRIAR ITENS
            # ============================================================

            from app.produtos_models import Produto

            for item_data in itens:
                # 🔒 VALIDAÇÃO CRÍTICA: XOR entre produto_id e product_variation_id
                produto_id = item_data.get("produto_id")
                product_variation_id = item_data.get("product_variation_id")

                if item_data.get("tipo") == "produto":
                    # Valida XOR: OU produto_id OU product_variation_id
                    if not produto_id and not product_variation_id:
                        raise HTTPException(
                            status_code=400,
                            detail="Item de venda deve conter product_id ou product_variation_id",
                        )

                    if produto_id and product_variation_id:
                        raise HTTPException(
                            status_code=400,
                            detail="Item de venda não pode conter product_id e product_variation_id ao mesmo tempo",
                        )

                    # Se for produto simples, valida e busca preço
                    if produto_id:
                        produto = (
                            db.query(Produto)
                            .filter(
                                Produto.id == produto_id,
                                Produto.tenant_id == payload.get("tenant_id"),
                            )
                            .first()
                        )

                        if not produto:
                            raise HTTPException(
                                status_code=404,
                                detail=f"Produto ID {produto_id} não encontrado",
                            )

                        if produto.tipo_produto == "PAI":
                            raise HTTPException(
                                status_code=400,
                                detail=f"Produto '{produto.nome}' é do tipo PAI e não pode ser vendido. Selecione uma variação.",
                            )

                    # Se for variação, valida e busca preço
                    if product_variation_id:
                        from app.produtos_models import Produto

                        variacao = (
                            db.query(Produto)
                            .filter(
                                Produto.id == product_variation_id,
                                Produto.tipo_produto == "VARIACAO",
                            )
                            .first()
                        )

                        if not variacao:
                            raise HTTPException(
                                status_code=404,
                                detail=f"Variação de produto ID {product_variation_id} não encontrada",
                            )

                # 🔒 ISOLAMENTO MULTI-TENANT: tenant_id obrigatório
                item = VendaItem(
                    venda_id=venda.id,
                    tenant_id=payload.get(
                        "tenant_id"
                    ),  # ✅ Dupla proteção: injeção automática + explícita
                    tipo=item_data.get("tipo", "produto"),
                    produto_id=produto_id,
                    product_variation_id=product_variation_id,
                    servico_descricao=item_data.get("servico_descricao"),
                    quantidade=item_data["quantidade"],
                    preco_unitario=item_data["preco_unitario"],
                    desconto_item=item_data.get("desconto_item", 0) or 0,
                    subtotal=item_data["subtotal"],
                    lote_id=item_data.get("lote_id"),
                    pet_id=item_data.get("pet_id"),
                )
                db.add(item)

            # 🔥 CRÍTICO: Flush para persistir os itens antes de baixar estoque
            db.flush()

            logger.debug(f"✅ {len(itens)} itens adicionados")

            # ============================================================
            # ETAPA 6: CRIAR LANÇAMENTO PREVISTO E CONTA A RECEBER
            # ============================================================

            # Buscar ou criar categoria de receitas
            tenant_id = payload.get("tenant_id")
            categoria_receitas = (
                db.query(CategoriaFinanceira)
                .filter(
                    CategoriaFinanceira.nome.ilike("%vendas%"),
                    CategoriaFinanceira.tipo == "receita",
                    CategoriaFinanceira.user_id == user_id,
                    CategoriaFinanceira.tenant_id == tenant_id,
                )
                .first()
            )

            if not categoria_receitas:
                categoria_receitas = CategoriaFinanceira(
                    nome="Receitas de Vendas",
                    tipo="receita",
                    user_id=user_id,
                    tenant_id=tenant_id,
                )
                db.add(categoria_receitas)
                db.flush()

            # Criar lançamento previsto (30 dias)
            prazo_dias = 30
            data_prevista = date.today() + timedelta(days=prazo_dias)

            lancamento = LancamentoManual(
                tipo="entrada",
                valor=Decimal(str(total)),
                descricao=f"Venda {numero_venda} - A receber",
                data_lancamento=data_prevista,
                status="previsto",
                categoria_id=categoria_receitas.id,
                documento=f"VENDA-{venda.id}",
                fornecedor_cliente=venda.cliente.nome
                if venda.cliente
                else "Cliente Avulso",
                user_id=user_id,
                tenant_id=tenant_id,
            )
            db.add(lancamento)

            # ⚠️ IMPORTANTE: Contas a receber NÃO são criadas aqui!
            # Elas são criadas durante a FINALIZAÇÃO da venda (ContasReceberService.criar_de_venda)
            # Isso evita duplicação e permite tratamento correto de parcelamento

            logger.info(
                f"📊 Lançamento previsto criado (R$ {total:.2f} em {data_prevista})"
            )

            # ============================================================
            # ETAPA 6.5: BAIXAR ESTOQUE IMEDIATAMENTE (PRODUTOS SEPARADOS)
            # ============================================================
            # 🎯 NOVO FLUXO: Estoque é baixado no momento da criação da venda
            # Motivo: Produtos são fisicamente separados ao criar a venda (pedido/entrega)

            logger.info(
                f"🔍 Iniciando baixa de estoque para venda #{venda.id} ({numero_venda})"
            )

            estoque_baixado = []

            # Buscar itens recém-criados
            itens_criados = db.query(VendaItem).filter_by(venda_id=venda.id).all()
            logger.info(
                f"📋 Encontrados {len(itens_criados)} itens para processar estoque"
            )

            for item in itens_criados:
                logger.info(
                    f"  → Item: tipo={item.tipo}, produto_id={item.produto_id}, qtd={item.quantidade}"
                )

                if item.tipo == "produto" and item.produto_id:
                    try:
                        from app.produtos_models import Produto

                        # Buscar produto
                        produto = (
                            db.query(Produto)
                            .filter(
                                Produto.id == item.produto_id,
                                Produto.tenant_id == tenant_id,
                            )
                            .first()
                        )

                        if not produto:
                            logger.warning(
                                f"⚠️  Produto {item.produto_id} não encontrado ao criar venda"
                            )
                            continue

                        # Baixar estoque
                        resultados = VendaService._processar_baixa_estoque_item(
                            produto=produto,
                            quantidade_vendida=float(item.quantidade),
                            venda_id=venda.id,
                            user_id=user_id,
                            tenant_id=tenant_id,
                            db=db,
                            product_variation_id=None,
                            venda_codigo=numero_venda,
                        )

                        estoque_baixado.extend(resultados)
                        logger.info(
                            f"📦 Estoque baixado ao criar venda: {produto.nome} -{item.quantidade}"
                        )

                    except Exception as e:
                        logger.error(
                            f"❌ Erro ao baixar estoque do produto {item.produto_id}: {e}"
                        )
                        # Reverter transação se falhar baixa de estoque
                        db.rollback()
                        raise HTTPException(
                            status_code=400, detail=f"Erro ao baixar estoque: {str(e)}"
                        )

            if estoque_baixado:
                logger.info(
                    f"✅ Estoque baixado: {len(estoque_baixado)} item(ns) processado(s)"
                )

            # ============================================================
            # ETAPA 7: COMMIT
            # ============================================================

            db.commit()
            db.refresh(venda)

            logger.info(f"✅ ✅ ✅ Venda {numero_venda} criada com sucesso! ✅ ✅ ✅")

            # ============================================================
            # ETAPA 8: AUDITORIA
            # ============================================================

            log_action(
                db,
                user_id,
                "CREATE",
                "vendas",
                venda.id,
                details=f"Venda {numero_venda} criada - Total: R$ {total:.2f}",
            )

            # ============================================================
            # ETAPA 9: EMITIR EVENTO DE DOMÍNIO
            # ============================================================

            # 🔒 EVENTOS DESABILITADOS TEMPORARIAMENTE (publish_event não exportado)
            # try:
            #     from app.domain.events import VendaCriada, publish_event
            #
            #     evento = VendaCriada(
            #         venda_id=venda.id,
            #         numero_venda=venda.numero_venda,
            #         user_id=user_id,
            #         cliente_id=venda.cliente_id,
            #         funcionario_id=venda.funcionario_id,
            #         total=float(venda.total),
            #         quantidade_itens=len(itens),
            #         tem_entrega=venda.tem_entrega,
            #         metadados={
            #             'taxa_entrega': float(taxa_entrega),
            #             'subtotal': float(subtotal_itens)
            #         }
            #     )
            #
            #     publish_event(evento)
            #     logger.debug(f"📢 Evento VendaCriada publicado (venda_id={venda.id})")
            #
            # except Exception as e:
            #     logger.error(f"⚠️  Erro ao publicar evento VendaCriada: {str(e)}", exc_info=True)
            #     # Não aborta a criação da venda

            try:
                from app.domain.events import VendaCriada, publish_event

                publish_event(
                    VendaCriada(
                        venda_id=venda.id,
                        numero_venda=venda.numero_venda,
                        user_id=user_id,
                        cliente_id=venda.cliente_id,
                        funcionario_id=venda.funcionario_id,
                        total=float(venda.total),
                        quantidade_itens=len(itens),
                        tem_entrega=venda.tem_entrega,
                        metadados={
                            "taxa_entrega": float(taxa_entrega),
                            "subtotal": float(subtotal_itens),
                        },
                    )
                )
                logger.debug("Evento VendaCriada publicado (venda_id=%s)", venda.id)
            except Exception as e:
                logger.error(
                    "Erro ao publicar evento VendaCriada: %s", str(e), exc_info=True
                )

            return venda.to_dict()

        except HTTPException:
            db.rollback()
            logger.error("❌ HTTPException ao criar venda - Rollback executado")
            raise

        except Exception as e:
            db.rollback()
            logger.error(f"❌ ERRO CRÍTICO ao criar venda: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=500, detail=f"Erro ao criar venda: {str(e)}"
            )

    @staticmethod
    def _processar_baixa_estoque_item(
        produto: "Produto",
        quantidade_vendida: float,
        venda_id: int,
        user_id: int,
        tenant_id: str,
        db: Session,
        product_variation_id: int = None,
        venda_codigo: str = None,
    ) -> List[Dict[str, Any]]:
        """
        Processa a baixa de estoque de um item de venda.

        Comportamento por tipo de produto:
        - SIMPLES/VARIACAO: Baixa estoque do próprio produto (ou da variação se product_variation_id fornecido)
        - KIT FÍSICO: Baixa estoque do KIT (tratado como produto simples)
        - KIT VIRTUAL: Baixa estoque de cada componente em cascata

        Args:
            produto: Objeto Produto (com tipo_produto e tipo_kit)
            quantidade_vendida: Quantidade vendida do produto
            venda_id: ID da venda
            user_id: ID do usuário (tenant)
            db: Sessão do banco (NÃO faz commit)
            product_variation_id: ID da variação do produto (se aplicável)

        Returns:
            List[Dict] com resultados da baixa de estoque para cada produto afetado

        Raises:
            ValueError: Se estoque insuficiente ou componente inválido
        """
        resultados = []

        # Se tiver product_variation_id, usar o produto da variação
        if product_variation_id:
            from app.produtos_models import Produto

            variacao = (
                db.query(Produto)
                .filter(
                    Produto.id == product_variation_id,
                    Produto.tipo_produto == "VARIACAO",
                )
                .first()
            )

            if variacao:
                produto = (
                    variacao  # A variação é o próprio produto a ser baixado do estoque
                )

        # ============================================================
        # CASO 1: PRODUTO SIMPLES OU VARIAÇÃO
        # ============================================================
        if produto.tipo_produto in ("SIMPLES", "VARIACAO"):
            resultado_estoque = EstoqueService.baixar_estoque(
                produto_id=produto.id,
                quantidade=quantidade_vendida,
                motivo="venda",
                referencia_id=venda_id,
                referencia_tipo="venda",
                user_id=user_id,
                tenant_id=tenant_id,
                db=db,
                documento=venda_codigo,
                observacao=None,
            )

            resultados.append(
                {
                    "produto": resultado_estoque["produto_nome"],
                    "produto_id": produto.id,
                    "tipo_produto": produto.tipo_produto,
                    "quantidade": quantidade_vendida,
                    "estoque_anterior": resultado_estoque["estoque_anterior"],
                    "estoque_novo": resultado_estoque["estoque_novo"],
                }
            )

            logger.info(
                f"📦 Estoque baixado: {resultado_estoque['produto_nome']} - "
                f"Qtd: {quantidade_vendida} ({resultado_estoque['estoque_anterior']} → {resultado_estoque['estoque_novo']})"
            )

            return resultados

        # ============================================================
        # CASO 2: PRODUTO KIT
        # ============================================================
        if produto.tipo_produto == "KIT":
            tipo_kit = produto.tipo_kit or "VIRTUAL"  # Default VIRTUAL se não definido

            # --------------------------------------------------------
            # CASO 2.1: KIT FÍSICO (tratado como produto simples)
            # LÓGICA: Venda de kit físico só baixa o estoque do KIT
            # Os componentes já foram baixados quando o kit foi montado (entrada)
            # Portanto, NÃO sensibiliza os componentes novamente
            # --------------------------------------------------------
            if tipo_kit == "FISICO":
                resultado_estoque = EstoqueService.baixar_estoque(
                    produto_id=produto.id,
                    quantidade=quantidade_vendida,
                    motivo="venda",
                    referencia_id=venda_id,
                    referencia_tipo="venda",
                    user_id=user_id,
                    tenant_id=tenant_id,
                    db=db,
                    documento=venda_codigo,
                    observacao="KIT FÍSICO - Estoque próprio (componentes já foram baixados na montagem)",
                )

                resultados.append(
                    {
                        "produto": resultado_estoque["produto_nome"],
                        "produto_id": produto.id,
                        "tipo_produto": "KIT",
                        "tipo_kit": "FISICO",
                        "quantidade": quantidade_vendida,
                        "estoque_anterior": resultado_estoque["estoque_anterior"],
                        "estoque_novo": resultado_estoque["estoque_novo"],
                    }
                )

                logger.info(
                    f"📦 KIT FÍSICO vendido: {resultado_estoque['produto_nome']} - "
                    f"Qtd: {quantidade_vendida} ({resultado_estoque['estoque_anterior']} → {resultado_estoque['estoque_novo']}) "
                    f"[Componentes NÃO sensibilizados - já foram baixados na montagem]"
                )

                return resultados

            # --------------------------------------------------------
            # CASO 2.2: KIT VIRTUAL (baixa em cascata dos componentes)
            # --------------------------------------------------------
            if tipo_kit == "VIRTUAL":
                from app.produtos_models import ProdutoKitComponente, Produto

                # Buscar componentes do KIT
                componentes = (
                    db.query(ProdutoKitComponente)
                    .filter(ProdutoKitComponente.kit_id == produto.id)
                    .all()
                )

                if not componentes:
                    raise ValueError(
                        f"KIT VIRTUAL '{produto.nome}' não possui componentes cadastrados. "
                        f"Não é possível processar a venda."
                    )

                logger.info(
                    f"📦 KIT VIRTUAL: {produto.nome} - "
                    f"Processando {len(componentes)} componentes (Qtd vendida: {quantidade_vendida})"
                )

                # Baixar estoque de cada componente
                for componente in componentes:
                    # Calcular quantidade total do componente
                    quantidade_componente = quantidade_vendida * componente.quantidade

                    # Buscar dados do produto componente
                    produto_componente = (
                        db.query(Produto)
                        .filter(
                            Produto.id == componente.produto_componente_id,
                            Produto.user_id == user_id,
                        )
                        .first()
                    )

                    if not produto_componente:
                        raise ValueError(
                            f"Componente ID {componente.produto_componente_id} não encontrado"
                        )

                    # Validar tipo do componente (apenas SIMPLES ou VARIACAO)
                    if produto_componente.tipo_produto not in ("SIMPLES", "VARIACAO"):
                        raise ValueError(
                            f"Componente '{produto_componente.nome}' possui tipo inválido: {produto_componente.tipo_produto}. "
                            f"KIT VIRTUAL aceita apenas componentes SIMPLES ou VARIACAO."
                        )

                    # Validar se componente está ativo (apenas warning, não bloqueia venda)
                    if not produto_componente.situacao:
                        logger.warning(
                            f"⚠️ Componente '{produto_componente.nome}' (ID: {produto_componente.id}) está INATIVO. "
                            f"Venda do KIT '{produto.nome}' será processada normalmente."
                        )

                    # Baixar estoque do componente
                    resultado_componente = EstoqueService.baixar_estoque(
                        produto_id=produto_componente.id,
                        quantidade=quantidade_componente,
                        motivo="venda",
                        referencia_id=venda_id,
                        referencia_tipo="venda",
                        user_id=user_id,
                        tenant_id=tenant_id,
                        db=db,
                        documento=venda_codigo,
                        observacao=f"Componente do KIT VIRTUAL '{produto.nome}' (vendido: {quantidade_vendida}x)",
                    )

                    resultados.append(
                        {
                            "produto": resultado_componente["produto_nome"],
                            "produto_id": produto_componente.id,
                            "tipo_produto": produto_componente.tipo_produto,
                            "quantidade": quantidade_componente,
                            "estoque_anterior": resultado_componente[
                                "estoque_anterior"
                            ],
                            "estoque_novo": resultado_componente["estoque_novo"],
                            "kit_origem": produto.nome,
                            "kit_id": produto.id,
                        }
                    )

                    logger.info(
                        f"   ↳ Componente: {resultado_componente['produto_nome']} - "
                        f"Qtd: {quantidade_componente} ({resultado_componente['estoque_anterior']} → {resultado_componente['estoque_novo']})"
                    )

                logger.info(
                    f"✅ KIT VIRTUAL '{produto.nome}' processado: {len(componentes)} componentes baixados"
                )

                return resultados

        # ============================================================
        # CASO 3: TIPO DE PRODUTO NÃO SUPORTADO
        # ============================================================
        raise ValueError(
            f"Tipo de produto '{produto.tipo_produto}' não suportado para baixa de estoque. "
            f"Tipos válidos: SIMPLES, VARIACAO, KIT"
        )

    @staticmethod
    def cancelar_venda(
        venda_id: int, motivo: str, user_id: int, tenant_id: str, db: Session
    ) -> Dict[str, Any]:
        """
        Cancela uma venda realizando estorno completo de todas as operações.

        Operações executadas (ordem de execução):
        1. Validar venda e permissões
        2. Estornar estoque de todos os itens
        3. Cancelar contas a receber vinculadas
        4. Cancelar lançamentos manuais (fluxo de caixa)
        5. Remover movimentações de caixa (dinheiro)
        6. Estornar movimentações bancárias (PIX/cartão)
        7. Estornar comissões
        8. Marcar venda como cancelada
        9. COMMIT
        10. Auditoria

        GARANTIAS:
        - ✅ Transação atômica (tudo ou nada)
        - ✅ Rollback automático em caso de erro
        - ✅ Segurança: apenas vendas do user_id atual
        - ✅ Idempotente: pode chamar múltiplas vezes
        - ✅ Histórico mantido (status='cancelado' em vez de delete)

        Args:
            venda_id: ID da venda a ser cancelada
            motivo: Motivo do cancelamento (obrigatório)
            user_id: ID do usuário cancelando
            db: Sessão do SQLAlchemy

        Returns:
            Dict com resultado do cancelamento:
            {
                'venda': dict,
                'estornos': {
                    'itens_estornados': int,
                    'contas_canceladas': int,
                    'lancamentos_cancelados': int,
                    'movimentacoes_removidas': int,
                    'movimentacoes_bancarias_estornadas': int
                }
            }

        Raises:
            HTTPException(404): Venda não encontrada
            HTTPException(400): Venda já está cancelada
        """
        from app.vendas_models import Venda, VendaItem
        from app.estoque.service import EstoqueService
        from app.caixa_models import MovimentacaoCaixa
        from app.financeiro_models import (
            ContaReceber,
            LancamentoManual,
            MovimentacaoFinanceira,
            ContaBancaria,
        )
        from app.audit_log import log_action
        from app.tenancy.context import set_tenant_context

        set_tenant_context(
            tenant_id if isinstance(tenant_id, UUID) else UUID(str(tenant_id))
        )

        logger.info(f"🔴 Iniciando cancelamento ATÔMICO da venda #{venda_id}")

        with transactional_session(db):
            # ============================================================
            # ETAPA 1: VALIDAR VENDA E PERMISSÕES
            # ============================================================

            venda = db.query(Venda).filter_by(id=venda_id, tenant_id=tenant_id).first()

            if not venda:
                raise HTTPException(status_code=404, detail="Venda não encontrada")

            if venda.status == "cancelada":
                raise HTTPException(status_code=400, detail="Venda já está cancelada")

            logger.info(
                f"📋 Cancelando venda #{venda.numero_venda} (Status: {venda.status})"
            )

            # ============================================================
            # ETAPA 2: ESTORNAR ESTOQUE DE TODOS OS ITENS
            # ============================================================

            itens = db.query(VendaItem).filter_by(venda_id=venda_id).all()
            itens_estornados = 0

            for item in itens:
                if item.produto_id:  # Apenas produtos físicos têm estoque
                    try:
                        resultado = EstoqueService.estornar_estoque(
                            produto_id=item.produto_id,
                            quantidade=item.quantidade,
                            motivo="cancelamento_venda",
                            referencia_id=venda_id,
                            referencia_tipo="venda",
                            user_id=user_id,
                            tenant_id=tenant_id,
                            db=db,
                            documento=venda.numero_venda,
                            observacao=f"Cancelamento: {motivo}",
                        )
                        itens_estornados += 1
                        logger.info(
                            f"  ✅ Estoque estornado: {resultado['produto_nome']} "
                            f"+{item.quantidade} ({resultado['estoque_anterior']} → {resultado['estoque_novo']})"
                        )
                    except Exception as e:
                        logger.error(f"  ❌ Erro ao estornar estoque: {e}")
                        raise HTTPException(
                            status_code=500,
                            detail=f"Erro ao estornar estoque: {str(e)}",
                        )

            logger.info(
                f"📦 Total de itens estornados: {itens_estornados}/{len(itens)}"
            )

            # ============================================================
            # ETAPA 3: CANCELAR CONTAS A RECEBER VINCULADAS
            # ============================================================

            contas_receber = db.query(ContaReceber).filter_by(venda_id=venda_id).all()
            contas_canceladas = 0

            for conta in contas_receber:
                if conta.status == "pendente" or conta.status == "parcial":
                    logger.info(
                        f"  💳 Removendo conta a receber pendente: {conta.descricao} - "
                        f"R$ {conta.valor_original}"
                    )
                    db.delete(conta)
                elif conta.status == "recebido":
                    conta.status = "cancelado"
                    logger.info(
                        f"  💳 Cancelando conta já recebida: {conta.descricao} - "
                        f"R$ {conta.valor_recebido}"
                    )
                contas_canceladas += 1

            logger.info(f"💳 Total de contas canceladas: {contas_canceladas}")

            # ============================================================
            # ETAPA 4: CANCELAR LANÇAMENTOS MANUAIS
            # ============================================================

            lancamentos = (
                db.query(LancamentoManual)
                .filter(
                    or_(
                        LancamentoManual.documento == f"VENDA-{venda_id}",
                        LancamentoManual.documento.like(f"VENDA-{venda_id}-%"),
                    )
                )
                .all()
            )

            lancamentos_cancelados = 0
            for lanc in lancamentos:
                if lanc.status == "previsto":
                    logger.info(
                        f"  📊 Removendo lançamento previsto: {lanc.descricao} - "
                        f"R$ {lanc.valor}"
                    )
                    db.delete(lanc)
                elif lanc.status == "realizado":
                    lanc.status = "cancelado"
                    logger.info(
                        f"  📊 Cancelando lançamento realizado: {lanc.descricao} - "
                        f"R$ {lanc.valor}"
                    )
                lancamentos_cancelados += 1

            logger.info(f"📊 Total de lançamentos cancelados: {lancamentos_cancelados}")

            # ============================================================
            # ETAPA 5: REMOVER MOVIMENTAÇÕES DE CAIXA
            # ============================================================

            movimentacoes_caixa = (
                db.query(MovimentacaoCaixa).filter_by(venda_id=venda_id).all()
            )

            movimentacoes_removidas = 0
            for mov in movimentacoes_caixa:
                logger.info(
                    f"  💵 Removendo movimentação de caixa: R$ {mov.valor} ({mov.tipo})"
                )
                db.delete(mov)
                movimentacoes_removidas += 1

            logger.info(
                f"💵 Total de movimentações de caixa removidas: {movimentacoes_removidas}"
            )

            # ============================================================
            # ETAPA 6: ESTORNAR MOVIMENTAÇÕES BANCÁRIAS
            # ============================================================

            movimentacoes_bancarias = (
                db.query(MovimentacaoFinanceira)
                .filter(
                    MovimentacaoFinanceira.tenant_id == tenant_id,
                    MovimentacaoFinanceira.origem_tipo == "venda",
                    MovimentacaoFinanceira.origem_id == venda_id,
                )
                .all()
            )

            movimentacoes_estornadas = 0
            for mov_banc in movimentacoes_bancarias:
                conta_bancaria = (
                    db.query(ContaBancaria)
                    .filter_by(id=mov_banc.conta_bancaria_id, user_id=user_id)
                    .first()
                )

                if conta_bancaria:
                    if mov_banc.tipo in ("receita", "entrada"):
                        conta_bancaria.saldo_atual -= mov_banc.valor
                        logger.info(
                            f"  🏦 Estornando saldo bancário: {conta_bancaria.nome} "
                            f"-R$ {mov_banc.valor}"
                        )
                    elif mov_banc.tipo in ("despesa", "saida"):
                        conta_bancaria.saldo_atual += mov_banc.valor
                        logger.info(
                            f"  🏦 Estornando saldo bancário: {conta_bancaria.nome} "
                            f"+R$ {mov_banc.valor}"
                        )

                    db.delete(mov_banc)
                    movimentacoes_estornadas += 1

            logger.info(
                f"🏦 Total de movimentações bancárias estornadas: {movimentacoes_estornadas}"
            )

            # ============================================================
            # ETAPA 6.5: REMOVER PARADAS DE ENTREGA
            # ============================================================

            from app.rotas_entrega_models import RotaEntregaParada

            paradas_removidas = 0

            paradas = db.query(RotaEntregaParada).filter_by(venda_id=venda_id).all()
            for parada in paradas:
                logger.info(f"🚚 Removendo parada de entrega da rota #{parada.rota_id}")
                db.delete(parada)
                paradas_removidas += 1

            if paradas_removidas > 0:
                logger.info(
                    f"📋 Total de paradas de entrega removidas: {paradas_removidas}"
                )
                # Reverter status de entrega
                venda.status_entrega = None

            # ============================================================
            # ETAPA 7: ESTORNAR COMISSÕES
            # ============================================================

            try:
                from app.comissoes_estorno import estornar_comissoes_venda

                resultado_estorno = estornar_comissoes_venda(
                    venda_id=venda_id,
                    motivo=f"Venda cancelada: {motivo}",
                    usuario_id=user_id,
                    db=db,
                )

                if (
                    resultado_estorno["success"]
                    and resultado_estorno["comissoes_estornadas"] > 0
                ):
                    logger.info(
                        f"  💰 Estornadas {resultado_estorno['comissoes_estornadas']} "
                        f"comissões (R$ {resultado_estorno['valor_estornado']:.2f})"
                    )
            except Exception as e:
                logger.warning(f"  ⚠️  Erro ao estornar comissões: {str(e)}")

            # ============================================================
            # ETAPA 8: MARCAR VENDA COMO CANCELADA
            # ============================================================

            status_anterior = venda.status
            venda.status = "cancelada"
            venda.cancelada_por = user_id
            venda.motivo_cancelamento = motivo
            venda.data_cancelamento = now_brasilia()
            venda.updated_at = now_brasilia()

            if status_anterior in ["baixa_parcial", "finalizada"]:
                get_or_build_venda_rentabilidade_snapshot(
                    venda,
                    db,
                    tenant_id,
                    persist_if_missing=True,
                    force_refresh=True,
                )
            else:
                invalidate_venda_rentabilidade_snapshot(venda)

            from app.campaigns.coupon_service import reverse_coupon_redemptions_for_sale
            from app.campaigns.loyalty_service import void_loyalty_stamps_for_sale

            reverse_coupon_redemptions_for_sale(
                db,
                tenant_id=tenant_id,
                venda_id=venda_id,
                reason=f"Venda cancelada: {motivo}",
            )

            void_loyalty_stamps_for_sale(
                db,
                tenant_id=tenant_id,
                venda_id=venda_id,
                reason=f"Venda cancelada: {motivo}",
            )

            db.flush()

            logger.info(
                f"🔒 Venda marcada como cancelada: {venda.numero_venda} "
                f"(status: {status_anterior} → cancelada)"
            )

            # ============================================================
            # ETAPA 9: AUDITORIA
            # ============================================================

            log_action(
                db=db,
                user_id=user_id,
                action="UPDATE",
                entity_type="vendas",
                entity_id=venda.id,
                details=(
                    f"Venda {venda.numero_venda} CANCELADA (ATÔMICO) - "
                    f"Motivo: {motivo} - "
                    f"Itens estornados: {itens_estornados} - "
                    f"Contas canceladas: {contas_canceladas}"
                ),
                tenant_id=tenant_id,
                commit=False,
            )

            # Commit automático pelo context manager

        # Refresh após commit
        db.refresh(venda)

        logger.info(
            f"✅ ✅ ✅ CANCELAMENTO CONCLUÍDO: Venda #{venda.numero_venda} ✅ ✅ ✅\n"
            f"   📦 Estoque estornado: {itens_estornados} itens\n"
            f"   💳 Contas canceladas: {contas_canceladas}\n"
            f"   📊 Lançamentos cancelados: {lancamentos_cancelados}\n"
            f"   💵 Movimentações caixa removidas: {movimentacoes_removidas}\n"
            f"   🏦 Movimentações bancárias estornadas: {movimentacoes_estornadas}"
        )

        # ============================================================
        # ETAPA 10: EMITIR EVENTO DE DOMÍNIO
        # ============================================================

        # 🔒 EVENTOS DESABILITADOS TEMPORARIAMENTE (publish_event não exportado)
        # try:
        #     from app.domain.events import VendaCancelada, publish_event
        #
        #     evento = VendaCancelada(
        #         venda_id=venda.id,
        #         numero_venda=venda.numero_venda,
        #         user_id=user_id,
        #         cliente_id=venda.cliente_id,
        #         funcionario_id=venda.funcionario_id,
        #         motivo=motivo,
        #         status_anterior=status_anterior,
        #         total=float(venda.total),
        #         itens_estornados=itens_estornados,
        #         contas_canceladas=contas_canceladas,
        #         comissoes_estornadas=(movimentacoes_estornadas > 0),
        #         metadados={
        #             'lancamentos_cancelados': lancamentos_cancelados,
        #             'movimentacoes_caixa_removidas': movimentacoes_removidas,
        #             'movimentacoes_bancarias_estornadas': movimentacoes_estornadas
        #         }
        #     )
        #
        #     publish_event(evento)
        #     logger.debug(f"📢 Evento VendaCancelada publicado (venda_id={venda.id})")
        #
        # except Exception as e:
        #     logger.error(f"⚠️  Erro ao publicar evento VendaCancelada: {str(e)}", exc_info=True)
        #     # Não aborta o cancelamento

        try:
            from app.domain.events import VendaCancelada, publish_event

            publish_event(
                VendaCancelada(
                    venda_id=venda.id,
                    numero_venda=venda.numero_venda,
                    user_id=user_id,
                    cliente_id=venda.cliente_id,
                    funcionario_id=venda.funcionario_id,
                    motivo=motivo,
                    status_anterior=status_anterior,
                    total=float(venda.total),
                    itens_estornados=itens_estornados,
                    contas_canceladas=contas_canceladas,
                    comissoes_estornadas=(movimentacoes_estornadas > 0),
                    metadados={
                        "lancamentos_cancelados": lancamentos_cancelados,
                        "movimentacoes_caixa_removidas": movimentacoes_removidas,
                        "movimentacoes_bancarias_estornadas": movimentacoes_estornadas,
                    },
                )
            )
            logger.debug("Evento VendaCancelada publicado (venda_id=%s)", venda.id)
        except Exception as e:
            logger.error(
                "Erro ao publicar evento VendaCancelada: %s", str(e), exc_info=True
            )

        return {
            "venda": venda.to_dict(),
            "estornos": {
                "itens_estornados": itens_estornados,
                "contas_canceladas": contas_canceladas,
                "lancamentos_cancelados": lancamentos_cancelados,
                "movimentacoes_removidas": movimentacoes_removidas,
                "movimentacoes_bancarias_estornadas": movimentacoes_estornadas,
            },
        }

    @staticmethod
    def _gerar_numero_venda(
        db: Session, tenant_id: str, user_id: int | None = None
    ) -> str:
        """
        Gera um número sequencial para a venda no formato YYYYMMDDNNNN.

        Args:
            db: Sessão do SQLAlchemy
            user_id: ID do usuário

        Returns:
            String no formato YYYYMMDDNNNN (ex: 202501230001)
        """
        from app.vendas_models import Venda

        hoje = now_brasilia()
        prefixo = hoje.strftime("%Y%m%d")

        # A numeracao pode repetir entre tenants, mas nunca dentro do mesmo tenant.
        ultima_venda = (
            db.query(Venda)
            .filter(
                Venda.numero_venda.like(f"{prefixo}%"), Venda.tenant_id == tenant_id
            )
            .order_by(desc(Venda.numero_venda))
            .first()
        )

        if ultima_venda:
            try:
                seq = int(ultima_venda.numero_venda[-4:]) + 1
            except (TypeError, ValueError):
                seq = 1
        else:
            seq = 1

        return f"{prefixo}{seq:04d}"

    @staticmethod
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
        from app.campaigns.coupon_service import consume_coupon_redemption
        from app.vendas_models import Venda, VendaPagamento
        from app.models import Cliente
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

            cupom_code_resolvido = (
                str(cupom_code).strip().upper() if cupom_code else venda.cupom_code
            )
            cupom_discount_resolvido = (
                cupom_discount_applied
                if cupom_discount_applied is not None
                else float(venda.cupom_discount_applied or 0)
                if venda.cupom_discount_applied is not None
                else None
            )

            cupom_consumido = None
            if cupom_code_resolvido:
                venda_total_para_cupom = float(venda.total or 0)
                if cupom_discount_resolvido:
                    venda_total_para_cupom += float(cupom_discount_resolvido or 0)
                cupom_consumido = consume_coupon_redemption(
                    db,
                    tenant_id=tenant_id,
                    code=cupom_code_resolvido,
                    venda_total=venda_total_para_cupom,
                    customer_id=venda.cliente_id,
                    venda_id=venda.id,
                    expected_discount_applied=cupom_discount_resolvido,
                )
                venda.cupom_code = cupom_code_resolvido
                venda.cupom_discount_applied = cupom_consumido.get("discount_applied")

            # ============================================================
            # ETAPA 2: PROCESSAR PAGAMENTOS
            # ============================================================

            movimentacoes_caixa_ids = []

            for pag_data in pagamentos:
                # ⚠️ ALERTA 1: VALIDAR PARCELAS CONTRA OPERADORA
                # Garante que número de parcelas não exceda o máximo da operadora
                operadora_id = pag_data.get("operadora_id")
                numero_parcelas = pag_data.get("numero_parcelas", 1)

                if operadora_id and numero_parcelas > 1:
                    from app.operadoras_models import OperadoraCartao

                    operadora = (
                        db.query(OperadoraCartao)
                        .filter(
                            OperadoraCartao.id == operadora_id,
                            OperadoraCartao.tenant_id == tenant_id,
                        )
                        .first()
                    )
                    if not operadora:
                        raise HTTPException(
                            status_code=400,
                            detail=f"❌ Operadora não encontrada (ID: {operadora_id})",
                        )

                    if numero_parcelas > operadora.max_parcelas:
                        raise HTTPException(
                            status_code=400,
                            detail=f"❌ PARCELAS EXCEDIDAS: {operadora.nome} permite no máximo "
                            f"{operadora.max_parcelas}x. Você tentou {numero_parcelas}x.",
                        )

                # ⚠️ ALERTA 2: VALIDAR NSU DUPLICADO
                # Garante que o mesmo NSU não seja usado duas vezes na mesma operadora
                nsu_informado = pag_data.get("nsu_cartao")
                if nsu_informado and operadora_id:
                    nsu_duplicado = (
                        db.query(VendaPagamento)
                        .filter(
                            VendaPagamento.tenant_id == tenant_id,
                            VendaPagamento.nsu_cartao == nsu_informado,
                            VendaPagamento.operadora_id == operadora_id,
                        )
                        .first()
                    )

                    if nsu_duplicado:
                        venda_duplicada = (
                            db.query(Venda).filter_by(id=nsu_duplicado.venda_id).first()
                        )
                        raise HTTPException(
                            status_code=400,
                            detail=f"❌ NSU DUPLICADO: O NSU '{nsu_informado}' já está vinculado à "
                            f"Venda {venda_duplicada.numero_venda if venda_duplicada else nsu_duplicado.venda_id}. "
                            f"Cada NSU deve ser usado apenas uma vez por operadora.",
                        )

                # Criar registro de pagamento
                # 🔒 ISOLAMENTO MULTI-TENANT: tenant_id obrigatório
                pagamento = VendaPagamento(
                    venda_id=venda.id,
                    tenant_id=tenant_id,  # ✅ Garantir isolamento entre empresas
                    forma_pagamento=pag_data["forma_pagamento"],
                    valor=pag_data["valor"],
                    numero_parcelas=numero_parcelas,
                    bandeira=pag_data.get("bandeira"),  # ✅ Bandeira do cartão
                    nsu_cartao=pag_data.get("nsu_cartao"),  # ✅ NSU para conciliação
                    operadora_id=operadora_id,  # ✅ Operadora de cartão
                )
                db.add(pagamento)
                db.flush()

                # Processar crédito de cliente
                forma_eh_credito = (
                    pag_data["forma_pagamento"].lower() == "credito_cliente"
                    or pag_data["forma_pagamento"] == "Crédito Cliente"
                )

                if forma_eh_credito:
                    if not venda.cliente_id:
                        raise HTTPException(
                            status_code=400,
                            detail="Crédito só pode ser usado em vendas com cliente vinculado",
                        )

                    cliente = db.query(Cliente).filter_by(id=venda.cliente_id).first()
                    if not cliente:
                        raise HTTPException(
                            status_code=404, detail="Cliente não encontrado"
                        )

                    credito_disponivel = float(cliente.credito or 0)
                    if pag_data["valor"] > credito_disponivel + 0.01:
                        raise HTTPException(
                            status_code=400,
                            detail=f"Crédito insuficiente. Disponível: R$ {credito_disponivel:.2f}",
                        )

                    cliente.credito = Decimal(
                        str(credito_disponivel - pag_data["valor"])
                    )
                    db.add(cliente)
                    logger.info(
                        f"🎁 Crédito utilizado: R$ {pag_data['valor']:.2f} - "
                        f"Saldo restante: R$ {float(cliente.credito):.2f}"
                    )
                    continue

                # Processar cashback de campanhas
                forma_eh_cashback = (
                    pag_data["forma_pagamento"].lower() == "cashback"
                    or pag_data["forma_pagamento"] == "Cashback"
                )

                if forma_eh_cashback:
                    if not venda.cliente_id:
                        raise HTTPException(
                            status_code=400,
                            detail="Cashback só pode ser usado em vendas com cliente vinculado",
                        )

                    from app.campaigns.models import (
                        CashbackTransaction,
                        CashbackSourceTypeEnum,
                    )

                    saldo_raw = (
                        db.query(func.sum(CashbackTransaction.amount))
                        .filter(
                            CashbackTransaction.tenant_id == tenant_id,
                            CashbackTransaction.customer_id == venda.cliente_id,
                        )
                        .scalar()
                    )
                    saldo_disponivel = float(saldo_raw or 0)

                    if pag_data["valor"] > saldo_disponivel + 0.01:
                        raise HTTPException(
                            status_code=400,
                            detail=f"Cashback insuficiente. Disponível: R$ {saldo_disponivel:.2f}",
                        )

                    debit = CashbackTransaction(
                        tenant_id=tenant_id,
                        customer_id=venda.cliente_id,
                        amount=-Decimal(str(pag_data["valor"])),
                        source_type=CashbackSourceTypeEnum.redemption,
                        source_id=venda.id,  # FK para rastreamento por venda
                        description=f"Resgate em venda {venda.numero_venda}",
                        tx_type="debit",
                    )
                    db.add(debit)

                    # ── DRE: registrar como despesa de campanhas/marketing ──
                    # Não gera fluxo de caixa (conta_bancaria_id=None)
                    from app.financeiro_models import (
                        LancamentoManual,
                        CategoriaFinanceira,
                    )
                    from datetime import date as _date

                    cat_campanha = (
                        db.query(CategoriaFinanceira)
                        .filter(
                            CategoriaFinanceira.nome.ilike("%campanha%"),
                            CategoriaFinanceira.tipo == "despesa",
                            CategoriaFinanceira.tenant_id == tenant_id,
                        )
                        .first()
                    )
                    if not cat_campanha:
                        cat_campanha = CategoriaFinanceira(
                            nome="Campanhas / Marketing",
                            tipo="despesa",
                            user_id=user_id,
                            tenant_id=tenant_id,
                        )
                        db.add(cat_campanha)
                        db.flush()

                    cliente_nome = venda.cliente.nome if venda.cliente else "Cliente"
                    lancamento_campanha = LancamentoManual(
                        tipo="saida",
                        valor=Decimal(str(pag_data["valor"])),
                        descricao=f"Cashback resgatado — {cliente_nome} — Venda {venda.numero_venda}",
                        data_lancamento=venda.data_venda.date()
                        if hasattr(venda.data_venda, "date")
                        else _date.today(),
                        status="realizado",
                        categoria_id=cat_campanha.id,
                        conta_bancaria_id=None,  # sem movimentação de caixa
                        fornecedor_cliente=cliente_nome,
                        documento=f"CASHBACK-{venda.numero_venda}",
                        gerado_automaticamente=True,
                        user_id=user_id,
                        tenant_id=tenant_id,
                    )
                    db.add(lancamento_campanha)
                    logger.info(
                        "💰 Cashback utilizado: R$ %.2f — DRE despesa campanha criada — venda=%s",
                        pag_data["valor"],
                        venda.numero_venda,
                    )
                    continue

                # Registrar no caixa (apenas dinheiro)
                if CaixaService.eh_forma_dinheiro(pag_data["forma_pagamento"]):
                    mov_info = CaixaService.registrar_movimentacao_venda(
                        caixa_id=caixa_aberto_id,
                        venda_id=venda.id,
                        venda_numero=venda.numero_venda,
                        valor=pag_data["valor"],
                        user_id=user_id,
                        user_nome=user_nome,
                        tenant_id=tenant_id,  # 🔒 Isolamento multi-tenant
                        db=db,
                    )
                    movimentacoes_caixa_ids.append(mov_info["movimentacao_id"])
                    logger.info(
                        f"💵 Caixa: Movimentação #{mov_info['movimentacao_id']} criada"
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
                        resultados = VendaService._processar_baixa_estoque_item(
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
                resultado_lancamentos = (
                    ContasReceberService.atualizar_lancamentos_venda(
                        venda_id=venda.id,
                        venda_numero=venda.numero_venda,
                        total_venda=total_venda,
                        total_recebido=total_recebido_venda,
                        user_id=user_id,
                        tenant_id=tenant_id,
                        db=db,
                    )
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

            # ============================================================
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
                    pagamentos[0]["forma_pagamento"]
                    if pagamentos
                    else "Não especificado"
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
                            quantidade=float(
                                kit_info.get("quantidade", item_venda.quantidade)
                            ),
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
            # ETAPA 8: OPERAÇÕES PÓS-COMMIT (não abortam se falharem)
            # ============================================================

            # Criar novas contas a receber
            contas_criadas_ids = []
            try:
                resultado_contas = ContasReceberService.criar_de_venda(
                    venda=venda, pagamentos=pagamentos, user_id=user_id, db=db
                )
                contas_criadas_ids = resultado_contas["contas_criadas"]
                db.commit()  # Commit separado para contas
                logger.info(
                    f"📋 Contas a receber criadas: {resultado_contas['total_contas']} conta(s), "
                    f"{len(resultado_contas['lancamentos_criados'])} lançamento(s)"
                )
            except Exception as e:
                logger.error(
                    f"⚠️ Erro ao criar contas a receber: {str(e)}", exc_info=True
                )
                db.rollback()  # Rollback apenas das contas (venda já commitada)

            # 🚚 Criar contas a pagar de entrega (taxa entregador + custo operacional)
            try:
                resultado_entrega = processar_contas_pagar_entrega(
                    venda=venda, user_id=user_id, tenant_id=tenant_id, db=db
                )
                if resultado_entrega["success"]:
                    db.commit()  # Commit separado para contas a pagar
                    logger.info(
                        f"🚚 Contas a pagar de entrega criadas: {resultado_entrega['total_contas']} conta(s), "
                        f"R$ {resultado_entrega['valor_total']:.2f}"
                    )
            except Exception as e:
                logger.error(
                    f"⚠️ Erro ao criar contas a pagar de entrega: {str(e)}",
                    exc_info=True,
                )
                db.rollback()  # Rollback apenas das contas (venda já commitada)

            # 💳 Criar contas a pagar de taxas de pagamento
            logger.info(
                f"💳 Iniciando processamento de taxas de pagamento - Venda #{venda.numero_venda}"
            )
            try:
                pagamentos_para_taxas = [
                    type(
                        "obj",
                        (object,),
                        {
                            "forma_pagamento": p["forma_pagamento"],
                            "valor": p["valor"],
                            "numero_parcelas": p.get("numero_parcelas", 1),
                        },
                    )()
                    for p in pagamentos
                ]

                logger.info(
                    f"💳 Total de pagamentos a processar: {len(pagamentos_para_taxas)}"
                )
                for pag in pagamentos_para_taxas:
                    logger.info(f"  - {pag.forma_pagamento}: R$ {pag.valor}")

                resultado_taxas = processar_contas_pagar_taxas(
                    venda=venda,
                    pagamentos=pagamentos_para_taxas,
                    user_id=user_id,
                    tenant_id=tenant_id,
                    db=db,
                )

                logger.info(f"💳 Resultado do processamento: {resultado_taxas}")

                if resultado_taxas["success"]:
                    db.commit()  # Commit separado para contas a pagar
                    logger.info(
                        f"💳 Contas a pagar de taxas criadas: {resultado_taxas['total_contas']} conta(s), "
                        f"R$ {resultado_taxas['valor_total']:.2f}"
                    )
                else:
                    logger.warning(
                        f"⚠️ Processamento de taxas falhou: {resultado_taxas.get('error', 'Erro desconhecido')}"
                    )
                    db.rollback()  # Limpa falha secundaria; a venda ja foi commitada antes dos efeitos financeiros
            except Exception as e:
                logger.error(
                    f"⚠️ Erro ao criar contas a pagar de taxas: {str(e)}", exc_info=True
                )
                db.rollback()  # Rollback apenas das contas (venda já commitada)

            # 📢 Enfileirar evento de campanha (purchase_completed)
            if venda.status == "finalizada" and venda.cliente_id:
                try:
                    from app.campaigns.models import CampaignEventQueue, EventOriginEnum
                    import uuid as _uuid

                    evento_campanha = CampaignEventQueue(
                        tenant_id=_uuid.UUID(str(tenant_id)),
                        event_type="purchase_completed",
                        event_origin=EventOriginEnum.user_action,
                        event_depth=0,
                        payload={
                            "customer_id": venda.cliente_id,
                            "venda_id": venda.id,
                            "venda_total": float(venda.total),
                            "canal": venda.canal or "loja_fisica",
                        },
                    )
                    db.add(evento_campanha)
                    db.commit()
                    logger.info(
                        "📢 [Campanhas] purchase_completed enfileirado: "
                        "venda=%s cliente_id=%d total=R$%.2f",
                        venda.numero_venda,
                        venda.cliente_id,
                        float(venda.total),
                    )
                except Exception as e:
                    logger.warning(
                        "[Campanhas] Falha ao enfileirar purchase_completed (não crítico): %s",
                        e,
                    )
                    db.rollback()

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
                },
                "pos_commit": {
                    "contas_novas": len(contas_criadas_ids),
                    "comissoes_geradas": False,  # Será processado na rota
                    "lembretes_criados": 0,  # Será processado na rota
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
