from app.base_models import BaseTenantModel
"""
ABA 7: DRE Inteligente - Modelos
Demonstração de Resultado do Exercício com análise de rentabilidade
"""

from sqlalchemy import Column, Integer, String, Float, Date, ForeignKey, DateTime, Text, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from app.db import Base


class DREPeriodo(Base):
    """Armazena DRE calculado para um período"""
    __tablename__ = "dre_periodos"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, index=True)  # Multi-tenant
    
    # Período
    data_inicio = Column(Date, nullable=False)
    data_fim = Column(Date, nullable=False)
    mes = Column(Integer)  # 1-12
    ano = Column(Integer)
    
    # ===== CANAL DE VENDA =====
    canal = Column(String(50), default='loja_fisica')  # 'loja_fisica', 'mercado_livre', 'shopee', 'amazon', 'todos'
    canais_incluidos = Column(Text)  # JSON array: ["loja_fisica", "mercado_livre"]
    
    # ===== RECEITAS =====
    receita_bruta = Column(Float, default=0)  # Total vendas
    deducoes_receita = Column(Float, default=0)  # Devoluções, descontos
    receita_liquida = Column(Float, default=0)  # Bruta - Deduções
    
    # ===== CUSTOS =====
    custo_produtos_vendidos = Column(Float, default=0)  # CMV
    lucro_bruto = Column(Float, default=0)  # Receita Líquida - CMV
    margem_bruta_percent = Column(Float, default=0)  # (Lucro Bruto / Receita Líquida) * 100
    
    # ===== DESPESAS OPERACIONAIS =====
    despesas_vendas = Column(Float, default=0)  # Comissões, marketing
    despesas_administrativas = Column(Float, default=0)  # Salários, aluguel
    despesas_financeiras = Column(Float, default=0)  # Juros, taxas
    outras_despesas = Column(Float, default=0)
    total_despesas_operacionais = Column(Float, default=0)
    
    # ===== RESULTADO =====
    lucro_operacional = Column(Float, default=0)  # Lucro Bruto - Despesas Operacionais
    margem_operacional_percent = Column(Float, default=0)
    
    # ===== IMPOSTOS =====
    impostos = Column(Float, default=0)  # Impostos calculados automaticamente
    impostos_detalhamento = Column(Text)  # JSON com detalhamento (PIS, COFINS, IRPJ, etc)
    aliquota_efetiva_percent = Column(Float, default=0)
    regime_tributario = Column(String(50))  # simples_nacional, lucro_presumido, etc
    
    lucro_liquido = Column(Float, default=0)  # Resultado final (após impostos)
    margem_liquida_percent = Column(Float, default=0)  # (Lucro Líquido / Receita Líquida) * 100
    
    # ===== ANÁLISES =====
    status = Column(String(50))  # "lucro", "prejuizo", "equilibrio"
    tendencia = Column(String(50))  # "crescimento", "queda", "estavel"
    score_saude = Column(Integer, default=0)  # 0-100
    
    # Metadados
    criado_em = Column(DateTime, default=datetime.utcnow)
    atualizado_em = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relacionamentos
    historico_atualizacoes = relationship("HistoricoAtualizacaoDRE", back_populates="dre_periodo", cascade="all, delete-orphan")


class DREProduto(BaseTenantModel):
    """Análise de rentabilidade por produto"""
    __tablename__ = "dre_produtos"
    
    id = Column(Integer, primary_key=True, index=True)
    dre_periodo_id = Column(Integer, ForeignKey("dre_periodos.id"))
    usuario_id = Column(Integer, index=True)
    
    # Produto
    produto_id = Column(Integer, index=True)
    produto_nome = Column(String(255))
    categoria = Column(String(100))
    
    # Métricas
    quantidade_vendida = Column(Integer, default=0)
    receita_total = Column(Float, default=0)
    custo_total = Column(Float, default=0)
    lucro_total = Column(Float, default=0)
    margem_percent = Column(Float, default=0)
    
    # Análises
    ranking_rentabilidade = Column(Integer)  # Posição no ranking
    eh_lucrativo = Column(Boolean, default=True)
    recomendacao = Column(Text)  # Sugestão de ação
    
    criado_em = Column(DateTime, default=datetime.utcnow)


class DRECategoriaAnalise(BaseTenantModel):
    """Análise de rentabilidade por categoria de produtos (LEGADO)"""
    __tablename__ = "dre_categorias_analise"
    
    id = Column(Integer, primary_key=True, index=True)
    dre_periodo_id = Column(Integer, ForeignKey("dre_periodos.id"))
    usuario_id = Column(Integer, index=True)
    
    # Categoria
    categoria_nome = Column(String(100))
    
    # Métricas
    quantidade_vendida = Column(Integer, default=0)
    receita_total = Column(Float, default=0)
    custo_total = Column(Float, default=0)
    lucro_total = Column(Float, default=0)
    margem_percent = Column(Float, default=0)
    participacao_receita_percent = Column(Float, default=0)
    
    # Análises
    eh_categoria_principal = Column(Boolean, default=False)
    tendencia = Column(String(50))
    
    criado_em = Column(DateTime, default=datetime.utcnow)


class DREComparacao(BaseTenantModel):
    """Comparação entre períodos"""
    __tablename__ = "dre_comparacoes"
    
    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, index=True)
    
    # Períodos comparados
    periodo1_id = Column(Integer, ForeignKey("dre_periodos.id"))
    periodo2_id = Column(Integer, ForeignKey("dre_periodos.id"))
    
    # Variações
    var_receita_percent = Column(Float)
    var_custo_percent = Column(Float)
    var_lucro_bruto_percent = Column(Float)
    var_despesas_percent = Column(Float)
    var_lucro_liquido_percent = Column(Float)
    
    # Análise
    resumo = Column(Text)
    principais_mudancas = Column(Text)  # JSON com lista de mudanças
    
    criado_em = Column(DateTime, default=datetime.utcnow)


class DREInsight(BaseTenantModel):
    """Insights gerados pela IA sobre o DRE"""
    __tablename__ = "dre_insights"
    
    id = Column(Integer, primary_key=True, index=True)
    dre_periodo_id = Column(Integer, ForeignKey("dre_periodos.id"))
    usuario_id = Column(Integer, index=True)
    
    # Insight
    tipo = Column(String(50))  # "alerta", "oportunidade", "recomendacao"
    categoria = Column(String(50))  # "receita", "custo", "despesa", "lucro"
    titulo = Column(String(255))
    descricao = Column(Text)
    impacto = Column(String(20))  # "alto", "medio", "baixo"
    
    # Ação sugerida
    acao_sugerida = Column(Text)
    impacto_estimado = Column(Float)  # Valor em R$
    
    # Status
    foi_lido = Column(Boolean, default=False)
    foi_aplicado = Column(Boolean, default=False)
    
    criado_em = Column(DateTime, default=datetime.utcnow)


class IndicesMercado(BaseTenantModel):
    """Benchmarks de mercado para comparação com DRE do usuário"""
    __tablename__ = "indices_mercado"
    
    id = Column(Integer, primary_key=True, index=True)
    setor = Column(String(100), nullable=False, index=True)  # 'pet_shop', 'varejo', 'servicos', 'restaurante'
    descricao = Column(String(255))  # Descrição do setor
    
    # ===== BENCHMARKS DE CUSTOS (em % da receita) =====
    cmv_ideal_min = Column(Float, default=30)  # CMV mínimo esperado
    cmv_ideal_max = Column(Float, default=50)  # CMV máximo aceitável
    
    # ===== BENCHMARKS DE MARGENS (em %) =====
    margem_bruta_ideal_min = Column(Float, default=40)
    margem_bruta_ideal_max = Column(Float, default=60)
    margem_liquida_ideal_min = Column(Float, default=10)
    margem_liquida_ideal_max = Column(Float, default=20)
    
    # ===== BENCHMARKS DE DESPESAS (em % da receita) =====
    despesas_admin_ideal_max = Column(Float, default=15)  # Máximo aceitável
    despesas_vendas_ideal_max = Column(Float, default=10)
    despesas_financeiras_ideal_max = Column(Float, default=5)
    despesas_totais_ideal_max = Column(Float, default=40)  # Soma de todas
    
    # ===== BENCHMARKS DE IMPOSTOS (em % da receita) =====
    impostos_ideal_min = Column(Float, default=5)   # Simples Nacional
    impostos_ideal_max = Column(Float, default=15)  # Lucro Real
    
    # ===== OUTROS INDICADORES =====
    ticket_medio_ideal_min = Column(Float, default=50)   # R$ mínimo por venda
    ticket_medio_ideal_max = Column(Float, default=200)  # R$ máximo esperado
    giro_estoque_ideal_dias = Column(Integer, default=60)  # Dias de giro
    prazo_recebimento_ideal_dias = Column(Integer, default=15)
    prazo_pagamento_ideal_dias = Column(Integer, default=30)
    
    # Metadados
    fonte = Column(String(255))  # "SEBRAE 2025", "Pesquisa de Mercado", etc
    referencia_ano = Column(Integer)  # Ano de referência dos dados
    ativo = Column(Boolean, default=True)
    atualizado_em = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
