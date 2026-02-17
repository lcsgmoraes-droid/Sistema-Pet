from app.base_models import BaseTenantModel
"""
ABA 6 e ABA 9: Modelos para Chat IA e WhatsApp

Modelos de banco de dados para:
- ConversaWhatsApp: Conversas com o bot
- MensagemWhatsApp: Histórico de mensagens
- ClienteConversaInteligente: Cache de análises
"""

from sqlalchemy import Column, Integer, Float, String, DateTime, Boolean, Text, ForeignKey, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from app.db import Base


class ConversaWhatsApp(BaseTenantModel):
    """
    Registro de uma conversa com o bot WhatsApp.
    Rastreia: estado, produto selecionado, venda gerada, etc.
    """
    __tablename__ = "conversas_whatsapp"
    
    id = Column(Integer, primary_key=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    cliente_id = Column(Integer, ForeignKey("cliente.id"), nullable=True)
    
    # Informações do contato
    numero_whatsapp = Column(String(20), nullable=False)
    nome_cliente = Column(String(200))
    
    # Estado da conversa
    estado_atual = Column(String)  # "inicial", "buscando", "desambiguacao", "quantidade", "confirmando", "venda_criada"
    
    # Venda associada
    venda_id = Column(Integer, ForeignKey("vendas.id"), nullable=True)
    venda_gerada_por_ia = Column(Boolean, default=True)
    confianca_ia = Column(Float)  # 0-100%
    
    # Histórico (JSON)
    historico_mensagens_json = Column(Text)  # JSON com [{"remetente": "cliente", "texto": "...", "timestamp": "..."}]
    
    # Métricas
    total_mensagens = Column(Integer, default=0)
    duracao_minutos = Column(Integer)
    
    # Feedback e aprendizado
    resultado_venda = Column(String)  # "criada", "confirmada", "rejeitada", "cancelada"
    motivo_rejeicao = Column(String)
    rating_cliente = Column(Float)  # 1-5 stars (se disponível)
    
    # Timestamps
    data_inicio = Column(DateTime, default=datetime.utcnow)
    data_fim = Column(DateTime, nullable=True)
    criado_em = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<ConversaWhatsApp {self.numero_whatsapp} estado={self.estado_atual}>"


class MensagemWhatsApp(BaseTenantModel):
    """
    Histórico detalhado de cada mensagem em uma conversa.
    Usado para rastreamento e treinamento de IA.
    """
    __tablename__ = "mensagens_whatsapp"
    
    id = Column(Integer, primary_key=True)
    conversa_id = Column(Integer, ForeignKey("conversas_whatsapp.id"), nullable=False)
    
    # Quem enviou
    remetente = Column(String)  # "cliente" ou "bot"
    
    # Conteúdo
    tipo = Column(String, default="texto")  # "texto", "imagem", "arquivo", "localizacao"
    mensagem = Column(Text)
    
    # Intenção detectada (ABA 6)
    intencao_detectada = Column(String)  # "fluxo_caixa", "vendas", "estoque", etc
    confianca_intencao = Column(Float)  # 0-100%
    
    # IA Processing
    processada_por_ia = Column(Boolean, default=False)
    resposta_ia = Column(Text)  # Resposta gerada
    
    # Timestamps
    data_hora = Column(DateTime, default=datetime.utcnow)
    criada_em = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<MensagemWhatsApp {self.remetente} {self.mensagem[:50]}>"


class AnaliseClienteInteligente(BaseTenantModel):
    """
    Cache de análises dinâmicas sobre um cliente.
    Atualizado quando cliente interage via chat (ABA 6).
    
    Usado para:
    - Recomendações personalizadas
    - Detecção de problemas
    - Sugestões de ação
    """
    __tablename__ = "analise_cliente_inteligente"
    
    id = Column(Integer, primary_key=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    cliente_id = Column(Integer, ForeignKey("cliente.id"), nullable=False)
    
    # Perfil de compra
    total_compras = Column(Integer, default=0)
    valor_total_gasto = Column(Float, default=0)
    ticket_medio = Column(Float)
    frequencia_dias = Column(Integer)  # A cada quantos dias compra?
    
    # Produtos favoritos
    produto_favorito_id = Column(Integer, ForeignKey("produtos.id"), nullable=True)
    categoria_favorita = Column(String)
    
    # Padrões
    melhor_dia_semana = Column(String)  # "segunda", "terça", etc
    melhor_horario = Column(String)  # "08:00", "14:00", etc
    
    # Status
    status_cliente = Column(String)  # "ativo", "inativo", "em_risco", "estrela"
    dias_ultima_compra = Column(Integer)
    
    # Recomendações geradas
    recomendacoes_json = Column(Text)  # JSON com recomendações
    
    # Scores
    score_fidelidade = Column(Float)  # 0-100
    score_lucratividade = Column(Float)  # 0-100
    
    # Timestamps
    ultima_atualizacao = Column(DateTime, default=datetime.utcnow)
    criada_em = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<AnaliseClienteInteligente cliente_id={self.cliente_id} status={self.status_cliente}>"


# ============================================================================
# Esquema SQL
# ============================================================================

SQL_CREATE_CONVERSA_WHATSAPP = """
CREATE TABLE IF NOT EXISTS conversas_whatsapp (
    id INTEGER PRIMARY KEY,
    usuario_id INTEGER NOT NULL REFERENCES usuarios(id),
    cliente_id INTEGER REFERENCES cliente(id),
    numero_whatsapp VARCHAR(20) NOT NULL,
    nome_cliente VARCHAR(200),
    estado_atual VARCHAR,
    venda_id INTEGER REFERENCES vendas(id),
    venda_gerada_por_ia BOOLEAN DEFAULT 1,
    confianca_ia FLOAT,
    historico_mensagens_json TEXT,
    total_mensagens INTEGER DEFAULT 0,
    duracao_minutos INTEGER,
    resultado_venda VARCHAR,
    motivo_rejeicao VARCHAR,
    rating_cliente FLOAT,
    data_inicio DATETIME DEFAULT CURRENT_TIMESTAMP,
    data_fim DATETIME,
    criado_em DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_conversa_usuario ON conversas_whatsapp(usuario_id);
CREATE INDEX idx_conversa_numero ON conversas_whatsapp(numero_whatsapp);
CREATE INDEX idx_conversa_venda ON conversas_whatsapp(venda_id);
"""

SQL_CREATE_MENSAGEM_WHATSAPP = """
CREATE TABLE IF NOT EXISTS mensagens_whatsapp (
    id INTEGER PRIMARY KEY,
    conversa_id INTEGER NOT NULL REFERENCES conversas_whatsapp(id),
    remetente VARCHAR,
    tipo VARCHAR DEFAULT 'texto',
    mensagem TEXT,
    intencao_detectada VARCHAR,
    confianca_intencao FLOAT,
    processada_por_ia BOOLEAN DEFAULT 0,
    resposta_ia TEXT,
    data_hora DATETIME DEFAULT CURRENT_TIMESTAMP,
    criada_em DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_mensagem_conversa ON mensagens_whatsapp(conversa_id);
"""

SQL_CREATE_ANALISE_CLIENTE = """
CREATE TABLE IF NOT EXISTS analise_cliente_inteligente (
    id INTEGER PRIMARY KEY,
    usuario_id INTEGER NOT NULL REFERENCES usuarios(id),
    cliente_id INTEGER NOT NULL REFERENCES cliente(id),
    total_compras INTEGER DEFAULT 0,
    valor_total_gasto FLOAT DEFAULT 0,
    ticket_medio FLOAT,
    frequencia_dias INTEGER,
    produto_favorito_id INTEGER REFERENCES produtos(id),
    categoria_favorita VARCHAR,
    melhor_dia_semana VARCHAR,
    melhor_horario VARCHAR,
    status_cliente VARCHAR,
    dias_ultima_compra INTEGER,
    recomendacoes_json TEXT,
    score_fidelidade FLOAT,
    score_lucratividade FLOAT,
    ultima_atualizacao DATETIME DEFAULT CURRENT_TIMESTAMP,
    criada_em DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_analise_usuario ON analise_cliente_inteligente(usuario_id);
CREATE INDEX idx_analise_cliente ON analise_cliente_inteligente(cliente_id);
"""
