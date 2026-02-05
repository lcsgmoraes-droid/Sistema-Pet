"""
Service de Cálculo de Custo de Produto KIT

Responsabilidades:
- Calcular custo de KIT VIRTUAL (soma dos componentes)
- Retornar custo de KIT FÍSICO (custo próprio)
- Validar estrutura do KIT
- Não gerar efeitos colaterais (apenas leitura)

Autor: Sistema
Data: 2026-01-24
"""

from decimal import Decimal
from typing import Optional
from sqlalchemy.orm import Session
import logging

from ..produtos_models import Produto, ProdutoKitComponente

# Logger
logger = logging.getLogger(__name__)


class KitCustoService:
    """
    Service para cálculo de custo de produtos KIT
    
    Implementa lógica de domínio pura para cálculo de custo,
    considerando KIT VIRTUAL e KIT FÍSICO.
    
    ⚠️ IMPORTANTE:
    - Apenas LEITURA
    - Não persiste dados
    - Não gera movimentações
    - Não altera produtos
    """
    
    @staticmethod
    def calcular_custo_kit(
        kit_id: int,
        db: Session,
        user_id: int
    ) -> Decimal:
        """
        Calcula o custo de um produto KIT
        
        Args:
            kit_id: ID do produto KIT
            db: Sessão do banco de dados
            user_id: ID do usuário (tenant isolation)
            
        Returns:
            Decimal: Custo total do KIT
            
        Raises:
            ValueError: Se validações falharem
            
        Regras:
        1. KIT FÍSICO → retorna preco_custo do KIT (0 se NULL)
        2. KIT VIRTUAL → soma (preco_custo × quantidade) dos componentes
        3. Componentes não podem ser KIT ou PAI
        4. Se componente não tem custo, considera 0
        
        Exemplos:
            >>> # KIT FÍSICO
            >>> custo = KitCustoService.calcular_custo_kit(kit_id=10, db=db, user_id=1)
            >>> # Retorna: Decimal('150.00')  # preco_custo do próprio KIT
            
            >>> # KIT VIRTUAL
            >>> custo = KitCustoService.calcular_custo_kit(kit_id=20, db=db, user_id=1)
            >>> # Retorna: Decimal('85.50')  # soma dos componentes
        """
        
        try:
            # ========================================
            # PASSO 1: BUSCAR E VALIDAR KIT
            # ========================================
            
            kit = db.query(Produto).filter(
                Produto.id == kit_id,
                Produto.user_id == user_id
            ).first()
            
            if not kit:
                raise ValueError(f"Produto ID {kit_id} não encontrado")
            
            if kit.tipo_produto != 'KIT':
                raise ValueError(
                    f"Produto '{kit.nome}' não é um KIT (tipo: {kit.tipo_produto}). "
                    f"Apenas produtos tipo='KIT' podem usar este serviço."
                )
            
            logger.info(
                f"📦 Calculando custo do KIT: {kit.nome} "
                f"(ID: {kit_id}, tipo_kit: {kit.tipo_kit or 'VIRTUAL'})"
            )
            
            # ========================================
            # PASSO 2: KIT FÍSICO → CUSTO PRÓPRIO
            # ========================================
            
            tipo_kit = kit.tipo_kit or 'VIRTUAL'  # Default VIRTUAL
            
            if tipo_kit == 'FISICO':
                custo_proprio = Decimal(str(kit.preco_custo or 0))
                
                logger.info(
                    f"💰 KIT FÍSICO: custo próprio = R$ {custo_proprio:.2f}"
                )
                
                return custo_proprio
            
            # ========================================
            # PASSO 3: KIT VIRTUAL → SOMA COMPONENTES
            # ========================================
            
            # Buscar componentes do KIT
            componentes = db.query(ProdutoKitComponente).filter(
                ProdutoKitComponente.kit_id == kit_id
            ).all()
            
            if not componentes:
                logger.warning(
                    f"⚠️  KIT VIRTUAL '{kit.nome}' não possui componentes. "
                    f"Retornando custo = 0"
                )
                return Decimal('0')
            
            logger.info(
                f"🔍 Encontrados {len(componentes)} componente(s) no KIT"
            )
            
            # Calcular custo total
            custo_total = Decimal('0')
            
            for componente in componentes:
                # Buscar produto componente
                produto_comp = db.query(Produto).filter(
                    Produto.id == componente.produto_componente_id,
                    Produto.user_id == user_id
                ).first()
                
                if not produto_comp:
                    logger.warning(
                        f"⚠️  Componente ID {componente.produto_componente_id} "
                        f"não encontrado (ignorando)"
                    )
                    continue
                
                # Validar que componente NÃO é KIT nem PAI
                if produto_comp.tipo_produto in ['KIT', 'PAI']:
                    raise ValueError(
                        f"Componente '{produto_comp.nome}' é do tipo "
                        f"'{produto_comp.tipo_produto}'. "
                        f"Componentes de KIT devem ser SIMPLES ou VARIACAO."
                    )
                
                # Obter custo do componente (0 se NULL)
                custo_componente = Decimal(str(produto_comp.preco_custo or 0))
                quantidade = Decimal(str(componente.quantidade))
                
                # Calcular custo deste componente
                custo_item = custo_componente * quantidade
                custo_total += custo_item
                
                logger.info(
                    f"   • {produto_comp.nome}: "
                    f"R$ {custo_componente:.2f} × {quantidade} = "
                    f"R$ {custo_item:.2f}"
                )
            
            logger.info(
                f"✅ Custo total do KIT VIRTUAL: R$ {custo_total:.2f}"
            )
            
            return custo_total
            
        except ValueError:
            # Re-raise erros de validação
            raise
            
        except Exception as e:
            logger.error(
                f"❌ Erro ao calcular custo do KIT {kit_id}: {str(e)}",
                exc_info=True
            )
            
            # Rollback em caso de erro
            if db:
                db.rollback()
            
            raise ValueError(
                f"Erro ao calcular custo do KIT: {str(e)}"
            )
    
    
    @staticmethod
    def validar_componentes_kit(
        kit_id: int,
        db: Session,
        user_id: int
    ) -> dict:
        """
        Valida a estrutura dos componentes de um KIT
        
        Args:
            kit_id: ID do produto KIT
            db: Sessão do banco de dados
            user_id: ID do usuário
            
        Returns:
            dict: Relatório de validação
            {
                'valido': bool,
                'total_componentes': int,
                'erros': List[str],
                'avisos': List[str]
            }
        """
        
        resultado = {
            'valido': True,
            'total_componentes': 0,
            'erros': [],
            'avisos': []
        }
        
        try:
            # Buscar KIT
            kit = db.query(Produto).filter(
                Produto.id == kit_id,
                Produto.user_id == user_id
            ).first()
            
            if not kit:
                resultado['valido'] = False
                resultado['erros'].append(f"KIT ID {kit_id} não encontrado")
                return resultado
            
            if kit.tipo_produto != 'KIT':
                resultado['valido'] = False
                resultado['erros'].append(
                    f"Produto não é KIT (tipo: {kit.tipo_produto})"
                )
                return resultado
            
            # Buscar componentes
            componentes = db.query(ProdutoKitComponente).filter(
                ProdutoKitComponente.kit_id == kit_id
            ).all()
            
            resultado['total_componentes'] = len(componentes)
            
            if not componentes:
                resultado['avisos'].append("KIT não possui componentes")
            
            # Validar cada componente
            for comp in componentes:
                produto_comp = db.query(Produto).filter(
                    Produto.id == comp.produto_componente_id
                ).first()
                
                if not produto_comp:
                    resultado['erros'].append(
                        f"Componente ID {comp.produto_componente_id} não existe"
                    )
                    resultado['valido'] = False
                    continue
                
                # Validar tipo
                if produto_comp.tipo_produto in ['KIT', 'PAI']:
                    resultado['erros'].append(
                        f"Componente '{produto_comp.nome}' é {produto_comp.tipo_produto} "
                        f"(apenas SIMPLES/VARIACAO permitidos)"
                    )
                    resultado['valido'] = False
                
                # Avisar se sem custo
                if not produto_comp.preco_custo or produto_comp.preco_custo == 0:
                    resultado['avisos'].append(
                        f"Componente '{produto_comp.nome}' sem custo definido"
                    )
                
                # Validar quantidade
                if comp.quantidade <= 0:
                    resultado['erros'].append(
                        f"Componente '{produto_comp.nome}' com quantidade inválida "
                        f"({comp.quantidade})"
                    )
                    resultado['valido'] = False
            
            return resultado
            
        except Exception as e:
            resultado['valido'] = False
            resultado['erros'].append(f"Erro na validação: {str(e)}")
            return resultado
