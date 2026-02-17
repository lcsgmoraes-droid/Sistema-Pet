# -*- coding: utf-8 -*-
"""
Serviço de Contas a Receber
============================

Este serviço isola TODA a lógica de gestão de contas a receber (recebíveis).

RESPONSABILIDADES:
------------------
1. Criar contas a receber a partir de vendas
2. Gerenciar parcelamento (múltiplas contas)
3. Baixar contas (parcial ou total)
4. Criar registros de recebimento
5. Atualizar status (pendente → parcial → recebido)
6. Calcular vencimentos e prazos
7. Gerenciar lançamentos manuais associados

IMPORTANTE - O QUE NÃO FAZ:
---------------------------
❌ NÃO trata movimentações de caixa físico (CaixaService)
❌ NÃO trata estoque (EstoqueService)
❌ NÃO trata movimentações bancárias (futura expansão)
❌ NÃO comita transações (apenas flush)

DECISÕES DE ARQUITETURA:
-------------------------
- Session recebida por parâmetro (inversão de dependência)
- Nunca comita (apenas flush para validações)
- Retorna dicts estruturados com informações claras
- Exceções HTTPException com mensagens amigáveis
- Logs detalhados para auditoria
- Docstrings completas em todos os métodos

PADRÃO DE USO:
--------------
```python
from app.financeiro import ContasReceberService

# Criar contas a partir de venda
resultado = ContasReceberService.criar_de_venda(
    venda=venda,
    pagamentos=pagamentos_list,
    user_id=1,
    db=db
)
logger.info(f"Criadas {len(resultado['contas_criadas'])} contas")

# Baixar contas existentes
resultado_baixa = ContasReceberService.baixar_contas_da_venda(
    venda_id=venda.id,
    valor_total_pagamento=100.50,
    forma_pagamento_id=1,
    user_id=1,
    db=db
)
```

AUTOR: Sistema Pet Shop - Refatoração Fase 3A
DATA: 2025-01-23
"""

import logging
from typing import Dict, Any, List, Optional
from decimal import Decimal
from datetime import datetime, date, timedelta
from fastapi import HTTPException
from sqlalchemy.orm import Session

# Logger
logger = logging.getLogger(__name__)


class ContasReceberService:
    """
    Serviço isolado para gerenciar CONTAS A RECEBER.
    
    Este serviço é STATELESS e todos os métodos são estáticos.
    Não mantém estado entre chamadas.
    """
    
    @staticmethod
    def criar_de_venda(
        venda: Any,
        pagamentos: List[Any],
        user_id: int,
        db: Session
    ) -> Dict[str, Any]:
        """
        Cria contas a receber automaticamente a partir de uma venda.
        
        Esta função analisa cada pagamento e:
        - Para cartão parcelado: cria múltiplas contas (uma por parcela)
        - Para pagamentos a prazo: cria uma conta com vencimento futuro
        - Para pagamentos à vista: cria conta E baixa automaticamente (rastreabilidade)
        
        REGRA IMPORTANTE:
        - prazo_dias = 0 → À vista, cria ContaReceber e baixa imediatamente
        - prazo_dias > 0 → A prazo, cria ContaReceber pendente
        
        Args:
            venda: Objeto Venda (deve ter: id, numero_venda, cliente_id, cliente)
            pagamentos: Lista de pagamentos (deve ter: forma_pagamento, valor, numero_parcelas)
            user_id: ID do usuário que está criando
            db: Sessão do SQLAlchemy (não será commitada)
            
        Returns:
            Dict com informações das contas criadas:
            {
                'contas_criadas': List[int],  # IDs das contas
                'lancamentos_criados': List[int],  # IDs dos lançamentos
                'total_contas': int,
                'total_valor': Decimal
            }
            
        Exemplo:
            >>> resultado = ContasReceberService.criar_de_venda(
            ...     venda=venda_obj,
            ...     pagamentos=[
            ...         {'forma_pagamento': 'Cartão Crédito', 'valor': 300.0, 'numero_parcelas': 3}
            ...     ],
            ...     user_id=1,
            ...     db=db
            ... )
            >>> logger.info(f"Criadas {len(resultado['contas_criadas'])} contas")
        """
        # Imports locais para evitar circular dependency
        from app.financeiro_models import (
            ContaReceber, FormaPagamento, LancamentoManual, 
            CategoriaFinanceira
        )
        
        logger.debug(
            f"🏦 Criando contas a receber para venda #{venda.numero_venda} - "
            f"{len(pagamentos)} pagamento(s)"
        )
        
        contas_criadas = []
        lancamentos_criados = []
        total_valor = Decimal('0')
        
        # Buscar ou criar categoria de receitas
        categoria_receitas = db.query(CategoriaFinanceira).filter(
            CategoriaFinanceira.nome.ilike('%vendas%'),
            CategoriaFinanceira.tipo == 'receita'
        ).first()
        
        if not categoria_receitas:
            categoria_receitas = CategoriaFinanceira(
                nome="Receitas de Vendas",
                tipo="receita",
                user_id=user_id
            )
            db.add(categoria_receitas)
            db.flush()
            logger.info(f"📁 Categoria 'Receitas de Vendas' criada automaticamente")
        
        for pag in pagamentos:
            # Suportar tanto dict quanto objeto
            forma_pag_nome = pag.get('forma_pagamento') if isinstance(pag, dict) else getattr(pag, 'forma_pagamento', None)
            
            # Buscar configuração da forma de pagamento
            forma_pag = db.query(FormaPagamento).filter(
                FormaPagamento.nome.ilike(f"%{forma_pag_nome}%")
            ).first()
            
            # Verificar se é cartão parcelado
            numero_parcelas = pag.get('numero_parcelas', 1) if isinstance(pag, dict) else getattr(pag, 'numero_parcelas', 1)
            numero_parcelas = numero_parcelas or 1
            eh_cartao_parcelado = (
                forma_pag and 
                forma_pag.tipo == 'cartao_credito' and 
                numero_parcelas > 1
            )
            
            if eh_cartao_parcelado:
                # CARTÃO PARCELADO: Criar múltiplas contas + lançamentos
                resultado_parcelado = ContasReceberService._criar_contas_parceladas(
                    venda=venda,
                    pagamento=pag,
                    forma_pag=forma_pag,
                    numero_parcelas=numero_parcelas,
                    categoria_receitas=categoria_receitas,
                    user_id=user_id,
                    db=db
                )
                
                contas_criadas.extend(resultado_parcelado['contas_ids'])
                lancamentos_criados.extend(resultado_parcelado['lancamentos_ids'])
                total_valor += resultado_parcelado['total_valor']
                
            else:
                # PAGAMENTO SIMPLES (à vista ou a prazo)
                resultado_simples = ContasReceberService._criar_conta_simples(
                    venda=venda,
                    pagamento=pag,
                    forma_pag=forma_pag,
                    categoria_receitas=categoria_receitas,
                    user_id=user_id,
                    db=db
                )
                
                # Sempre adicionar conta (agora todas as vendas geram contas)
                contas_criadas.append(resultado_simples['conta_id'])
                lancamentos_criados.append(resultado_simples['lancamento_id'])
                total_valor += resultado_simples['valor']
        
        logger.info(
            f"✅ Contas a receber criadas: {len(contas_criadas)} conta(s), "
            f"{len(lancamentos_criados)} lançamento(s), Total: R$ {float(total_valor):.2f}"
        )
        
        return {
            'contas_criadas': contas_criadas,
            'lancamentos_criados': lancamentos_criados,
            'total_contas': len(contas_criadas),
            'total_valor': total_valor
        }
    
    @staticmethod
    def _criar_contas_parceladas(
        venda: Any,
        pagamento: Any,
        forma_pag: Any,
        numero_parcelas: int,
        categoria_receitas: Any,
        user_id: int,
        db: Session
    ) -> Dict[str, Any]:
        """
        Cria múltiplas contas a receber para pagamento parcelado.
        
        Método interno usado por criar_de_venda().
        """
        from app.financeiro_models import ContaReceber, LancamentoManual
        
        valor = pagamento.get('valor') if isinstance(pagamento, dict) else getattr(pagamento, 'valor', 0)
        valor_total = Decimal(str(valor))
        valor_parcela = valor_total / numero_parcelas
        
        contas_ids = []
        lancamentos_ids = []
        
        logger.debug(
            f"💳 Criando {numero_parcelas} parcelas de R$ {float(valor_parcela):.2f} "
            f"(Total: R$ {float(valor_total):.2f})"
        )
        
        for i in range(1, numero_parcelas + 1):
            data_vencimento = date.today() + timedelta(days=30 * i)
            
            # Criar lançamento manual previsto
            lancamento = LancamentoManual(
                tipo='entrada',
                valor=valor_parcela,
                descricao=f"Venda {venda.numero_venda} - Parcela {i}/{numero_parcelas} - {forma_pag.nome}",
                data_lancamento=data_vencimento,
                status='previsto',
                categoria_id=categoria_receitas.id,
                documento=f"VENDA-{venda.id}",
                fornecedor_cliente=venda.cliente.nome if venda.cliente else None,
                user_id=user_id,
                tenant_id=getattr(venda, 'tenant_id', None)
            )
            db.add(lancamento)
            db.flush()
            lancamentos_ids.append(lancamento.id)
            
            # Criar conta a receber
            # Garantir valores não-nulos para campos obrigatórios
            canal_venda = getattr(venda, 'canal', None) or 'loja_fisica'
            dre_subcategoria = 1  # TODO: Mapear por forma_pagamento ou categoria
            
            conta = ContaReceber(
                descricao=f"Venda {venda.numero_venda} - Parcela {i}/{numero_parcelas}",
                cliente_id=venda.cliente_id,
                forma_pagamento_id=forma_pag.id,
                # ====== CAMPOS OBRIGATÓRIOS DRE ======
                dre_subcategoria_id=dre_subcategoria,
                canal=canal_venda,
                # ======================================
                valor_original=valor_parcela,
                valor_recebido=Decimal('0'),
                valor_final=valor_parcela,
                data_emissao=date.today(),
                data_vencimento=data_vencimento,
                data_recebimento=None,
                venda_id=venda.id,
                documento=f"VENDA-{venda.id}",
                numero_parcela=i,
                total_parcelas=numero_parcelas,
                status='pendente',
                user_id=user_id,
                tenant_id=getattr(venda, 'tenant_id', None)  # Propagar tenant_id da venda
            )
            
            db.add(conta)
            db.flush()
            contas_ids.append(conta.id)
            
            logger.debug(f"💳 Parcela {i}/{numero_parcelas}: Conta #{conta.id}, Venc: {data_vencimento}")
        
        return {
            'contas_ids': contas_ids,
            'lancamentos_ids': lancamentos_ids,
            'total_valor': valor_total
        }
    
    @staticmethod
    def _criar_conta_simples(
        venda: Any,
        pagamento: Any,
        forma_pag: Optional[Any],
        categoria_receitas: Any,
        user_id: int,
        db: Session
    ) -> Dict[str, Any]:
        """
        Cria conta a receber para pagamento simples (à vista ou a prazo).
        
        Método interno usado por criar_de_venda().
        """
        from app.financeiro_models import ContaReceber, LancamentoManual
        
        # Suportar tanto dict quanto objeto
        valor = pagamento.get('valor') if isinstance(pagamento, dict) else getattr(pagamento, 'valor', 0)
        forma_pag_nome = pagamento.get('forma_pagamento') if isinstance(pagamento, dict) else getattr(pagamento, 'forma_pagamento', '')
        
        # Determinar prazo
        prazo_dias = 0
        if forma_pag and forma_pag.prazo_dias:
            prazo_dias = forma_pag.prazo_dias
        elif forma_pag_nome.lower() in ['credito', 'crédito', 'cartao_credito']:
            prazo_dias = 30  # Padrão cartão de crédito
        elif forma_pag_nome.lower() in ['debito', 'débito', 'pix', 'dinheiro']:
            prazo_dias = 0  # Recebimento imediato
        
        valor = Decimal(str(valor))
        
        # Status do lançamento: realizado se prazo=0, previsto se tem prazo
        status_lancamento = 'realizado' if prazo_dias == 0 else 'previsto'
        data_lancamento = date.today() if prazo_dias == 0 else (date.today() + timedelta(days=prazo_dias))
        
        # SEMPRE criar lançamento manual
        lancamento = LancamentoManual(
            tipo='entrada',
            valor=valor,
            descricao=f"Venda {venda.numero_venda} - {forma_pag_nome}",
            data_lancamento=data_lancamento,
            status=status_lancamento,
            categoria_id=categoria_receitas.id,
            documento=f"VENDA-{venda.id}",
            fornecedor_cliente=venda.cliente.nome if venda.cliente else None,
            user_id=user_id,
            tenant_id=getattr(venda, 'tenant_id', None)
        )
        db.add(lancamento)
        db.flush()
        
        logger.debug(f"💰 Lançamento {status_lancamento}: R$ {float(valor):.2f} - {forma_pag_nome}")
        
        # SEMPRE criar conta a receber (inclusive à vista, para rastreabilidade)
        data_vencimento = date.today() if prazo_dias == 0 else (date.today() + timedelta(days=prazo_dias))
        
        # Se for à vista (prazo = 0), criar conta já recebida
        if prazo_dias == 0:
            status_conta = 'recebido'
            valor_recebido = valor
            data_recebimento = date.today()
            logger.debug(f"✅ Pagamento à vista: criando conta recebida automaticamente")
        else:
            status_conta = 'pendente'
            valor_recebido = Decimal('0')
            data_recebimento = None
            logger.debug(f"⏳ Pagamento a prazo: criando conta pendente")
        
        # Garantir valores não-nulos para campos obrigatórios
        canal_venda = getattr(venda, 'canal', None) or 'loja_fisica'
        dre_subcategoria = 1  # TODO: Mapear por forma_pagamento ou categoria
        
        conta = ContaReceber(
            descricao=f"Venda {venda.numero_venda} - {forma_pag_nome}",
            cliente_id=venda.cliente_id,
            forma_pagamento_id=forma_pag.id if forma_pag else None,
            # ====== CAMPOS OBRIGATÓRIOS DRE ======
            dre_subcategoria_id=dre_subcategoria,
            canal=canal_venda,
            # ======================================
            valor_original=valor,
            valor_recebido=valor_recebido,
            valor_final=valor,
            data_emissao=date.today(),
            data_vencimento=data_vencimento,
            data_recebimento=data_recebimento,
            status=status_conta,
            venda_id=venda.id,
            user_id=user_id,
            tenant_id=getattr(venda, 'tenant_id', None)  # Propagar tenant_id da venda
        )
        db.add(conta)
        db.flush()
        conta_id = conta.id
        
        logger.debug(f"📋 ContaReceber criada: #{conta_id}, R$ {float(valor):.2f}, Status: {status_conta}, Venc: {data_vencimento}")
        
        # Se for à vista, criar registro de recebimento imediato
        recebimento_id = None
        if prazo_dias == 0:
            from app.financeiro_models import Recebimento
            
            recebimento = Recebimento(
                conta_receber_id=conta.id,
                valor_recebido=valor,
                data_recebimento=date.today(),
                forma_pagamento_id=forma_pag.id if forma_pag else None,
                observacoes=f"Recebimento automático - Venda à vista #{venda.numero_venda}",
                user_id=user_id,
                tenant_id=getattr(venda, 'tenant_id', None)
            )
            db.add(recebimento)
            db.flush()
            recebimento_id = recebimento.id
            
            logger.debug(f"💵 Recebimento automático criado: #{recebimento_id}")
        
        return {
            'conta_id': conta_id,
            'lancamento_id': lancamento.id,
            'recebimento_id': recebimento_id,
            'valor': valor
        }
    
    @staticmethod
    def baixar_contas_da_venda(
        venda_id: int,
        venda_numero: str,
        valor_total_pagamento: float,
        forma_pagamento_nome: str,
        user_id: int,
        tenant_id: str,
        db: Session
    ) -> Dict[str, Any]:
        """
        Baixa contas a receber pendentes de uma venda (parcial ou total).
        
        Este método:
        1. Busca contas pendentes/parciais da venda
        2. Distribui o valor do pagamento entre as contas (FIFO)
        3. Cria registros de Recebimento
        4. Atualiza status das contas (pendente → parcial → recebido)
        
        Args:
            venda_id: ID da venda
            venda_numero: Número formatado da venda (ex: "VD-2025-00001")
            valor_total_pagamento: Valor total do pagamento a distribuir
            forma_pagamento_nome: Nome da forma de pagamento usada
            user_id: ID do usuário
            db: Sessão do SQLAlchemy
            
        Returns:
            Dict com resultado da baixa:
            {
                'contas_baixadas': List[dict],  # Lista de contas afetadas
                'recebimentos_criados': List[int],  # IDs dos recebimentos
                'valor_distribuido': Decimal,
                'valor_restante': Decimal
            }
            
        Raises:
            HTTPException(404): Se não encontrar contas para baixar
            
        Exemplo:
            >>> resultado = ContasReceberService.baixar_contas_da_venda(
            ...     venda_id=120,
            ...     venda_numero="VD-2025-00120",
            ...     valor_total_pagamento=150.00,
            ...     forma_pagamento_nome="PIX",
            ...     user_id=1,
            ...     db=db
            ... )
            >>> logger.info(f"Baixadas {len(resultado['contas_baixadas'])} contas")
        """
        from app.financeiro_models import ContaReceber, Recebimento, FormaPagamento
        
        logger.debug(
            f"💰 Baixando contas da venda #{venda_numero} - "
            f"Valor: R$ {valor_total_pagamento:.2f}"
        )
        
        # Buscar contas pendentes/parciais da venda
        contas_originais = db.query(ContaReceber).filter(
            ContaReceber.venda_id == venda_id,
            ContaReceber.status.in_(['pendente', 'parcial', 'vencido'])
        ).order_by(ContaReceber.data_vencimento).all()
        
        if not contas_originais:
            logger.warning(f"⚠️ Nenhuma conta pendente encontrada para venda ID {venda_id}")
            return {
                'contas_baixadas': [],
                'recebimentos_criados': [],
                'valor_distribuido': Decimal('0'),
                'valor_restante': Decimal(str(valor_total_pagamento))
            }
        
        # Buscar forma de pagamento
        forma_pag = db.query(FormaPagamento).filter(
            FormaPagamento.nome.ilike(f"%{forma_pagamento_nome}%")
        ).first()
        forma_pag_id = forma_pag.id if forma_pag else None
        
        valor_disponivel = valor_total_pagamento
        contas_baixadas = []
        recebimentos_criados = []
        
        for conta in contas_originais:
            if valor_disponivel <= 0.01:
                break
            
            # Calcular quanto ainda falta nesta conta
            valor_pendente_conta = float(conta.valor_final) - float(conta.valor_recebido or 0)
            
            # Calcular quanto pode baixar desta conta
            valor_a_baixar = min(valor_pendente_conta, valor_disponivel)
            
            if valor_a_baixar > 0.01:
                # Atualizar valor recebido
                novo_valor_recebido = float(conta.valor_recebido or 0) + valor_a_baixar
                conta.valor_recebido = Decimal(str(novo_valor_recebido))
                
                # Criar registro de recebimento
                # 🔒 ISOLAMENTO MULTI-TENANT: tenant_id obrigatório
                recebimento = Recebimento(
                    conta_receber_id=conta.id,
                    valor_recebido=Decimal(str(valor_a_baixar)),
                    data_recebimento=date.today(),
                    forma_pagamento_id=forma_pag_id,
                    observacoes=f"Recebimento venda #{venda_numero}",
                    user_id=user_id,
                    tenant_id=tenant_id  # ✅ Garantir isolamento entre empresas
                )
                db.add(recebimento)
                db.flush()
                recebimentos_criados.append(recebimento.id)
                
                # Atualizar status
                if abs(novo_valor_recebido - float(conta.valor_final)) < 0.01:
                    # Conta totalmente paga
                    conta.status = 'recebido'
                    conta.data_recebimento = date.today()
                    logger.info(
                        f"✅ Conta #{conta.id} TOTALMENTE baixada - "
                        f"R$ {valor_a_baixar:.2f} (Recebimento #{recebimento.id})"
                    )
                else:
                    # Conta parcialmente paga
                    conta.status = 'parcial'
                    logger.info(
                        f"📊 Conta #{conta.id} baixa PARCIAL - "
                        f"R$ {valor_a_baixar:.2f} (total recebido: R$ {novo_valor_recebido:.2f})"
                    )
                
                db.add(conta)
                
                contas_baixadas.append({
                    'conta_id': conta.id,
                    'descricao': conta.descricao,
                    'valor_baixado': Decimal(str(valor_a_baixar)),
                    'valor_total': conta.valor_final,
                    'valor_recebido': conta.valor_recebido,
                    'status': conta.status
                })
                
                # Diminuir valor disponível
                valor_disponivel -= valor_a_baixar
        
        valor_distribuido = valor_total_pagamento - valor_disponivel
        
        logger.info(
            f"🎯 Baixa concluída: {len(contas_baixadas)} conta(s), "
            f"R$ {valor_distribuido:.2f} distribuído"
        )
        
        return {
            'contas_baixadas': contas_baixadas,
            'recebimentos_criados': recebimentos_criados,
            'valor_distribuido': Decimal(str(valor_distribuido)),
            'valor_restante': Decimal(str(valor_disponivel))
        }
    
    @staticmethod
    def atualizar_lancamentos_venda(
        venda_id: int,
        venda_numero: str,
        total_venda: float,
        total_recebido: float,
        user_id: int,
        tenant_id: str,
        db: Session
    ) -> Dict[str, Any]:
        """
        Atualiza lançamentos manuais previstos após pagamento de venda.
        
        Quando uma venda é parcialmente ou totalmente paga, esta função:
        1. Busca lançamentos previstos da venda
        2. Se pago totalmente: marca lançamento como 'realizado'
        3. Se pago parcialmente: cria lançamento realizado + ajusta previsto
        
        Args:
            venda_id: ID da venda
            venda_numero: Número formatado da venda
            total_venda: Valor total da venda
            total_recebido: Valor total já recebido
            user_id: ID do usuário
            tenant_id: ID do tenant (empresa)
            db: Sessão do SQLAlchemy
            
        Returns:
            Dict com resultado:
            {
                'lancamentos_atualizados': List[int],
                'lancamentos_criados': List[int],
                'status': str  # 'totalmente_pago', 'parcialmente_pago', 'nenhum'
            }
        """
        from app.financeiro_models import LancamentoManual
        
        logger.debug(
            f"📝 Atualizando lançamentos da venda #{venda_numero} - "
            f"Total: R$ {total_venda:.2f}, Recebido: R$ {total_recebido:.2f}"
        )
        
        # Buscar lançamentos previstos
        lancamentos_previstos = db.query(LancamentoManual).filter(
            LancamentoManual.documento == f"VENDA-{venda_id}",
            LancamentoManual.status == 'previsto',
            LancamentoManual.tipo == 'entrada'
        ).all()
        
        if not lancamentos_previstos:
            logger.debug("ℹ️ Nenhum lançamento previsto encontrado")
            return {
                'lancamentos_atualizados': [],
                'lancamentos_criados': [],
                'status': 'nenhum'
            }
        
        lancamentos_atualizados = []
        lancamentos_criados = []
        
        # Verificar se pagou tudo
        if abs(total_recebido - total_venda) < 0.01:
            # TOTALMENTE PAGO: Marcar lançamentos como realizados
            for lanc_prev in lancamentos_previstos:
                lanc_prev.status = 'realizado'
                lanc_prev.data_lancamento = date.today()
                db.add(lanc_prev)
                lancamentos_atualizados.append(lanc_prev.id)
                logger.info(f"✅ Lançamento #{lanc_prev.id} marcado como REALIZADO")
            
            return {
                'lancamentos_atualizados': lancamentos_atualizados,
                'lancamentos_criados': [],
                'status': 'totalmente_pago'
            }
        
        elif total_recebido > 0.01:
            # PARCIALMENTE PAGO: Criar lançamento realizado + ajustar previsto
            for lanc_prev in lancamentos_previstos:
                # Criar lançamento realizado
                lanc_realizado = LancamentoManual(
                    tipo='entrada',
                    valor=Decimal(str(total_recebido)),
                    descricao=f"Venda {venda_numero} - Recebido (parcial)",
                    data_lancamento=date.today(),
                    status='realizado',
                    categoria_id=lanc_prev.categoria_id,
                    documento=f"VENDA-{venda_id}-REALIZADO",
                    fornecedor_cliente=lanc_prev.fornecedor_cliente,
                    user_id=user_id,
                    tenant_id=tenant_id
                )
                db.add(lanc_realizado)
                db.flush()
                lancamentos_criados.append(lanc_realizado.id)
                
                # Ajustar lançamento previsto para saldo restante
                saldo_restante = total_venda - total_recebido
                lanc_prev.valor = Decimal(str(saldo_restante))
                lanc_prev.descricao = f"{lanc_prev.descricao} - Saldo restante"
                db.add(lanc_prev)
                lancamentos_atualizados.append(lanc_prev.id)
                
                logger.info(
                    f"📊 Lançamento parcial: Realizado #{lanc_realizado.id} (R$ {total_recebido:.2f}), "
                    f"Previsto #{lanc_prev.id} ajustado (R$ {saldo_restante:.2f})"
                )
            
            return {
                'lancamentos_atualizados': lancamentos_atualizados,
                'lancamentos_criados': lancamentos_criados,
                'status': 'parcialmente_pago'
            }
        
        return {
            'lancamentos_atualizados': [],
            'lancamentos_criados': [],
            'status': 'nenhum'
        }


# ============================================================================
# FUNÇÕES AUXILIARES
# ============================================================================

def calcular_total_pendente_venda(venda_id: int, db: Session) -> Decimal:
    """
    Calcula quanto ainda falta receber de uma venda.
    
    Args:
        venda_id: ID da venda
        db: Sessão do SQLAlchemy
        
    Returns:
        Valor total pendente (soma de todas as contas pendentes/parciais)
    """
    from app.financeiro_models import ContaReceber
    
    contas = db.query(ContaReceber).filter(
        ContaReceber.venda_id == venda_id,
        ContaReceber.status.in_(['pendente', 'parcial', 'vencido'])
    ).all()
    
    total_pendente = Decimal('0')
    for conta in contas:
        pendente_conta = conta.valor_final - (conta.valor_recebido or Decimal('0'))
        total_pendente += pendente_conta
    
    return total_pendente


def listar_contas_vencidas(user_id: int, db: Session) -> List[Dict[str, Any]]:
    """
    Lista todas as contas vencidas de um usuário.
    
    Args:
        user_id: ID do usuário
        db: Sessão do SQLAlchemy
        
    Returns:
        Lista de dicts com informações das contas vencidas
    """
    from app.financeiro_models import ContaReceber
    
    hoje = date.today()
    
    contas = db.query(ContaReceber).filter(
        ContaReceber.user_id == user_id,
        ContaReceber.status.in_(['pendente', 'parcial']),
        ContaReceber.data_vencimento < hoje
    ).order_by(ContaReceber.data_vencimento).all()
    
    resultado = []
    for conta in contas:
        dias_atraso = (hoje - conta.data_vencimento).days
        pendente = float(conta.valor_final) - float(conta.valor_recebido or 0)
        
        resultado.append({
            'conta_id': conta.id,
            'descricao': conta.descricao,
            'cliente_id': conta.cliente_id,
            'valor_pendente': Decimal(str(pendente)),
            'data_vencimento': conta.data_vencimento,
            'dias_atraso': dias_atraso,
            'venda_id': conta.venda_id
        })
    
    return resultado
