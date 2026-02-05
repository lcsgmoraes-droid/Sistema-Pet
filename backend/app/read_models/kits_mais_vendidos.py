"""
Kits Mais Vendidos Read Model
==============================

Read Model que analisa eventos de kits vendidos e fornece
insights sobre os kits mais populares.

Funcionalidades:
- Top N kits mais vendidos
- Análise por tipo de kit (FÍSICO vs VIRTUAL)
- Agregação por quantidade ou valor
- Performance de componentes de kits

Eventos consumidos:
- KitVendidoEvent

NÃO persiste dados - trabalha apenas com eventos em memória.
"""

from typing import List, Dict, Optional
from datetime import datetime, timedelta
from collections import defaultdict

from app.events import KitVendidoEvent
from .base_read_model import BaseReadModel


class KitsMaisVendidosReadModel(BaseReadModel):
    """
    Read Model para análise de kits mais vendidos.
    
    Consome eventos de kits vendidos e fornece agregações
    sobre os kits mais populares.
    
    Uso:
    ```python
    read_model = KitsMaisVendidosReadModel()
    top10 = read_model.top_kits(limit=10, user_id=1)
    ```
    """
    
    def top_kits(
        self,
        limit: int = 10,
        user_id: Optional[int] = None,
        por_valor: bool = False,
        tipo_kit: Optional[str] = None,
        dias: Optional[int] = None
    ) -> List[Dict]:
        """
        Retorna os kits mais vendidos.
        
        Args:
            limit: Quantidade de kits a retornar
            user_id: Filtrar por tenant (None = todos)
            por_valor: Se True, ordena por valor total; se False, por quantidade
            tipo_kit: Filtrar por "FISICO" ou "VIRTUAL" (None = todos)
            dias: Se fornecido, considera apenas últimos N dias
            
        Returns:
            Lista de dicts com:
            - kit_id: ID do kit
            - kit_nome: Nome do kit
            - tipo_kit: FISICO ou VIRTUAL
            - quantidade_vendida: Total de kits vendidos
            - valor_total: Valor total das vendas
            - numero_vendas: Quantidade de vendas que incluíram o kit
            - ticket_medio: Valor médio por venda
            - preco_medio: Preço médio praticado
            - total_componentes_baixados: Total de componentes baixados
        """
        # Obter eventos de kits vendidos
        eventos = self.get_eventos_por_usuario(
            user_id=user_id,
            event_type=KitVendidoEvent
        )
        
        # Filtrar por tipo de kit
        if tipo_kit is not None:
            eventos = [e for e in eventos if e.tipo_kit == tipo_kit]
        
        # Filtrar por período se necessário
        if dias is not None:
            data_limite = datetime.now() - timedelta(days=dias)
            eventos = [e for e in eventos if e.timestamp >= data_limite]
        
        # Agregar dados por kit
        kits_agregados = defaultdict(lambda: {
            'kit_id': 0,
            'kit_nome': '',
            'tipo_kit': '',
            'quantidade_vendida': 0.0,
            'valor_total': 0.0,
            'numero_vendas': 0,
            'vendas_ids': set(),  # Para contar vendas únicas
            'total_componentes_baixados': 0
        })
        
        for evento in eventos:
            kit_id = evento.kit_id
            dados = kits_agregados[kit_id]
            
            # Dados básicos (primeira vez)
            if dados['kit_id'] == 0:
                dados['kit_id'] = evento.kit_id
                dados['kit_nome'] = evento.kit_nome
                dados['tipo_kit'] = evento.tipo_kit
            
            # Agregações
            dados['quantidade_vendida'] += evento.quantidade
            dados['valor_total'] += evento.preco_total
            dados['total_componentes_baixados'] += len(evento.componentes_baixados)
            
            # Contar vendas únicas
            if evento.venda_id not in dados['vendas_ids']:
                dados['vendas_ids'].add(evento.venda_id)
                dados['numero_vendas'] += 1
        
        # Calcular métricas derivadas e limpar vendas_ids
        resultado = []
        for kit_id, dados in kits_agregados.items():
            numero_vendas = dados['numero_vendas']
            quantidade_vendida = dados['quantidade_vendida']
            valor_total = dados['valor_total']
            
            resultado.append({
                'kit_id': dados['kit_id'],
                'kit_nome': dados['kit_nome'],
                'tipo_kit': dados['tipo_kit'],
                'quantidade_vendida': round(quantidade_vendida, 2),
                'valor_total': round(valor_total, 2),
                'numero_vendas': numero_vendas,
                'ticket_medio': round(valor_total / numero_vendas, 2) if numero_vendas > 0 else 0.0,
                'preco_medio': round(valor_total / quantidade_vendida, 2) if quantidade_vendida > 0 else 0.0,
                'total_componentes_baixados': dados['total_componentes_baixados']
            })
        
        # Ordenar
        if por_valor:
            resultado.sort(key=lambda x: x['valor_total'], reverse=True)
        else:
            resultado.sort(key=lambda x: x['quantidade_vendida'], reverse=True)
        
        # Limitar resultados
        return resultado[:limit]
    
    def kit_detalhado(
        self,
        kit_id: int,
        user_id: Optional[int] = None,
        dias: Optional[int] = None
    ) -> Optional[Dict]:
        """
        Retorna análise detalhada de um kit específico.
        
        Args:
            kit_id: ID do kit
            user_id: Filtrar por tenant
            dias: Período de análise
            
        Returns:
            Dict com métricas detalhadas ou None se não houver vendas
        """
        # Obter eventos do kit
        eventos = self.get_eventos_por_usuario(
            user_id=user_id,
            event_type=KitVendidoEvent
        )
        
        eventos = [e for e in eventos if e.kit_id == kit_id]
        
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
        total_componentes = sum(len(e.componentes_baixados) for e in eventos)
        
        # Primeira e última venda
        eventos_ordenados = sorted(eventos, key=lambda e: e.timestamp)
        primeira_venda = eventos_ordenados[0]
        ultima_venda = eventos_ordenados[-1]
        
        return {
            'kit_id': kit_id,
            'kit_nome': primeira_venda.kit_nome,
            'tipo_kit': primeira_venda.tipo_kit,
            'quantidade_vendida': round(quantidade_total, 2),
            'valor_total': round(valor_total, 2),
            'numero_vendas': vendas_unicas,
            'ticket_medio': round(valor_total / vendas_unicas, 2) if vendas_unicas > 0 else 0.0,
            'preco_medio': round(valor_total / quantidade_total, 2) if quantidade_total > 0 else 0.0,
            'total_componentes_baixados': total_componentes,
            'componentes_medio_por_kit': round(total_componentes / len(eventos), 2) if eventos else 0.0,
            'primeira_venda': primeira_venda.timestamp.isoformat(),
            'ultima_venda': ultima_venda.timestamp.isoformat(),
            'total_eventos': len(eventos)
        }
    
    def componentes_mais_vendidos_em_kits(
        self,
        limit: int = 10,
        user_id: Optional[int] = None,
        tipo_kit: Optional[str] = None
    ) -> List[Dict]:
        """
        Retorna os componentes que mais aparecem em kits vendidos.
        
        Útil para entender quais produtos são mais "movimentados" via kits.
        
        Args:
            limit: Quantidade de componentes a retornar
            user_id: Filtrar por tenant
            tipo_kit: Filtrar por tipo de kit
            
        Returns:
            Lista com componentes e suas métricas
        """
        # Obter eventos de kits
        eventos = self.get_eventos_por_usuario(
            user_id=user_id,
            event_type=KitVendidoEvent
        )
        
        # Filtrar por tipo
        if tipo_kit is not None:
            eventos = [e for e in eventos if e.tipo_kit == tipo_kit]
        
        # Agregar componentes
        componentes_agregados = defaultdict(lambda: {
            'produto_id': 0,
            'produto_nome': '',
            'quantidade_total': 0.0,
            'numero_kits': 0,
            'kits_ids': set()
        })
        
        for evento in eventos:
            for componente in evento.componentes_baixados:
                produto_id = componente.get('produto_id')
                if produto_id is None:
                    continue
                
                dados = componentes_agregados[produto_id]
                
                # Primeira vez
                if dados['produto_id'] == 0:
                    dados['produto_id'] = produto_id
                    dados['produto_nome'] = componente.get('nome', f'Produto {produto_id}')
                
                # Agregações
                dados['quantidade_total'] += componente.get('quantidade', 0.0)
                
                # Contar kits únicos
                if evento.kit_id not in dados['kits_ids']:
                    dados['kits_ids'].add(evento.kit_id)
                    dados['numero_kits'] += 1
        
        # Preparar resultado
        resultado = []
        for produto_id, dados in componentes_agregados.items():
            resultado.append({
                'produto_id': dados['produto_id'],
                'produto_nome': dados['produto_nome'],
                'quantidade_total': round(dados['quantidade_total'], 2),
                'numero_kits_diferentes': dados['numero_kits'],
                'quantidade_media_por_kit': round(
                    dados['quantidade_total'] / dados['numero_kits'], 2
                ) if dados['numero_kits'] > 0 else 0.0
            })
        
        # Ordenar por quantidade total
        resultado.sort(key=lambda x: x['quantidade_total'], reverse=True)
        
        return resultado[:limit]
    
    def kits_por_tipo(
        self,
        tipo_kit: str,
        limit: int = 10,
        user_id: Optional[int] = None,
        por_valor: bool = False
    ) -> List[Dict]:
        """
        Retorna kits mais vendidos de um tipo específico.
        
        Args:
            tipo_kit: "FISICO" ou "VIRTUAL"
            limit: Quantidade de kits
            user_id: Filtrar por tenant
            por_valor: Ordenar por valor ou quantidade
            
        Returns:
            Lista de kits do tipo especificado
        """
        return self.top_kits(
            limit=limit,
            user_id=user_id,
            por_valor=por_valor,
            tipo_kit=tipo_kit
        )
