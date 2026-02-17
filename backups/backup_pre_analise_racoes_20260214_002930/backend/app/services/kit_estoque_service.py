"""
Serviço de Domínio para Cálculo de Estoque Virtual de KITs

⚠️ REGRA DE NEGÓCIO CRÍTICA:
================================

Para produtos do tipo KIT com tipo_kit='VIRTUAL':

    estoque_virtual_kit = MIN(
        estoque_componente / quantidade_necessaria
    )

Exemplo:
    Kit Banho = 2 Shampoos + 1 Condicionador + 3 Toalhas
    
    Shampoo: estoque=20 → 20/2 = 10 kits possíveis
    Condicionador: estoque=5 → 5/1 = 5 kits possíveis
    Toalha: estoque=30 → 30/3 = 10 kits possíveis
    
    Estoque Virtual do Kit = MIN(10, 5, 10) = 5 kits

⚠️ Este estoque NÃO é persistido no banco de dados.
⚠️ É sempre calculado em tempo real.
⚠️ Ao vender/movimentar componentes, o estoque virtual recalcula automaticamente.

Autor: Sistema ERP Pet Shop
Data: 2026-01-25
"""

from sqlalchemy.orm import Session
from typing import Dict, List, Optional
import logging
from ..produtos_models import Produto, ProdutoKitComponente

logger = logging.getLogger(__name__)


class KitEstoqueService:
    """
    Serviço de domínio responsável por calcular estoque virtual de produtos KIT.
    
    Não persiste dados - apenas calcula valores derivados.
    """
    
    @staticmethod
    def calcular_estoque_virtual_kit(db: Session, kit_id: int) -> int:
        """
        Calcula quantos kits podem ser montados com base no estoque dos componentes.
        
        Args:
            db: Sessão do banco de dados
            kit_id: ID do produto KIT
            
        Returns:
            int: Quantidade de kits que podem ser montados (estoque virtual)
            
        Raises:
            ValueError: Se o produto não for do tipo KIT
        """
        # Buscar o produto KIT
        kit = db.query(Produto).filter(Produto.id == kit_id).first()
        
        if not kit:
            logger.warning(f"Produto #{kit_id} não encontrado")
            return 0
        
        if kit.tipo_produto != 'KIT':
            raise ValueError(f"Produto #{kit_id} não é do tipo KIT (tipo atual: {kit.tipo_produto})")
        
        # Se for KIT FÍSICO, retornar estoque próprio
        if kit.tipo_kit == 'FISICO':
            return int(kit.estoque_atual or 0)
        
        # Buscar componentes do KIT
        componentes = db.query(ProdutoKitComponente).filter(
            ProdutoKitComponente.kit_id == kit_id
        ).all()
        
        if not componentes:
            logger.warning(f"Kit #{kit_id} não possui componentes cadastrados")
            return 0
        
        # Calcular quantos kits podem ser montados com cada componente
        kits_possiveis_por_componente = []
        
        for comp in componentes:
            produto_componente = db.query(Produto).filter(
                Produto.id == comp.produto_componente_id
            ).first()
            
            if not produto_componente:
                logger.error(f"Componente #{comp.produto_componente_id} não encontrado")
                return 0
            
            estoque_componente = produto_componente.estoque_atual or 0
            quantidade_necessaria = comp.quantidade or 1
            
            # Quantos kits podemos montar com este componente?
            kits_possiveis = int(estoque_componente // quantidade_necessaria)
            kits_possiveis_por_componente.append(kits_possiveis)
            
            logger.debug(
                f"Componente '{produto_componente.nome}': "
                f"estoque={estoque_componente}, "
                f"necessário={quantidade_necessaria}, "
                f"kits_possíveis={kits_possiveis}"
            )
        
        # O estoque virtual do kit é o MENOR valor (gargalo)
        estoque_virtual = min(kits_possiveis_por_componente) if kits_possiveis_por_componente else 0
        
        logger.info(
            f"Kit #{kit_id} '{kit.nome}': "
            f"estoque_virtual={estoque_virtual} "
            f"(componentes: {kits_possiveis_por_componente})"
        )
        
        return estoque_virtual
    
    @staticmethod
    def recalcular_kits_que_usam_produto(db: Session, produto_id: int) -> Dict[int, int]:
        """
        Recalcula estoque virtual de todos os KITs que utilizam um produto como componente.
        
        Útil para chamar após movimentações de estoque (vendas, entradas, ajustes).
        
        Args:
            db: Sessão do banco de dados
            produto_id: ID do produto componente que teve estoque alterado
            
        Returns:
            Dict[int, int]: Dicionário {kit_id: estoque_virtual}
        """
        # Buscar todos os kits que usam este produto como componente
        componentes_kits = db.query(ProdutoKitComponente).filter(
            ProdutoKitComponente.produto_componente_id == produto_id
        ).all()
        
        if not componentes_kits:
            logger.debug(f"Produto #{produto_id} não é usado em nenhum KIT")
            return {}
        
        # Recalcular estoque virtual de cada kit afetado
        resultado = {}
        for comp in componentes_kits:
            kit_id = comp.kit_id
            estoque_virtual = KitEstoqueService.calcular_estoque_virtual_kit(db, kit_id)
            resultado[kit_id] = estoque_virtual
            
            logger.info(
                f"Recalculado estoque do Kit #{kit_id}: "
                f"novo_estoque_virtual={estoque_virtual}"
            )
        
        return resultado
    
    @staticmethod
    def validar_componentes_kit(
        db: Session,
        kit_id: int,
        componentes: List[Dict]
    ) -> tuple[bool, Optional[str]]:
        """
        Valida se os componentes de um KIT são válidos.
        
        Regras:
        1. Componente deve existir
        2. Componente deve ser SIMPLES ou VARIACAO (não pode ser KIT ou PAI)
        3. Quantidade deve ser > 0
        4. Componente não pode ser o próprio KIT (evitar recursão)
        5. Não pode ter componente duplicado
        
        Args:
            db: Sessão do banco de dados
            kit_id: ID do KIT sendo criado/editado
            componentes: Lista de dicts com {produto_id, quantidade}
            
        Returns:
            tuple: (válido: bool, mensagem_erro: str ou None)
        """
        if not componentes:
            return False, "Kit deve ter pelo menos 1 componente"
        
        produto_ids_unicos = set()
        
        for idx, comp in enumerate(componentes):
            produto_id = comp.get('produto_componente_id') or comp.get('produto_id')
            quantidade = comp.get('quantidade', 0)
            
            # Validação 3: Quantidade > 0
            if quantidade <= 0:
                return False, f"Componente #{idx+1}: quantidade deve ser maior que 0"
            
            # Validação 4: Não pode ser o próprio KIT
            if produto_id == kit_id:
                return False, f"Componente #{idx+1}: KIT não pode conter a si mesmo (recursão não permitida)"
            
            # Validação 5: Não pode duplicar componente
            if produto_id in produto_ids_unicos:
                return False, f"Componente produto_id={produto_id} está duplicado"
            produto_ids_unicos.add(produto_id)
            
            # Validação 1: Componente existe?
            produto = db.query(Produto).filter(Produto.id == produto_id).first()
            if not produto:
                return False, f"Componente #{idx+1}: produto_id={produto_id} não encontrado"
            
            # Validação 2: Tipo do produto é válido?
            if produto.tipo_produto not in ('SIMPLES', 'VARIACAO'):
                return False, (
                    f"Componente '{produto.nome}': tipo_produto={produto.tipo_produto} inválido. "
                    f"Apenas produtos SIMPLES ou VARIACAO podem ser componentes de KIT."
                )
        
        return True, None
    
    @staticmethod
    def obter_detalhes_composicao(db: Session, kit_id: int) -> List[Dict]:
        """
        Retorna detalhes completos da composição de um KIT.
        
        Args:
            db: Sessão do banco de dados
            kit_id: ID do produto KIT
            
        Returns:
            Lista de dicts com dados completos de cada componente
        """
        componentes = db.query(ProdutoKitComponente).filter(
            ProdutoKitComponente.kit_id == kit_id
        ).all()
        
        resultado = []
        for comp in componentes:
            produto = db.query(Produto).filter(
                Produto.id == comp.produto_componente_id
            ).first()
            
            if produto:
                estoque_atual = produto.estoque_atual or 0
                kits_possiveis = int(estoque_atual // comp.quantidade)
                
                resultado.append({
                    'id': comp.id,
                    'produto_id': produto.id,
                    'produto_nome': produto.nome,
                    'produto_sku': produto.codigo,
                    'produto_tipo': produto.tipo_produto,
                    'quantidade': comp.quantidade,
                    'estoque_componente': estoque_atual,
                    'kits_possiveis': kits_possiveis,
                    'ordem': comp.ordem,
                    'opcional': comp.opcional,
                })
        
        return resultado
