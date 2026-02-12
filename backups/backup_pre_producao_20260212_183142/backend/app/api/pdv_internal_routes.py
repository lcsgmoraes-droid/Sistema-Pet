"""
PDV INTERNAL ROUTES

Rotas internas para o PDV consultar dados preparados em background.
NÃO são rotas públicas - apenas para uso do frontend PDV.

Segurança:
- Multi-tenant obrigatório
- Read-only para consultas, Write-only para eventos
- Fail-safe (erro = lista vazia / sucesso silencioso)
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel

from app.db import get_session
from app.auth.dependencies import get_current_user_and_tenant
from app.vendas_models import Venda
from app.services.opportunity_background_processor import _cache_manager
from app.opportunity_events_models import OpportunityEvent, OpportunityEventTypeEnum


router = APIRouter(prefix="/internal/pdv", tags=["pdv-internal"])


# ============================================================================
# SCHEMAS PYDANTIC
# ============================================================================

class RegistrarEventoOportunidadeRequest(BaseModel):
    """Schema para registro de evento de oportunidade"""
    opportunity_id: str
    event_type: str  # "oportunidade_convertida", "oportunidade_refinada", "oportunidade_rejeitada"
    user_id: Optional[int] = None
    contexto: str = "PDV"
    extra_data: Optional[Dict[str, Any]] = None


@router.get("/oportunidades/{venda_id}")
def buscar_oportunidades_venda(
    venda_id: int,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
) -> Dict[str, Any]:
    """
    Busca oportunidades preparadas em background para uma venda específica.
    
    🔒 ENDPOINT INTERNO - Uso exclusivo do frontend PDV.
    
    Comportamento:
    - Busca oportunidades do cache em memória (TTL: 5 minutos)
    - Valida que venda pertence ao tenant do usuário autenticado
    - Retorna lista vazia se:
      - Venda não existe
      - Venda não possui cliente
      - Cache expirou ou não existe
      - Ocorreu erro (fail-safe)
    
    Segurança:
    - ✅ Multi-tenant: Valida tenant_id obrigatoriamente
    - ✅ Read-only: Apenas leitura do cache
    - ✅ Fail-safe: Nunca lança exceção ao cliente
    
    Args:
        venda_id: ID da venda
        
    Returns:
        {
            "venda_id": int,
            "cliente_id": int | None,
            "oportunidades": [...]  # Lista de oportunidades ou []
        }
    """
    try:
        current_user, tenant_id = user_and_tenant
        
        # ============================================================================
        # 🔒 VALIDAÇÃO 1: Venda existe e pertence ao tenant
        # ============================================================================
        venda = db.query(Venda).filter(
            Venda.id == venda_id,
            Venda.tenant_id == tenant_id  # ✅ Isolamento multi-tenant
        ).first()
        
        if not venda:
            # Venda não existe ou não pertence ao tenant - retornar vazio
            return {
                "venda_id": venda_id,
                "cliente_id": None,
                "oportunidades": []
            }
        
        # ============================================================================
        # 🔒 VALIDAÇÃO 2: Venda possui cliente selecionado
        # ============================================================================
        if not venda.cliente_id:
            # Sem cliente = sem oportunidades contextualizadas
            return {
                "venda_id": venda_id,
                "cliente_id": None,
                "oportunidades": []
            }
        
        # ============================================================================
        # 📦 BUSCAR OPORTUNIDADES DO CACHE (read-only)
        # ============================================================================
        session_id = f"venda_{venda_id}"
        oportunidades = _cache_manager.get_opportunities(
            tenant_id=UUID(str(tenant_id)),
            session_id=session_id
        )
        
        # Cache pode retornar None se expirou ou não existe
        if oportunidades is None:
            oportunidades = []
        
        return {
            "venda_id": venda_id,
            "cliente_id": venda.cliente_id,
            "oportunidades": oportunidades
        }
        
    except Exception as e:
        # ============================================================================
        # 🛡️ FAIL-SAFE: Nunca deixar endpoint falhar
        # ============================================================================
        # Log silencioso (debug only)
        import logging
        logger = logging.getLogger(__name__)
        logger.debug(f"Erro ao buscar oportunidades (venda {venda_id}): {str(e)}")
        
        # Retornar lista vazia em caso de qualquer erro
        return {
            "venda_id": venda_id,
            "cliente_id": None,
            "oportunidades": []
        }


@router.post("/eventos-oportunidade")
def registrar_evento_oportunidade(
    dados: RegistrarEventoOportunidadeRequest,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
) -> Dict[str, Any]:
    """
    Registra evento de interação do operador com oportunidade.
    
    🔒 ENDPOINT INTERNO - Uso exclusivo do frontend PDV.
    
    Comportamento:
    - Registra evento de forma fail-safe (nunca lança exceção)
    - Valida tenant_id para isolamento multi-tenant
    - Fire-and-forget: frontend não aguarda resposta
    - Tipos de evento:
      - oportunidade_convertida: Operador adicionou ao carrinho
      - oportunidade_refinada: Operador pediu alternativa
      - oportunidade_rejeitada: Operador ignorou sugestão
    
    Segurança:
    - ✅ Multi-tenant: Valida tenant_id obrigatoriamente
    - ✅ Write-only: Apenas escrita de eventos
    - ✅ Fail-safe: Nunca lança exceção ao cliente
    
    Args:
        dados: Dados do evento
        
    Returns:
        {"success": true, "event_id": str}
    """
    try:
        current_user, tenant_id = user_and_tenant
        
        # ============================================================================
        # 🔒 VALIDAÇÃO: Mapear string para enum
        # ============================================================================
        try:
            event_type_enum = OpportunityEventTypeEnum(dados.event_type)
        except ValueError:
            # Tipo de evento inválido - retornar sucesso silencioso (fail-safe)
            return {"success": True, "event_id": None}
        
        # ============================================================================
        # 📝 CRIAR EVENTO NO BANCO
        # ============================================================================
        evento = OpportunityEvent(
            tenant_id=tenant_id,
            opportunity_id=UUID(dados.opportunity_id) if dados.opportunity_id else None,
            event_type=event_type_enum,
            user_id=current_user.id,
            contexto=dados.contexto,
            extra_data=dados.extra_data or {}
        )
        
        db.add(evento)
        db.commit()
        db.refresh(evento)
        
        return {
            "success": True,
            "event_id": str(evento.id)
        }
        
    except Exception as e:
        # ============================================================================
        # 🛡️ FAIL-SAFE: Nunca deixar endpoint falhar
        # ============================================================================
        import logging
        logger = logging.getLogger(__name__)
        logger.debug(f"Erro ao registrar evento de oportunidade: {str(e)}")
        
        # Retornar sucesso silencioso em caso de qualquer erro
        # Frontend não precisa saber que falhou
        return {
            "success": True,
            "event_id": None
        }
