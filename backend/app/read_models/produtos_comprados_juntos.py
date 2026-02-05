"""
Produtos Comprados Juntos Read Model
=====================================

Read Model que analisa padrões de compra para identificar produtos
frequentemente comprados juntos (Market Basket Analysis).

Funcionalidades:
- Produtos comprados juntos com um produto específico
- Produtos que aparecem juntos em vendas
- Análise de correlação entre produtos
- Sugestões de cross-sell

Eventos consumidos:
- VendaRealizadaEvent
- ProdutoVendidoEvent

Algoritmo:
1. Identifica todas as vendas que contêm um produto específico
2. Lista todos os outros produtos vendidos nessas vendas
3. Conta frequência de co-ocorrência
4. Ordena por frequência

NÃO persiste dados - trabalha apenas com eventos em memória.
"""

from typing import List, Dict, Optional, Set
from datetime import datetime, timedelta
from collections import defaultdict

from app.events import VendaRealizadaEvent, ProdutoVendidoEvent
from .base_read_model import BaseReadModel


class ProdutosCompradosJuntosReadModel(BaseReadModel):
    """
    Read Model para análise de produtos comprados juntos.
    
    Identifica padrões de compra e produtos que costumam
    ser vendidos em conjunto.
    
    Uso:
    ```python
    read_model = ProdutosCompradosJuntosReadModel()
    sugestoes = read_model.produtos_comprados_juntos(produto_id=123, limit=5)
    ```
    """
    
    def produtos_comprados_juntos(
        self,
        produto_id: int,
        limit: int = 10,
        user_id: Optional[int] = None,
        dias: Optional[int] = None,
        min_ocorrencias: int = 2
    ) -> List[Dict]:
        """
        Retorna produtos frequentemente comprados junto com um produto específico.
        
        Args:
            produto_id: ID do produto de referência
            limit: Quantidade de sugestões a retornar
            user_id: Filtrar por tenant
            dias: Considerar apenas últimos N dias
            min_ocorrencias: Mínimo de co-ocorrências para considerar
            
        Returns:
            Lista de dicts com:
            - produto_id: ID do produto sugerido
            - produto_nome: Nome do produto
            - tipo_produto: SIMPLES ou VARIACAO
            - frequencia: Quantas vezes apareceu junto
            - confianca: % de vendas do produto original que incluem este
            - valor_medio_combinado: Valor médio quando vendidos juntos
        """
        # Obter eventos de produtos vendidos
        eventos_produtos = self.get_eventos_por_usuario(
            user_id=user_id,
            event_type=ProdutoVendidoEvent
        )
        
        # Filtrar por período
        if dias is not None:
            data_limite = datetime.now() - timedelta(days=dias)
            eventos_produtos = [e for e in eventos_produtos if e.timestamp >= data_limite]
        
        # Identificar vendas que contêm o produto de referência
        vendas_com_produto = set()
        for evento in eventos_produtos:
            if evento.produto_id == produto_id:
                vendas_com_produto.add(evento.venda_id)
        
        if not vendas_com_produto:
            return []
        
        # Contar co-ocorrências de outros produtos nessas vendas
        co_ocorrencias = defaultdict(lambda: {
            'produto_id': 0,
            'produto_nome': '',
            'tipo_produto': '',
            'frequencia': 0,
            'vendas_ids': set(),
            'valores_combinados': []
        })
        
        for evento in eventos_produtos:
            # Pular o próprio produto de referência
            if evento.produto_id == produto_id:
                continue
            
            # Verificar se está em uma venda com o produto de referência
            if evento.venda_id in vendas_com_produto:
                dados = co_ocorrencias[evento.produto_id]
                
                # Primeira vez
                if dados['produto_id'] == 0:
                    dados['produto_id'] = evento.produto_id
                    dados['produto_nome'] = evento.produto_nome
                    dados['tipo_produto'] = evento.tipo_produto
                
                # Contar vendas únicas
                if evento.venda_id not in dados['vendas_ids']:
                    dados['vendas_ids'].add(evento.venda_id)
                    dados['frequencia'] += 1
                
                # Coletar valores para média
                dados['valores_combinados'].append(evento.preco_total)
        
        # Preparar resultado
        resultado = []
        total_vendas_produto = len(vendas_com_produto)
        
        for produto_id_sugestao, dados in co_ocorrencias.items():
            frequencia = dados['frequencia']
            
            # Filtrar por mínimo de ocorrências
            if frequencia < min_ocorrencias:
                continue
            
            # Calcular confiança (% de vendas do produto original que incluem este)
            confianca = (frequencia / total_vendas_produto) * 100
            
            # Valor médio combinado
            valores = dados['valores_combinados']
            valor_medio = sum(valores) / len(valores) if valores else 0.0
            
            resultado.append({
                'produto_id': dados['produto_id'],
                'produto_nome': dados['produto_nome'],
                'tipo_produto': dados['tipo_produto'],
                'frequencia': frequencia,
                'confianca': round(confianca, 2),
                'valor_medio_combinado': round(valor_medio, 2),
                'total_vendas_produto_original': total_vendas_produto
            })
        
        # Ordenar por frequência (ou confiança)
        resultado.sort(key=lambda x: x['frequencia'], reverse=True)
        
        return resultado[:limit]
    
    def produtos_que_aparecem_juntos(
        self,
        limit: int = 10,
        user_id: Optional[int] = None,
        dias: Optional[int] = None,
        min_ocorrencias: int = 3
    ) -> List[Dict]:
        """
        Retorna pares de produtos que frequentemente aparecem juntos.
        
        Útil para identificar combos naturais de produtos.
        
        Args:
            limit: Quantidade de pares a retornar
            user_id: Filtrar por tenant
            dias: Período de análise
            min_ocorrencias: Mínimo de co-ocorrências
            
        Returns:
            Lista de pares de produtos com frequência
        """
        # Obter eventos de produtos
        eventos_produtos = self.get_eventos_por_usuario(
            user_id=user_id,
            event_type=ProdutoVendidoEvent
        )
        
        # Filtrar por período
        if dias is not None:
            data_limite = datetime.now() - timedelta(days=dias)
            eventos_produtos = [e for e in eventos_produtos if e.timestamp >= data_limite]
        
        # Agrupar produtos por venda
        vendas_produtos = defaultdict(list)
        produtos_info = {}  # Cache de info dos produtos
        
        for evento in eventos_produtos:
            vendas_produtos[evento.venda_id].append(evento.produto_id)
            
            # Guardar info do produto
            if evento.produto_id not in produtos_info:
                produtos_info[evento.produto_id] = {
                    'nome': evento.produto_nome,
                    'tipo': evento.tipo_produto
                }
        
        # Contar pares de produtos
        pares = defaultdict(int)
        
        for venda_id, produtos_ids in vendas_produtos.items():
            # Apenas vendas com 2+ produtos
            if len(produtos_ids) < 2:
                continue
            
            # Gerar todos os pares únicos
            produtos_unicos = set(produtos_ids)
            for i, prod1 in enumerate(sorted(produtos_unicos)):
                for prod2 in sorted(list(produtos_unicos)[i+1:]):
                    # Ordenar para evitar duplicatas (A,B) vs (B,A)
                    par = tuple(sorted([prod1, prod2]))
                    pares[par] += 1
        
        # Preparar resultado
        resultado = []
        for (prod1_id, prod2_id), frequencia in pares.items():
            if frequencia < min_ocorrencias:
                continue
            
            resultado.append({
                'produto1_id': prod1_id,
                'produto1_nome': produtos_info.get(prod1_id, {}).get('nome', f'Produto {prod1_id}'),
                'produto2_id': prod2_id,
                'produto2_nome': produtos_info.get(prod2_id, {}).get('nome', f'Produto {prod2_id}'),
                'frequencia': frequencia
            })
        
        # Ordenar por frequência
        resultado.sort(key=lambda x: x['frequencia'], reverse=True)
        
        return resultado[:limit]
    
    def analise_cesta_venda(
        self,
        venda_id: int,
        user_id: Optional[int] = None
    ) -> Dict:
        """
        Analisa os produtos de uma venda específica e sugere complementos.
        
        Args:
            venda_id: ID da venda
            user_id: Filtrar por tenant
            
        Returns:
            Dict com produtos da venda e sugestões de cross-sell
        """
        # Obter eventos da venda
        eventos_venda = self.get_eventos_por_venda(venda_id)
        
        # Filtrar apenas produtos (não kits por enquanto)
        from app.events import ProdutoVendidoEvent
        produtos_venda = [
            e for e in eventos_venda 
            if isinstance(e, ProdutoVendidoEvent)
        ]
        
        if not produtos_venda:
            return {
                'venda_id': venda_id,
                'produtos': [],
                'sugestoes': []
            }
        
        # Listar produtos da venda
        produtos_na_venda = []
        produtos_ids = set()
        
        for evento in produtos_venda:
            produtos_ids.add(evento.produto_id)
            produtos_na_venda.append({
                'produto_id': evento.produto_id,
                'produto_nome': evento.produto_nome,
                'quantidade': evento.quantidade,
                'preco_total': evento.preco_total
            })
        
        # Coletar sugestões para cada produto
        todas_sugestoes = []
        for produto_id in produtos_ids:
            sugestoes_produto = self.produtos_comprados_juntos(
                produto_id=produto_id,
                limit=5,
                user_id=user_id,
                min_ocorrencias=1
            )
            
            # Filtrar produtos que já estão na venda
            sugestoes_filtradas = [
                s for s in sugestoes_produto 
                if s['produto_id'] not in produtos_ids
            ]
            
            todas_sugestoes.extend(sugestoes_filtradas)
        
        # Consolidar sugestões (remover duplicatas, somar scores)
        sugestoes_consolidadas = defaultdict(lambda: {
            'produto_id': 0,
            'produto_nome': '',
            'score_total': 0,
            'frequencia_total': 0
        })
        
        for sugestao in todas_sugestoes:
            produto_id = sugestao['produto_id']
            dados = sugestoes_consolidadas[produto_id]
            
            if dados['produto_id'] == 0:
                dados['produto_id'] = produto_id
                dados['produto_nome'] = sugestao['produto_nome']
            
            dados['score_total'] += sugestao['confianca']
            dados['frequencia_total'] += sugestao['frequencia']
        
        # Preparar lista final de sugestões
        sugestoes_finais = []
        for dados in sugestoes_consolidadas.values():
            sugestoes_finais.append({
                'produto_id': dados['produto_id'],
                'produto_nome': dados['produto_nome'],
                'score': round(dados['score_total'], 2),
                'frequencia': dados['frequencia_total']
            })
        
        # Ordenar por score
        sugestoes_finais.sort(key=lambda x: x['score'], reverse=True)
        
        return {
            'venda_id': venda_id,
            'produtos': produtos_na_venda,
            'sugestoes': sugestoes_finais[:10]
        }
