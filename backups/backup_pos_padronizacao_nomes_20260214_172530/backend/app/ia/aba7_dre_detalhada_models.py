from app.base_models import BaseTenantModel
"""
ABA 7: DRE Detalhada por Canal - Nova Estrutura
Cada canal em linha separada, com consolidação ao final
"""

from sqlalchemy import Column, Integer, String, Float, Date, ForeignKey, DateTime, Text, Boolean, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from app.db import Base


class DREDetalheCanal(BaseTenantModel):
    """Armazena detalhes do DRE de CADA CANAL separadamente"""
    __tablename__ = "dre_detalhe_canais"
    
    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, index=True)
    
    # Período
    data_inicio = Column(Date, nullable=False)
    data_fim = Column(Date, nullable=False)
    mes = Column(Integer)
    ano = Column(Integer)
    
    # Canal (uma linha para cada canal)
    canal = Column(String(50), nullable=False, index=True)  # loja_fisica, mercado_livre, shopee, amazon
    
    # ===== RECEITAS =====
    receita_bruta = Column(Float, default=0)
    deducoes_receita = Column(Float, default=0)
    receita_liquida = Column(Float, default=0)
    
    # ===== CUSTOS =====
    custo_produtos_vendidos = Column(Float, default=0)
    lucro_bruto = Column(Float, default=0)
    margem_bruta_percent = Column(Float, default=0)
    
    # ===== DESPESAS (SEM RATEIO - ALOCAÇÃO ESPECÍFICA DO CANAL) =====
    despesas_vendas = Column(Float, default=0)  # Comissões, taxas marketplace (já específicas do canal)
    despesas_pessoal = Column(Float, default=0)  # Salários, encargos (alocado manualmente)
    despesas_administrativas = Column(Float, default=0)  # Água, luz, internet, telefone, aluguel (alocado manualmente)
    despesas_financeiras = Column(Float, default=0)  # Juros, taxas bancárias (alocado manualmente)
    outras_despesas = Column(Float, default=0)  # Alocado manualmente
    total_despesas_operacionais = Column(Float, default=0)
    
    # ===== RESULTADO =====
    lucro_operacional = Column(Float, default=0)
    margem_operacional_percent = Column(Float, default=0)
    
    # ===== IMPOSTOS =====
    impostos = Column(Float, default=0)
    impostos_detalhamento = Column(Text)  # JSON
    aliquota_efetiva_percent = Column(Float, default=0)
    regime_tributario = Column(String(50))
    
    lucro_liquido = Column(Float, default=0)
    margem_liquida_percent = Column(Float, default=0)
    
    # ===== ANÁLISES =====
    status = Column(String(50))  # lucro, prejuizo, equilibrio
    score_saude = Column(Integer, default=0)
    
    # ===== AUDITORIA E RASTREABILIDADE =====
    origem = Column(String(50), index=True)  # PROVISAO, AJUSTE, REAL
    origem_evento = Column(String(50), index=True)  # NF, DAS, FGTS, FERIAS, 13, BOLETO
    referencia_id = Column(String(100), index=True)  # ID da NF, Conta a Pagar, etc
    observacao = Column(Text)  # Texto humano explicativo
    
    criado_em = Column(DateTime, default=datetime.utcnow, index=True)
    atualizado_em = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class DREConsolidado(BaseTenantModel):
    """Armazena DRE CONSOLIDADO (soma de todos os canais selecionados)"""
    __tablename__ = "dre_consolidado"
    
    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, index=True)
    
    # Período
    data_inicio = Column(Date, nullable=False)
    data_fim = Column(Date, nullable=False)
    mes = Column(Integer)
    ano = Column(Integer)
    
    # Canais inclusos (JSON array)
    canais_selecionados = Column(Text)  # JSON: ["loja_fisica", "mercado_livre"]
    
    # ===== RECEITAS CONSOLIDADAS =====
    receita_bruta = Column(Float, default=0)
    deducoes_receita = Column(Float, default=0)
    receita_liquida = Column(Float, default=0)
    
    # Detalhamento por canal (JSON para mostrar breakdown)
    receita_por_canal = Column(Text)  # JSON: {"loja_fisica": 10000, "mercado_livre": 5000}
    
    # ===== CUSTOS CONSOLIDADOS =====
    custo_produtos_vendidos = Column(Float, default=0)
    lucro_bruto = Column(Float, default=0)
    margem_bruta_percent = Column(Float, default=0)
    
    # ===== DESPESAS CONSOLIDADAS =====
    despesas_vendas = Column(Float, default=0)
    despesas_pessoal = Column(Float, default=0)  # Soma das despesas com pessoal de todos os canais
    despesas_administrativas = Column(Float, default=0)
    despesas_financeiras = Column(Float, default=0)
    outras_despesas = Column(Float, default=0)
    total_despesas_operacionais = Column(Float, default=0)
    
    # Detalhamento por canal (JSON)
    despesas_por_canal = Column(Text)  # JSON: {"loja_fisica": 3000, "mercado_livre": 1500, "shopee": 1500}
    
    # ===== RESULTADO CONSOLIDADO =====
    lucro_operacional = Column(Float, default=0)
    margem_operacional_percent = Column(Float, default=0)
    
    impostos = Column(Float, default=0)
    aliquota_efetiva_percent = Column(Float, default=0)
    
    lucro_liquido = Column(Float, default=0)
    margem_liquida_percent = Column(Float, default=0)
    
    status = Column(String(50))
    score_saude = Column(Integer, default=0)
    
    criado_em = Column(DateTime, default=datetime.utcnow)
    atualizado_em = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class AlocacaoDespesaCanal(BaseTenantModel):
    """Define como as despesas são alocadas aos canais"""
    __tablename__ = "alocacao_despesa_canal"
    
    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey('users.id'), index=True)
    
    # Período
    data_inicio = Column(Date, nullable=False)
    data_fim = Column(Date, nullable=False)
    
    # Despesa
    categoria_despesa = Column(String(100), nullable=False)  # "aluguel", "salario", etc
    descricao = Column(String(255), nullable=True)
    valor_total = Column(Float, nullable=False)
    
    # Modo de alocação
    modo_alocacao = Column(String(20), nullable=False)  # "proporcional" ou "manual"
    
    # Se proporcional: baseado em faturamento ou percentual fixo
    usar_faturamento = Column(Boolean, default=True)  # Se True, usa receita de cada canal; se False, percentual manual
    
    # Se manual: detalhamento por canal (JSON)
    # {"loja_fisica": {"valor": 7000, "percentual": 70}, "mercado_livre": {"valor": 2000, "percentual": 20}, "shopee": {"valor": 1000, "percentual": 10}}
    alocacao_manual = Column(Text)  # JSON com distribuição manual
    
    # Canais afetados
    canais_afetados = Column(Text)  # JSON: ["loja_fisica", "mercado_livre", "shopee"]
    
    # Observações
    observacoes = Column(Text, nullable=True)
    
    criado_em = Column(DateTime, default=datetime.utcnow)
    atualizado_em = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relacionamento
    usuario = relationship("User", foreign_keys=[usuario_id])
