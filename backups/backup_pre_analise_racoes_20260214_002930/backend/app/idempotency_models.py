from app.base_models import BaseTenantModel
"""
Modelo para controle de Idempotência
Garante que requisições duplicadas não gerem efeitos colaterais duplicados
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, Index
from sqlalchemy.sql import func
from app.db import Base


class IdempotencyKey(BaseTenantModel):
    """
    Armazena chaves de idempotência para evitar processamento duplicado
    
    Funciona assim:
    1. Cliente envia requisição com Idempotency-Key único (UUID/ULID)
    2. Servidor verifica se já processou essa chave
    3. Se SIM → retorna resposta anterior (sem reprocessar)
    4. Se NÃO → processa normalmente e armazena resultado
    
    Segurança:
    - Chaves são por user_id (isolamento por tenant)
    - Chaves expiram em 24h (limpeza automática)
    - Requisições diferentes com mesma chave = erro
    """
    __tablename__ = "idempotency_keys"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    
    # Identificação da requisição
    endpoint = Column(String(255), nullable=False)  # Ex: POST /vendas/
    chave_idempotencia = Column(String(255), nullable=False, index=True)
    
    # Fingerprint da requisição (para detectar requisições diferentes com mesma chave)
    request_hash = Column(String(64), nullable=False)  # SHA256 do body serializado
    
    # Estado do processamento
    status = Column(String(50), nullable=False, default='processing')
    # Valores possíveis:
    # - 'processing': Em andamento (evita race condition)
    # - 'completed': Processado com sucesso
    # - 'failed': Processamento falhou
    
    # Resposta armazenada
    response_status_code = Column(Integer, nullable=True)
    response_body = Column(Text, nullable=True)  # JSON serializado
    error_message = Column(Text, nullable=True)  # Se status='failed'
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Índices compostos para performance
    __table_args__ = (
        # Busca principal: user + chave
        Index('idx_user_key', 'user_id', 'chave_idempotencia'),
        # Limpeza de expirados
        Index('idx_created_at', 'created_at'),
    )
    
    def to_dict(self):
        """Serializa para JSON"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'endpoint': self.endpoint,
            'chave_idempotencia': self.chave_idempotencia,
            'status': self.status,
            'response_status_code': self.response_status_code,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
        }
