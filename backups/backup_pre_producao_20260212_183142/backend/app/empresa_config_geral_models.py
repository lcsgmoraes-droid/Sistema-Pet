"""
Modelo de Configuração Geral da Empresa
Contém parâmetros de negócio, margens e indicadores
"""

from sqlalchemy import Column, Integer, String, Numeric, Boolean, DateTime, Text
from sqlalchemy.sql import func
from datetime import datetime
from .db import Base
from .base_models import BaseTenantModel


class EmpresaConfigGeral(BaseTenantModel):
    """
    Configuração geral da empresa (multi-tenant)
    Define parâmetros de negócio, margens e indicadores
    """
    __tablename__ = "empresa_config_geral"

    # ID, tenant_id, created_at e updated_at já vêm do BaseTenantModel

    # ============================
    # DADOS BÁSICOS
    # ============================
    razao_social = Column(String(200))
    nome_fantasia = Column(String(200))
    cnpj = Column(String(18))
    inscricao_estadual = Column(String(20))
    inscricao_municipal = Column(String(20))
    
    # Endereço
    logradouro = Column(String(200))
    numero = Column(String(20))
    complemento = Column(String(100))
    bairro = Column(String(100))
    cidade = Column(String(100))
    uf = Column(String(2))
    cep = Column(String(10))
    
    # Contato
    telefone = Column(String(20))
    email = Column(String(100))
    site = Column(String(100))
    
    # ============================
    # PARÂMETROS DE MARGEM (PDV)
    # ============================
    # Define os limites de margem para classificar vendas
    margem_saudavel_minima = Column(Numeric(5, 2), default=30.0)  # % mínima para ser "saudável"
    margem_alerta_minima = Column(Numeric(5, 2), default=15.0)     # % mínima para ser "alerta" (abaixo é "crítico")
    
    # Margem crítica é automática: < margem_alerta_minima
    
    # Mensagens personalizadas para o PDV
    mensagem_venda_saudavel = Column(Text, default="✅ Venda Saudável! Margem excelente.")
    mensagem_venda_alerta = Column(Text, default="⚠️ ATENÇÃO: Margem reduzida! Revisar preço.")
    mensagem_venda_critica = Column(Text, default="🚨 CRÍTICO: Margem muito baixa! Venda com prejuízo!")
    
    # ============================
    # PARÂMETROS FINANCEIROS
    # ============================
    # Dias para considerar contas como vencidas
    dias_tolerancia_atraso = Column(Integer, default=5)
    
    # Meta de faturamento mensal (para dashboard)
    meta_faturamento_mensal = Column(Numeric(12, 2), default=0)
    
    # ============================
    # PARÂMETROS DE ESTOQUE
    # ============================
    # Alertar quando estoque atingir X% do mínimo
    alerta_estoque_percentual = Column(Integer, default=20)  # 20% do estoque_minimo
    
    # Dias para considerar produto parado
    dias_produto_parado = Column(Integer, default=90)
    
    # ============================
    # CONFIGURAÇÕES FISCAIS RÁPIDAS
    # ============================
    # Alíquota padrão de imposto (Simples Nacional ou outro)
    aliquota_imposto_padrao = Column(Numeric(5, 2), default=7.0)  # 7% Simples Nacional
    
    # ============================
    # AUDITORIA
    # ============================
    ativo = Column(Boolean, default=True)
    # created_at e updated_at já vêm do BaseTenantModel
    
    def to_dict(self):
        return {
            'id': self.id,
            'razao_social': self.razao_social,
            'nome_fantasia': self.nome_fantasia,
            'cnpj': self.cnpj,
            'inscricao_estadual': self.inscricao_estadual,
            'inscricao_municipal': self.inscricao_municipal,
            'logradouro': self.logradouro,
            'numero': self.numero,
            'complemento': self.complemento,
            'bairro': self.bairro,
            'cidade': self.cidade,
            'uf': self.uf,
            'cep': self.cep,
            'telefone': self.telefone,
            'email': self.email,
            'site': self.site,
            'margem_saudavel_minima': float(self.margem_saudavel_minima) if self.margem_saudavel_minima else 30.0,
            'margem_alerta_minima': float(self.margem_alerta_minima) if self.margem_alerta_minima else 15.0,
            'mensagem_venda_saudavel': self.mensagem_venda_saudavel,
            'mensagem_venda_alerta': self.mensagem_venda_alerta,
            'mensagem_venda_critica': self.mensagem_venda_critica,
            'dias_tolerancia_atraso': self.dias_tolerancia_atraso,
            'meta_faturamento_mensal': float(self.meta_faturamento_mensal) if self.meta_faturamento_mensal else 0,
            'alerta_estoque_percentual': self.alerta_estoque_percentual,
            'dias_produto_parado': self.dias_produto_parado,
            'aliquota_imposto_padrao': float(self.aliquota_imposto_padrao) if self.aliquota_imposto_padrao else 7.0,
            'ativo': self.ativo,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    def calcular_status_margem(self, margem_percentual: float) -> dict:
        """
        Calcula o status da margem de uma venda
        
        Args:
            margem_percentual: Margem em % da venda
            
        Returns:
            dict com status, mensagem e cor
        """
        margem_saudavel = float(self.margem_saudavel_minima) if self.margem_saudavel_minima else 30.0
        margem_alerta = float(self.margem_alerta_minima) if self.margem_alerta_minima else 15.0
        
        if margem_percentual >= margem_saudavel:
            return {
                'status': 'saudavel',
                'mensagem': self.mensagem_venda_saudavel or "✅ Venda Saudável!",
                'cor': 'success',
                'icone': '✅'
            }
        elif margem_percentual >= margem_alerta:
            return {
                'status': 'alerta',
                'mensagem': self.mensagem_venda_alerta or "⚠️ ATENÇÃO: Margem reduzida!",
                'cor': 'warning',
                'icone': '⚠️'
            }
        else:
            return {
                'status': 'critico',
                'mensagem': self.mensagem_venda_critica or "🚨 CRÍTICO: Margem muito baixa!",
                'cor': 'danger',
                'icone': '🚨'
            }
