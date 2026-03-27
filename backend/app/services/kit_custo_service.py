"""
Service de Cálculo de Custo de Produto Composto

Responsabilidades:
- Calcular custo por soma dos componentes para KIT e VARIACAO-KIT
- Sincronizar preco_custo persistido de produtos compostos
- Recalcular produtos compostos afetados quando um componente muda de custo
- Validar estrutura do produto composto
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
    Service para cálculo de custo de produtos compostos
    
    Implementa lógica de domínio pura para cálculo de custo,
    considerando qualquer produto com composição (KIT e VARIACAO-KIT).
    
    ⚠️ IMPORTANTE:
    A regra operacional do sistema é simples:
    - Se o produto tem composição de kit, o custo vem da soma dos componentes
    - O valor manual em preco_custo não prevalece sobre a composição
    """

    @staticmethod
    def produto_usa_custo_por_componentes(produto: Optional[Produto]) -> bool:
        if not produto:
            return False

        return produto.tipo_produto in ('KIT', 'VARIACAO') and bool(produto.tipo_kit)
    
    @staticmethod
    def calcular_custo_kit(
        kit_id: int,
        db: Session,
        user_id: Optional[int] = None
    ) -> Decimal:
        """
        Calcula o custo de um produto composto
        
        Args:
            kit_id: ID do produto composto
            db: Sessão do banco de dados
            user_id: parâmetro legado, mantido por compatibilidade
            
        Returns:
            Decimal: Custo total do KIT
            
        Raises:
            ValueError: Se validações falharem
            
        Regras:
        1. Produto composto → soma (preco_custo × quantidade) dos componentes
        2. Componentes não podem ser KIT nem PAI
        3. Se componente não tem custo, considera 0
        
        Exemplos:
            >>> custo = KitCustoService.calcular_custo_kit(kit_id=20, db=db, user_id=1)
            >>> # Retorna: Decimal('85.50')  # soma dos componentes
        """
        
        try:
            # ========================================
            # PASSO 1: BUSCAR E VALIDAR KIT
            # ========================================
            
            kit = db.query(Produto).filter(Produto.id == kit_id).first()
            
            if not kit:
                raise ValueError(f"Produto ID {kit_id} não encontrado")
            
            if not KitCustoService.produto_usa_custo_por_componentes(kit):
                raise ValueError(
                    f"Produto '{kit.nome}' não usa custo por composição "
                    f"(tipo: {kit.tipo_produto}, tipo_kit: {kit.tipo_kit})."
                )
            
            logger.info(
                f"📦 Calculando custo do produto composto: {kit.nome} "
                f"(ID: {kit_id}, tipo_kit: {kit.tipo_kit or 'VIRTUAL'})"
            )
            
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
                    Produto.id == componente.produto_componente_id
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
                f"✅ Custo total do produto composto: R$ {custo_total:.2f}"
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
    def sincronizar_custo_kit(db: Session, kit_id: int) -> Decimal:
        """
        Recalcula e persiste o preco_custo de um produto composto.

        Não faz commit. Usa flush para permitir composição com a transação atual.
        """
        kit = db.query(Produto).filter(Produto.id == kit_id).first()

        if not kit:
            raise ValueError(f"Produto ID {kit_id} não encontrado")

        if not KitCustoService.produto_usa_custo_por_componentes(kit):
            return Decimal(str(kit.preco_custo or 0))

        custo_total = KitCustoService.calcular_custo_kit(kit_id=kit_id, db=db)
        kit.preco_custo = float(custo_total)
        db.flush()

        logger.info(
            f"💰 Produto composto #{kit.id} sincronizado com preco_custo=R$ {custo_total:.2f}"
        )

        return custo_total

    @staticmethod
    def recalcular_kits_que_usam_produto(db: Session, produto_id: int) -> dict[int, Decimal]:
        """
        Recalcula o custo de todos os produtos compostos que usam um produto como componente.

        Não faz commit. Deixa a transação com o chamador.
        """
        componentes_kits = db.query(ProdutoKitComponente).filter(
            ProdutoKitComponente.produto_componente_id == produto_id
        ).all()

        resultado: dict[int, Decimal] = {}

        for comp in componentes_kits:
            kit = db.query(Produto).filter(Produto.id == comp.kit_id).first()
            if not KitCustoService.produto_usa_custo_por_componentes(kit):
                continue

            resultado[comp.kit_id] = KitCustoService.sincronizar_custo_kit(db, comp.kit_id)

        return resultado

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
