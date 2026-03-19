"""
Serviço de Produto - Centraliza regras de negócio
"""
from typing import Dict, Any, List
from sqlalchemy.orm import Session
import logging

from ..produtos_models import Produto, Categoria, Marca, ProdutoKitComponente

logger = logging.getLogger(__name__)


class ProdutoService:
    """
    Service para gerenciar regras de negócio de produtos
    
    Responsabilidades:
    - Validações de negócio específicas de tipo de produto
    - Criação de produtos com regras aplicadas
    - Gerenciamento de composição de KITs
    - Lógica de domínio isolada de FastAPI
    """
    
    @staticmethod
    def create_produto(dados: Dict[str, Any], db: Session, tenant_id: str) -> Produto:
        """
        Cria um novo produto aplicando regras de negócio
        
        Args:
            dados: Dicionário com dados do produto
            db: Sessão do banco de dados
            tenant_id: ID do tenant (isolamento multi-tenant)
            
        Returns:
            Produto criado e persistido
            
        Raises:
            ValueError: Quando regras de negócio são violadas
        """
        
        tipo_produto = dados.get('tipo_produto', 'SIMPLES')
        
        # ========================================
        # REGRA 1: Produto PAI não pode ter preços
        # ========================================
        if tipo_produto == 'PAI':
            # Produto PAI não tem preços - forçar como 0
            dados['preco_venda'] = 0
            dados['preco_custo'] = 0
            dados['preco_promocional'] = None
        
        # ========================================
        # REGRA 2: Produtos vendáveis precisam de preço (exceto KIT VIRTUAL e VARIACAO-KIT)
        # ========================================
        # VARIACAO pode ser KIT conforme regras oficiais do projeto
        eh_kit = tipo_produto == 'KIT' or (tipo_produto == 'VARIACAO' and dados.get('tipo_kit'))
        
        if tipo_produto not in ('PAI', 'KIT') and not eh_kit:
            preco = dados.get('preco_venda')
            if preco is None or preco <= 0:
                raise ValueError(
                    f"Produto do tipo '{tipo_produto}' deve ter preço de venda maior que zero."
                )
        
        # ========================================
        # REGRA 3: VARIACAO precisa de produto_pai_id
        # ========================================
        if tipo_produto == 'VARIACAO':
            if not dados.get('produto_pai_id'):
                raise ValueError(
                    "Produto do tipo VARIACAO deve ter um produto_pai_id informado."
                )
        
        # ========================================
        # REGRA 4: KIT/VARIACAO-KIT - Processar tipo_kit e composição
        # REGRA OFICIAL: Variação vendável PODE ser marcada como KIT
        # ========================================
        composicao_kit = dados.pop('composicao_kit', [])  # Extrair composição antes de criar produto
        
        # Mapear e_kit_fisico (boolean) para tipo_kit (enum)
        if dados.get('e_kit_fisico') is not None:
            e_kit_fisico = dados.get('e_kit_fisico', False)
            dados['tipo_kit'] = 'FISICO' if e_kit_fisico else 'VIRTUAL'
        
        # Se tem tipo_kit definido (KIT ou VARIACAO-KIT), validar composição
        if dados.get('tipo_kit'):
            # ⚠️ VALIDAÇÃO OBRIGATÓRIA: KIT deve ter pelo menos 1 componente
            if not composicao_kit or len(composicao_kit) == 0:
                tipo_desc = f"{tipo_produto}-KIT" if tipo_produto == 'VARIACAO' else tipo_produto
                raise ValueError(
                    f"Produto do tipo {tipo_desc} deve ter pelo menos 1 componente na composição. "
                    "Adicione os produtos que fazem parte do kit antes de salvar."
                )
        
        # ========================================
        # CRIAR PRODUTO
        # ========================================
        
        # Forçar controle_lote=True para todos os produtos
        dados['controle_lote'] = True
        
        # Remover campos None ou vazios (exceto campos numéricos que podem ser 0)
        dados_limpos = {
            k: v for k, v in dados.items() 
            if v is not None or k in ['preco_custo', 'estoque_minimo']
        }
        
        # Remover campo e_kit_fisico (já foi mapeado para tipo_kit)
        dados_limpos.pop('e_kit_fisico', None)
        
        # 🔒 ISOLAMENTO MULTI-TENANT: Adicionar tenant_id obrigatório
        dados_limpos['tenant_id'] = tenant_id
        
        logger.info(f"💾 ProdutoService: Criando produto tipo '{tipo_produto}' com {len(dados_limpos)} campos")
        
        # Criar instância
        novo_produto = Produto(**dados_limpos)
        db.add(novo_produto)
        
        try:
            db.flush()  # Flush para obter ID sem commit completo
            
            # ========================================
            # PROCESSAR COMPOSIÇÃO (KIT e VARIACAO-KIT) - TRANSAÇÃO ATÔMICA
            # ========================================
            if dados.get('tipo_kit') and composicao_kit:
                tipo_desc = f"{tipo_produto}-KIT" if tipo_produto == 'VARIACAO' else tipo_produto
                logger.info(f"🧩 Processando {len(composicao_kit)} componentes da composição para {tipo_desc}")
                
                # Validar composição
                from .kit_estoque_service import KitEstoqueService
                valido, erro = KitEstoqueService.validar_componentes_kit(
                    db=db,
                    kit_id=novo_produto.id,
                    componentes=composicao_kit
                )
                
                if not valido:
                    raise ValueError(f"Composição inválida para {tipo_desc}: {erro}")
                
                # Criar componentes
                for comp in composicao_kit:
                    componente = ProdutoKitComponente(
                        kit_id=novo_produto.id,
                        produto_componente_id=comp.get('produto_componente_id'),
                        quantidade=comp.get('quantidade', 1.0),
                        ordem=comp.get('ordem', 0),
                        opcional=comp.get('opcional', False),
                        tenant_id=novo_produto.tenant_id,
                    )
                    db.add(componente)
                
                logger.info(f"✅ {len(composicao_kit)} componentes adicionados para {tipo_desc}")
            
            db.commit()
            db.refresh(novo_produto)
            logger.info(f"✅ ProdutoService: Produto criado com sucesso! ID: {novo_produto.id}")
            return novo_produto
            
        except ValueError as e:
            # Rollback em caso de erro de validação
            db.rollback()
            logger.error(f"❌ Validação falhou: {str(e)}")
            raise
        except Exception as e:
            db.rollback()
            logger.error(f"❌ ProdutoService: Erro ao salvar produto: {str(e)}")
            raise ValueError(f"Erro ao salvar produto no banco: {str(e)}")
