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
from typing import Dict, Any, List, Optional
from decimal import Decimal
from datetime import datetime, date, timedelta
from fastapi import HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc, or_, func, String
import json
from uuid import UUID

# Timezone Brasília
from app.utils.timezone import now_brasilia

# Services
from app.estoque.service import EstoqueService
from app.db.transaction import transactional_session

# Logger
logger = logging.getLogger(__name__)


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
        payload: Dict[str, Any],
        user_id: int,
        db: Session
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
        from app.financeiro_models import ContaReceber, LancamentoManual, CategoriaFinanceira
        from app.audit_log import log_action
        
        logger.info(f"📝 Criando nova venda para user_id={user_id}")
        
        try:
            # ============================================================
            # ETAPA 1: VALIDAÇÕES
            # ============================================================
            
            itens = payload.get('itens', [])
            if not itens or len(itens) == 0:
                raise HTTPException(status_code=400, detail='A venda deve ter pelo menos um item')
            
            logger.debug(f"✅ Validação OK: {len(itens)} itens")
            
            # ============================================================
            # ETAPA 2: GERAR NÚMERO DA VENDA
            # ============================================================
            
            numero_venda = VendaService._gerar_numero_venda(db, user_id)
            logger.debug(f"✅ Número gerado: {numero_venda}")
            
            # ============================================================
            # ETAPA 3: CALCULAR TOTAIS
            # ============================================================
            
            subtotal_itens = sum(item['subtotal'] for item in itens)
            taxa_entrega = payload.get('taxa_entrega', 0) or 0
            total = subtotal_itens + taxa_entrega
            
            # 🚚 Calcular distribuição da taxa de entrega
            percentual_taxa_entregador = payload.get('percentual_taxa_entregador', 0) or 0
            percentual_taxa_loja = payload.get('percentual_taxa_loja', 100)
            
            logger.info(f"📥 PAYLOAD RECEBIDO - percentual_taxa_entregador: {percentual_taxa_entregador}, percentual_taxa_loja: {percentual_taxa_loja}")
            
            # Se não foi informado percentual mas tem taxa, assumir 100% para loja (compatibilidade)
            if taxa_entrega > 0 and percentual_taxa_entregador == 0 and percentual_taxa_loja == 0:
                percentual_taxa_loja = 100
            
            # Calcular valores baseados nos percentuais
            valor_taxa_entregador = (taxa_entrega * percentual_taxa_entregador / 100) if taxa_entrega > 0 else 0
            valor_taxa_loja = (taxa_entrega * percentual_taxa_loja / 100) if taxa_entrega > 0 else 0
            
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
                cliente_id=payload.get('cliente_id'),
                vendedor_id=payload.get('vendedor_id') or user_id,
                funcionario_id=payload.get('funcionario_id'),
                subtotal=float(subtotal_itens),
                desconto_valor=float(payload.get('desconto_valor', 0) or 0),  # Desconto aplicado na venda
                desconto_percentual=payload.get('desconto_percentual', 0) or 0,
                total=float(total),
                observacoes=payload.get('observacoes'),
                tem_entrega=payload.get('tem_entrega', False),
                taxa_entrega=float(taxa_entrega),
                percentual_taxa_entregador=float(percentual_taxa_entregador),
                percentual_taxa_loja=float(percentual_taxa_loja),
                valor_taxa_entregador=float(valor_taxa_entregador),
                valor_taxa_loja=float(valor_taxa_loja),
                entregador_id=payload.get('entregador_id'),
                loja_origem=payload.get('loja_origem'),
                endereco_entrega=payload.get('endereco_entrega'),
                distancia_km=payload.get('distancia_km'),
                valor_por_km=payload.get('valor_por_km'),
                observacoes_entrega=payload.get('observacoes_entrega'),
                status_entrega='pendente' if payload.get('tem_entrega') else None,
                canal=payload.get('canal', 'loja_fisica'),  # Canal de venda para DRE
                status='aberta',
                data_venda=now_brasilia(),
                user_id=user_id,
                tenant_id=payload.get('tenant_id')
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
                produto_id = item_data.get('produto_id')
                product_variation_id = item_data.get('product_variation_id')
                
                if item_data.get('tipo') == 'produto':
                    # Valida XOR: OU produto_id OU product_variation_id
                    if not produto_id and not product_variation_id:
                        raise HTTPException(
                            status_code=400,
                            detail="Item de venda deve conter product_id ou product_variation_id"
                        )
                    
                    if produto_id and product_variation_id:
                        raise HTTPException(
                            status_code=400,
                            detail="Item de venda não pode conter product_id e product_variation_id ao mesmo tempo"
                        )
                    
                    # Se for produto simples, valida e busca preço
                    if produto_id:
                        produto = db.query(Produto).filter(
                            Produto.id == produto_id,
                            Produto.tenant_id == payload.get('tenant_id')
                        ).first()
                        
                        if not produto:
                            raise HTTPException(
                                status_code=404,
                                detail=f"Produto ID {produto_id} não encontrado"
                            )
                        
                        if produto.tipo_produto == 'PAI':
                            raise HTTPException(
                                status_code=400,
                                detail=f"Produto '{produto.nome}' é do tipo PAI e não pode ser vendido. Selecione uma variação."
                            )
                    
                    # Se for variação, valida e busca preço
                    if product_variation_id:
                        from app.produtos_models import Produto
                        variacao = db.query(Produto).filter(
                            Produto.id == product_variation_id,
                            Produto.tipo_produto == 'VARIACAO'
                        ).first()
                        
                        if not variacao:
                            raise HTTPException(
                                status_code=404,
                                detail=f"Variação de produto ID {product_variation_id} não encontrada"
                            )
                
                # 🔒 ISOLAMENTO MULTI-TENANT: tenant_id obrigatório
                item = VendaItem(
                    venda_id=venda.id,
                    tenant_id=payload.get('tenant_id'),  # ✅ Dupla proteção: injeção automática + explícita
                    tipo=item_data.get('tipo', 'produto'),
                    produto_id=produto_id,
                    product_variation_id=product_variation_id,
                    servico_descricao=item_data.get('servico_descricao'),
                    quantidade=item_data['quantidade'],
                    preco_unitario=item_data['preco_unitario'],
                    desconto_item=item_data.get('desconto_item', 0) or 0,
                    subtotal=item_data['subtotal'],
                    lote_id=item_data.get('lote_id'),
                    pet_id=item_data.get('pet_id')
                )
                db.add(item)
            
            # 🔥 CRÍTICO: Flush para persistir os itens antes de baixar estoque
            db.flush()
            
            logger.debug(f"✅ {len(itens)} itens adicionados")
            
            # ============================================================
            # ETAPA 6: CRIAR LANÇAMENTO PREVISTO E CONTA A RECEBER
            # ============================================================
            
            # Buscar ou criar categoria de receitas
            tenant_id = payload.get('tenant_id')
            categoria_receitas = db.query(CategoriaFinanceira).filter(
                CategoriaFinanceira.nome.ilike('%vendas%'),
                CategoriaFinanceira.tipo == 'receita',
                CategoriaFinanceira.user_id == user_id,
                CategoriaFinanceira.tenant_id == tenant_id
            ).first()
            
            if not categoria_receitas:
                categoria_receitas = CategoriaFinanceira(
                    nome="Receitas de Vendas",
                    tipo="receita",
                    user_id=user_id,
                    tenant_id=tenant_id
                )
                db.add(categoria_receitas)
                db.flush()
            
            # Criar lançamento previsto (30 dias)
            prazo_dias = 30
            data_prevista = date.today() + timedelta(days=prazo_dias)
            
            lancamento = LancamentoManual(
                tipo='entrada',
                valor=Decimal(str(total)),
                descricao=f"Venda {numero_venda} - A receber",
                data_lancamento=data_prevista,
                status='previsto',
                categoria_id=categoria_receitas.id,
                documento=f"VENDA-{venda.id}",
                fornecedor_cliente=venda.cliente.nome if venda.cliente else "Cliente Avulso",
                user_id=user_id,
                tenant_id=tenant_id
            )
            db.add(lancamento)
            
            # ⚠️ IMPORTANTE: Contas a receber NÃO são criadas aqui!
            # Elas são criadas durante a FINALIZAÇÃO da venda (ContasReceberService.criar_de_venda)
            # Isso evita duplicação e permite tratamento correto de parcelamento
            
            logger.info(f"📊 Lançamento previsto criado (R$ {total:.2f} em {data_prevista})")
            
            # ============================================================
            # ETAPA 6.5: BAIXAR ESTOQUE IMEDIATAMENTE (PRODUTOS SEPARADOS)
            # ============================================================
            # 🎯 NOVO FLUXO: Estoque é baixado no momento da criação da venda
            # Motivo: Produtos são fisicamente separados ao criar a venda (pedido/entrega)
            
            logger.info(f"🔍 Iniciando baixa de estoque para venda #{venda.id} ({numero_venda})")
            
            estoque_baixado = []
            
            # Buscar itens recém-criados
            itens_criados = db.query(VendaItem).filter_by(venda_id=venda.id).all()
            logger.info(f"📋 Encontrados {len(itens_criados)} itens para processar estoque")
            
            for item in itens_criados:
                logger.info(f"  → Item: tipo={item.tipo}, produto_id={item.produto_id}, qtd={item.quantidade}")
                
                if item.tipo == 'produto' and item.produto_id:
                    try:
                        from app.produtos_models import Produto
                        
                        # Buscar produto
                        produto = db.query(Produto).filter(
                            Produto.id == item.produto_id,
                            Produto.tenant_id == tenant_id
                        ).first()
                        
                        if not produto:
                            logger.warning(f"⚠️  Produto {item.produto_id} não encontrado ao criar venda")
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
                            venda_codigo=numero_venda
                        )
                        
                        estoque_baixado.extend(resultados)
                        logger.info(f"📦 Estoque baixado ao criar venda: {produto.nome} -{item.quantidade}")
                        
                    except Exception as e:
                        logger.error(f"❌ Erro ao baixar estoque do produto {item.produto_id}: {e}")
                        # Reverter transação se falhar baixa de estoque
                        db.rollback()
                        raise HTTPException(
                            status_code=400,
                            detail=f"Erro ao baixar estoque: {str(e)}"
                        )
            
            if estoque_baixado:
                logger.info(f"✅ Estoque baixado: {len(estoque_baixado)} item(ns) processado(s)")
            
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
                db, user_id, 'CREATE', 'vendas', venda.id,
                details=f'Venda {numero_venda} criada - Total: R$ {total:.2f}'
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
            
            return venda.to_dict()
            
        except HTTPException:
            db.rollback()
            logger.error(f"❌ HTTPException ao criar venda - Rollback executado")
            raise
            
        except Exception as e:
            db.rollback()
            logger.error(f"❌ ERRO CRÍTICO ao criar venda: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"Erro ao criar venda: {str(e)}"
            )
    
    @staticmethod
    def _processar_baixa_estoque_item(
        produto: 'Produto',
        quantidade_vendida: float,
        venda_id: int,
        user_id: int,
        tenant_id: str,
        db: Session,
        product_variation_id: int = None,
        venda_codigo: str = None
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
            variacao = db.query(Produto).filter(
                Produto.id == product_variation_id,
                Produto.tipo_produto == 'VARIACAO'
            ).first()
            
            if variacao:
                produto = variacao  # A variação é o próprio produto a ser baixado do estoque
        
        # ============================================================
        # CASO 1: PRODUTO SIMPLES OU VARIAÇÃO
        # ============================================================
        if produto.tipo_produto in ('SIMPLES', 'VARIACAO'):
            resultado_estoque = EstoqueService.baixar_estoque(
                produto_id=produto.id,
                quantidade=quantidade_vendida,
                motivo='venda',
                referencia_id=venda_id,
                referencia_tipo='venda',
                user_id=user_id,
                tenant_id=tenant_id,
                db=db,
                documento=venda_codigo,
                observacao=None
            )
            
            resultados.append({
                'produto': resultado_estoque['produto_nome'],
                'produto_id': produto.id,
                'tipo_produto': produto.tipo_produto,
                'quantidade': quantidade_vendida,
                'estoque_anterior': resultado_estoque['estoque_anterior'],
                'estoque_novo': resultado_estoque['estoque_novo']
            })
            
            logger.info(
                f"📦 Estoque baixado: {resultado_estoque['produto_nome']} - "
                f"Qtd: {quantidade_vendida} ({resultado_estoque['estoque_anterior']} → {resultado_estoque['estoque_novo']})"
            )
            
            return resultados
        
        # ============================================================
        # CASO 2: PRODUTO KIT
        # ============================================================
        if produto.tipo_produto == 'KIT':
            tipo_kit = produto.tipo_kit or 'VIRTUAL'  # Default VIRTUAL se não definido
            
            # --------------------------------------------------------
            # CASO 2.1: KIT FÍSICO (tratado como produto simples)
            # LÓGICA: Venda de kit físico só baixa o estoque do KIT
            # Os componentes já foram baixados quando o kit foi montado (entrada)
            # Portanto, NÃO sensibiliza os componentes novamente
            # --------------------------------------------------------
            if tipo_kit == 'FISICO':
                resultado_estoque = EstoqueService.baixar_estoque(
                    produto_id=produto.id,
                    quantidade=quantidade_vendida,
                    motivo='venda',
                    referencia_id=venda_id,
                    referencia_tipo='venda',
                    user_id=user_id,
                    tenant_id=tenant_id,
                    db=db,
                    documento=venda_codigo,
                    observacao=f"KIT FÍSICO - Estoque próprio (componentes já foram baixados na montagem)"
                )
                
                resultados.append({
                    'produto': resultado_estoque['produto_nome'],
                    'produto_id': produto.id,
                    'tipo_produto': 'KIT',
                    'tipo_kit': 'FISICO',
                    'quantidade': quantidade_vendida,
                    'estoque_anterior': resultado_estoque['estoque_anterior'],
                    'estoque_novo': resultado_estoque['estoque_novo']
                })
                
                logger.info(
                    f"📦 KIT FÍSICO vendido: {resultado_estoque['produto_nome']} - "
                    f"Qtd: {quantidade_vendida} ({resultado_estoque['estoque_anterior']} → {resultado_estoque['estoque_novo']}) "
                    f"[Componentes NÃO sensibilizados - já foram baixados na montagem]"
                )
                
                return resultados
            
            # --------------------------------------------------------
            # CASO 2.2: KIT VIRTUAL (baixa em cascata dos componentes)
            # --------------------------------------------------------
            if tipo_kit == 'VIRTUAL':
                from app.produtos_models import ProdutoKitComponente, Produto
                
                # Buscar componentes do KIT
                componentes = db.query(ProdutoKitComponente).filter(
                    ProdutoKitComponente.kit_id == produto.id
                ).all()
                
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
                    produto_componente = db.query(Produto).filter(
                        Produto.id == componente.produto_componente_id,
                        Produto.user_id == user_id
                    ).first()
                    
                    if not produto_componente:
                        raise ValueError(
                            f"Componente ID {componente.produto_componente_id} não encontrado"
                        )
                    
                    # Validar tipo do componente (apenas SIMPLES ou VARIACAO)
                    if produto_componente.tipo_produto not in ('SIMPLES', 'VARIACAO'):
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
                        motivo='venda',
                        referencia_id=venda_id,
                        referencia_tipo='venda',
                        user_id=user_id,
                        tenant_id=tenant_id,
                        db=db,
                        documento=venda_codigo,
                        observacao=f"Componente do KIT VIRTUAL '{produto.nome}' (vendido: {quantidade_vendida}x)"
                    )
                    
                    resultados.append({
                        'produto': resultado_componente['produto_nome'],
                        'produto_id': produto_componente.id,
                        'tipo_produto': produto_componente.tipo_produto,
                        'quantidade': quantidade_componente,
                        'estoque_anterior': resultado_componente['estoque_anterior'],
                        'estoque_novo': resultado_componente['estoque_novo'],
                        'kit_origem': produto.nome,
                        'kit_id': produto.id
                    })
                    
                    logger.info(
                        f"   ↳ Componente: {resultado_componente['produto_nome']} - "
                        f"Qtd: {quantidade_componente} ({resultado_componente['estoque_anterior']} → {resultado_componente['estoque_novo']})"
                    )
                
                logger.info(f"✅ KIT VIRTUAL '{produto.nome}' processado: {len(componentes)} componentes baixados")
                
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
        venda_id: int,
        motivo: str,
        user_id: int,
        tenant_id: str,
        db: Session
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
        from app.vendas_models import Venda, VendaItem, VendaPagamento
        from app.estoque.service import EstoqueService
        from app.caixa_models import MovimentacaoCaixa
        from app.financeiro_models import ContaReceber, LancamentoManual, MovimentacaoFinanceira, ContaBancaria
        from app.audit_log import log_action
        
        logger.info(f"🔴 Iniciando cancelamento ATÔMICO da venda #{venda_id}")
        
        with transactional_session(db):
            # ============================================================
            # ETAPA 1: VALIDAR VENDA E PERMISSÕES
            # ============================================================
            
            venda = db.query(Venda).filter_by(
                id=venda_id,
                user_id=user_id
            ).first()
            
            if not venda:
                raise HTTPException(status_code=404, detail='Venda não encontrada')
            
            if venda.status == 'cancelada':
                raise HTTPException(status_code=400, detail='Venda já está cancelada')
            
            logger.info(f"📋 Cancelando venda #{venda.numero_venda} (Status: {venda.status})")
            
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
                            motivo='cancelamento_venda',
                            referencia_id=venda_id,
                            referencia_tipo='venda',
                            user_id=user_id,
                            tenant_id=tenant_id,
                            db=db,
                            documento=venda.numero_venda,
                            observacao=f"Cancelamento: {motivo}"
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
                            detail=f'Erro ao estornar estoque: {str(e)}'
                        )
            
            logger.info(f"📦 Total de itens estornados: {itens_estornados}/{len(itens)}")
            
            # ============================================================
            # ETAPA 3: CANCELAR CONTAS A RECEBER VINCULADAS
            # ============================================================
            
            contas_receber = db.query(ContaReceber).filter_by(venda_id=venda_id).all()
            contas_canceladas = 0
            
            for conta in contas_receber:
                if conta.status == 'pendente' or conta.status == 'parcial':
                    logger.info(
                        f"  💳 Removendo conta a receber pendente: {conta.descricao} - "
                        f"R$ {conta.valor_original}"
                    )
                    db.delete(conta)
                elif conta.status == 'recebido':
                    conta.status = 'cancelado'
                    logger.info(
                        f"  💳 Cancelando conta já recebida: {conta.descricao} - "
                        f"R$ {conta.valor_recebido}"
                    )
                contas_canceladas += 1
            
            logger.info(f"💳 Total de contas canceladas: {contas_canceladas}")
            
            # ============================================================
            # ETAPA 4: CANCELAR LANÇAMENTOS MANUAIS
            # ============================================================
            
            lancamentos = db.query(LancamentoManual).filter(
                or_(
                    LancamentoManual.documento == f"VENDA-{venda_id}",
                    LancamentoManual.documento.like(f"VENDA-{venda_id}-%")
                )
            ).all()
            
            lancamentos_cancelados = 0
            for lanc in lancamentos:
                if lanc.status == 'previsto':
                    logger.info(
                        f"  📊 Removendo lançamento previsto: {lanc.descricao} - "
                        f"R$ {lanc.valor}"
                    )
                    db.delete(lanc)
                elif lanc.status == 'realizado':
                    lanc.status = 'cancelado'
                    logger.info(
                        f"  📊 Cancelando lançamento realizado: {lanc.descricao} - "
                        f"R$ {lanc.valor}"
                    )
                lancamentos_cancelados += 1
            
            logger.info(f"📊 Total de lançamentos cancelados: {lancamentos_cancelados}")
            
            # ============================================================
            # ETAPA 5: REMOVER MOVIMENTAÇÕES DE CAIXA
            # ============================================================
            
            movimentacoes_caixa = db.query(MovimentacaoCaixa).filter_by(
                venda_id=venda_id
            ).all()
            
            movimentacoes_removidas = 0
            for mov in movimentacoes_caixa:
                logger.info(
                    f"  💵 Removendo movimentação de caixa: R$ {mov.valor} ({mov.tipo})"
                )
                db.delete(mov)
                movimentacoes_removidas += 1
            
            logger.info(f"💵 Total de movimentações de caixa removidas: {movimentacoes_removidas}")
            
            # ============================================================
            # ETAPA 6: ESTORNAR MOVIMENTAÇÕES BANCÁRIAS
            # ============================================================
            
            movimentacoes_bancarias = db.query(MovimentacaoFinanceira).filter_by(
                venda_id=venda_id
            ).all()
            
            movimentacoes_estornadas = 0
            for mov_banc in movimentacoes_bancarias:
                conta_bancaria = db.query(ContaBancaria).filter_by(
                    id=mov_banc.conta_bancaria_id,
                    user_id=user_id
                ).first()
                
                if conta_bancaria:
                    if mov_banc.tipo == 'receita':
                        conta_bancaria.saldo_atual -= mov_banc.valor
                        logger.info(
                            f"  🏦 Estornando saldo bancário: {conta_bancaria.nome} "
                            f"-R$ {mov_banc.valor}"
                        )
                    elif mov_banc.tipo == 'despesa':
                        conta_bancaria.saldo_atual += mov_banc.valor
                        logger.info(
                            f"  🏦 Estornando saldo bancário: {conta_bancaria.nome} "
                            f"+R$ {mov_banc.valor}"
                        )
                    
                    db.delete(mov_banc)
                    movimentacoes_estornadas += 1
            
            logger.info(f"🏦 Total de movimentações bancárias estornadas: {movimentacoes_estornadas}")
            
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
                logger.info(f"📋 Total de paradas de entrega removidas: {paradas_removidas}")
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
                    db=db
                )
                
                if resultado_estorno['success'] and resultado_estorno['comissoes_estornadas'] > 0:
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
            venda.status = 'cancelada'
            venda.cancelada_por = user_id
            venda.motivo_cancelamento = motivo
            venda.data_cancelamento = now_brasilia()
            venda.updated_at = now_brasilia()
            
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
                action='UPDATE',
                entity_type='vendas',
                entity_id=venda.id,
                details=(
                    f'Venda {venda.numero_venda} CANCELADA (ATÔMICO) - '
                    f'Motivo: {motivo} - '
                    f'Itens estornados: {itens_estornados} - '
                    f'Contas canceladas: {contas_canceladas}'
                )
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
        
        return {
            'venda': venda.to_dict(),
            'estornos': {
                'itens_estornados': itens_estornados,
                'contas_canceladas': contas_canceladas,
                'lancamentos_cancelados': lancamentos_cancelados,
                'movimentacoes_removidas': movimentacoes_removidas,
                'movimentacoes_bancarias_estornadas': movimentacoes_estornadas
            }
        }
    
    @staticmethod
    def _gerar_numero_venda(db: Session, user_id: int) -> str:
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
        prefixo = hoje.strftime('%Y%m%d')
        
        # Buscar última venda do dia
        ultima_venda = db.query(Venda).filter(
            Venda.numero_venda.like(f'{prefixo}%'),
            Venda.user_id == user_id
        ).order_by(desc(Venda.numero_venda)).first()
        
        if ultima_venda:
            try:
                seq = int(ultima_venda.numero_venda[-4:]) + 1
            except:
                seq = 1
        else:
            seq = 1
        
        return f'{prefixo}{seq:04d}'
    
    @staticmethod
    def finalizar_venda(
        venda_id: int,
        pagamentos: List[Dict[str, Any]],
        user_id: int,
        user_nome: str,
        tenant_id: str,
        db: Session
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
        from app.models import Cliente
        from app.estoque.service import EstoqueService
        from app.caixa.service import CaixaService
        from app.financeiro import ContasReceberService
        from app.financeiro_models import LancamentoManual, CategoriaFinanceira
        
        logger.info(f"🚀 Iniciando finalização da venda #{venda_id} - {len(pagamentos)} pagamento(s)")
        
        try:
            # ============================================================
            # ETAPA 1: VALIDAÇÕES INICIAIS
            # ============================================================
            
            # Validar caixa aberto
            caixa_info = CaixaService.validar_caixa_aberto(user_id=user_id, db=db)
            caixa_aberto_id = caixa_info['caixa_id']
            logger.debug(f"✅ Caixa validado: ID={caixa_aberto_id}")
            
            # Buscar venda
            venda = db.query(Venda).filter_by(id=venda_id, tenant_id=tenant_id).first()
            if not venda:
                raise HTTPException(status_code=404, detail='Venda não encontrada')
            
            # Validar status
            if venda.status not in ['aberta', 'baixa_parcial']:
                raise HTTPException(
                    status_code=400,
                    detail=f'Apenas vendas abertas ou com baixa parcial podem receber pagamentos (status atual: {venda.status})'
                )
            
            # Validar pagamentos
            if not pagamentos:
                raise HTTPException(status_code=400, detail='Informe pelo menos uma forma de pagamento')
            
            # Calcular totais
            pagamentos_existentes = db.query(VendaPagamento).filter_by(venda_id=venda.id).all()
            total_ja_pago = sum(float(p.valor) for p in pagamentos_existentes)
            total_venda = float(venda.total)
            valor_restante = total_venda - total_ja_pago
            
            if abs(valor_restante) < 0.01:
                raise HTTPException(status_code=400, detail='Venda já está totalmente paga')
            
            total_novos_pagamentos = sum(p['valor'] for p in pagamentos)
            total_pagamentos = total_ja_pago + total_novos_pagamentos
            
            logger.info(
                f"💰 Totais: Venda=R$ {total_venda:.2f}, "
                f"Já pago=R$ {total_ja_pago:.2f}, "
                f"Novos=R$ {total_novos_pagamentos:.2f}"
            )
            
            # ============================================================
            # ETAPA 2: PROCESSAR PAGAMENTOS
            # ============================================================
            
            movimentacoes_caixa_ids = []
            
            for pag_data in pagamentos:
                # ⚠️ ALERTA 1: VALIDAR PARCELAS CONTRA OPERADORA
                # Garante que número de parcelas não exceda o máximo da operadora
                operadora_id = pag_data.get('operadora_id')
                numero_parcelas = pag_data.get('numero_parcelas', 1)
                
                if operadora_id and numero_parcelas > 1:
                    from app.operadoras_models import OperadoraCartao
                    
                    operadora = db.query(OperadoraCartao).filter_by(id=operadora_id).first()
                    if not operadora:
                        raise HTTPException(
                            status_code=400,
                            detail=f"❌ Operadora não encontrada (ID: {operadora_id})"
                        )
                    
                    if numero_parcelas > operadora.max_parcelas:
                        raise HTTPException(
                            status_code=400,
                            detail=f"❌ PARCELAS EXCEDIDAS: {operadora.nome} permite no máximo "
                                   f"{operadora.max_parcelas}x. Você tentou {numero_parcelas}x."
                        )
                
                # ⚠️ ALERTA 2: VALIDAR NSU DUPLICADO
                # Garante que o mesmo NSU não seja usado duas vezes na mesma operadora
                nsu_informado = pag_data.get('nsu_cartao')
                if nsu_informado and operadora_id:
                    nsu_duplicado = db.query(VendaPagamento).filter(
                        VendaPagamento.tenant_id == tenant_id,
                        VendaPagamento.nsu_cartao == nsu_informado,
                        VendaPagamento.operadora_id == operadora_id
                    ).first()
                    
                    if nsu_duplicado:
                        venda_duplicada = db.query(Venda).filter_by(id=nsu_duplicado.venda_id).first()
                        raise HTTPException(
                            status_code=400,
                            detail=f"❌ NSU DUPLICADO: O NSU '{nsu_informado}' já está vinculado à "
                                   f"Venda {venda_duplicada.numero_venda if venda_duplicada else nsu_duplicado.venda_id}. "
                                   f"Cada NSU deve ser usado apenas uma vez por operadora."
                        )
                
                # Criar registro de pagamento
                # 🔒 ISOLAMENTO MULTI-TENANT: tenant_id obrigatório
                pagamento = VendaPagamento(
                    venda_id=venda.id,
                    tenant_id=tenant_id,  # ✅ Garantir isolamento entre empresas
                    forma_pagamento=pag_data['forma_pagamento'],
                    valor=pag_data['valor'],
                    numero_parcelas=numero_parcelas,
                    bandeira=pag_data.get('bandeira'),  # ✅ Bandeira do cartão
                    nsu_cartao=pag_data.get('nsu_cartao'),  # ✅ NSU para conciliação
                    operadora_id=operadora_id  # ✅ Operadora de cartão
                )
                db.add(pagamento)
                db.flush()
                
                # Processar crédito de cliente
                forma_eh_credito = (
                    pag_data['forma_pagamento'].lower() == 'credito_cliente' or
                    pag_data['forma_pagamento'] == 'Crédito Cliente'
                )
                
                if forma_eh_credito:
                    if not venda.cliente_id:
                        raise HTTPException(
                            status_code=400,
                            detail='Crédito só pode ser usado em vendas com cliente vinculado'
                        )
                    
                    cliente = db.query(Cliente).filter_by(id=venda.cliente_id).first()
                    if not cliente:
                        raise HTTPException(status_code=404, detail='Cliente não encontrado')
                    
                    credito_disponivel = float(cliente.credito or 0)
                    if pag_data['valor'] > credito_disponivel + 0.01:
                        raise HTTPException(
                            status_code=400,
                            detail=f'Crédito insuficiente. Disponível: R$ {credito_disponivel:.2f}'
                        )
                    
                    cliente.credito = Decimal(str(credito_disponivel - pag_data['valor']))
                    db.add(cliente)
                    logger.info(
                        f"🎁 Crédito utilizado: R$ {pag_data['valor']:.2f} - "
                        f"Saldo restante: R$ {float(cliente.credito):.2f}"
                    )
                    continue

                # Processar cashback de campanhas
                forma_eh_cashback = (
                    pag_data['forma_pagamento'].lower() == 'cashback' or
                    pag_data['forma_pagamento'] == 'Cashback'
                )

                if forma_eh_cashback:
                    if not venda.cliente_id:
                        raise HTTPException(
                            status_code=400,
                            detail='Cashback só pode ser usado em vendas com cliente vinculado'
                        )

                    from app.campaigns.models import CashbackTransaction, CashbackSourceTypeEnum

                    saldo_raw = db.query(func.sum(CashbackTransaction.amount)).filter(
                        CashbackTransaction.tenant_id == tenant_id,
                        CashbackTransaction.customer_id == venda.cliente_id,
                    ).scalar()
                    saldo_disponivel = float(saldo_raw or 0)

                    if pag_data['valor'] > saldo_disponivel + 0.01:
                        raise HTTPException(
                            status_code=400,
                            detail=f'Cashback insuficiente. Disponível: R$ {saldo_disponivel:.2f}'
                        )

                    debit = CashbackTransaction(
                        tenant_id=tenant_id,
                        customer_id=venda.cliente_id,
                        amount=-Decimal(str(pag_data['valor'])),
                        source_type=CashbackSourceTypeEnum.manual,
                        source_id=venda.id,  # FK para rastreamento por venda
                        description=f"Resgate em venda {venda.numero_venda}",
                    )
                    db.add(debit)

                    # ── DRE: registrar como despesa de campanhas/marketing ──
                    # Não gera fluxo de caixa (conta_bancaria_id=None)
                    from app.financeiro_models import LancamentoManual, CategoriaFinanceira
                    from datetime import date as _date

                    cat_campanha = db.query(CategoriaFinanceira).filter(
                        CategoriaFinanceira.nome.ilike('%campanha%'),
                        CategoriaFinanceira.tipo == 'despesa',
                        CategoriaFinanceira.tenant_id == tenant_id,
                    ).first()
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
                        valor=Decimal(str(pag_data['valor'])),
                        descricao=f"Cashback resgatado — {cliente_nome} — Venda {venda.numero_venda}",
                        data_lancamento=venda.data_venda.date() if hasattr(venda.data_venda, 'date') else _date.today(),
                        status="realizado",
                        categoria_id=cat_campanha.id,
                        conta_bancaria_id=None,   # sem movimentação de caixa
                        fornecedor_cliente=cliente_nome,
                        documento=f"CASHBACK-{venda.numero_venda}",
                        gerado_automaticamente=True,
                        user_id=user_id,
                        tenant_id=tenant_id,
                    )
                    db.add(lancamento_campanha)
                    logger.info(
                        "💰 Cashback utilizado: R$ %.2f — DRE despesa campanha criada — venda=%s",
                        pag_data['valor'], venda.numero_venda,
                    )
                    continue

                # Registrar no caixa (apenas dinheiro)
                if CaixaService.eh_forma_dinheiro(pag_data['forma_pagamento']):
                    mov_info = CaixaService.registrar_movimentacao_venda(
                        caixa_id=caixa_aberto_id,
                        venda_id=venda.id,
                        venda_numero=venda.numero_venda,
                        valor=pag_data['valor'],
                        user_id=user_id,
                        user_nome=user_nome,
                        tenant_id=tenant_id,  # 🔒 Isolamento multi-tenant
                        db=db
                    )
                    movimentacoes_caixa_ids.append(mov_info['movimentacao_id'])
                    logger.info(f"💵 Caixa: Movimentação #{mov_info['movimentacao_id']} criada")
            
            # ============================================================
            # ETAPA 3: ATUALIZAR STATUS DA VENDA
            # ============================================================
            
            # 🎯 GUARDAR STATUS ANTERIOR (para decisão de baixa de estoque)
            status_anterior = venda.status
            logger.info(f"📋 Status anterior: {status_anterior}")
            
            if abs(total_pagamentos - total_venda) < 0.01:
                # Pagamento completo
                venda.status = 'finalizada'
                venda.data_finalizacao = now_brasilia()
                logger.info(f"✅ Venda FINALIZADA - Pagamento completo")
            elif total_pagamentos > 0:
                # Pagamento parcial
                venda.status = 'baixa_parcial'
                logger.info(f"📊 Venda BAIXA PARCIAL - R$ {total_pagamentos:.2f} de R$ {total_venda:.2f}")
                
                # Criar lançamento previsto para saldo em aberto
                saldo_em_aberto = total_venda - total_pagamentos
                if saldo_em_aberto > 0.01:
                    categoria_receitas = db.query(CategoriaFinanceira).filter(
                        CategoriaFinanceira.nome.ilike('%vendas%'),
                        CategoriaFinanceira.tipo == 'receita',
                        CategoriaFinanceira.tenant_id == tenant_id
                    ).first()
                    
                    if not categoria_receitas:
                        categoria_receitas = CategoriaFinanceira(
                            nome="Receitas de Vendas",
                            tipo="receita",
                            user_id=user_id,
                            tenant_id=tenant_id  # ✅ Garantir isolamento multi-tenant
                        )
                        db.add(categoria_receitas)
                        db.flush()
                    
                    data_prevista = date.today() + timedelta(days=30)
                    lancamento_saldo = LancamentoManual(
                        tipo='entrada',
                        valor=Decimal(str(saldo_em_aberto)),
                        descricao=f"Venda {venda.numero_venda} - Saldo em aberto",
                        data_lancamento=data_prevista,
                        status='previsto',
                        categoria_id=categoria_receitas.id,
                        documento=f"VENDA-{venda.id}-SALDO",
                        fornecedor_cliente=venda.cliente.nome if venda.cliente else "Cliente Avulso",
                        user_id=user_id,
                        tenant_id=tenant_id  # ✅ Garantir isolamento multi-tenant
                    )
                    db.add(lancamento_saldo)
                    logger.info(f"📝 Lançamento previsto criado: R$ {saldo_em_aberto:.2f} em {data_prevista}")
            else:
                venda.status = 'aberta'
            
            venda.updated_at = now_brasilia()
            
            # ============================================================
            # ETAPA 3.5: GERAR DRE POR COMPETÊNCIA (PASSO 1 - Sprint 5)
            # ============================================================
            
            # 🎯 EVENTO DE EFETIVAÇÃO: Venda passou de 'aberta' para qualquer status com pagamento
            # Condições para gerar DRE:
            # 1. Venda tem pagamento (parcial ou total)
            # 2. DRE ainda não foi gerada (venda.dre_gerada == False)
            # 3. Status é 'baixa_parcial' ou 'finalizada' (não 'aberta')
            
            if venda.status in ['baixa_parcial', 'finalizada'] and not venda.dre_gerada:
                logger.info(
                    f"🎯 EVENTO DE EFETIVAÇÃO DETECTADO: Venda #{venda.numero_venda} "
                    f"mudou para status '{venda.status}' - Gerando DRE por competência..."
                )
                
                try:
                    resultado_dre = gerar_dre_competencia_venda(
                        venda_id=venda.id,
                        user_id=user_id,
                        tenant_id=tenant_id,
                        db=db
                    )
                    
                    if resultado_dre['success']:
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
                        exc_info=True
                    )
                    # Continua a finalização da venda normalmente
            
            # ============================================================
            # ETAPA 4: BAIXAR ESTOQUE (COM SUPORTE A KIT)
            # ============================================================
            # 🎯 LÓGICA CRÍTICA: Só baixa estoque se venda NÃO veio de status 'aberta'
            # - Se status_anterior = 'aberta': estoque JÁ foi baixado na criação
            # - Se status_anterior != 'aberta': venda criada direto como finalizada, baixar agora
            
            estoque_baixado = []
            deve_baixar_estoque = (status_anterior != 'aberta')
            
            if deve_baixar_estoque:
                logger.info(f"📦 Baixando estoque (venda não veio de status aberta)")
            else:
                logger.info(f"ℹ️  Estoque NÃO será baixado (já foi baixado quando venda estava aberta)")
            
            for item in venda.itens:
                if item.tipo == 'produto':
                    # Determinar se é produto simples ou variação
                    produto_id = item.produto_id
                    product_variation_id = item.product_variation_id
                    
                    # Buscar produto (simples ou da variação)
                    from app.produtos_models import Produto
                    
                    if product_variation_id:
                        # Item com variação: buscar o produto da variação
                        variacao = db.query(Produto).filter(
                            Produto.id == product_variation_id,
                            Produto.tipo_produto == 'VARIACAO'
                        ).first()
                        
                        if not variacao:
                            raise ValueError(f"Variação ID {product_variation_id} não encontrada")
                        
                        produto = variacao
                    elif produto_id:
                        # Item com produto simples
                        produto = db.query(Produto).filter(
                            Produto.id == produto_id,
                            Produto.tenant_id == tenant_id
                        ).first()
                        
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
                            venda_codigo=venda.numero_venda
                        )
                        
                        # Acumular resultados
                        estoque_baixado.extend(resultados)
            
            # ============================================================
            # ETAPA 5: VINCULAR AO CAIXA
            # ============================================================
            
            if not venda.caixa_id:
                CaixaService.vincular_venda_ao_caixa(
                    venda_id=venda.id,
                    caixa_id=caixa_aberto_id,
                    db=db
                )
                logger.info(f"🔗 Venda vinculada ao caixa #{caixa_aberto_id}")
            
            # ============================================================
            # ETAPA 6: BAIXAR CONTAS A RECEBER EXISTENTES
            # ============================================================
            
            contas_baixadas = []
            if total_novos_pagamentos > 0.01:
                forma_pag_nome = pagamentos[0]['forma_pagamento'] if pagamentos else "Diversos"
                
                resultado_baixa = ContasReceberService.baixar_contas_da_venda(
                    venda_id=venda.id,
                    venda_numero=venda.numero_venda,
                    valor_total_pagamento=total_novos_pagamentos,
                    forma_pagamento_nome=forma_pag_nome,
                    user_id=user_id,
                    tenant_id=tenant_id,
                    db=db
                )
                
                contas_baixadas = resultado_baixa['contas_baixadas']
                
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
                    db=db
                )
                
                logger.info(
                    f"📝 Lançamentos: {len(resultado_lancamentos['lancamentos_atualizados'])} atualizado(s), "
                    f"Status: {resultado_lancamentos['status']}"
                )
            
            # ============================================================
            # 🔥 COMMIT ÚNICO - TRANSAÇÃO ATÔMICA 🔥
            # ============================================================
            
            db.commit()
            logger.info(f"✅ ✅ ✅ COMMIT REALIZADO - Venda #{venda.numero_venda} finalizada com sucesso! ✅ ✅ ✅")
            
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
            
            # Novos eventos: VendaRealizadaEvent + eventos por produto/KIT
            try:
                from app.events import VendaRealizadaEvent, ProdutoVendidoEvent, KitVendidoEvent, publish_event
                
                # 1. Evento principal da venda
                forma_pagamento_principal = pagamentos[0]['forma_pagamento'] if pagamentos else "Não especificado"
                tem_kit = any(
                    resultado.get('kit_origem') or resultado.get('tipo_kit') 
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
                        'status': venda.status,
                        'total_pago': total_pagamentos,
                        'formas_pagamento': [p['forma_pagamento'] for p in pagamentos],
                        'tem_entrega': venda.tem_entrega
                    }
                )
                publish_event(evento_venda)
                logger.debug(f"📢 VendaRealizadaEvent publicado (venda_id={venda.id})")
                
                # 2. Eventos por produto/KIT vendido
                # Agrupar resultados por produto (pode ter múltiplas entradas para KIT VIRTUAL)
                produtos_processados = {}
                kits_processados = {}
                
                for resultado in estoque_baixado:
                    produto_id = resultado.get('produto_id')
                    
                    # Se é componente de KIT VIRTUAL
                    if resultado.get('kit_origem'):
                        kit_id = resultado.get('kit_id')
                        kit_nome = resultado.get('kit_origem')
                        
                        # Acumular componentes do KIT
                        if kit_id not in kits_processados:
                            kits_processados[kit_id] = {
                                'kit_nome': kit_nome,
                                'tipo_kit': 'VIRTUAL',
                                'componentes': []
                            }
                        
                        kits_processados[kit_id]['componentes'].append({
                            'produto_id': produto_id,
                            'nome': resultado.get('produto'),
                            'quantidade': resultado.get('quantidade'),
                            'estoque_anterior': resultado.get('estoque_anterior'),
                            'estoque_novo': resultado.get('estoque_novo')
                        })
                    
                    # Se é KIT FÍSICO
                    elif resultado.get('tipo_kit') == 'FISICO':
                        kit_id = produto_id
                        kit_nome = resultado.get('produto')
                        
                        kits_processados[kit_id] = {
                            'kit_nome': kit_nome,
                            'tipo_kit': 'FISICO',
                            'quantidade': resultado.get('quantidade'),
                            'estoque_anterior': resultado.get('estoque_anterior'),
                            'estoque_novo': resultado.get('estoque_novo'),
                            'componentes': []
                        }
                    
                    # Se é produto SIMPLES/VARIACAO (não é componente de KIT)
                    elif not resultado.get('kit_origem'):
                        produtos_processados[produto_id] = resultado
                
                # Publicar eventos de produtos SIMPLES/VARIACAO
                for produto_id, resultado in produtos_processados.items():
                    # Buscar item da venda para obter preços
                    item_venda = next(
                        (item for item in venda.itens if item.produto_id == produto_id),
                        None
                    )
                    
                    if item_venda:
                        evento_produto = ProdutoVendidoEvent(
                            venda_id=venda.id,
                            produto_id=produto_id,
                            produto_nome=resultado.get('produto'),
                            tipo_produto=resultado.get('tipo_produto', 'SIMPLES'),
                            quantidade=float(resultado.get('quantidade')),
                            preco_unitario=float(item_venda.preco_unitario or 0),
                            preco_total=float(item_venda.subtotal or 0),
                            estoque_anterior=float(resultado.get('estoque_anterior')),
                            estoque_novo=float(resultado.get('estoque_novo')),
                            user_id=user_id
                        )
                        publish_event(evento_produto)
                        logger.debug(f"📢 ProdutoVendidoEvent publicado (produto_id={produto_id})")
                
                # Publicar eventos de KITs
                for kit_id, kit_info in kits_processados.items():
                    # Buscar item da venda para obter preços
                    item_venda = next(
                        (item for item in venda.itens if item.produto_id == kit_id),
                        None
                    )
                    
                    if item_venda:
                        evento_kit = KitVendidoEvent(
                            venda_id=venda.id,
                            kit_id=kit_id,
                            kit_nome=kit_info['kit_nome'],
                            tipo_kit=kit_info['tipo_kit'],
                            quantidade=float(kit_info.get('quantidade', item_venda.quantidade)),
                            preco_unitario=float(item_venda.preco_unitario or 0),
                            preco_total=float(item_venda.preco_total or 0),
                            componentes_baixados=kit_info.get('componentes', []),
                            estoque_kit_anterior=float(kit_info.get('estoque_anterior')) if kit_info.get('estoque_anterior') else None,
                            estoque_kit_novo=float(kit_info.get('estoque_novo')) if kit_info.get('estoque_novo') else None,
                            user_id=user_id
                        )
                        publish_event(evento_kit)
                        logger.debug(f"📢 KitVendidoEvent publicado (kit_id={kit_id}, tipo={kit_info['tipo_kit']})")
                
                logger.info(
                    f"📢 Eventos publicados: 1 VendaRealizadaEvent, "
                    f"{len(produtos_processados)} ProdutoVendidoEvent, "
                    f"{len(kits_processados)} KitVendidoEvent"
                )
                
            except Exception as e:
                logger.error(f"⚠️  Erro ao publicar novos eventos de domínio: {str(e)}", exc_info=True)
                # Não aborta a finalização
            
            # ============================================================
            # ETAPA 8: OPERAÇÕES PÓS-COMMIT (não abortam se falharem)
            # ============================================================
            
            # Criar novas contas a receber
            contas_criadas_ids = []
            try:
                resultado_contas = ContasReceberService.criar_de_venda(
                    venda=venda,
                    pagamentos=pagamentos,
                    user_id=user_id,
                    db=db
                )
                contas_criadas_ids = resultado_contas['contas_criadas']
                db.commit()  # Commit separado para contas
                logger.info(
                    f"📋 Contas a receber criadas: {resultado_contas['total_contas']} conta(s), "
                    f"{len(resultado_contas['lancamentos_criados'])} lançamento(s)"
                )
            except Exception as e:
                logger.error(f"⚠️ Erro ao criar contas a receber: {str(e)}", exc_info=True)
                db.rollback()  # Rollback apenas das contas (venda já commitada)
            
            # 🚚 Criar contas a pagar de entrega (taxa entregador + custo operacional)
            contas_pagar_entrega_ids = []
            try:
                resultado_entrega = processar_contas_pagar_entrega(
                    venda=venda,
                    user_id=user_id,
                    tenant_id=tenant_id,
                    db=db
                )
                if resultado_entrega['success']:
                    contas_pagar_entrega_ids = resultado_entrega['contas_criadas']
                    db.commit()  # Commit separado para contas a pagar
                    logger.info(
                        f"🚚 Contas a pagar de entrega criadas: {resultado_entrega['total_contas']} conta(s), "
                        f"R$ {resultado_entrega['valor_total']:.2f}"
                    )
            except Exception as e:
                logger.error(f"⚠️ Erro ao criar contas a pagar de entrega: {str(e)}", exc_info=True)
                db.rollback()  # Rollback apenas das contas (venda já commitada)
            
            # 💳 Criar contas a pagar de taxas de pagamento
            contas_pagar_taxas_ids = []
            logger.info(f"💳 Iniciando processamento de taxas de pagamento - Venda #{venda.numero_venda}")
            try:
                # Combinar pagamentos existentes com novos
                todos_pagamentos = list(pagamentos_existentes) + [
                    type('obj', (object,), {
                        'forma_pagamento': p['forma_pagamento'],
                        'valor': p['valor'],
                        'numero_parcelas': p.get('numero_parcelas', 1)
                    })() for p in pagamentos
                ]
                
                logger.info(f"💳 Total de pagamentos a processar: {len(todos_pagamentos)}")
                for pag in todos_pagamentos:
                    logger.info(f"  - {pag.forma_pagamento}: R$ {pag.valor}")
                
                resultado_taxas = processar_contas_pagar_taxas(
                    venda=venda,
                    pagamentos=todos_pagamentos,
                    user_id=user_id,
                    tenant_id=tenant_id,
                    db=db
                )
                
                logger.info(f"💳 Resultado do processamento: {resultado_taxas}")
                
                if resultado_taxas['success']:
                    contas_pagar_taxas_ids = resultado_taxas['contas_criadas']
                    db.commit()  # Commit separado para contas a pagar
                    logger.info(
                        f"💳 Contas a pagar de taxas criadas: {resultado_taxas['total_contas']} conta(s), "
                        f"R$ {resultado_taxas['valor_total']:.2f}"
                    )
                else:
                    logger.warning(f"⚠️ Processamento de taxas falhou: {resultado_taxas.get('error', 'Erro desconhecido')}")
            except Exception as e:
                logger.error(f"⚠️ Erro ao criar contas a pagar de taxas: {str(e)}", exc_info=True)
                db.rollback()  # Rollback apenas das contas (venda já commitada)
            
            # 📢 Enfileirar evento de campanha (purchase_completed)
            if venda.status == 'finalizada' and venda.cliente_id:
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
                        },
                    )
                    db.add(evento_campanha)
                    db.commit()
                    logger.info(
                        "📢 [Campanhas] purchase_completed enfileirado: "
                        "venda=%s cliente_id=%d total=R$%.2f",
                        venda.numero_venda, venda.cliente_id, float(venda.total)
                    )
                except Exception as e:
                    logger.warning("[Campanhas] Falha ao enfileirar purchase_completed (não crítico): %s", e)
                    db.rollback()

            # Preparar retorno
            return {
                'venda': {
                    'id': venda.id,
                    'numero_venda': venda.numero_venda,
                    'status': venda.status,
                    'total': float(venda.total),
                    'total_pago': total_pagamentos,
                    'data_finalizacao': venda.data_finalizacao.isoformat() if venda.data_finalizacao else None
                },
                'operacoes': {
                    'estoque_baixado': estoque_baixado,
                    'caixa_movimentacoes': movimentacoes_caixa_ids,
                    'contas_baixadas': contas_baixadas,
                    'contas_criadas': contas_criadas_ids
                },
                'pos_commit': {
                    'contas_novas': len(contas_criadas_ids),
                    'comissoes_geradas': False,  # Será processado na rota
                    'lembretes_criados': 0  # Será processado na rota
                }
            }
            
        except HTTPException:
            # Re-lançar HTTPException (já tem mensagem amigável)
            db.rollback()
            logger.error(f"❌ HTTPException na finalização da venda #{venda_id} - Rollback executado")
            raise
            
        except Exception as e:
            # Rollback em caso de erro inesperado
            db.rollback()
            logger.error(f"❌ ERRO CRÍTICO na finalização da venda #{venda_id}: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"Erro ao finalizar venda: {str(e)}"
            )


# ============================================================================
# FUNÇÕES AUXILIARES
# ============================================================================

def processar_comissoes_venda(
    venda_id: int,
    funcionario_id: Optional[int],
    valor_pago: Optional[float],
    user_id: int,
    db: Session
) -> Dict[str, Any]:
    """
    Processa comissões de uma venda (operação pós-commit).
    
    Esta função é chamada APÓS o commit da venda principal,
    portanto erros aqui não abortam a venda.
    
    Args:
        venda_id: ID da venda
        funcionario_id: ID do funcionário (se houver)
        valor_pago: Valor pago (para parciais)
        user_id: ID do usuário
        db: Sessão do SQLAlchemy
        
    Returns:
        Dict com resultado do processamento
    """
    if not funcionario_id:
        return {
            'success': False,
            'message': 'Venda sem funcionário vinculado'
        }
    
    try:
        from app.comissoes_service import gerar_comissoes_venda
        from decimal import Decimal
        
        valor_pago_decimal = Decimal(str(valor_pago)) if valor_pago else None
        
        resultado = gerar_comissoes_venda(
            venda_id=venda_id,
            funcionario_id=funcionario_id,
            valor_pago=valor_pago_decimal,
            db=db
        )
        
        if resultado and resultado.get('success'):
            return {
                'success': True,
                'total_comissao': float(resultado.get('total_comissao', 0)),
                'duplicated': resultado.get('duplicated', False)
            }
        else:
            return {
                'success': False,
                'message': 'Nenhuma comissão gerada (sem configuração)'
            }
            
    except Exception as e:
        logger.error(f"⚠️ Erro ao processar comissões (venda {venda_id}): {str(e)}", exc_info=True)
        return {
            'success': False,
            'error': str(e)
        }


def processar_lembretes_venda(
    venda_id: int,
    cliente_id: Optional[int],
    itens: List[Any],
    user_id: int,
    db: Session
) -> Dict[str, Any]:
    """
    Processa lembretes/recorrências de uma venda (operação pós-commit).
    
    Esta função é chamada APÓS o commit da venda principal,
    portanto erros aqui não abortam a venda.
    
    Args:
        venda_id: ID da venda
        cliente_id: ID do cliente (se houver)
        itens: Lista de itens da venda
        user_id: ID do usuário
        db: Sessão do SQLAlchemy
        
    Returns:
        Dict com resultado do processamento
    """
    if not cliente_id:
        return {
            'success': False,
            'message': 'Venda sem cliente vinculado'
        }
    
    try:
        from app.produtos_models import Produto, Lembrete
        from app.models import Pet
        
        lembretes_criados = []
        lembretes_atualizados = []
        
        for item in itens:
            if item.tipo == 'produto' and item.produto_id and item.pet_id:
                produto = db.query(Produto).get(item.produto_id)
                pet = db.query(Pet).get(item.pet_id)
                
                if produto and pet and produto.tem_recorrencia and produto.intervalo_dias:
                    # Processar lembrete (lógica simplificada - detalhes na rota)
                    logger.info(f"🔔 Processando lembrete: {produto.nome} para {pet.nome}")
                    lembretes_criados.append(produto.nome)
        
        return {
            'success': True,
            'lembretes_criados': len(lembretes_criados),
            'lembretes_atualizados': len(lembretes_atualizados)
        }
        
    except Exception as e:
        logger.error(f"⚠️ Erro ao processar lembretes (venda {venda_id}): {str(e)}", exc_info=True)
        return {
            'success': False,
            'error': str(e)
        }


def processar_contas_pagar_entrega(
    venda: 'Venda',
    user_id: int,
    tenant_id: str,
    db: Session
) -> Dict[str, Any]:
    """
    Cria contas a pagar relacionadas à entrega (operação pós-commit).
    
    Cria 2 tipos de contas a pagar:
    1. Taxa do entregador (parte da taxa de entrega que vai para ele)
    2. Custo operacional (fixo ou controla_rh - KM rodado é criado ao fechar rota)
    
    Args:
        venda: Objeto Venda (já commitada)
        user_id: ID do usuário
        tenant_id: UUID do tenant
        db: Sessão do SQLAlchemy
        
    Returns:
        Dict com resultado:
        {
            'success': bool,
            'total_contas': int,
            'valor_total': float,
            'contas_criadas': List[int],
            'detalhes': List[str]
        }
    """
    from app.financeiro_models import ContaPagar
    from app.models import User
    from decimal import Decimal
    from datetime import date, timedelta
    
    if not venda.tem_entrega or not venda.entregador_id:
        return {
            'success': True,
            'total_contas': 0,
            'valor_total': 0.0,
            'contas_criadas': [],
            'detalhes': ['Venda sem entrega ou sem entregador']
        }
    
    contas_criadas_ids = []
    valor_total = Decimal('0')
    detalhes = []
    
    try:
        # Buscar entregador
        entregador = db.query(User).filter_by(id=venda.entregador_id, tenant_id=tenant_id).first()
        if not entregador:
            logger.warning(f"⚠️ Entregador ID {venda.entregador_id} não encontrado")
            return {
                'success': False,
                'message': f'Entregador ID {venda.entregador_id} não encontrado'
            }
        
        # Calcula a próxima segunda-feira de pagamento
        # Lógica: Vendas de domingo a sábado são pagas na segunda-feira seguinte
        # Ex: Venda em 08/02 (domingo) → Fecha 14/02 (sábado) → Paga 16/02 (segunda)
        data_venda = date.today()
        dia_semana = data_venda.weekday()  # 0=Segunda, 6=Domingo
        
        # Calcular dias até o próximo sábado (fim da semana)
        if dia_semana == 6:  # Domingo
            dias_ate_sabado = 6
        elif dia_semana == 5:  # Sábado
            dias_ate_sabado = 0
        else:  # Segunda a Sexta
            dias_ate_sabado = 5 - dia_semana
        
        proximo_sabado = data_venda + timedelta(days=dias_ate_sabado)
        data_vencimento = proximo_sabado + timedelta(days=2)  # Segunda-feira = sábado + 2
        
        # Mapear canal para nome legível (sem acentos para compatibilidade)
        CANAIS_NOMES = {
            'loja_fisica': 'Loja Fisica',
            'mercado_livre': 'Mercado Livre',
            'shopee': 'Shopee',
            'amazon': 'Amazon'
        }
        canal = venda.canal or 'loja_fisica'
        canal_nome = CANAIS_NOMES.get(canal, 'Loja Física')
        
        # 1️⃣ CONTA A PAGAR: Taxa do entregador (Comissão)
        if venda.valor_taxa_entregador and float(venda.valor_taxa_entregador) > 0:
            # Buscar subcategoria "Comissao Entregador - {Canal}" (sem acentos)
            from app.dre_plano_contas_models import DRESubcategoria
            subcategoria_comissao = db.query(DRESubcategoria).filter(
                DRESubcategoria.tenant_id == tenant_id,
                DRESubcategoria.nome == f"Comissao Entregador - {canal_nome}"
            ).first()
            
            if not subcategoria_comissao:
                logger.warning(f"❌ Subcategoria não encontrada: 'Comissão Entregador - {canal_nome}' (tenant: {tenant_id})")
            else:
                logger.info(f"✅ Subcategoria encontrada: ID {subcategoria_comissao.id}")
            
            conta_taxa = ContaPagar(
                descricao=f"Taxa de entrega - {entregador.nome} - Venda {venda.numero_venda}",
                fornecedor_id=venda.entregador_id,
                valor_original=venda.valor_taxa_entregador,
                valor_final=venda.valor_taxa_entregador,
                data_emissao=date.today(),
                data_vencimento=data_vencimento,
                status='pendente',
                user_id=user_id,
                tenant_id=tenant_id,
                canal=canal,
                dre_subcategoria_id=subcategoria_comissao.id if subcategoria_comissao else None,
                observacoes=f"Taxa de entrega ref. venda {venda.numero_venda} - {venda.percentual_taxa_entregador}% da taxa de R$ {venda.taxa_entrega} - Acerto semanal (segunda-feira {data_vencimento.strftime('%d/%m/%Y')})"
            )
            db.add(conta_taxa)
            db.flush()
            contas_criadas_ids.append(conta_taxa.id)
            valor_total += venda.valor_taxa_entregador
            detalhes.append(f"Taxa entregador: R$ {venda.valor_taxa_entregador:.2f}")
            logger.info(f"✅ Conta a pagar criada: Taxa entregador R$ {venda.valor_taxa_entregador:.2f}")
        
        # 2️⃣ CONTA A PAGAR: Custo operacional (apenas fixo ou controla_rh)
        if entregador.custo_operacional_tipo in ['fixo', 'controla_rh']:
            if entregador.custo_operacional_valor and float(entregador.custo_operacional_valor) > 0:
                tipo_descricao = 'Custo fixo' if entregador.custo_operacional_tipo == 'fixo' else 'Controla RH'
                
                observacoes = f"Custo operacional ({entregador.custo_operacional_tipo}) ref. venda {venda.numero_venda} - Acerto semanal (segunda-feira {data_vencimento.strftime('%d/%m/%Y')})"
                if entregador.custo_operacional_tipo == 'controla_rh' and entregador.custo_operacional_controla_rh_id:
                    observacoes += f" - ID Controla RH: {entregador.custo_operacional_controla_rh_id}"
                
                # Buscar subcategoria "Frete Operacional - {Canal}"
                from app.dre_plano_contas_models import DRESubcategoria
                subcategoria_frete_op = db.query(DRESubcategoria).filter(
                    DRESubcategoria.tenant_id == tenant_id,
                    DRESubcategoria.nome == f"Frete Operacional - {canal_nome}"
                ).first()
                
                if not subcategoria_frete_op:
                    logger.warning(f"❌ Subcategoria não encontrada: 'Frete Operacional - {canal_nome}' (tenant: {tenant_id})")
                else:
                    logger.info(f"✅ Subcategoria encontrada: ID {subcategoria_frete_op.id}")
                
                conta_custo = ContaPagar(
                    descricao=f"{tipo_descricao} entrega - {entregador.nome} - Venda {venda.numero_venda}",
                    fornecedor_id=venda.entregador_id,
                    valor_original=entregador.custo_operacional_valor,
                    valor_final=entregador.custo_operacional_valor,
                    data_emissao=date.today(),
                    data_vencimento=data_vencimento,
                    status='pendente',
                    user_id=user_id,
                    tenant_id=tenant_id,
                    canal=canal,
                    dre_subcategoria_id=subcategoria_frete_op.id if subcategoria_frete_op else None,
                    observacoes=observacoes
                )
                
                db.add(conta_custo)
                db.flush()
                contas_criadas_ids.append(conta_custo.id)
                valor_total += entregador.custo_operacional_valor
                detalhes.append(f"{tipo_descricao}: R$ {entregador.custo_operacional_valor:.2f}")
                logger.info(f"✅ Conta a pagar criada: {tipo_descricao} R$ {entregador.custo_operacional_valor:.2f}")
        
        # Nota: KM rodado será criado ao fechar a rota, não aqui
        if entregador.custo_operacional_tipo == 'km_rodado':
            detalhes.append(f"Custo por KM (R$ {entregador.custo_operacional_valor:.2f}/km) - será criado ao fechar rota")
        
        return {
            'success': True,
            'total_contas': len(contas_criadas_ids),
            'valor_total': float(valor_total),
            'contas_criadas': contas_criadas_ids,
            'detalhes': detalhes
        }
        
    except Exception as e:
        logger.error(f"❌ Erro ao criar contas a pagar de entrega (venda {venda.id}): {str(e)}", exc_info=True)
        return {
            'success': False,
            'error': str(e)
        }


def gerar_dre_competencia_venda(
    venda_id: int,
    user_id: int,
    tenant_id: str,
    db: Session
) -> Dict[str, Any]:
    """
    Gera lançamentos de DRE por competência para uma venda (PASSO 1 - Sprint 5).
    
    Esta função é chamada no PRIMEIRO MOMENTO em que a venda se torna EFETIVADA
    (ou seja, quando passa a ter qualquer valor recebido, parcial ou total).
    
    Operações executadas:
    1. Lançar RECEITA (100% do valor bruto) na DRE
    2. Lançar CMV (custo total dos produtos) na DRE
    3. Lançar DESCONTO (se houver) na DRE
    
    GARANTIAS:
    - ✅ Idempotente: verifica se DRE já foi gerada (campo venda.dre_gerada)
    - ✅ Multi-tenant: todos os lançamentos isolados por tenant_id
    - ✅ Regime de competência: gera no momento da efetivação, não no pagamento
    - ✅ Atomicidade: chamada dentro da transação principal
    
    Args:
        venda_id: ID da venda
        user_id: ID do usuário (para auditoria)
        tenant_id: UUID do tenant (isolamento multi-tenant)
        db: Sessão do SQLAlchemy (NÃO faz commit, apenas flush)
        
    Returns:
        Dict com resultado:
        {
            'success': bool,
            'lancamentos_criados': int,
            'receita_gerada': float,
            'cmv_gerado': float,
            'desconto_gerado': float,
            'message': str
        }
        
    Raises:
        HTTPException: Se venda não encontrada ou subcategorias DRE inválidas
        
    Exemplo:
        >>> resultado = gerar_dre_competencia_venda(
        ...     venda_id=120,
        ...     user_id=1,
        ...     tenant_id="uuid-tenant",
        ...     db=db
        ... )
        >>> logger.info(f"DRE gerada: {resultado['lancamentos_criados']} lançamentos")
    """


def processar_contas_pagar_taxas(
    venda: 'Venda',
    pagamentos: List[Any],
    user_id: int,
    tenant_id: str,
    db: Session
) -> Dict[str, Any]:
    """
    Cria contas a pagar para taxas de pagamento (operação pós-commit).
    
    Para cada pagamento da venda:
    1. Busca a forma de pagamento e suas taxas (taxa_percentual, taxa_fixa, taxas_por_parcela)
    2. Calcula o valor da taxa
    3. Identifica a subcategoria DRE apropriada (baseado no tipo e canal)
    4. Cria conta a pagar na DRE
    
    Tipos de taxa suportados:
    - Cartão de crédito (com ou sem parcelamento)
    - Cartão de débito
    - PIX
    - Transferência
    - Boleto
    
    Args:
        venda: Objeto Venda (já commitada)
        pagamentos: Lista de objetos de pagamento (VendaPagamento)
        user_id: ID do usuário
        tenant_id: UUID do tenant
        db: Sessão do SQLAlchemy
        
    Returns:
        Dict com resultado:
        {
            'success': bool,
            'total_contas': int,
            'valor_total': float,
            'contas_criadas': List[int],
            'detalhes': List[str]
        }
    """
    from app.financeiro_models import ContaPagar, FormaPagamento
    from app.dre_plano_contas_models import DRESubcategoria
    from decimal import Decimal
    from datetime import date
    import json
    
    if not pagamentos:
        return {
            'success': True,
            'total_contas': 0,
            'valor_total': 0.0,
            'contas_criadas': [],
            'detalhes': ['Nenhum pagamento para processar']
        }
    
    contas_criadas_ids = []
    valor_total = Decimal('0')
    detalhes = []
    
    try:
        # Mapear canal para determinar subcategoria DRE apropriada
        canal = venda.canal or 'loja_fisica'
        
        # Mapear tipo de pagamento para nome da subcategoria DRE
        MAPA_SUBCATEGORIAS = {
            'cartao_credito': 'Taxas de Cartao de Credito',
            'credito': 'Taxas de Cartao de Credito',
            'Cartão Crédito': 'Taxas de Cartao de Credito',
            'cartao_debito': 'Taxas de Cartao de Debito',
            'debito': 'Taxas de Cartao de Debito',
            'Cartão Débito': 'Taxas de Cartao de Debito',
            'pix': 'Taxa de PIX',
            'PIX': 'Taxa de PIX',
            'Pix': 'Taxa de PIX',
            'boleto': 'Taxas de Boleto',
        }
        
        # Mapear canal para sufixo da subcategoria
        MAPA_CANAIS = {
            'loja_fisica': 'Loja Fisica',
            'pdv': 'Loja Fisica',  # PDV = Loja Fisica
            'ecommerce': 'E-commerce',
            'mercado_livre': 'Mercado Livre',
            'shopee': 'Shopee',
            'amazon': 'Amazon'
        }
        
        canal_sufixo = MAPA_CANAIS.get(canal, 'Loja Fisica')  # Default: Loja Fisica
        
        # Processar cada pagamento
        for pagamento in pagamentos:
            # Pular formas de pagamento sem taxa (dinheiro, crédito cliente)
            forma_pag_nome = pagamento.forma_pagamento.lower()
            if 'dinheiro' in forma_pag_nome or 'credito_cliente' in forma_pag_nome:
                continue
            
            # Buscar configuração da forma de pagamento
            forma_pag = db.query(FormaPagamento).filter(
                FormaPagamento.tenant_id == tenant_id,
                FormaPagamento.ativo == True
            ).filter(
                (FormaPagamento.nome == pagamento.forma_pagamento) |
                (FormaPagamento.tipo == pagamento.forma_pagamento) |
                (func.lower(FormaPagamento.nome).like(f'%{forma_pag_nome}%'))
            ).first()
            
            if not forma_pag:
                logger.warning(f"⚠️ Forma de pagamento não encontrada: {pagamento.forma_pagamento}")
                continue
            
            # Verificar se tem taxa configurada
            taxa_percentual = Decimal(str(forma_pag.taxa_percentual or 0))
            taxa_fixa = Decimal(str(forma_pag.taxa_fixa or 0))
            
            if taxa_percentual == 0 and taxa_fixa == 0:
                logger.debug(f"✓ Forma de pagamento sem taxa: {forma_pag.nome}")
                continue
            
            # Verificar se tem taxa específica para número de parcelas
            num_parcelas = getattr(pagamento, 'numero_parcelas', 1) or 1
            
            if num_parcelas > 1 and forma_pag.taxas_por_parcela:
                try:
                    taxas_por_parcela_dict = json.loads(forma_pag.taxas_por_parcela)
                    if str(num_parcelas) in taxas_por_parcela_dict:
                        taxa_parcela_config = taxas_por_parcela_dict[str(num_parcelas)]
                        taxa_percentual = Decimal(str(taxa_parcela_config.get('taxa_percentual', taxa_percentual)))
                        taxa_fixa = Decimal(str(taxa_parcela_config.get('taxa_fixa', taxa_fixa)))
                        logger.info(f"💳 Taxa específica para {num_parcelas}x: {taxa_percentual}% + R$ {taxa_fixa}")
                except (json.JSONDecodeError, KeyError, ValueError) as e:
                    logger.warning(f"⚠️ Erro ao processar taxas_por_parcela: {str(e)}")
            
            # Calcular valor da taxa
            valor_pagamento = Decimal(str(pagamento.valor))
            valor_taxa = (valor_pagamento * taxa_percentual / Decimal('100')) + taxa_fixa
            
            if valor_taxa <= 0:
                continue
            
            # Determinar nome da subcategoria DRE
            tipo_pagamento_base = forma_pag.tipo or pagamento.forma_pagamento
            nome_subcategoria_base = MAPA_SUBCATEGORIAS.get(
                tipo_pagamento_base,
                MAPA_SUBCATEGORIAS.get(pagamento.forma_pagamento, None)
            )
            
            if not nome_subcategoria_base:
                logger.warning(f"⚠️ Tipo de pagamento não mapeado: {tipo_pagamento_base}")
                continue
            
            # Montar nome completo da subcategoria (com canal)
            nome_subcategoria = f"{nome_subcategoria_base} - {canal_sufixo}"
            
            # Buscar subcategoria DRE
            subcategoria_taxa = db.query(DRESubcategoria).filter(
                DRESubcategoria.tenant_id == tenant_id,
                DRESubcategoria.nome == nome_subcategoria,
                DRESubcategoria.ativo == True
            ).first()
            
            # Se não encontrar com canal, tentar genérico
            if not subcategoria_taxa:
                subcategoria_taxa = db.query(DRESubcategoria).filter(
                    DRESubcategoria.tenant_id == tenant_id,
                    DRESubcategoria.nome == nome_subcategoria_base,
                    DRESubcategoria.ativo == True
                ).first()
            
            if not subcategoria_taxa:
                logger.warning(f"❌ Subcategoria DRE não encontrada: {nome_subcategoria} (tentou também {nome_subcategoria_base})")
                continue
            
            logger.info(f"✅ Subcategoria DRE encontrada: {subcategoria_taxa.nome} (ID: {subcategoria_taxa.id})")
            
            # Criar conta a pagar
            descricao = f"Taxa {forma_pag.nome}"
            if num_parcelas > 1:
                descricao += f" {num_parcelas}x"
            descricao += f" - Venda {venda.numero_venda}"
            
            observacoes = f"Taxa de pagamento ref. venda {venda.numero_venda}"
            if taxa_percentual > 0 and taxa_fixa > 0:
                observacoes += f" - {taxa_percentual}% + R$ {taxa_fixa} sobre R$ {valor_pagamento}"
            elif taxa_percentual > 0:
                observacoes += f" - {taxa_percentual}% sobre R$ {valor_pagamento}"
            else:
                observacoes += f" - Taxa fixa de R$ {taxa_fixa}"
            
            # Data de vencimento: assumindo 30 dias (pode ser ajustado pelo campo prazo_dias)
            prazo_dias = forma_pag.prazo_dias or forma_pag.prazo_recebimento or 30
            data_vencimento = date.today() + timedelta(days=prazo_dias)
            
            conta_taxa = ContaPagar(
                descricao=descricao,
                fornecedor_id=None,  # Taxa não tem fornecedor específico
                valor_original=valor_taxa,
                valor_final=valor_taxa,
                data_emissao=date.today(),
                data_vencimento=data_vencimento,
                status='pendente',
                user_id=user_id,
                tenant_id=tenant_id,
                canal=canal,
                dre_subcategoria_id=subcategoria_taxa.id,
                observacoes=observacoes
            )
            
            db.add(conta_taxa)
            db.flush()
            
            contas_criadas_ids.append(conta_taxa.id)
            valor_total += valor_taxa
            detalhes.append(f"{forma_pag.nome}: R$ {valor_taxa:.2f}")
            
            logger.info(f"✅ Conta a pagar criada: Taxa {forma_pag.nome} R$ {valor_taxa:.2f}")
        
        return {
            'success': True,
            'total_contas': len(contas_criadas_ids),
            'valor_total': float(valor_total),
            'contas_criadas': contas_criadas_ids,
            'detalhes': detalhes
        }
        
    except Exception as e:
        logger.error(f"❌ Erro ao criar contas a pagar de taxas (venda {venda.id}): {str(e)}", exc_info=True)
        return {
            'success': False,
            'error': str(e)
        }


def gerar_dre_competencia_venda(
    venda_id: int,
    user_id: int,
    tenant_id: str,
    db: Session
) -> Dict[str, Any]:
    """
    Gera lançamentos de DRE por competência para uma venda (PASSO 1 - Sprint 5).
    
    Esta função é chamada no PRIMEIRO MOMENTO em que a venda se torna EFETIVADA
    (ou seja, quando passa a ter qualquer valor recebido, parcial ou total).
    
    Operações executadas:
    1. Lançar RECEITA (100% do valor bruto) na DRE
    2. Lançar CMV (custo total dos produtos) na DRE
    3. Lançar DESCONTO (se houver) na DRE
    
    GARANTIAS:
    - ✅ Idempotente: verifica se DRE já foi gerada (campo venda.dre_gerada)
    - ✅ Multi-tenant: todos os lançamentos isolados por tenant_id
    - ✅ Regime de competência: gera no momento da efetivação, não no pagamento
    - ✅ Atomicidade: chamada dentro da transação principal
    
    Args:
        venda_id: ID da venda
        user_id: ID do usuário (para auditoria)
        tenant_id: UUID do tenant (isolamento multi-tenant)
        db: Sessão do SQLAlchemy (NÃO faz commit, apenas flush)
        
    Returns:
        Dict com resultado:
        {
            'success': bool,
            'lancamentos_criados': int,
            'receita_gerada': float,
            'cmv_gerado': float,
            'desconto_gerado': float,
            'message': str
        }
        
    Raises:
        HTTPException: Se venda não encontrada ou subcategorias DRE inválidas
        
    Exemplo:
        >>> resultado = gerar_dre_competencia_venda(
        ...     venda_id=120,
        ...     user_id=1,
        ...     tenant_id="uuid-tenant",
        ...     db=db
        ... )
        >>> logger.info(f"DRE gerada: {resultado['lancamentos_criados']} lançamentos")
    """
    from app.vendas_models import Venda, VendaItem
    from app.produtos_models import Produto
    from app.domain.dre.lancamento_dre_sync import atualizar_dre_por_lancamento
    from app.dre_plano_contas_models import DRESubcategoria, NaturezaDRE
    
    logger.info(f"📊 Iniciando geração de DRE por competência - Venda #{venda_id}")
    
    try:
        # ============================================================
        # ETAPA 0: GARANTIR TENANT_ID COMO UUID
        # ============================================================
        
        # Converter tenant_id para UUID se necessário (fix PostgreSQL cast error)
        if tenant_id and not isinstance(tenant_id, UUID):
            try:
                tenant_uuid = UUID(str(tenant_id))
            except (ValueError, AttributeError):
                tenant_uuid = tenant_id
        else:
            tenant_uuid = tenant_id
        
        # ============================================================
        # ETAPA 1: BUSCAR VENDA E VALIDAR
        # ============================================================
        
        venda = db.query(Venda).filter_by(
            id=venda_id,
            tenant_id=tenant_uuid
        ).first()
        
        if not venda:
            raise HTTPException(status_code=404, detail='Venda não encontrada')
        
        # ✅ IDEMPOTÊNCIA: Verificar se DRE já foi gerada
        if venda.dre_gerada:
            logger.info(
                f"⚠️  DRE já foi gerada anteriormente para venda #{venda.numero_venda} "
                f"em {venda.data_geracao_dre}"
            )
            return {
                'success': False,
                'lancamentos_criados': 0,
                'receita_gerada': 0,
                'cmv_gerado': 0,
                'desconto_gerado': 0,
                'message': 'DRE já foi gerada anteriormente (idempotência)'
            }
        
        # ============================================================
        # ETAPA 2: BUSCAR SUBCATEGORIAS DRE
        # ============================================================
        
        # Buscar subcategoria de RECEITA
        subcat_receita = db.query(DRESubcategoria).filter(
            DRESubcategoria.tenant_id == tenant_uuid,
            DRESubcategoria.nome.ilike('%receita%venda%'),
            DRESubcategoria.ativo == True
        ).first()
        
        if not subcat_receita:
            # Tentar buscar qualquer receita
            subcat_receita = db.query(DRESubcategoria).filter(
                DRESubcategoria.tenant_id == tenant_uuid,
                DRESubcategoria.ativo == True
            ).join(DRESubcategoria.categoria).filter(
                func.lower(func.cast(DRESubcategoria.categoria.property.mapper.class_.natureza, String)).like('%receita%')
            ).first()
        
        if not subcat_receita:
            raise HTTPException(
                status_code=500,
                detail='Subcategoria DRE de Receita não encontrada. Configure o plano de contas DRE.'
            )
        
        # Buscar subcategoria de CMV
        subcat_cmv = db.query(DRESubcategoria).filter(
            DRESubcategoria.tenant_id == tenant_uuid,
            DRESubcategoria.nome.ilike('%cmv%'),
            DRESubcategoria.ativo == True
        ).first()
        
        if not subcat_cmv:
            # Tentar buscar "Custo dos Produtos Vendidos"
            subcat_cmv = db.query(DRESubcategoria).filter(
                DRESubcategoria.tenant_id == tenant_uuid,
                DRESubcategoria.nome.ilike('%custo%produto%'),
                DRESubcategoria.ativo == True
            ).first()
        
        if not subcat_cmv:
            raise HTTPException(
                status_code=500,
                detail='Subcategoria DRE de CMV não encontrada. Configure o plano de contas DRE.'
            )
        
        # Buscar subcategoria de DESCONTO (opcional)
        subcat_desconto = db.query(DRESubcategoria).filter(
            DRESubcategoria.tenant_id == tenant_uuid,
            DRESubcategoria.nome.ilike('%desconto%'),
            DRESubcategoria.ativo == True
        ).first()
        
        if not subcat_desconto:
            # Tentar buscar "Deduções de Receita"
            subcat_desconto = db.query(DRESubcategoria).filter(
                DRESubcategoria.tenant_id == tenant_uuid,
                DRESubcategoria.nome.ilike('%dedu%'),
                DRESubcategoria.ativo == True
            ).first()
        
        logger.info(
            f"✅ Subcategorias DRE localizadas: "
            f"Receita (ID={subcat_receita.id}), "
            f"CMV (ID={subcat_cmv.id}), "
            f"Desconto (ID={subcat_desconto.id if subcat_desconto else 'N/A'})"
        )
        
        # ============================================================
        # ETAPA 3: CALCULAR VALORES
        # ============================================================
        
        # Receita bruta = subtotal da venda (antes de descontos)
        receita_bruta = Decimal(str(venda.subtotal))
        
        # CMV = somar custo de todos os produtos vendidos
        cmv_total = Decimal('0')
        
        for item in venda.itens:
            if item.tipo == 'produto' and item.produto_id:
                produto = db.query(Produto).filter_by(
                    id=item.produto_id,
                    user_id=user_id
                ).first()
                
                if produto and produto.preco_custo:
                    custo_item = Decimal(str(produto.preco_custo)) * Decimal(str(item.quantidade))
                    cmv_total += custo_item
        
        # Desconto = desconto concedido na venda
        desconto_total = Decimal(str(venda.desconto_valor or 0))
        
        # Canal da venda (para DRE por canal)
        canal = venda.canal or 'loja_fisica'
        
        # Data da venda (para identificar período DRE)
        data_venda = venda.data_venda.date() if isinstance(venda.data_venda, datetime) else venda.data_venda
        
        logger.info(
            f"💰 Valores calculados: "
            f"Receita=R$ {float(receita_bruta):.2f}, "
            f"CMV=R$ {float(cmv_total):.2f}, "
            f"Desconto=R$ {float(desconto_total):.2f}"
        )
        
        # ============================================================
        # ETAPA 4: GERAR LANÇAMENTOS NA DRE
        # ============================================================
        
        lancamentos_criados = 0
        
        # 4.1 - Lançamento de RECEITA (100%)
        if receita_bruta > 0:
            try:
                atualizar_dre_por_lancamento(
                    db=db,
                    tenant_id=tenant_uuid,
                    dre_subcategoria_id=subcat_receita.id,
                    canal=canal,
                    valor=receita_bruta,
                    data_lancamento=data_venda,
                    tipo_movimentacao='RECEITA'
                )
                lancamentos_criados += 1
                logger.info(f"  ✅ Receita lançada: R$ {float(receita_bruta):.2f}")
            except Exception as e:
                logger.error(f"  ❌ Erro ao lançar receita: {str(e)}", exc_info=True)
                raise
        
        # 4.2 - Lançamento de CMV
        if cmv_total > 0:
            try:
                atualizar_dre_por_lancamento(
                    db=db,
                    tenant_id=tenant_uuid,
                    dre_subcategoria_id=subcat_cmv.id,
                    canal=canal,
                    valor=cmv_total,
                    data_lancamento=data_venda,
                    tipo_movimentacao='DESPESA'  # CMV é um custo
                )
                lancamentos_criados += 1
                logger.info(f"  ✅ CMV lançado: R$ {float(cmv_total):.2f}")
            except Exception as e:
                logger.error(f"  ❌ Erro ao lançar CMV: {str(e)}", exc_info=True)
                raise
        
        # 4.3 - Lançamento de DESCONTO (se houver e se tiver subcategoria)
        if desconto_total > 0 and subcat_desconto:
            try:
                atualizar_dre_por_lancamento(
                    db=db,
                    tenant_id=tenant_uuid,
                    dre_subcategoria_id=subcat_desconto.id,
                    canal=canal,
                    valor=desconto_total,
                    data_lancamento=data_venda,
                    tipo_movimentacao='DESPESA'  # Desconto reduz receita
                )
                lancamentos_criados += 1
                logger.info(f"  ✅ Desconto lançado: R$ {float(desconto_total):.2f}")
            except Exception as e:
                logger.error(f"  ❌ Erro ao lançar desconto: {str(e)}", exc_info=True)
                raise
        elif desconto_total > 0:
            logger.warning(f"  ⚠️  Desconto de R$ {float(desconto_total):.2f} não lançado (subcategoria não encontrada)")
        
        # ============================================================
        # ETAPA 5: MARCAR VENDA COMO DRE GERADA
        # ============================================================
        
        venda.dre_gerada = True
        venda.data_geracao_dre = now_brasilia()
        db.flush()
        
        logger.info(
            f"✅ ✅ ✅ DRE POR COMPETÊNCIA GERADA: Venda #{venda.numero_venda} ✅ ✅ ✅\n"
            f"   📊 Lançamentos criados: {lancamentos_criados}\n"
            f"   💰 Receita: R$ {float(receita_bruta):.2f}\n"
            f"   📦 CMV: R$ {float(cmv_total):.2f}\n"
            f"   🎁 Desconto: R$ {float(desconto_total):.2f}\n"
            f"   🏪 Canal: {canal}"
        )
        
        return {
            'success': True,
            'lancamentos_criados': lancamentos_criados,
            'receita_gerada': float(receita_bruta),
            'cmv_gerado': float(cmv_total),
            'desconto_gerado': float(desconto_total),
            'message': f'{lancamentos_criados} lançamentos criados na DRE'
        }
        
    except HTTPException:
        # Re-lançar HTTPException
        raise
        
    except Exception as e:
        logger.error(f"❌ ERRO CRÍTICO ao gerar DRE por competência: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao gerar DRE: {str(e)}"
        )
