# -*- coding: utf-8 -*-
"""
Modelo para armazenar pares de produtos marcados como não-duplicatas
Evita que o sistema continue sugerindo o mesmo par
"""

from sqlalchemy import Column, Integer, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from .db import Base


class DuplicataIgnorada(Base):
    """
    Tabela para registrar pares de produtos que foram marcados como NÃO-DUPLICATAS
    Quando usuário clica em "Ignorar", o par é salvo aqui
    O endpoint de detecção filtra esses pares
    """
    __tablename__ = "duplicatas_ignoradas"
    
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    
    # Os dois produtos do par (sempre salvar em ordem: menor ID primeiro)
    produto_id_1 = Column(Integer, ForeignKey("produtos.id"), nullable=False, index=True)
    produto_id_2 = Column(Integer, ForeignKey("produtos.id"), nullable=False, index=True)
    
    # Auditoria
    usuario_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    data_ignorado = Column(DateTime(timezone=True), server_default=func.now())
    
    # Constraint: um par só pode ser ignorado uma vez por tenant
    __table_args__ = (
        UniqueConstraint('tenant_id', 'produto_id_1', 'produto_id_2', name='uq_duplicata_ignorada'),
    )
