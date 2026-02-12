from app.base_models import BaseTenantModel
"""
ABA 5: Fluxo de Caixa Preditivo - Modelos SQLAlchemy

Modelos de banco de dados para:
- FluxoCaixa: Histórico de movimentações
- IndicesSaudeCaixa: Índices calculados (cache)
- ProjecaoFluxoCaixa: Projeções futuras
"""

from sqlalchemy import Column, Integer, Float, String, DateTime, Boolean, Text, ForeignKey, Index
from sqlalchemy.orm import relationship
from datetime import datetime
from app.db import Base


class FluxoCaixa(BaseTenantModel):
    """
    Registro de toda movimentação de caixa.
    Inclui: vendas, despesas, contas a pagar/receber, etc.
    """
    __tablename__ = "fluxo_caixa"
    
    id = Column(Integer, primary_key=True)
    usuario_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Tipo de movimentação
    tipo = Column(String, nullable=False)  # "receita" ou "despesa"
    categoria = Column(String, nullable=False)  # "Venda", "Salário", "Aluguel", etc
    descricao = Column(String(500))
    
    # Valores
    valor = Column(Float, nullable=False)
    
    # Datas
    data_movimentacao = Column(DateTime, default=datetime.utcnow)  # quando efetivamente ocorreu
    data_prevista = Column(DateTime)  # quando se prevê que ocorra
    
    # Status
    status = Column(String, nullable=False)  # "realizado", "previsto", "cancelado"
    
    # Rastreamento de origem
    origem_tipo = Column(String)  # "venda", "compra", "lancamento_manual", "whatsapp", etc
    origem_id = Column(Integer)  # ID da venda, compra, etc
    
    # Índices para performance
    __table_args__ = (
        Index('idx_fluxo_usuario_data', 'usuario_id', 'data_movimentacao'),
        Index('idx_fluxo_usuario_tipo', 'usuario_id', 'tipo'),
        Index('idx_fluxo_usuario_status', 'usuario_id', 'status'),
    )
    
    # Override timestamps com nomes em português (tabela usa criado_em/atualizado_em)
    created_at = Column('criado_em', DateTime, default=datetime.utcnow)
    updated_at = Column('atualizado_em', DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<FluxoCaixa {self.id}: {self.tipo} {self.categoria} R${self.valor}>"


class IndicesSaudeCaixa(BaseTenantModel):
    """
    Cache de índices de saúde do caixa.
    Recalculado a cada 2 horas ou quando há movimentações grandes.
    
    Inclui:
    - dias_de_caixa: Quantos dias de despesa o caixa aguenta
    - ciclo_operacional: Quanto tempo demora pra virar dinheiro
    - margem_caixa: Margem de segurança
    - tendencia: Está melhorando ou piorando?
    """
    __tablename__ = "indices_saude_caixa"
    
    id = Column(Integer, primary_key=True)
    usuario_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Índices principais
    saldo_atual = Column(Float, nullable=False)  # Saldo de caixa agora
    despesa_media_diaria = Column(Float, nullable=False)  # R$ por dia
    dias_de_caixa = Column(Float, nullable=False)  # Quantos dias aguenta
    
    # Ciclo operacional
    dias_para_receber = Column(Float)  # Quando recebe de clientes
    dias_para_pagar = Column(Float)  # Quando tem que pagar
    ciclo_operacional = Column(Float)  # dias_para_receber + dias_para_pagar
    
    # Fluxos
    receita_mensal_estimada = Column(Float)
    despesa_mensal_estimada = Column(Float)
    saldo_mensal_estimado = Column(Float)
    
    # Status
    status = Column(String)  # "critico", "alerta", "ok"
    tendencia = Column(String)  # "piorando", "estavel", "melhorando"
    percentual_variacao_7d = Column(Float)  # % de variação em 7 dias
    
    # Score geral (0-100)
    score_saude = Column(Float)  # 0-100, usado em ABA 6 e 9
    
    # Timestamps
    calculado_em = Column(DateTime, default=datetime.utcnow)
    proxima_atualizacao = Column(DateTime)  # Quando recalcular
    
    def __repr__(self):
        return f"<IndicesSaudeCaixa dias_caixa={self.dias_de_caixa:.1f} status={self.status}>"


class ProjecaoFluxoCaixa(BaseTenantModel):
    """
    Projeção de fluxo de caixa para os próximos dias.
    Gerada pelo algoritmo Prophet (ABA 5).
    
    Atualizado a cada 2 horas ou quando há mudanças significativas.
    """
    __tablename__ = "projecao_fluxo_caixa"
    
    id = Column(Integer, primary_key=True)
    usuario_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Data da projeção
    data_projetada = Column(DateTime, nullable=False)
    dias_futuros = Column(Integer)  # Quantos dias pra frente
    
    # Valores projetados
    valor_entrada_estimada = Column(Float)  # Receita estimada
    valor_saida_estimada = Column(Float)  # Despesa estimada
    saldo_estimado = Column(Float)  # Saldo estimado nesse dia
    
    # Intervalo de confiança (95%)
    limite_inferior = Column(Float)  # Cenário pessimista
    limite_superior = Column(Float)  # Cenário otimista
    
    # Alertas
    vai_faltar_caixa = Column(Boolean)  # True = vai ficar negativo
    alerta_nivel = Column(String)  # "critico", "alerta", "ok"
    mensagem_alerta = Column(String(500))
    
    # Rastreamento
    gerado_em = Column(DateTime, default=datetime.utcnow)
    versao_modelo = Column(String)  # Versão do Prophet/modelo usada
    
    def __repr__(self):
        return f"<ProjecaoFluxoCaixa {self.data_projetada.date()} saldo={self.saldo_estimado:.2f}>"


# ============================================================================
# Esquema SQL (para criar manualmente se necessário)
# ============================================================================

SQL_CREATE_FLUXO_CAIXA = """
CREATE TABLE IF NOT EXISTS fluxo_caixa (
    id INTEGER PRIMARY KEY,
    usuario_id INTEGER NOT NULL REFERENCES usuarios(id),
    tipo VARCHAR NOT NULL,
    categoria VARCHAR NOT NULL,
    descricao VARCHAR(500),
    valor FLOAT NOT NULL,
    data_movimentacao DATETIME DEFAULT CURRENT_TIMESTAMP,
    data_prevista DATETIME,
    status VARCHAR NOT NULL,
    origem_tipo VARCHAR,
    origem_id INTEGER,
    criado_em DATETIME DEFAULT CURRENT_TIMESTAMP,
    atualizado_em DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_fluxo_usuario_data ON fluxo_caixa(usuario_id, data_movimentacao);
CREATE INDEX idx_fluxo_usuario_tipo ON fluxo_caixa(usuario_id, tipo);
CREATE INDEX idx_fluxo_usuario_status ON fluxo_caixa(usuario_id, status);
"""

SQL_CREATE_INDICES_SAUDE = """
CREATE TABLE IF NOT EXISTS indices_saude_caixa (
    id INTEGER PRIMARY KEY,
    usuario_id INTEGER NOT NULL REFERENCES usuarios(id),
    saldo_atual FLOAT NOT NULL,
    despesa_media_diaria FLOAT NOT NULL,
    dias_de_caixa FLOAT NOT NULL,
    dias_para_receber FLOAT,
    dias_para_pagar FLOAT,
    ciclo_operacional FLOAT,
    receita_mensal_estimada FLOAT,
    despesa_mensal_estimada FLOAT,
    saldo_mensal_estimado FLOAT,
    status VARCHAR,
    tendencia VARCHAR,
    percentual_variacao_7d FLOAT,
    score_saude FLOAT,
    calculado_em DATETIME DEFAULT CURRENT_TIMESTAMP,
    proxima_atualizacao DATETIME
);

CREATE INDEX idx_indices_usuario ON indices_saude_caixa(usuario_id);
"""

SQL_CREATE_PROJECAO = """
CREATE TABLE IF NOT EXISTS projecao_fluxo_caixa (
    id INTEGER PRIMARY KEY,
    usuario_id INTEGER NOT NULL REFERENCES usuarios(id),
    data_projetada DATETIME NOT NULL,
    dias_futuros INTEGER,
    valor_entrada_estimada FLOAT,
    valor_saida_estimada FLOAT,
    saldo_estimado FLOAT,
    limite_inferior FLOAT,
    limite_superior FLOAT,
    vai_faltar_caixa BOOLEAN,
    alerta_nivel VARCHAR,
    mensagem_alerta VARCHAR(500),
    gerado_em DATETIME DEFAULT CURRENT_TIMESTAMP,
    versao_modelo VARCHAR
);

CREATE INDEX idx_projecao_usuario ON projecao_fluxo_caixa(usuario_id, data_projetada);
"""
