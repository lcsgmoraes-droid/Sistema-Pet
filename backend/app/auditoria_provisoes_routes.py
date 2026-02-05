"""
Rotas para Auditoria de Provisões
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List, Dict
from pydantic import BaseModel

from app.auth import get_current_user
from app.models import User
from app.db import get_session
from app.services.auditoria_provisao_service import auditar_provisoes, auditar_provisoes_anual


router = APIRouter(prefix="/auditoria/provisoes", tags=["Auditoria - Provisões"])


# ============================================================================
# SCHEMAS
# ============================================================================

class ItemAuditoriaResponse(BaseModel):
    item: str
    provisao: float
    realizado: float
    diferenca: float
    status: str
    status_emoji: str
    percentual_realizado: float


class AuditoriaMensalResponse(BaseModel):
    mes: int
    ano: int
    itens: List[ItemAuditoriaResponse]
    total_provisao: float
    total_realizado: float
    total_diferenca: float


# ============================================================================
# ENDPOINTS
# ============================================================================

@router.get("/mensal", response_model=AuditoriaMensalResponse)
def buscar_auditoria_mensal(
    mes: int,
    ano: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session)
):
    """
    Retorna auditoria de provisões vs realizado para um mês específico.
    
    Compara:
    - Simples Nacional
    - INSS
    - FGTS
    - Folha de Pagamento
    - Férias
    - 13º Salário
    
    Status possíveis:
    - OK (✅): Provisão = Realizado
    - AJUSTE (⚠️): Tem pagamento mas diferença existe
    - ACUMULANDO (🕒): Provisionado mas não pago
    - SEM_DADOS (➖): Sem provisão e sem pagamento
    """
    
    tenant_id = current_user.tenant_id
    
    itens = auditar_provisoes(db, tenant_id, mes, ano)
    
    # Calcular totais
    total_provisao = sum(item["provisao"] for item in itens)
    total_realizado = sum(item["realizado"] for item in itens)
    total_diferenca = sum(item["diferenca"] for item in itens)
    
    return {
        "mes": mes,
        "ano": ano,
        "itens": itens,
        "total_provisao": total_provisao,
        "total_realizado": total_realizado,
        "total_diferenca": total_diferenca
    }


@router.get("/anual")
def buscar_auditoria_anual(
    ano: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session)
):
    """
    Retorna auditoria consolidada do ano inteiro.
    
    Útil para:
    - Análise anual de provisões
    - Planejamento tributário
    - Relatórios para contabilidade
    """
    
    tenant_id = current_user.tenant_id
    
    resultado = auditar_provisoes_anual(db, tenant_id, ano)
    
    return {
        "ano": ano,
        "itens": resultado
    }


@router.get("/resumo")
def buscar_resumo_status(
    mes: int,
    ano: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session)
):
    """
    Retorna resumo rápido do status das provisões.
    
    Útil para dashboard e alertas.
    """
    
    tenant_id = current_user.tenant_id
    
    itens = auditar_provisoes(db, tenant_id, mes, ano)
    
    # Contar status
    ok_count = sum(1 for item in itens if item["status"] == "OK")
    ajuste_count = sum(1 for item in itens if item["status"] == "AJUSTE")
    acumulando_count = sum(1 for item in itens if item["status"] == "ACUMULANDO")
    sem_dados_count = sum(1 for item in itens if item["status"] == "SEM_DADOS")
    
    return {
        "mes": mes,
        "ano": ano,
        "total_itens": len(itens),
        "ok": ok_count,
        "ajuste": ajuste_count,
        "acumulando": acumulando_count,
        "sem_dados": sem_dados_count,
        "status_geral": "OK" if ajuste_count == 0 else "ATENÇÃO"
    }
