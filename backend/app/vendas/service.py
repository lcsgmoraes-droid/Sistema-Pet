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
from fastapi import HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc, or_
from uuid import UUID

from app.produtos_models import Produto as Produto
from app.vendas_models import (
    Venda as Venda,
    VendaItem as VendaItem,
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
from app.vendas.finalizacao import _calcular_pagamentos_finalizacao
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
        from app.vendas.criacao import criar_venda as criar_venda_impl

        return criar_venda_impl(
            payload=payload,
            user_id=user_id,
            db=db,
            gerar_numero_venda=VendaService._gerar_numero_venda,
            processar_baixa_estoque_item=VendaService._processar_baixa_estoque_item,
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
        from app.vendas.finalizacao import finalizar_venda as finalizar_venda_impl

        return finalizar_venda_impl(
            venda_id=venda_id,
            pagamentos=pagamentos,
            user_id=user_id,
            user_nome=user_nome,
            tenant_id=tenant_id,
            db=db,
            cupom_code=cupom_code,
            cupom_discount_applied=cupom_discount_applied,
            caixa_id=caixa_id,
            permitir_caixa_tenant=permitir_caixa_tenant,
            processar_baixa_estoque_item=VendaService._processar_baixa_estoque_item,
        )
