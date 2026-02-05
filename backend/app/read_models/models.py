from app.base_models import BaseTenantModel
"""
Read Models - Modelos de Leitura CQRS
======================================

Modelos otimizados para consulta, derivados de eventos de domínio.

IMPORTANTE:
- Estes modelos são SOMENTE LEITURA do ponto de vista do domínio
- São atualizados exclusivamente por handlers de eventos
- Não devem ser modificados diretamente por serviços de negócio
- Podem ter índices otimizados para consultas específicas
"""

from sqlalchemy import Column, Integer, String, Float, Date, DateTime, DECIMAL, Index
from sqlalchemy.sql import func
from datetime import datetime
from app.db import Base


class VendasResumoDiario(BaseTenantModel):
    """
    Resumo agregado de vendas por dia.
    
    Atualizado pelos eventos:
    - VendaCriada: incrementa quantidade_aberta
    - VendaFinalizada: incrementa quantidade_finalizada, total_vendido
    - VendaCancelada: incrementa quantidade_cancelada, decrementa valores
    
    Casos de uso:
    - Dashboard gerencial
    - Gráficos de vendas diárias
    - Análise de tendências
    """
    __tablename__ = 'read_vendas_resumo_diario'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    data = Column(Date, nullable=False, unique=True, index=True)
    
    # Métricas agregadas
    quantidade_aberta = Column(Integer, default=0)
    quantidade_finalizada = Column(Integer, default=0)
    quantidade_cancelada = Column(Integer, default=0)
    
    total_vendido = Column(DECIMAL(10, 2), default=0)
    total_cancelado = Column(DECIMAL(10, 2), default=0)
    ticket_medio = Column(DECIMAL(10, 2), default=0)
    
    # Metadados
    atualizado_em = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Índice para otimizar consultas por período
    __table_args__ = (
        Index('idx_vendas_resumo_data', 'data'),
    )
    
    def calcular_ticket_medio(self):
        """Calcula o ticket médio baseado em vendas finalizadas"""
        if self.quantidade_finalizada > 0:
            self.ticket_medio = self.total_vendido / self.quantidade_finalizada
        else:
            self.ticket_medio = 0
    
    def to_dict(self):
        """Serialização para API"""
        return {
            'data': self.data.isoformat() if self.data else None,
            'quantidade_aberta': self.quantidade_aberta,
            'quantidade_finalizada': self.quantidade_finalizada,
            'quantidade_cancelada': self.quantidade_cancelada,
            'total_vendido': float(self.total_vendido),
            'total_cancelado': float(self.total_cancelado),
            'ticket_medio': float(self.ticket_medio),
            'atualizado_em': self.atualizado_em.isoformat() if self.atualizado_em else None
        }


class PerformanceParceiro(BaseTenantModel):
    """
    Métricas de desempenho por parceiro/funcionário.
    
    Atualizado pelos eventos:
    - VendaFinalizada: incrementa vendas e comissões
    - VendaCancelada: ajusta métricas
    
    Casos de uso:
    - Ranking de vendedores
    - Dashboard de performance
    - Cálculo de bonificações
    - Análise de produtividade
    """
    __tablename__ = 'read_performance_parceiro'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    funcionario_id = Column(Integer, nullable=False, index=True)
    mes_referencia = Column(Date, nullable=False, index=True)  # Primeiro dia do mês
    
    # Métricas de vendas
    quantidade_vendas = Column(Integer, default=0)
    total_vendido = Column(DECIMAL(10, 2), default=0)
    ticket_medio = Column(DECIMAL(10, 2), default=0)
    
    # Métricas de qualidade
    taxa_cancelamento = Column(DECIMAL(5, 2), default=0)  # Percentual
    vendas_canceladas = Column(Integer, default=0)
    
    # Ranking
    ranking_mes = Column(Integer, nullable=True)  # Posição no ranking mensal
    
    # Metadados
    atualizado_em = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Índices compostos para otimizar consultas
    __table_args__ = (
        Index('idx_perf_func_mes', 'funcionario_id', 'mes_referencia'),
        Index('idx_perf_mes_ranking', 'mes_referencia', 'ranking_mes'),
    )
    
    def calcular_metricas(self):
        """Recalcula métricas derivadas"""
        # Ticket médio
        if self.quantidade_vendas > 0:
            self.ticket_medio = self.total_vendido / self.quantidade_vendas
        else:
            self.ticket_medio = 0
        
        # Taxa de cancelamento
        total_operacoes = self.quantidade_vendas + self.vendas_canceladas
        if total_operacoes > 0:
            self.taxa_cancelamento = (self.vendas_canceladas / total_operacoes) * 100
        else:
            self.taxa_cancelamento = 0
    
    def to_dict(self):
        """Serialização para API"""
        return {
            'funcionario_id': self.funcionario_id,
            'mes_referencia': self.mes_referencia.isoformat() if self.mes_referencia else None,
            'quantidade_vendas': self.quantidade_vendas,
            'total_vendido': float(self.total_vendido),
            'ticket_medio': float(self.ticket_medio),
            'taxa_cancelamento': float(self.taxa_cancelamento),
            'vendas_canceladas': self.vendas_canceladas,
            'ranking_mes': self.ranking_mes,
            'atualizado_em': self.atualizado_em.isoformat() if self.atualizado_em else None
        }


class ReceitaMensal(BaseTenantModel):
    """
    Agregação de receita por mês.
    
    Atualizado pelos eventos:
    - VendaFinalizada: adiciona receita
    - VendaCancelada: subtrai receita
    
    Casos de uso:
    - Planejamento financeiro
    - Projeções de receita
    - Relatórios gerenciais
    - Análise de crescimento
    """
    __tablename__ = 'read_receita_mensal'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    mes_referencia = Column(Date, nullable=False, unique=True, index=True)  # Primeiro dia do mês
    
    # Métricas financeiras
    receita_bruta = Column(DECIMAL(12, 2), default=0)
    receita_cancelada = Column(DECIMAL(12, 2), default=0)
    receita_liquida = Column(DECIMAL(12, 2), default=0)
    
    # Métricas operacionais
    quantidade_vendas = Column(Integer, default=0)
    quantidade_cancelamentos = Column(Integer, default=0)
    ticket_medio = Column(DECIMAL(10, 2), default=0)
    
    # Comparativo
    variacao_percentual = Column(DECIMAL(5, 2), nullable=True)  # Em relação ao mês anterior
    
    # Metadados
    atualizado_em = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Índice para ordenação cronológica
    __table_args__ = (
        Index('idx_receita_mes', 'mes_referencia'),
    )
    
    def calcular_metricas(self):
        """Recalcula métricas derivadas"""
        # Receita líquida
        self.receita_liquida = self.receita_bruta - self.receita_cancelada
        
        # Ticket médio
        if self.quantidade_vendas > 0:
            self.ticket_medio = self.receita_bruta / self.quantidade_vendas
        else:
            self.ticket_medio = 0
    
    def to_dict(self):
        """Serialização para API"""
        return {
            'mes_referencia': self.mes_referencia.isoformat() if self.mes_referencia else None,
            'receita_bruta': float(self.receita_bruta),
            'receita_cancelada': float(self.receita_cancelada),
            'receita_liquida': float(self.receita_liquida),
            'quantidade_vendas': self.quantidade_vendas,
            'quantidade_cancelamentos': self.quantidade_cancelamentos,
            'ticket_medio': float(self.ticket_medio),
            'variacao_percentual': float(self.variacao_percentual) if self.variacao_percentual else None,
            'atualizado_em': self.atualizado_em.isoformat() if self.atualizado_em else None
        }
