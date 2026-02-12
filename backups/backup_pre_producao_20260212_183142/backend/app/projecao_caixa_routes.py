"""
Rotas de Projeção de Caixa
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List

from app.db import get_session
from app.auth.core import get_current_user
from app.auth.dependencies import get_current_user_and_tenant
from app.services.projecao_caixa_service import projetar_caixa, obter_resumo_projecao

router = APIRouter(prefix="/projecao-caixa", tags=["Projeção de Caixa"])


@router.get("/")
def buscar_projecao(
    meses_a_frente: int = 3,
    db: Session = Depends(get_session),
    auth = Depends(get_current_user_and_tenant)
):
    """
    Retorna projeção de caixa para os próximos N meses.
    
    Parâmetros:
    - meses_a_frente: Número de meses para projetar (padrão: 3)
    """
    current_user, tenant_id = auth
    
    projecao = projetar_caixa(
        db=db,
        tenant_id=tenant_id,
        meses_a_frente=meses_a_frente
    )
    
    return {
        "sucesso": True,
        "projecao": projecao,
        "meses_projetados": len(projecao)
    }


@router.get("/resumo")
def buscar_resumo_projecao(
    meses_a_frente: int = 3,
    db: Session = Depends(get_session),
    auth = Depends(get_current_user_and_tenant)
):
    """
    Retorna resumo da projeção de caixa.
    
    Fornece indicadores agregados como:
    - Total de receitas projetadas
    - Total de despesas projetadas
    - Saldo total projetado
    - Quantidade de meses positivos/negativos
    - Tendência geral
    """
    current_user, tenant_id = auth
    
    resumo = obter_resumo_projecao(
        db=db,
        tenant_id=tenant_id,
        meses_a_frente=meses_a_frente
    )
    
    return {
        "sucesso": True,
        "resumo": resumo
    }
