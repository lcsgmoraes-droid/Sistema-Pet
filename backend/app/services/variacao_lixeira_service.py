"""
Service de Domínio - Lixeira de Variações

Responsável por gerenciar exclusão lógica (soft delete) e
restauração de produtos do tipo VARIACAO.
"""
from typing import List
from sqlalchemy.orm import Session
from datetime import datetime
import logging

from ..produtos_models import Produto

logger = logging.getLogger(__name__)


class VariacaoLixeiraService:
    """
    Service para gerenciar lixeira de variações
    
    Responsabilidades:
    - Exclusão lógica de variações (soft delete)
    - Restauração de variações excluídas
    - Listagem de variações ativas e excluídas
    
    Regras:
    - Apenas produtos VARIACAO podem ser excluídos/restaurados
    - Exclusão lógica: ativo=False, deleted_at=now
    - Restauração: ativo=True, deleted_at=NULL
    - Vínculos em ProdutoVariacaoAtributo são preservados
    """
    
    @staticmethod
    def excluir_variacao(
        variacao_id: int,
        db: Session,
        user_id: int
    ) -> Produto:
        """
        Exclui logicamente (soft delete) uma variação
        
        Args:
            variacao_id: ID da variação a excluir
            db: Sessão do banco de dados
            user_id: ID do usuário (tenant)
            
        Returns:
            Produto variação excluída
            
        Raises:
            ValueError: Quando regras de negócio são violadas
        """
        
        logger.info(f"🗑️ Excluindo variação ID={variacao_id}")
        
        # ========================================
        # VALIDAÇÃO 1: Produto existe
        # ========================================
        variacao = db.query(Produto).filter(
            Produto.id == variacao_id,
            Produto.user_id == user_id
        ).first()
        
        if not variacao:
            raise ValueError(f"Produto com ID {variacao_id} não encontrado")
        
        # ========================================
        # VALIDAÇÃO 2: É do tipo VARIACAO
        # ========================================
        if variacao.tipo_produto != 'VARIACAO':
            raise ValueError(
                f"Apenas produtos do tipo VARIACAO podem ser excluídos via lixeira. "
                f"Tipo atual: {variacao.tipo_produto}"
            )
        
        # ========================================
        # VALIDAÇÃO 3: Não está já excluída
        # ========================================
        if not variacao.ativo or variacao.deleted_at:
            raise ValueError(
                f"Variação '{variacao.nome}' já está na lixeira. "
                f"Excluída em: {variacao.deleted_at}"
            )
        
        # ========================================
        # EXECUTAR SOFT DELETE
        # ========================================
        try:
            variacao.ativo = False
            variacao.deleted_at = datetime.utcnow()
            variacao.updated_at = datetime.utcnow()
            
            db.commit()
            db.refresh(variacao)
            
            logger.info(f"✅ Variação excluída: {variacao.nome}")
            logger.info(f"   ID: {variacao.id}")
            logger.info(f"   Excluída em: {variacao.deleted_at}")
            
            return variacao
            
        except Exception as e:
            db.rollback()
            logger.error(f"❌ Erro ao excluir variação: {str(e)}")
            raise ValueError(f"Erro ao excluir variação: {str(e)}")
    
    @staticmethod
    def restaurar_variacao(
        variacao_id: int,
        db: Session,
        user_id: int
    ) -> Produto:
        """
        Restaura uma variação excluída (remove da lixeira)
        
        Args:
            variacao_id: ID da variação a restaurar
            db: Sessão do banco de dados
            user_id: ID do usuário (tenant)
            
        Returns:
            Produto variação restaurada
            
        Raises:
            ValueError: Quando regras de negócio são violadas
        """
        
        logger.info(f"♻️ Restaurando variação ID={variacao_id}")
        
        # ========================================
        # VALIDAÇÃO 1: Produto existe
        # ========================================
        variacao = db.query(Produto).filter(
            Produto.id == variacao_id,
            Produto.user_id == user_id
        ).first()
        
        if not variacao:
            raise ValueError(f"Produto com ID {variacao_id} não encontrado")
        
        # ========================================
        # VALIDAÇÃO 2: É do tipo VARIACAO
        # ========================================
        if variacao.tipo_produto != 'VARIACAO':
            raise ValueError(
                f"Apenas produtos do tipo VARIACAO podem ser restaurados via lixeira. "
                f"Tipo atual: {variacao.tipo_produto}"
            )
        
        # ========================================
        # VALIDAÇÃO 3: Está na lixeira
        # ========================================
        if variacao.ativo and not variacao.deleted_at:
            raise ValueError(
                f"Variação '{variacao.nome}' não está na lixeira. "
                "Apenas variações excluídas podem ser restauradas."
            )
        
        # ========================================
        # EXECUTAR RESTAURAÇÃO
        # ========================================
        try:
            variacao.ativo = True
            variacao.deleted_at = None
            variacao.updated_at = datetime.utcnow()
            
            db.commit()
            db.refresh(variacao)
            
            logger.info(f"✅ Variação restaurada: {variacao.nome}")
            logger.info(f"   ID: {variacao.id}")
            logger.info("   Status: Ativa novamente")
            
            return variacao
            
        except Exception as e:
            db.rollback()
            logger.error(f"❌ Erro ao restaurar variação: {str(e)}")
            raise ValueError(f"Erro ao restaurar variação: {str(e)}")
    
    @staticmethod
    def listar_variacoes_ativas(
        produto_pai_id: int,
        db: Session,
        user_id: int
    ) -> List[Produto]:
        """
        Lista todas as variações ATIVAS de um produto PAI
        
        Args:
            produto_pai_id: ID do produto PAI
            db: Sessão do banco de dados
            user_id: ID do usuário (tenant)
            
        Returns:
            Lista de produtos VARIACAO ativos
        """
        
        variacoes = db.query(Produto).filter(
            Produto.produto_pai_id == produto_pai_id,
            Produto.tipo_produto == 'VARIACAO',
            Produto.ativo.is_(True),
            Produto.deleted_at.is_(None),
            Produto.user_id == user_id
        ).order_by(Produto.nome).all()
        
        logger.info(f"📋 {len(variacoes)} variações ativas encontradas para produto_pai_id={produto_pai_id}")
        
        return variacoes
    
    @staticmethod
    def listar_variacoes_excluidas(
        produto_pai_id: int,
        db: Session,
        user_id: int
    ) -> List[Produto]:
        """
        Lista todas as variações EXCLUÍDAS (lixeira) de um produto PAI
        
        Args:
            produto_pai_id: ID do produto PAI
            db: Sessão do banco de dados
            user_id: ID do usuário (tenant)
            
        Returns:
            Lista de produtos VARIACAO na lixeira
        """
        
        variacoes = db.query(Produto).filter(
            Produto.produto_pai_id == produto_pai_id,
            Produto.tipo_produto == 'VARIACAO',
            Produto.ativo.is_(False),
            Produto.deleted_at.isnot(None),
            Produto.user_id == user_id
        ).order_by(Produto.deleted_at.desc()).all()
        
        logger.info(f"🗑️ {len(variacoes)} variações na lixeira encontradas para produto_pai_id={produto_pai_id}")
        
        return variacoes
    
    @staticmethod
    def contar_variacoes(
        produto_pai_id: int,
        db: Session,
        user_id: int
    ) -> dict:
        """
        Conta variações ativas e excluídas de um produto PAI
        
        Args:
            produto_pai_id: ID do produto PAI
            db: Sessão do banco de dados
            user_id: ID do usuário (tenant)
            
        Returns:
            Dict com contadores: {'ativas': X, 'excluidas': Y, 'total': Z}
        """
        
        # Contar ativas
        ativas = db.query(Produto).filter(
            Produto.produto_pai_id == produto_pai_id,
            Produto.tipo_produto == 'VARIACAO',
            Produto.ativo.is_(True),
            Produto.deleted_at.is_(None),
            Produto.user_id == user_id
        ).count()
        
        # Contar excluídas
        excluidas = db.query(Produto).filter(
            Produto.produto_pai_id == produto_pai_id,
            Produto.tipo_produto == 'VARIACAO',
            Produto.ativo.is_(False),
            Produto.deleted_at.isnot(None),
            Produto.user_id == user_id
        ).count()
        
        total = ativas + excluidas
        
        resultado = {
            'ativas': ativas,
            'excluidas': excluidas,
            'total': total
        }
        
        logger.info(f"📊 Contadores para produto_pai_id={produto_pai_id}: {resultado}")
        
        return resultado
