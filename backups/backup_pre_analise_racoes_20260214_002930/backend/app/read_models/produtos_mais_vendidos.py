"""
Produtos Mais Vendidos Read Model
==================================

Read Model que analisa eventos de produtos vendidos e fornece
insights sobre os produtos mais vendidos.

Funcionalidades:
- Top N produtos mais vendidos
- Agregação por quantidade ou valor
- Filtros por período, tenant, categoria
- Análise de tendências de vendas

Eventos consumidos:
- ProdutoVendidoEvent

NÃO persiste dados - trabalha apenas com eventos em memória.
"""

from typing import List, Dict, Optional
from datetime import datetime, timedelta
from collections import defaultdict

from app.events import ProdutoVendidoEvent
from .base_read_model import BaseReadModel


class ProdutosMaisVendidosReadModel(BaseReadModel):
    """
    Read Model para análise de produtos mais vendidos.
    
    Consome eventos de produtos vendidos e fornece agregações
    sobre os produtos mais populares.
    
    Uso:
    ```python
    read_model = ProdutosMaisVendidosReadModel()
    top10 = read_model.top_produtos(limit=10, user_id=1)
    ```
    """
    
    def top_produtos(
        self, 
        limit: int = 10,
        user_id: Optional[int] = None,
        por_valor: bool = False,
        dias: Optional[int] = None
    ) -> List[Dict]:
        """
        Retorna os produtos mais vendidos.
        
        Args:
            limit: Quantidade de produtos a retornar
            user_id: Filtrar por tenant (None = todos)
            por_valor: Se True, ordena por valor total; se False, por quantidade
            dias: Se fornecido, considera apenas últimos N dias
            
        Returns:
            Lista de dicts com:
            - produto_id: ID do produto
            - produto_nome: Nome do produto
            - tipo_produto: SIMPLES ou VARIACAO
            - quantidade_vendida: Total de unidades vendidas
            - valor_total: Valor total das vendas
            - numero_vendas: Quantidade de vendas que incluíram o produto
            - ticket_medio: Valor médio por venda
            - preco_medio: Preço médio praticado
        """
        # Obter eventos de produtos vendidos
        eventos = self.get_eventos_por_usuario(
            user_id=user_id,
            event_type=ProdutoVendidoEvent
        )
        
        # Filtrar por período se necessário
        if dias is not None:
            data_limite = datetime.now() - timedelta(days=dias)
            eventos = [e for e in eventos if e.timestamp >= data_limite]
        
        # Agregar dados por produto
        produtos_agregados = defaultdict(lambda: {
            'produto_id': 0,
            'produto_nome': '',
            'tipo_produto': '',
            'quantidade_vendida': 0.0,
            'valor_total': 0.0,
            'numero_vendas': 0,
            'vendas_ids': set()  # Para contar vendas únicas
        })
        
        for evento in eventos:
            produto_id = evento.produto_id
            dados = produtos_agregados[produto_id]
            
            # Dados básicos (primeira vez)
            if dados['produto_id'] == 0:
                dados['produto_id'] = evento.produto_id
                dados['produto_nome'] = evento.produto_nome
                dados['tipo_produto'] = evento.tipo_produto
            
            # Agregações
            dados['quantidade_vendida'] += evento.quantidade
            dados['valor_total'] += evento.preco_total
            
            # Contar vendas únicas
            if evento.venda_id not in dados['vendas_ids']:
                dados['vendas_ids'].add(evento.venda_id)
                dados['numero_vendas'] += 1
        
        # Calcular métricas derivadas e limpar vendas_ids
        resultado = []
        for produto_id, dados in produtos_agregados.items():
            numero_vendas = dados['numero_vendas']
            quantidade_vendida = dados['quantidade_vendida']
            valor_total = dados['valor_total']
            
            resultado.append({
                'produto_id': dados['produto_id'],
                'produto_nome': dados['produto_nome'],
                'tipo_produto': dados['tipo_produto'],
                'quantidade_vendida': round(quantidade_vendida, 2),
                'valor_total': round(valor_total, 2),
                'numero_vendas': numero_vendas,
                'ticket_medio': round(valor_total / numero_vendas, 2) if numero_vendas > 0 else 0.0,
                'preco_medio': round(valor_total / quantidade_vendida, 2) if quantidade_vendida > 0 else 0.0
            })
        
        # Ordenar
        if por_valor:
            resultado.sort(key=lambda x: x['valor_total'], reverse=True)
        else:
            resultado.sort(key=lambda x: x['quantidade_vendida'], reverse=True)
        
        # Limitar resultados
        return resultado[:limit]
    
    def produto_detalhado(
        self, 
        produto_id: int,
        user_id: Optional[int] = None,
        dias: Optional[int] = None
    ) -> Optional[Dict]:
        """
        Retorna análise detalhada de um produto específico.
        
        Args:
            produto_id: ID do produto
            user_id: Filtrar por tenant
            dias: Período de análise
            
        Returns:
            Dict com métricas detalhadas ou None se não houver vendas
        """
        # Obter eventos do produto
        eventos = self.get_eventos_por_usuario(
            user_id=user_id,
            event_type=ProdutoVendidoEvent
        )
        
        eventos = [e for e in eventos if e.produto_id == produto_id]
        
        # Filtrar por período
        if dias is not None:
            data_limite = datetime.now() - timedelta(days=dias)
            eventos = [e for e in eventos if e.timestamp >= data_limite]
        
        if not eventos:
            return None
        
        # Agregar dados
        quantidade_total = sum(e.quantidade for e in eventos)
        valor_total = sum(e.preco_total for e in eventos)
        vendas_unicas = len(set(e.venda_id for e in eventos))
        
        # Primeira e última venda
        eventos_ordenados = sorted(eventos, key=lambda e: e.timestamp)
        primeira_venda = eventos_ordenados[0]
        ultima_venda = eventos_ordenados[-1]
        
        return {
            'produto_id': produto_id,
            'produto_nome': primeira_venda.produto_nome,
            'tipo_produto': primeira_venda.tipo_produto,
            'quantidade_vendida': round(quantidade_total, 2),
            'valor_total': round(valor_total, 2),
            'numero_vendas': vendas_unicas,
            'ticket_medio': round(valor_total / vendas_unicas, 2) if vendas_unicas > 0 else 0.0,
            'preco_medio': round(valor_total / quantidade_total, 2) if quantidade_total > 0 else 0.0,
            'primeira_venda': primeira_venda.timestamp.isoformat(),
            'ultima_venda': ultima_venda.timestamp.isoformat(),
            'total_eventos': len(eventos)
        }
    
    def produtos_por_tipo(
        self,
        tipo_produto: str,
        limit: int = 10,
        user_id: Optional[int] = None,
        por_valor: bool = False
    ) -> List[Dict]:
        """
        Retorna produtos mais vendidos de um tipo específico.
        
        Args:
            tipo_produto: "SIMPLES" ou "VARIACAO"
            limit: Quantidade de produtos
            user_id: Filtrar por tenant
            por_valor: Ordenar por valor ou quantidade
            
        Returns:
            Lista de produtos do tipo especificado
        """
        todos_produtos = self.top_produtos(
            limit=1000,  # Pegar todos para filtrar
            user_id=user_id,
            por_valor=por_valor
        )
        
        # Filtrar por tipo
        produtos_filtrados = [
            p for p in todos_produtos 
            if p['tipo_produto'] == tipo_produto
        ]
        
        return produtos_filtrados[:limit]
