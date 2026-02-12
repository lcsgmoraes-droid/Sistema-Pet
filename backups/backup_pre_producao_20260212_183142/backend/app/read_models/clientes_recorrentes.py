"""
Clientes Recorrentes Read Model
================================

Read Model que analisa padrões de compra de clientes para
identificar clientes recorrentes e sua frequência de compras.

Funcionalidades:
- Identificar clientes recorrentes (múltiplas compras)
- Análise de frequência de compras
- Lifetime value (LTV) por cliente
- Identificar clientes em risco de churn

Eventos consumidos:
- VendaRealizadaEvent

NÃO persiste dados - trabalha apenas com eventos em memória.
"""

from typing import List, Dict, Optional
from datetime import datetime, timedelta
from collections import defaultdict

from app.events import VendaRealizadaEvent
from .base_read_model import BaseReadModel


class ClientesRecorrentesReadModel(BaseReadModel):
    """
    Read Model para análise de clientes recorrentes.
    
    Identifica padrões de compra de clientes e métricas
    de recorrência.
    
    Uso:
    ```python
    read_model = ClientesRecorrentesReadModel()
    clientes = read_model.clientes_recorrentes(dias=30, user_id=1)
    ```
    """
    
    def clientes_recorrentes(
        self,
        dias: int = 30,
        user_id: Optional[int] = None,
        min_compras: int = 2,
        limit: Optional[int] = None
    ) -> List[Dict]:
        """
        Retorna clientes que fizeram múltiplas compras no período.
        
        Args:
            dias: Período de análise (últimos N dias)
            user_id: Filtrar por tenant
            min_compras: Mínimo de compras para considerar recorrente
            limit: Limitar quantidade de resultados
            
        Returns:
            Lista de dicts com:
            - cliente_id: ID do cliente (pode ser None para vendas sem cliente)
            - numero_compras: Quantidade de compras no período
            - valor_total: Valor total gasto
            - ticket_medio: Valor médio por compra
            - primeira_compra: Data da primeira compra
            - ultima_compra: Data da última compra
            - dias_entre_compras: Média de dias entre compras
            - recencia: Dias desde última compra
        """
        # Obter eventos de vendas
        eventos = self.get_eventos_por_usuario(
            user_id=user_id,
            event_type=VendaRealizadaEvent
        )
        
        # Filtrar por período
        data_limite = datetime.now() - timedelta(days=dias)
        eventos = [e for e in eventos if e.timestamp >= data_limite]
        
        # Agregar por cliente
        clientes_agregados = defaultdict(lambda: {
            'cliente_id': None,
            'vendas': [],
            'valor_total': 0.0
        })
        
        for evento in eventos:
            cliente_id = evento.cliente_id
            
            # Pular vendas sem cliente identificado se quisermos apenas clientes conhecidos
            # (Comentado para incluir vendas sem cliente também)
            # if cliente_id is None:
            #     continue
            
            dados = clientes_agregados[cliente_id]
            dados['cliente_id'] = cliente_id
            dados['vendas'].append({
                'venda_id': evento.venda_id,
                'timestamp': evento.timestamp,
                'total': evento.total
            })
            dados['valor_total'] += evento.total
        
        # Calcular métricas e filtrar
        resultado = []
        data_atual = datetime.now()
        
        for cliente_id, dados in clientes_agregados.items():
            vendas = dados['vendas']
            numero_compras = len(vendas)
            
            # Filtrar por mínimo de compras
            if numero_compras < min_compras:
                continue
            
            # Ordenar vendas por data
            vendas_ordenadas = sorted(vendas, key=lambda v: v['timestamp'])
            
            primeira_compra = vendas_ordenadas[0]['timestamp']
            ultima_compra = vendas_ordenadas[-1]['timestamp']
            
            # Calcular dias entre compras
            if numero_compras > 1:
                total_dias = (ultima_compra - primeira_compra).days
                dias_entre_compras = total_dias / (numero_compras - 1) if numero_compras > 1 else 0
            else:
                dias_entre_compras = 0
            
            # Recência (dias desde última compra)
            recencia = (data_atual - ultima_compra).days
            
            resultado.append({
                'cliente_id': cliente_id,
                'numero_compras': numero_compras,
                'valor_total': round(dados['valor_total'], 2),
                'ticket_medio': round(dados['valor_total'] / numero_compras, 2),
                'primeira_compra': primeira_compra.isoformat(),
                'ultima_compra': ultima_compra.isoformat(),
                'dias_entre_compras': round(dias_entre_compras, 1),
                'recencia': recencia,
                'periodo_ativo_dias': (ultima_compra - primeira_compra).days
            })
        
        # Ordenar por número de compras (mais recorrentes primeiro)
        resultado.sort(key=lambda x: x['numero_compras'], reverse=True)
        
        # Limitar se necessário
        if limit is not None:
            resultado = resultado[:limit]
        
        return resultado
    
    def cliente_detalhado(
        self,
        cliente_id: int,
        user_id: Optional[int] = None,
        dias: Optional[int] = None
    ) -> Optional[Dict]:
        """
        Retorna análise detalhada de um cliente específico.
        
        Args:
            cliente_id: ID do cliente
            user_id: Filtrar por tenant
            dias: Período de análise (None = todos os tempos)
            
        Returns:
            Dict com métricas detalhadas ou None se não houver compras
        """
        # Obter eventos de vendas
        eventos = self.get_eventos_por_usuario(
            user_id=user_id,
            event_type=VendaRealizadaEvent
        )
        
        # Filtrar por cliente
        eventos = [e for e in eventos if e.cliente_id == cliente_id]
        
        # Filtrar por período
        if dias is not None:
            data_limite = datetime.now() - timedelta(days=dias)
            eventos = [e for e in eventos if e.timestamp >= data_limite]
        
        if not eventos:
            return None
        
        # Ordenar por data
        eventos_ordenados = sorted(eventos, key=lambda e: e.timestamp)
        
        # Métricas básicas
        numero_compras = len(eventos)
        valor_total = sum(e.total for e in eventos)
        primeira_compra = eventos_ordenados[0]
        ultima_compra = eventos_ordenados[-1]
        
        # Frequência de compras
        total_dias = (ultima_compra.timestamp - primeira_compra.timestamp).days
        dias_entre_compras = total_dias / (numero_compras - 1) if numero_compras > 1 else 0
        
        # Recência
        recencia = (datetime.now() - ultima_compra.timestamp).days
        
        # Análise de formas de pagamento
        formas_pagamento = defaultdict(int)
        for evento in eventos:
            formas_pagamento[evento.forma_pagamento] += 1
        
        # Vendas com e sem vendedor/funcionário
        com_vendedor = sum(1 for e in eventos if e.vendedor_id is not None)
        com_funcionario = sum(1 for e in eventos if e.funcionario_id is not None)
        
        # Vendas com kit
        vendas_com_kit = sum(1 for e in eventos if e.tem_kit)
        
        return {
            'cliente_id': cliente_id,
            'numero_compras': numero_compras,
            'valor_total': round(valor_total, 2),
            'ticket_medio': round(valor_total / numero_compras, 2),
            'primeira_compra': primeira_compra.timestamp.isoformat(),
            'ultima_compra': ultima_compra.timestamp.isoformat(),
            'dias_entre_compras': round(dias_entre_compras, 1),
            'recencia': recencia,
            'periodo_ativo_dias': total_dias,
            'formas_pagamento_favoritas': dict(formas_pagamento),
            'vendas_com_vendedor': com_vendedor,
            'vendas_com_funcionario': com_funcionario,
            'vendas_com_kit': vendas_com_kit,
            'percentual_vendas_kit': round((vendas_com_kit / numero_compras) * 100, 2)
        }
    
    def clientes_em_risco_churn(
        self,
        dias_inatividade: int = 60,
        user_id: Optional[int] = None,
        min_compras_historico: int = 2
    ) -> List[Dict]:
        """
        Identifica clientes recorrentes que não compram há muito tempo.
        
        Clientes em risco de churn são aqueles que:
        - Já compraram múltiplas vezes (são recorrentes)
        - Não compram há X dias (período de inatividade)
        
        Args:
            dias_inatividade: Dias sem comprar para considerar em risco
            user_id: Filtrar por tenant
            min_compras_historico: Mínimo de compras históricas
            
        Returns:
            Lista de clientes em risco com suas métricas
        """
        # Obter eventos de vendas (todo o histórico)
        eventos = self.get_eventos_por_usuario(
            user_id=user_id,
            event_type=VendaRealizadaEvent
        )
        
        # Agregar por cliente
        clientes_agregados = defaultdict(lambda: {
            'cliente_id': None,
            'numero_compras': 0,
            'ultima_compra': None,
            'valor_total': 0.0
        })
        
        for evento in eventos:
            cliente_id = evento.cliente_id
            if cliente_id is None:
                continue
            
            dados = clientes_agregados[cliente_id]
            dados['cliente_id'] = cliente_id
            dados['numero_compras'] += 1
            dados['valor_total'] += evento.total
            
            # Atualizar última compra
            if dados['ultima_compra'] is None or evento.timestamp > dados['ultima_compra']:
                dados['ultima_compra'] = evento.timestamp
        
        # Filtrar e preparar resultado
        resultado = []
        data_atual = datetime.now()
        limite_inatividade = data_atual - timedelta(days=dias_inatividade)
        
        for cliente_id, dados in clientes_agregados.items():
            # Deve ter histórico de compras
            if dados['numero_compras'] < min_compras_historico:
                continue
            
            # Última compra deve ser antes do limite de inatividade
            if dados['ultima_compra'] > limite_inatividade:
                continue
            
            dias_sem_comprar = (data_atual - dados['ultima_compra']).days
            
            resultado.append({
                'cliente_id': cliente_id,
                'numero_compras_historico': dados['numero_compras'],
                'valor_total_historico': round(dados['valor_total'], 2),
                'ticket_medio': round(dados['valor_total'] / dados['numero_compras'], 2),
                'ultima_compra': dados['ultima_compra'].isoformat(),
                'dias_sem_comprar': dias_sem_comprar,
                'risco_nivel': self._calcular_nivel_risco(dias_sem_comprar, dias_inatividade)
            })
        
        # Ordenar por dias sem comprar (mais tempo = maior risco)
        resultado.sort(key=lambda x: x['dias_sem_comprar'], reverse=True)
        
        return resultado
    
    def _calcular_nivel_risco(self, dias_sem_comprar: int, limite: int) -> str:
        """
        Calcula o nível de risco de churn baseado nos dias sem comprar.
        
        Args:
            dias_sem_comprar: Dias desde última compra
            limite: Limite mínimo para considerar em risco
            
        Returns:
            "BAIXO", "MEDIO" ou "ALTO"
        """
        if dias_sem_comprar >= limite * 2:
            return "ALTO"
        elif dias_sem_comprar >= limite * 1.5:
            return "MEDIO"
        else:
            return "BAIXO"
    
    def rfm_analise(
        self,
        user_id: Optional[int] = None,
        dias: int = 90
    ) -> List[Dict]:
        """
        Análise RFM (Recency, Frequency, Monetary) dos clientes.
        
        Segmenta clientes em categorias baseado em:
        - R (Recency): Quão recentemente compraram
        - F (Frequency): Quantas vezes compraram
        - M (Monetary): Quanto gastaram
        
        Args:
            user_id: Filtrar por tenant
            dias: Período de análise
            
        Returns:
            Lista de clientes com scores RFM
        """
        # Obter clientes recorrentes
        clientes = self.clientes_recorrentes(
            dias=dias,
            user_id=user_id,
            min_compras=1  # Incluir todos
        )
        
        if not clientes:
            return []
        
        # Calcular quartis para cada métrica
        recencias = [c['recencia'] for c in clientes]
        frequencias = [c['numero_compras'] for c in clientes]
        monetarios = [c['valor_total'] for c in clientes]
        
        # Calcular scores (1-5, sendo 5 o melhor)
        for cliente in clientes:
            # Recency: menor é melhor (invertido)
            r_score = self._calcular_score_invertido(cliente['recencia'], recencias)
            
            # Frequency: maior é melhor
            f_score = self._calcular_score(cliente['numero_compras'], frequencias)
            
            # Monetary: maior é melhor
            m_score = self._calcular_score(cliente['valor_total'], monetarios)
            
            cliente['r_score'] = r_score
            cliente['f_score'] = f_score
            cliente['m_score'] = m_score
            cliente['rfm_score'] = f"{r_score}{f_score}{m_score}"
            cliente['segmento'] = self._determinar_segmento(r_score, f_score, m_score)
        
        return clientes
    
    def _calcular_score(self, valor: float, valores: List[float]) -> int:
        """Calcula score de 1-5 baseado em quartis (maior é melhor)"""
        valores_sorted = sorted(valores)
        if valor >= valores_sorted[int(len(valores_sorted) * 0.8)]:
            return 5
        elif valor >= valores_sorted[int(len(valores_sorted) * 0.6)]:
            return 4
        elif valor >= valores_sorted[int(len(valores_sorted) * 0.4)]:
            return 3
        elif valor >= valores_sorted[int(len(valores_sorted) * 0.2)]:
            return 2
        else:
            return 1
    
    def _calcular_score_invertido(self, valor: float, valores: List[float]) -> int:
        """Calcula score de 1-5 baseado em quartis (menor é melhor)"""
        valores_sorted = sorted(valores, reverse=True)
        if valor >= valores_sorted[int(len(valores_sorted) * 0.8)]:
            return 1
        elif valor >= valores_sorted[int(len(valores_sorted) * 0.6)]:
            return 2
        elif valor >= valores_sorted[int(len(valores_sorted) * 0.4)]:
            return 3
        elif valor >= valores_sorted[int(len(valores_sorted) * 0.2)]:
            return 4
        else:
            return 5
    
    def _determinar_segmento(self, r: int, f: int, m: int) -> str:
        """
        Determina segmento do cliente baseado em scores RFM.
        
        Segmentos:
        - CAMPEOES: RFM alto
        - LEAIS: RF alto, M médio
        - POTENCIAL: R alto, FM médio/baixo
        - EM_RISCO: R baixo, FM alto
        - PERDIDOS: RFM baixo
        """
        if r >= 4 and f >= 4 and m >= 4:
            return "CAMPEOES"
        elif r >= 4 and f >= 3:
            return "LEAIS"
        elif r >= 4:
            return "POTENCIAL"
        elif f >= 3 and m >= 3:
            return "EM_RISCO"
        else:
            return "PERDIDOS"
