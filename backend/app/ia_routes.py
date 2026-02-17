"""
ABA 5: Fluxo de Caixa Preditivo - Endpoints FastAPI

Endpoints:
- GET  /api/ia/fluxo/indices-saude/{usuario_id}
- GET  /api/ia/fluxo/projecoes/{usuario_id}
- POST /api/ia/fluxo/projetar-15-dias/{usuario_id}
- POST /api/ia/fluxo/simular-cenario/{usuario_id}
- GET  /api/ia/fluxo/alertas/{usuario_id}
- POST /api/ia/fluxo/registrar-movimentacao/{usuario_id}
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel

from app.auth import get_current_user
from app.auth.dependencies import get_current_user_and_tenant
from app.db import get_session
from app.models import User
from app.ia.aba5_fluxo_caixa import (
    calcular_indices_saude,
    projetar_fluxo_15_dias,
    obter_projecoes_proximos_dias,
    simular_cenario,
    gerar_alertas_caixa,
    registrar_movimentacao
)

# ============================================================================
# ROUTER
# ============================================================================

router = APIRouter(
    prefix="/ia/fluxo",
    tags=["IA - Fluxo de Caixa"],
    dependencies=[Depends(get_current_user)]
)

# ============================================================================
# SCHEMAS (REQUEST/RESPONSE)
# ============================================================================

class IndicesSaudeResponse(BaseModel):
    saldo_atual: float
    despesa_media_diaria: float
    dias_de_caixa: float
    dias_para_receber: float
    dias_para_pagar: float
    ciclo_operacional: float
    receita_mensal_estimada: float
    despesa_mensal_estimada: float
    saldo_mensal_estimado: float
    status: str  # critico, alerta, ok
    tendencia: str  # piorando, estavel, melhorando
    percentual_variacao_7d: float
    score_saude: float


class ProjecaoResponse(BaseModel):
    data: str
    dias_futuros: int
    saldo_estimado: float
    entrada_estimada: float
    saida_estimada: float
    limite_inferior: float
    limite_superior: float
    vai_faltar_caixa: bool
    alerta_nivel: str


class AlertaResponse(BaseModel):
    tipo: str
    titulo: str
    mensagem: str
    data: str


class SimularCenarioRequest(BaseModel):
    cenario: str  # otimista, pessimista, realista


class SimularCenarioResponse(BaseModel):
    cenario: str
    projecoes_ajustadas: List[dict]


class RegistrarMovimentacaoRequest(BaseModel):
    tipo: str  # receita, despesa
    categoria: str
    valor: float
    descricao: Optional[str] = ""
    data_prevista: Optional[datetime] = None


class RegistrarMovimentacaoResponse(BaseModel):
    id: int
    tipo: str
    categoria: str
    valor: float
    status: str


# ============================================================================
# ENDPOINT 1: GET ÍNDICES DE SAÚDE DO CAIXA
# ============================================================================

@router.get(
    "/indices-saude/{usuario_id}",
    response_model=IndicesSaudeResponse,
    summary="Índices de saúde do caixa",
    description="Retorna índices calculados: dias de caixa, status, score, tendência"
)
async def get_indices_saude(
    usuario_id: int,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """
    Retorna os índices de saúde do caixa.
    
    **Exemplo de resposta:**
    ```json
    {
      "saldo_atual": 15000.50,
      "dias_de_caixa": 18.5,
      "status": "ok",
      "score_saude": 82.3,
      "tendencia": "melhorando"
    }
    ```
    """
    current_user, tenant_id = user_and_tenant
    
    # Verificar permissão
    if usuario_id != current_user.id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Sem permissão")
    
    # Calcular índices
    resultado = calcular_indices_saude(usuario_id, db)
    
    if not resultado:
        raise HTTPException(status_code=500, detail="Erro ao calcular índices")
    
    return resultado


# ============================================================================
# ENDPOINT 2: GET PROJEÇÕES JÁ CALCULADAS
# ============================================================================

@router.get(
    "/projecoes/{usuario_id}",
    response_model=List[ProjecaoResponse],
    summary="Projeções de fluxo de caixa",
    description="Retorna projeções já calculadas para os próximos dias"
)
async def get_projecoes(
    usuario_id: int,
    dias: int = Query(15, description="Quantos dias futuro"),
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """
    Retorna projeções já calculadas.
    
    Se nenhuma projeção existir, retorna vazio (use POST /projetar-15-dias primeiro).
    """
    current_user, tenant_id = user_and_tenant
    
    if usuario_id != current_user.id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Sem permissão")
    
    projecoes = obter_projecoes_proximos_dias(usuario_id, dias, db)
    
    # Transformar para ProjecaoResponse
    return [
        ProjecaoResponse(
            data=p['data'] if isinstance(p['data'], str) else p['data'].isoformat(),
            dias_futuros=p['dias_futuros'],
            saldo_estimado=p['saldo_estimado'],
            entrada_estimada=p['entrada_estimada'],
            saida_estimada=p['saida_estimada'],
            limite_inferior=p['limite_inferior'],
            limite_superior=p['limite_superior'],
            vai_faltar_caixa=p['vai_faltar_caixa'],
            alerta_nivel=p['alerta_nivel']
        )
        for p in projecoes
    ]


# ============================================================================
# ENDPOINT 3: POST PROJETAR 15 DIAS
# ============================================================================

@router.post(
    "/projetar-15-dias/{usuario_id}",
    response_model=List[ProjecaoResponse],
    summary="Gerar projeção 15 dias",
    description="Treina Prophet e projeta fluxo de caixa para próximos 15 dias"
)
async def post_projetar_15_dias(
    usuario_id: int,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """
    Calcula projeção de 15 dias usando Prophet.
    
    ⚠️ **Requer mínimo 10 dias de dados históricos**
    
    **Exemplo de resposta:**
    ```json
    [
      {
        "data": "2026-01-12",
        "saldo_estimado": 15200.00,
        "vai_faltar_caixa": false,
        "alerta_nivel": "ok"
      },
      ...
    ]
    ```
    """
    current_user, tenant_id = user_and_tenant
    
    if usuario_id != current_user.id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Sem permissão")
    
    projecoes = projetar_fluxo_15_dias(usuario_id, db)
    
    if not projecoes:
        raise HTTPException(
            status_code=400,
            detail="Dados insuficientes. Precisa mínimo 10 dias de histórico."
        )
    
    # Transformar para ProjecaoResponse
    return [
        ProjecaoResponse(
            data=p['data'] if isinstance(p['data'], str) else p['data'].isoformat(),
            dias_futuros=p['dias_futuros'],
            saldo_estimado=p['saldo_estimado'],
            entrada_estimada=p['entrada_estimada'],
            saida_estimada=p['saida_estimada'],
            limite_inferior=p['limite_inferior'],
            limite_superior=p['limite_superior'],
            vai_faltar_caixa=p['vai_faltar_caixa'],
            alerta_nivel=p['alerta_nivel']
        )
        for p in projecoes
    ]


# ============================================================================
# ENDPOINT 4: POST SIMULAR CENÁRIO
# ============================================================================

@router.post(
    "/simular-cenario/{usuario_id}",
    response_model=SimularCenarioResponse,
    summary="Simular cenário",
    description="Simula cenários: otimista, pessimista, realista"
)
async def post_simular_cenario(
    usuario_id: int,
    request: SimularCenarioRequest,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """
    Simula cenários diferentes sobre a projeção atual.
    
    **Cenários:**
    - `otimista`: +20% entradas, -10% saídas
    - `pessimista`: -20% entradas, +10% saídas
    - `realista`: sem modificação
    
    **Exemplo request:**
    ```json
    {
      "cenario": "otimista"
    }
    ```
    """
    current_user, tenant_id = user_and_tenant
    
    if usuario_id != current_user.id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Sem permissão")
    
    if request.cenario not in ["otimista", "pessimista", "realista"]:
        raise HTTPException(
            status_code=400,
            detail="Cenário inválido. Use: otimista, pessimista ou realista"
        )
    
    resultado = simular_cenario(usuario_id, request.cenario, db)
    
    if not resultado:
        raise HTTPException(status_code=500, detail="Erro ao simular cenário")
    
    return resultado


# ============================================================================
# ENDPOINT 5: GET ALERTAS
# ============================================================================

@router.get(
    "/alertas/{usuario_id}",
    response_model=List[AlertaResponse],
    summary="Alertas de caixa",
    description="Retorna alertas: caixa crítico, tendência negativa, projeção negativa"
)
async def get_alertas(
    usuario_id: int,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """
    Retorna lista de alertas gerados.
    
    **Tipos de alertas:**
    - `critico`: Caixa < 7 dias ou projeção negativa
    - `alerta`: Caixa < 15 dias
    - `aviso`: Tendência piorando
    
    **Exemplo de resposta:**
    ```json
    [
      {
        "tipo": "critico",
        "titulo": "🚨 CAIXA CRÍTICO",
        "mensagem": "Caixa com apenas 5.2 dias..."
      }
    ]
    ```
    """
    current_user, tenant_id = user_and_tenant
    
    if usuario_id != current_user.id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Sem permissão")
    
    alertas = gerar_alertas_caixa(usuario_id, db)
    
    return alertas


# ============================================================================
# ENDPOINT 6: POST REGISTRAR MOVIMENTAÇÃO
# ============================================================================

@router.post(
    "/registrar-movimentacao/{usuario_id}",
    response_model=RegistrarMovimentacaoResponse,
    summary="Registrar movimentação manual",
    description="Lança uma movimentação manual de receita ou despesa"
)
async def post_registrar_movimentacao(
    usuario_id: int,
    request: RegistrarMovimentacaoRequest,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """
    Registra uma movimentação manual no fluxo de caixa.
    
    **Exemplo request:**
    ```json
    {
      "tipo": "receita",
      "categoria": "Venda PDV",
      "valor": 1500.00,
      "descricao": "Venda de ração premium",
      "data_prevista": "2026-01-12T10:00:00"
    }
    ```
    """
    current_user, tenant_id = user_and_tenant
    
    if usuario_id != current_user.id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Sem permissão")
    
    if request.tipo not in ["receita", "despesa"]:
        raise HTTPException(
            status_code=400,
            detail="Tipo inválido. Use: receita ou despesa"
        )
    
    if request.valor <= 0:
        raise HTTPException(status_code=400, detail="Valor deve ser > 0")
    
    mov = registrar_movimentacao(
        usuario_id=usuario_id,
        tipo=request.tipo,
        categoria=request.categoria,
        valor=request.valor,
        descricao=request.descricao,
        data_prevista=request.data_prevista,
        db=db
    )
    
    if not mov:
        raise HTTPException(status_code=500, detail="Erro ao registrar movimentação")
    
    return {
        "id": mov.id,
        "tipo": mov.tipo,
        "categoria": mov.categoria,
        "valor": mov.valor,
        "status": mov.status
    }


# ============================================================================
# HEALTH CHECK
# ============================================================================

@router.get(
    "/health",
    tags=["Health"],
    summary="Health check",
    description="Verifica se o módulo IA está funcional"
)
async def health_check():
    """
    Health check do módulo IA.
    """
    return {
        "status": "ok",
        "modulo": "ABA 5 - Fluxo de Caixa Preditivo",
        "endpoints": 6,
        "database": "ok"
    }
