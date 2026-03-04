# -*- coding: utf-8 -*-
"""
Serviço de Caixa (Cash Register Service)
=========================================

Este serviço isola TODA a lógica relacionada ao CAIXA físico do PDV.

RESPONSABILIDADES:
------------------
1. Validar se há caixa aberto antes de finalizar vendas
2. Registrar movimentações de DINHEIRO em ESPÉCIE (entrada/saída)
3. Vincular vendas ao caixa aberto
4. Registrar devoluções em dinheiro
5. Validar formas de pagamento que afetam o caixa físico

IMPORTANTE - O QUE NÃO FAZ:
---------------------------
❌ NÃO trata PIX, cartão de débito/crédito (isso é movimentação bancária/financeira)
❌ NÃO cria contas a receber (responsabilidade do módulo financeiro)
❌ NÃO comita transações (apenas flush)
❌ NÃO trata crédito de clientes (responsabilidade do módulo de clientes)

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
from app.caixa import CaixaService

# Validar caixa antes de iniciar venda
caixa_info = CaixaService.validar_caixa_aberto(user_id=1, db=db)
caixa_id = caixa_info['caixa_id']

# Registrar movimentação de venda em dinheiro
mov_info = CaixaService.registrar_movimentacao_venda(
    caixa_id=caixa_id,
    venda_id=venda.id,
    venda_numero=venda.numero_venda,
    valor=100.50,
    user_id=1,
    user_nome="João",
    db=db
)

# Registrar devolução em dinheiro
dev_info = CaixaService.registrar_devolucao(
    caixa_id=caixa_id,
    venda_id=venda.id,
    venda_numero=venda.numero_venda,
    valor=50.00,
    motivo="Produto com defeito",
    user_id=1,
    user_nome="João",
    db=db
)
```

AUTOR: Sistema Pet Shop - Refatoração Fase 2
DATA: 2025-01-23
"""

import logging
from typing import Dict, Any
from decimal import Decimal
from datetime import datetime
from fastapi import HTTPException
from sqlalchemy.orm import Session

# Logger
logger = logging.getLogger(__name__)


class CaixaService:
    """
    Serviço isolado para gerenciar operações de CAIXA físico (dinheiro em espécie).
    
    Este serviço é STATELESS e todos os métodos são estáticos.
    Não mantém estado entre chamadas.
    """
    
    @staticmethod
    def validar_caixa_aberto(user_id: int, db: Session) -> Dict[str, Any]:
        """
        Valida se existe um caixa aberto para o usuário.
        
        Esta validação é OBRIGATÓRIA antes de:
        - Finalizar qualquer venda
        - Registrar movimentações manuais
        - Processar devoluções
        
        Args:
            user_id: ID do usuário/funcionário
            db: Sessão do SQLAlchemy (não será commitada)
            
        Returns:
            Dict com informações do caixa:
            {
                'caixa_id': int,
                'valor_abertura': Decimal,
                'data_abertura': datetime,
                'usuario_id': int
            }
            
        Raises:
            HTTPException(400): Se não houver caixa aberto para o usuário
            
        Exemplo:
            >>> caixa_info = CaixaService.validar_caixa_aberto(user_id=1, db=db)
            >>> logger.info(f"Caixa ID: {caixa_info['caixa_id']}")
        """
        # Import local para evitar circular dependency
        from app.caixa_models import Caixa
        
        logger.debug(f"🔍 Validando caixa aberto para user_id={user_id}")
        
        caixa_aberto = db.query(Caixa).filter(
            Caixa.usuario_id == user_id,
            Caixa.status == 'aberto'
        ).first()
        
        if not caixa_aberto:
            logger.warning(f"⚠️ Tentativa de operação sem caixa aberto - user_id={user_id}")
            raise HTTPException(
                status_code=400,
                detail='Não há caixa aberto. Abra um caixa antes de realizar vendas.'
            )
        
        logger.info(f"✅ Caixa válido - ID={caixa_aberto.id}, user_id={user_id}")
        
        return {
            'caixa_id': caixa_aberto.id,
            'valor_abertura': caixa_aberto.valor_abertura,
            'data_abertura': caixa_aberto.data_abertura,
            'usuario_id': caixa_aberto.usuario_id
        }
    
    @staticmethod
    def eh_forma_dinheiro(forma_pagamento: Any) -> bool:
        """
        Verifica se a forma de pagamento é DINHEIRO em ESPÉCIE.
        
        Esta função normaliza diferentes representações de "Dinheiro":
        - String: "Dinheiro", "dinheiro", "DINHEIRO"
        - ID: 1 (int ou string)
        
        Args:
            forma_pagamento: Pode ser string, int ou qualquer tipo
            
        Returns:
            True se for dinheiro, False caso contrário
            
        Exemplo:
            >>> CaixaService.eh_forma_dinheiro("Dinheiro")
            True
            >>> CaixaService.eh_forma_dinheiro(1)
            True
            >>> CaixaService.eh_forma_dinheiro("PIX")
            False
        """
        if isinstance(forma_pagamento, str):
            return forma_pagamento.lower() == 'dinheiro'
        
        if isinstance(forma_pagamento, int):
            return forma_pagamento == 1
        
        # Tentar converter para string e comparar
        return str(forma_pagamento) == '1'
    
    @staticmethod
    def registrar_movimentacao_venda(
        caixa_id: int,
        venda_id: int,
        venda_numero: str,
        valor: float,
        user_id: int,
        user_nome: str,
        tenant_id,  # UUID do tenant (obrigatório para isolamento)
        db: Session
    ) -> Dict[str, Any]:
        """
        Registra movimentação de ENTRADA no caixa referente a venda em DINHEIRO.
        
        Este método deve ser chamado APENAS para pagamentos em dinheiro vivo.
        PIX, cartões e outras formas vão para o módulo financeiro.
        
        Args:
            caixa_id: ID do caixa aberto
            venda_id: ID da venda (FK)
            venda_numero: Número formatado da venda (ex: "VD-2025-00001")
            valor: Valor em dinheiro recebido
            user_id: ID do usuário que está registrando
            user_nome: Nome do usuário (para auditoria)
            tenant_id: UUID do tenant (isolamento multi-tenant)
            db: Sessão do SQLAlchemy (não será commitada)
            
        Returns:
            Dict com informações da movimentação:
            {
                'movimentacao_id': int,
                'tipo': 'venda',
                'valor': Decimal,
                'descricao': str
            }
            
        Raises:
            ValueError: Se o valor for <= 0
            
        Exemplo:
            >>> mov = CaixaService.registrar_movimentacao_venda(
            ...     caixa_id=5,
            ...     venda_id=120,
            ...     venda_numero="VD-2025-00120",
            ...     valor=150.00,
            ...     user_id=1,
            ...     user_nome="João Silva",
            ...     db=db
            ... )
            >>> logger.info(f"Movimentação criada: ID {mov['movimentacao_id']}")
        """
        # Import local para evitar circular dependency
        from app.caixa_models import MovimentacaoCaixa
        
        if valor <= 0:
            raise ValueError("Valor da movimentação deve ser maior que zero")
        
        logger.debug(
            f"💰 Registrando movimentação de venda: "
            f"caixa_id={caixa_id}, venda_id={venda_id}, valor={valor:.2f}"
        )
        
        # 🔒 ISOLAMENTO MULTI-TENANT: tenant_id obrigatório
        movimentacao = MovimentacaoCaixa(
            caixa_id=caixa_id,
            tipo='venda',
            valor=valor,
            forma_pagamento='Dinheiro',  # Sempre "Dinheiro" (não ID)
            descricao=f'Venda #{venda_numero}',
            venda_id=venda_id,
            usuario_id=user_id,
            usuario_nome=user_nome or 'Usuário',  # fallback: usuario sem nome cadastrado
            tenant_id=tenant_id  # ✅ Garantir isolamento entre empresas
        )
        
        db.add(movimentacao)
        db.flush()  # Para obter o ID, mas não commitar
        
        logger.info(
            f"✅ Movimentação de caixa criada: "
            f"ID={movimentacao.id}, Venda={venda_numero}, Valor=R$ {valor:.2f}"
        )
        
        return {
            'movimentacao_id': movimentacao.id,
            'tipo': 'venda',
            'valor': Decimal(str(valor)),
            'descricao': movimentacao.descricao
        }
    
    @staticmethod
    def registrar_devolucao(
        caixa_id: int,
        venda_id: int,
        venda_numero: str,
        valor: float,
        motivo: str,
        user_id: int,
        user_nome: str,
        tenant_id,  # UUID do tenant (obrigatório para isolamento)
        db: Session
    ) -> Dict[str, Any]:
        """
        Registra movimentação de SAÍDA no caixa referente a devolução em DINHEIRO.
        
        Este método registra devoluções onde o dinheiro sai fisicamente do caixa
        para devolver ao cliente.
        
        Args:
            caixa_id: ID do caixa aberto
            venda_id: ID da venda original (FK)
            venda_numero: Número formatado da venda (ex: "VD-2025-00001")
            valor: Valor em dinheiro devolvido ao cliente
            motivo: Motivo da devolução (para auditoria)
            user_id: ID do usuário que está registrando
            user_nome: Nome do usuário (para auditoria)
            tenant_id: UUID do tenant (isolamento multi-tenant)
            db: Sessão do SQLAlchemy (não será commitada)
            
        Returns:
            Dict com informações da movimentação:
            {
                'movimentacao_id': int,
                'tipo': 'devolucao',
                'valor': Decimal,
                'descricao': str
            }
            
        Raises:
            ValueError: Se o valor for <= 0
            
        Exemplo:
            >>> dev = CaixaService.registrar_devolucao(
            ...     caixa_id=5,
            ...     venda_id=120,
            ...     venda_numero="VD-2025-00120",
            ...     valor=50.00,
            ...     motivo="Produto com defeito",
            ...     user_id=1,
            ...     user_nome="João Silva",
            ...     db=db
            ... )
            >>> logger.info(f"Devolução registrada: ID {dev['movimentacao_id']}")
        """
        # Import local para evitar circular dependency
        from app.caixa_models import MovimentacaoCaixa
        
        if valor <= 0:
            raise ValueError("Valor da devolução deve ser maior que zero")
        
        logger.debug(
            f"🔄 Registrando devolução em dinheiro: "
            f"caixa_id={caixa_id}, venda_id={venda_id}, valor={valor:.2f}, motivo={motivo}"
        )
        
        # 🔒 ISOLAMENTO MULTI-TENANT: tenant_id obrigatório
        movimentacao = MovimentacaoCaixa(
            caixa_id=caixa_id,
            tipo='devolucao',
            valor=valor,
            forma_pagamento='Dinheiro',
            descricao=f'Devolução Venda #{venda_numero}: {motivo}',
            venda_id=venda_id,
            usuario_id=user_id,
            usuario_nome=user_nome,
            tenant_id=tenant_id  # ✅ Garantir isolamento entre empresas
        )
        
        db.add(movimentacao)
        db.flush()  # Para obter o ID, mas não commitar
        
        logger.info(
            f"✅ Devolução em caixa registrada: "
            f"ID={movimentacao.id}, Venda={venda_numero}, Valor=R$ {valor:.2f}"
        )
        
        return {
            'movimentacao_id': movimentacao.id,
            'tipo': 'devolucao',
            'valor': Decimal(str(valor)),
            'descricao': movimentacao.descricao
        }
    
    @staticmethod
    def vincular_venda_ao_caixa(
        venda_id: int,
        caixa_id: int,
        db: Session
    ) -> Dict[str, Any]:
        """
        Vincula uma venda ao caixa aberto (atualiza venda.caixa_id).
        
        Este método é chamado após finalizar a venda com sucesso,
        criando o vínculo entre a venda e o caixa que estava aberto
        no momento da venda.
        
        Args:
            venda_id: ID da venda
            caixa_id: ID do caixa aberto
            db: Sessão do SQLAlchemy (não será commitada)
            
        Returns:
            Dict confirmando o vínculo:
            {
                'venda_id': int,
                'caixa_id': int,
                'vinculado': bool
            }
            
        Raises:
            HTTPException(404): Se a venda não for encontrada
            
        Exemplo:
            >>> vinculo = CaixaService.vincular_venda_ao_caixa(
            ...     venda_id=120,
            ...     caixa_id=5,
            ...     db=db
            ... )
            >>> logger.info(f"Venda vinculada: {vinculo['vinculado']}")
        """
        # Import local para evitar circular dependency
        from app.vendas_models import Venda
        
        logger.debug(f"🔗 Vinculando venda_id={venda_id} ao caixa_id={caixa_id}")
        
        venda = db.query(Venda).filter(Venda.id == venda_id).first()
        
        if not venda:
            logger.error(f"❌ Venda não encontrada: ID={venda_id}")
            raise HTTPException(
                status_code=404,
                detail=f'Venda ID {venda_id} não encontrada'
            )
        
        venda.caixa_id = caixa_id
        db.add(venda)
        db.flush()
        
        logger.info(f"✅ Venda vinculada ao caixa: venda_id={venda_id}, caixa_id={caixa_id}")
        
        return {
            'venda_id': venda_id,
            'caixa_id': caixa_id,
            'vinculado': True
        }


# ============================================================================
# FUNÇÕES AUXILIARES (se necessário no futuro)
# ============================================================================

def calcular_saldo_caixa(caixa_id: int, db: Session) -> Decimal:
    """
    Calcula o saldo atual do caixa somando todas as movimentações.
    
    NOTA: Esta função pode ser útil no futuro para relatórios,
    mas não é usada no fluxo de vendas (apenas no fechamento).
    
    Args:
        caixa_id: ID do caixa
        db: Sessão do SQLAlchemy
        
    Returns:
        Saldo calculado (saldo_inicial + entradas - saídas)
    """
    from app.caixa_models import Caixa, MovimentacaoCaixa
    from sqlalchemy import func
    
    caixa = db.query(Caixa).filter(Caixa.id == caixa_id).first()
    if not caixa:
        return Decimal('0.00')
    
    # Somar movimentações
    movimentacoes = db.query(MovimentacaoCaixa).filter(
        MovimentacaoCaixa.caixa_id == caixa_id
    ).all()
    
    saldo = Decimal(str(caixa.valor_abertura or 0))
    
    for mov in movimentacoes:
        if mov.tipo in ['venda', 'entrada', 'sangria_entrada']:
            saldo += Decimal(str(mov.valor))
        elif mov.tipo in ['devolucao', 'saida', 'sangria']:
            saldo -= Decimal(str(mov.valor))
    
    return saldo
