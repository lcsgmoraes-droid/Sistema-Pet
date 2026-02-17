from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, validator


# ======================================
# SCHEMAS PARA ENVIO DE MENSAGEM
# ======================================

class WhatsAppEnviarRequest(BaseModel):
    """Request para enviar mensagem WhatsApp (mock)"""
    cliente_id: int = Field(..., description="ID do cliente")
    pet_id: Optional[int] = Field(None, description="ID do pet (opcional)")
    telefone: str = Field(..., description="Número do telefone com DDD", min_length=10, max_length=20)
    conteudo: str = Field(..., description="Conteúdo da mensagem", min_length=1)
    
    @validator('telefone')
    def validar_telefone(cls, v):
        """Remove caracteres especiais do telefone"""
        return ''.join(filter(str.isdigit, v))


class WhatsAppEnviarResponse(BaseModel):
    """Response após enviar mensagem"""
    id: int
    cliente_id: int
    telefone: str
    direcao: str
    status: str
    created_at: datetime
    mensagem: str = "Mensagem registrada. Envie manualmente pelo WhatsApp."
    
    class Config:
        from_attributes = True


# ======================================
# SCHEMAS PARA LISTAGEM
# ======================================

class WhatsAppMessageResponse(BaseModel):
    """Response com detalhes da mensagem WhatsApp"""
    id: int
    user_id: Optional[int] = None
    cliente_id: int
    pet_id: Optional[int]
    telefone: str
    direcao: str
    conteudo: str
    status: str
    created_at: datetime
    
    # Campos extras para UX
    preview: str = Field(default="", description="Preview do conteúdo (100 chars)")
    
    class Config:
        from_attributes = True


class WhatsAppHistoricoResponse(BaseModel):
    """Response com histórico de mensagens do cliente"""
    cliente_id: int
    total: int
    mensagens: list[WhatsAppMessageResponse]


# ======================================
# SCHEMAS PARA RECEBER MENSAGEM (MOCK)
# ======================================

class WhatsAppReceberRequest(BaseModel):
    """Request para registrar mensagem recebida (mock)"""
    cliente_id: int = Field(..., description="ID do cliente")
    telefone: str = Field(..., description="Número do telefone com DDD")
    conteudo: str = Field(..., description="Conteúdo da mensagem recebida")
    
    @validator('telefone')
    def validar_telefone(cls, v):
        """Remove caracteres especiais do telefone"""
        return ''.join(filter(str.isdigit, v))
