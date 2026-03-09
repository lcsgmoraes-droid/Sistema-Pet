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
from sqlalchemy import func
from typing import List, Dict, Any, Optional
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel

from app.db import get_session
from app.auth.dependencies import get_current_user_and_tenant
from app.vendas_models import Venda, VendaItem
from app.services.opportunity_background_processor import _cache_manager
from app.opportunity_events_models import OpportunityEvent, OpportunityEventTypeEnum


router = APIRouter(prefix="/internal/pdv", tags=["pdv-internal"])


# ============================================================================
# HELPER: Gera sugestões baseadas no histórico de compras do cliente
# ============================================================================

def _gerar_sugestoes_historico(
    db: Session,
    cliente_id: int,
    tenant_id,
    excluir_produto_ids: List[int] = None
) -> List[Dict[str, Any]]:
    """
    Consulta os produtos mais comprados pelo cliente (últimas 50 vendas)
    e retorna uma lista de sugestões ordenadas por frequência.
    """
    try:
        excluir = set(excluir_produto_ids or [])

        # Top produtos comprados pelo cliente neste tenant
        rows = (
            db.query(
                VendaItem.produto_id,
                VendaItem.produto_nome,
                func.count(VendaItem.id).label("frequencia"),
            )
            .join(Venda, VendaItem.venda_id == Venda.id)
            .filter(
                Venda.cliente_id == cliente_id,
                Venda.tenant_id == tenant_id,
                Venda.status.in_(["finalizada", "pago_nf"]),
                VendaItem.produto_id.isnot(None),
            )
            .group_by(VendaItem.produto_id, VendaItem.produto_nome)
            .order_by(func.count(VendaItem.id).desc())
            .limit(20)
            .all()
        )

        sugestoes = []
        for row in rows:
            if row.produto_id in excluir:
                continue
            freq = row.frequencia
            if freq == 1:
                descricao = "Comprou 1 vez — produto do histórico"
            else:
                descricao = f"Comprou {freq}x — produto frequente"
            sugestoes.append({
                "id": f"hist_cli{cliente_id}_prod{row.produto_id}",
                "titulo": row.produto_nome or f"Produto #{row.produto_id}",
                "descricao_curta": descricao,
                "tipo": "historico",
                "produto_sugerido_id": row.produto_id,
                "produto_origem_id": None,
                "confianca": round(min(1.0, freq / 10.0), 2),
            })
            if len(sugestoes) >= 5:
                break

        return sugestoes

    except Exception:
        return []


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
        # Nesse caso, gerar sugestões on-demand a partir do histórico do cliente
        if not oportunidades:
            # Produtos já no carrinho (para não sugerir o que já está sendo comprado)
            itens_atuais = db.query(VendaItem.produto_id).filter(
                VendaItem.venda_id == venda_id,
                VendaItem.produto_id.isnot(None),
            ).all()
            ids_no_carrinho = [row.produto_id for row in itens_atuais]

            oportunidades = _gerar_sugestoes_historico(
                db=db,
                cliente_id=venda.cliente_id,
                tenant_id=tenant_id,
                excluir_produto_ids=ids_no_carrinho,
            )

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


@router.get("/oportunidades-cliente/{cliente_id}")
def buscar_oportunidades_por_cliente(
    cliente_id: int,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
) -> Dict[str, Any]:
    """
    Busca sugestões baseadas no histórico de compras do cliente.
    Usado quando ainda não há uma venda salva (nova venda em andamento).
    """
    try:
        current_user, tenant_id = user_and_tenant

        oportunidades = _gerar_sugestoes_historico(
            db=db,
            cliente_id=cliente_id,
            tenant_id=tenant_id,
        )

        return {
            "venda_id": None,
            "cliente_id": cliente_id,
            "oportunidades": oportunidades,
        }

    except Exception as e:
        import logging
        logging.getLogger(__name__).debug(f"Erro ao buscar oportunidades cliente {cliente_id}: {str(e)}")
        return {
            "venda_id": None,
            "cliente_id": cliente_id,
            "oportunidades": [],
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
