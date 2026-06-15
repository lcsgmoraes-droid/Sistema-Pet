"""
Service de Domínio - Gerador Automático de Variações de Produtos

Responsável por gerar todas as combinações possíveis de variações
a partir dos atributos e opções definidos em um produto PAI.
"""
from typing import List, Tuple
from sqlalchemy.orm import Session
from itertools import product
import logging

from ..produtos_models import (
    Produto, 
    ProdutoAtributo, 
    ProdutoAtributoOpcao, 
    ProdutoVariacaoAtributo
)

logger = logging.getLogger(__name__)


class GeradorVariacoesService:
    """
    Service de domínio para geração automática de variações
    
    Responsabilidades:
    - Validar produto PAI e seus atributos
    - Gerar produto cartesiano de opções
    - Criar variações não existentes
    - Vincular opções às variações criadas
    
    Exemplo:
    --------
    Produto PAI: "Ração Golden Adulto"
    Atributos:
        - Peso: [1kg, 3kg, 15kg]
        - Sabor: [Carne, Frango]
    
    Resultado: 6 variações
        1. Ração Golden Adulto - 1kg - Carne
        2. Ração Golden Adulto - 1kg - Frango
        3. Ração Golden Adulto - 3kg - Carne
        4. Ração Golden Adulto - 3kg - Frango
        5. Ração Golden Adulto - 15kg - Carne
        6. Ração Golden Adulto - 15kg - Frango
    """
    
    @staticmethod
    def generate_variacoes(
        produto_pai_id: int,
        db: Session,
        user_id: int
    ) -> List[Produto]:
        """
        Gera todas as variações possíveis de um produto PAI
        
        Args:
            produto_pai_id: ID do produto PAI
            db: Sessão do banco de dados
            user_id: ID do usuário (tenant)
            
        Returns:
            Lista de produtos VARIACAO criados (apenas os novos)
            
        Raises:
            ValueError: Quando regras de negócio são violadas
        """
        
        logger.info(f"🔄 Iniciando geração de variações para produto_pai_id={produto_pai_id}")
        
        # ========================================
        # VALIDAÇÃO 1: Produto existe e é PAI
        # ========================================
        produto_pai = db.query(Produto).filter(
            Produto.id == produto_pai_id,
            Produto.user_id == user_id
        ).first()
        
        if not produto_pai:
            raise ValueError(f"Produto com ID {produto_pai_id} não encontrado")
        
        if produto_pai.tipo_produto != 'PAI':
            raise ValueError(
                f"Produto '{produto_pai.nome}' não é do tipo PAI. "
                f"Tipo atual: {produto_pai.tipo_produto}"
            )
        
        logger.info(f"✅ Produto PAI validado: {produto_pai.nome}")
        
        # ========================================
        # BUSCAR ATRIBUTOS E OPÇÕES ATIVAS
        # ========================================
        atributos = db.query(ProdutoAtributo).filter(
            ProdutoAtributo.produto_pai_id == produto_pai_id,
            ProdutoAtributo.ativo.is_(True)
        ).order_by(ProdutoAtributo.ordem).all()
        
        if not atributos:
            raise ValueError(
                f"Produto PAI '{produto_pai.nome}' não possui atributos definidos. "
                "Crie atributos antes de gerar variações."
            )
        
        logger.info(f"📋 {len(atributos)} atributos encontrados")
        
        # Buscar opções para cada atributo
        atributos_com_opcoes = []
        for atributo in atributos:
            opcoes = db.query(ProdutoAtributoOpcao).filter(
                ProdutoAtributoOpcao.atributo_id == atributo.id,
                ProdutoAtributoOpcao.ativo.is_(True)
            ).order_by(ProdutoAtributoOpcao.ordem).all()
            
            if not opcoes:
                raise ValueError(
                    f"Atributo '{atributo.nome}' não possui opções definidas. "
                    "Todos os atributos devem ter pelo menos uma opção."
                )
            
            atributos_com_opcoes.append((atributo, opcoes))
            logger.info(f"  - {atributo.nome}: {len(opcoes)} opções")
        
        # ========================================
        # GERAR PRODUTO CARTESIANO
        # ========================================
        # Extrair apenas as opções para o produto cartesiano
        listas_opcoes = [opcoes for _, opcoes in atributos_com_opcoes]
        
        # Gerar todas as combinações possíveis
        combinacoes = list(product(*listas_opcoes))
        
        logger.info(f"🎲 {len(combinacoes)} combinações possíveis geradas")
        
        # ========================================
        # CRIAR VARIAÇÕES (com transação)
        # ========================================
        variacoes_criadas = []
        variacoes_ignoradas = 0
        
        try:
            for combinacao in combinacoes:
                # Verificar se variação já existe
                if GeradorVariacoesService._variacao_existe(
                    produto_pai_id, combinacao, db
                ):
                    variacoes_ignoradas += 1
                    logger.debug(f"⏭️ Variação já existe: {[op.valor for op in combinacao]}")
                    continue
                
                # Criar nova variação
                variacao = GeradorVariacoesService._criar_variacao(
                    produto_pai=produto_pai,
                    combinacao=combinacao,
                    atributos=[atr for atr, _ in atributos_com_opcoes],
                    user_id=user_id,
                    db=db
                )
                
                variacoes_criadas.append(variacao)
                logger.info(f"✅ Variação criada: {variacao.nome}")
            
            # Commit da transação
            db.commit()
            
            logger.info("🎉 Processo concluído!")
            logger.info(f"  ✅ {len(variacoes_criadas)} variações criadas")
            logger.info(f"  ⏭️ {variacoes_ignoradas} variações já existentes")
            
            return variacoes_criadas
            
        except Exception as e:
            db.rollback()
            logger.error(f"❌ Erro ao gerar variações: {str(e)}")
            raise ValueError(f"Erro ao gerar variações: {str(e)}")
    
    @staticmethod
    def _variacao_existe(
        produto_pai_id: int,
        combinacao: Tuple[ProdutoAtributoOpcao, ...],
        db: Session
    ) -> bool:
        """
        Verifica se já existe uma variação com essa combinação de opções
        
        Args:
            produto_pai_id: ID do produto PAI
            combinacao: Tupla de opções
            db: Sessão do banco de dados
            
        Returns:
            True se a variação já existe, False caso contrário
        """
        
        # Buscar todas as variações do produto PAI
        variacoes = db.query(Produto).filter(
            Produto.produto_pai_id == produto_pai_id,
            Produto.tipo_produto == 'VARIACAO',
            Produto.ativo.is_(True)
        ).all()
        
        # IDs das opções da combinação atual
        opcoes_ids = set(opcao.id for opcao in combinacao)
        
        # Verificar cada variação existente
        for variacao in variacoes:
            # Buscar atributos da variação
            atributos_variacao = db.query(ProdutoVariacaoAtributo).filter(
                ProdutoVariacaoAtributo.variacao_id == variacao.id
            ).all()
            
            # IDs das opções da variação existente
            opcoes_variacao_ids = set(av.opcao_id for av in atributos_variacao)
            
            # Se os conjuntos são iguais, a variação já existe
            if opcoes_ids == opcoes_variacao_ids:
                return True
        
        return False
    
    @staticmethod
    def _criar_variacao(
        produto_pai: Produto,
        combinacao: Tuple[ProdutoAtributoOpcao, ...],
        atributos: List[ProdutoAtributo],
        user_id: int,
        db: Session
    ) -> Produto:
        """
        Cria uma variação com a combinação especificada
        
        Args:
            produto_pai: Instância do produto PAI
            combinacao: Tupla de opções
            atributos: Lista de atributos (para ordenação correta)
            user_id: ID do usuário
            db: Sessão do banco de dados
            
        Returns:
            Produto VARIACAO criado
        """
        
        # ========================================
        # GERAR NOME AUTOMÁTICO
        # ========================================
        # Formato: "{Nome do PAI} - {opcao1} - {opcao2} - ..."
        valores_opcoes = [opcao.valor for opcao in combinacao]
        nome_variacao = f"{produto_pai.nome} - {' - '.join(valores_opcoes)}"
        
        # ========================================
        # CRIAR PRODUTO VARIACAO
        # ========================================
        variacao = Produto(
            # Identificação
            codigo=f"VAR-TEMP-{produto_pai.id}",  # Temporário - será atualizado depois
            nome=nome_variacao,
            tipo_produto='VARIACAO',
            produto_pai_id=produto_pai.id,
            
            # Herdar do PAI
            categoria_id=produto_pai.categoria_id,
            marca_id=produto_pai.marca_id,
            departamento_id=produto_pai.departamento_id,
            unidade=produto_pai.unidade,
            
            # Campos obrigatórios (valores padrão)
            preco_venda=0,  # Será definido pelo usuário depois
            preco_custo=0,
            estoque_atual=0,
            estoque_minimo=0,
            controle_lote=True,
            
            # Auditoria
            user_id=user_id,
            ativo=True
        )
        
        db.add(variacao)
        db.flush()  # Gera o ID sem fazer commit
        
        # Atualizar código com ID real
        variacao.codigo = f"VAR-{variacao.id}"
        
        # ========================================
        # CRIAR VÍNCULOS COM OPÇÕES
        # ========================================
        for i, opcao in enumerate(combinacao):
            atributo = atributos[i]
            
            vinculo = ProdutoVariacaoAtributo(
                variacao_id=variacao.id,
                atributo_id=atributo.id,
                opcao_id=opcao.id
            )
            
            db.add(vinculo)
        
        return variacao
