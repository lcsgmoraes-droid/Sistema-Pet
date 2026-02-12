from app.base_models import BaseTenantModel
"""
ABA 8: Modelos para Otimização de Entregas

Modelos de banco de dados para:
- Rota: Uma rota de entrega planejada
- Entrega: Um item a ser entregue
- HistoricoEntregas: Log de entregas realizadas
"""

from sqlalchemy import Column, Integer, Float, String, DateTime, Boolean, Text, ForeignKey, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from app.db import Base


class Rota(BaseTenantModel):
    """
    Uma rota planejada de entrega.
    Pode ter múltiplas paradas (entregas).
    """
    __tablename__ = "rotas_entrega"
    
    id = Column(Integer, primary_key=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    
    # Identificação
    numero_rota = Column(String, unique=True)  # ROTA-20260111-001
    data_rota = Column(DateTime, nullable=False)
    
    # Motorista (opcional)
    nome_motorista = Column(String)
    telefone_motorista = Column(String)
    veiculo = Column(String)  # "van", "carro", "moto", etc
    
    # Planejamento
    total_paradas = Column(Integer)
    ordem_otimizada = Column(Text)  # JSON: [parada1, parada2, parada3]
    
    # Métricas
    distancia_total_km = Column(Float)
    tempo_estimado_minutos = Column(Integer)
    custo_estimado = Column(Float)
    
    # Algoritmo usado
    algoritmo = Column(String)  # "forca_bruta", "greedy_2opt"
    tempo_otimizacao_segundos = Column(Float)
    
    # Status
    status = Column(String)  # "planejada", "em_andamento", "finalizada", "cancelada"
    
    # Rastreamento em tempo real
    latitude_atual = Column(Float)
    longitude_atual = Column(Float)
    ultima_atualizacao_gps = Column(DateTime)
    
    # Resultados
    distancia_real_km = Column(Float)
    tempo_real_minutos = Column(Integer)
    custo_real = Column(Float)
    
    # Timestamps
    data_criacao = Column(DateTime, default=datetime.utcnow)
    data_inicio = Column(DateTime)
    data_conclusao = Column(DateTime)
    
    def __repr__(self):
        return f"<Rota {self.numero_rota} {self.total_paradas} paradas>"


class Entrega(BaseTenantModel):
    """
    Uma entrega individual dentro de uma rota.
    Cada venda pode virar uma ou mais entregas.
    """
    __tablename__ = "entregas"
    
    id = Column(Integer, primary_key=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    rota_id = Column(Integer, ForeignKey("rotas_entrega.id"), nullable=True)
    
    # Origem (pode ser venda, compra, devolução, etc)
    origem_tipo = Column(String)  # "venda", "compra", "devolução", "entrega_especial"
    origem_id = Column(Integer)
    
    # Cliente
    cliente_id = Column(Integer, ForeignKey("cliente.id"), nullable=False)
    nome_cliente = Column(String(200))
    telefone_cliente = Column(String(20))
    
    # Endereço de entrega
    endereco_completo = Column(String(500))
    latitude = Column(Float)
    longitude = Column(Float)
    referencia = Column(String(200))
    
    # Informações da entrega
    peso_estimado_kg = Column(Float)
    volume_estimado_litros = Column(Float)
    valor_total = Column(Float)
    
    # Sequência na rota
    sequencia_rota = Column(Integer)
    tempo_chegada_estimado = Column(DateTime)
    
    # Status
    status = Column(String)  # "pendente", "em_transito", "entregue", "problema", "cancelada"
    
    # Detalhes da entrega
    assinatura_cliente = Column(String)  # URL da imagem
    foto_prova = Column(String)  # URL da foto
    observacao_entrega = Column(String(500))
    
    # Rastreamento
    timestamp_chegada = Column(DateTime)
    timestamp_entrega = Column(DateTime)
    
    # Distância até próxima parada
    distancia_proxima_km = Column(Float)
    
    # Timestamps
    criada_em = Column(DateTime, default=datetime.utcnow)
    atualizada_em = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<Entrega {self.id} cliente={self.nome_cliente} status={self.status}>"


class HistoricoEntregas(BaseTenantModel):
    """
    Histórico detalhado de entregas realizadas.
    Usado para análise e otimização futura.
    """
    __tablename__ = "historico_entregas"
    
    id = Column(Integer, primary_key=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    
    # Referência
    entrega_id = Column(Integer, ForeignKey("entregas.id"), nullable=False)
    rota_id = Column(Integer, ForeignKey("rotas_entrega.id"), nullable=False)
    
    # Tempos
    tempo_chegada_estimado = Column(Integer)  # minutos
    tempo_chegada_real = Column(Integer)  # minutos
    diferenca_tempo = Column(Integer)  # real - estimado
    
    # Distâncias
    distancia_estimada = Column(Float)  # km
    distancia_real = Column(Float)  # km
    diferenca_distancia = Column(Float)  # real - estimado
    
    # Condições
    condicao_transito = Column(String)  # "normal", "congestionado", "bloqueado"
    clima = Column(String)  # "claro", "chuva", "neblina"
    
    # Feedback
    cliente_satisfeito = Column(Boolean)
    motivo_insatisfacao = Column(String)
    
    # Otimização (aprendizado)
    sequencia_planejada = Column(Integer)
    sequencia_real = Column(Integer)
    
    # Timestamps
    data_entrega = Column(DateTime, default=datetime.utcnow)
    criado_em = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<HistoricoEntregas entrega_id={self.entrega_id} diferenca_tempo={self.diferenca_tempo}min>"


# ============================================================================
# Esquema SQL
# ============================================================================

SQL_CREATE_ROTA = """
CREATE TABLE IF NOT EXISTS rotas_entrega (
    id INTEGER PRIMARY KEY,
    usuario_id INTEGER NOT NULL REFERENCES usuarios(id),
    numero_rota VARCHAR UNIQUE,
    data_rota DATETIME NOT NULL,
    nome_motorista VARCHAR,
    telefone_motorista VARCHAR,
    veiculo VARCHAR,
    total_paradas INTEGER,
    ordem_otimizada TEXT,
    distancia_total_km FLOAT,
    tempo_estimado_minutos INTEGER,
    custo_estimado FLOAT,
    algoritmo VARCHAR,
    tempo_otimizacao_segundos FLOAT,
    status VARCHAR,
    latitude_atual FLOAT,
    longitude_atual FLOAT,
    ultima_atualizacao_gps DATETIME,
    distancia_real_km FLOAT,
    tempo_real_minutos INTEGER,
    custo_real FLOAT,
    data_criacao DATETIME DEFAULT CURRENT_TIMESTAMP,
    data_inicio DATETIME,
    data_conclusao DATETIME
);

CREATE INDEX idx_rota_usuario ON rotas_entrega(usuario_id);
CREATE INDEX idx_rota_data ON rotas_entrega(data_rota);
CREATE INDEX idx_rota_status ON rotas_entrega(status);
"""

SQL_CREATE_ENTREGA = """
CREATE TABLE IF NOT EXISTS entregas (
    id INTEGER PRIMARY KEY,
    usuario_id INTEGER NOT NULL REFERENCES usuarios(id),
    rota_id INTEGER REFERENCES rotas_entrega(id),
    origem_tipo VARCHAR,
    origem_id INTEGER,
    cliente_id INTEGER NOT NULL REFERENCES cliente(id),
    nome_cliente VARCHAR(200),
    telefone_cliente VARCHAR(20),
    endereco_completo VARCHAR(500),
    latitude FLOAT,
    longitude FLOAT,
    referencia VARCHAR(200),
    peso_estimado_kg FLOAT,
    volume_estimado_litros FLOAT,
    valor_total FLOAT,
    sequencia_rota INTEGER,
    tempo_chegada_estimado DATETIME,
    status VARCHAR,
    assinatura_cliente VARCHAR,
    foto_prova VARCHAR,
    observacao_entrega VARCHAR(500),
    timestamp_chegada DATETIME,
    timestamp_entrega DATETIME,
    distancia_proxima_km FLOAT,
    criada_em DATETIME DEFAULT CURRENT_TIMESTAMP,
    atualizada_em DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_entrega_usuario ON entregas(usuario_id);
CREATE INDEX idx_entrega_rota ON entregas(rota_id);
CREATE INDEX idx_entrega_cliente ON entregas(cliente_id);
CREATE INDEX idx_entrega_status ON entregas(status);
"""

SQL_CREATE_HISTORICO_ENTREGA = """
CREATE TABLE IF NOT EXISTS historico_entregas (
    id INTEGER PRIMARY KEY,
    usuario_id INTEGER NOT NULL REFERENCES usuarios(id),
    entrega_id INTEGER NOT NULL REFERENCES entregas(id),
    rota_id INTEGER NOT NULL REFERENCES rotas_entrega(id),
    tempo_chegada_estimado INTEGER,
    tempo_chegada_real INTEGER,
    diferenca_tempo INTEGER,
    distancia_estimada FLOAT,
    distancia_real FLOAT,
    diferenca_distancia FLOAT,
    condicao_transito VARCHAR,
    clima VARCHAR,
    cliente_satisfeito BOOLEAN,
    motivo_insatisfacao VARCHAR,
    sequencia_planejada INTEGER,
    sequencia_real INTEGER,
    data_entrega DATETIME DEFAULT CURRENT_TIMESTAMP,
    criado_em DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_historico_usuario ON historico_entregas(usuario_id);
CREATE INDEX idx_historico_entrega ON historico_entregas(entrega_id);
CREATE INDEX idx_historico_data ON historico_entregas(data_entrega);
"""
