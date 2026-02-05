"""
Rotas de Simulação de Contratação
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from typing import Optional
from datetime import date

from app.auth.core import get_current_user
from app.auth.dependencies import get_current_user_and_tenant
from app.services.simulacao_contratacao_service import simular_contratacao

router = APIRouter(prefix="/simulacao-contratacao", tags=["Simulação de Contratação"])


class SimulacaoContratacaoRequest(BaseModel):
    """Payload para simular contratação"""
    salario_base: float = Field(..., description="Salário bruto mensal", gt=0)
    inss_percentual: float = Field(20.0, description="Percentual de INSS patronal", ge=0, le=100)
    fgts_percentual: float = Field(8.0, description="Percentual de FGTS", ge=0, le=100)
    meses: int = Field(6, description="Quantidade de meses para simular", ge=1, le=24)
    cargo: Optional[str] = Field(None, description="Nome do cargo")
    data_inicio: Optional[date] = Field(None, description="Data de início da contratação")


@router.post("/")
def simular_nova_contratacao(
    payload: SimulacaoContratacaoRequest,
    auth = Depends(get_current_user_and_tenant)
):
    """
    Simula o impacto financeiro de contratar um novo funcionário.
    
    **Nada é gravado no banco de dados** - é apenas uma projeção.
    
    Calcula:
    - Custo mensal (salário + encargos + provisões)
    - Detalhamento mês a mês
    - Totais acumulados
    - Análise de percentuais
    
    Útil para responder:
    "Se eu contratar agora, o que acontece com meu resultado e meu caixa?"
    """
    current_user, tenant_id = auth
    
    resultado = simular_contratacao(
        salario_base=payload.salario_base,
        inss_percentual=payload.inss_percentual,
        fgts_percentual=payload.fgts_percentual,
        meses=payload.meses,
        cargo=payload.cargo,
        data_inicio=payload.data_inicio,
    )
    
    return {
        "sucesso": True,
        "simulacao": resultado,
        "mensagem": f"Simulação realizada para {payload.meses} meses. Nada foi gravado no banco."
    }
