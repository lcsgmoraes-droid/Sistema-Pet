"""
Schemas Pydantic para ConfiguracaoEntrega
Sprint 1 - Módulo de Entregas
"""
from typing import Optional
from pydantic import BaseModel
from uuid import UUID


class ConfiguracaoEntregaBase(BaseModel):
    """Campos base da configuração de entrega"""
    entregador_padrao_id: Optional[int] = None
    # Endereço completo do ponto inicial
    logradouro: Optional[str] = None
    cep: Optional[str] = None
    numero: Optional[str] = None
    complemento: Optional[str] = None
    bairro: Optional[str] = None
    cidade: Optional[str] = None
    estado: Optional[str] = None


class ConfiguracaoEntregaUpdate(ConfiguracaoEntregaBase):
    """Schema para atualização de configuração"""
    pass


class ConfiguracaoEntregaResponse(ConfiguracaoEntregaBase):
    """Schema de resposta da configuração"""
    id: int
    tenant_id: UUID

    class Config:
        from_attributes = True  # Pydantic v2
