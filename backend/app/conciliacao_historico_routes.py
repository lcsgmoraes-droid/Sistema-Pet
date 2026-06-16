"""
Routes para Histórico de Conciliações

Endpoints:
1. POST /api/conciliacao/historico/verificar - Verifica se data/operadora já foi conciliada
2. POST /api/conciliacao/historico/iniciar - Inicia novo registro de conciliação
3. PUT /api/conciliacao/historico/{id}/aba1 - Marca Aba 1 como concluída
4. PUT /api/conciliacao/historico/{id}/aba2 - Marca Aba 2 como concluída
5. PUT /api/conciliacao/historico/{id}/aba3 - Marca Aba 3 como concluída e finaliza
6. GET /api/conciliacao/historico - Lista histórico de conciliações
7. GET /api/conciliacao/historico/{id} - Detalhes de uma conciliação
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc
from datetime import datetime, date
from typing import Optional, List
from pydantic import BaseModel, Field
from decimal import Decimal

from .db import get_session as get_db
from .auth import get_current_user_and_tenant
from .conciliacao_models import HistoricoConciliacao


# ============================================================================
# ROUTER
# ============================================================================
router = APIRouter(prefix="/conciliacao/historico", tags=["Histórico Conciliação"])


# ============================================================================
# SCHEMAS
# ============================================================================

class VerificarConciliacaoRequest(BaseModel):
    data_referencia: date = Field(..., description="Data a ser conciliada (ex: 2026-02-10)")
    operadora: str = Field(..., description="Nome da operadora (ex: Stone, PagSeguro)")

class VerificarConciliacaoResponse(BaseModel):
    ja_conciliado: bool
    pode_reprocessar: bool
    mensagem: str
    historico: Optional[dict] = None

class IniciarConciliacaoRequest(BaseModel):
    data_referencia: date
    operadora: str
    arquivos: Optional[List[dict]] = Field(default=[], description="Lista de arquivos enviados")
    observacoes: Optional[str] = None

class IniciarConciliacaoResponse(BaseModel):
    id: int
    data_referencia: date
    operadora: str
    status: str
    mensagem: str

class AtualizarAbaRequest(BaseModel):
    totais: Optional[dict] = None
    divergencias_encontradas: Optional[int] = None
    divergencias_aceitas: Optional[bool] = None
    parcelas_amarradas: Optional[int] = None
    parcelas_orfas: Optional[int] = None
    observacoes: Optional[str] = None

class AtualizarAbaResponse(BaseModel):
    id: int
    aba_concluida: str
    concluida_em: datetime
    todas_concluidas: bool
    mensagem: str


# ============================================================================
# ENDPOINTS
# ============================================================================

@router.post("/verificar", response_model=VerificarConciliacaoResponse)
def verificar_conciliacao(
    request: VerificarConciliacaoRequest,
    db: Session = Depends(get_db),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """
    Verifica se uma data/operadora já foi conciliada.
    
    Retorna:
    - ja_conciliado: True se já existe registro
    - pode_reprocessar: True se usuário pode reprocessar (com aviso)
    - mensagem: Orientação sobre o que fazer
    - historico: Dados do registro existente (se houver)
    """
    _current_user, tenant_id = user_and_tenant
    
    # Buscar registro existente
    historico_existente = db.query(HistoricoConciliacao).filter(
        and_(
            HistoricoConciliacao.tenant_id == tenant_id,
            HistoricoConciliacao.data_referencia == request.data_referencia,
            HistoricoConciliacao.operadora == request.operadora,
            HistoricoConciliacao.status != 'cancelada'  # Ignora canceladas
        )
    ).first()
    
    if not historico_existente:
        return VerificarConciliacaoResponse(
            ja_conciliado=False,
            pode_reprocessar=True,
            mensagem=f"Data {request.data_referencia} da operadora {request.operadora} ainda não foi conciliada. Pode prosseguir.",
            historico=None
        )
    
    # Se concluída, bloqueia reprocessamento
    if historico_existente.status == 'concluida':
        return VerificarConciliacaoResponse(
            ja_conciliado=True,
            pode_reprocessar=False,
            mensagem=f"⚠️ ATENÇÃO: Data {request.data_referencia} da operadora {request.operadora} já foi conciliada em {historico_existente.concluida_em.strftime('%d/%m/%Y %H:%M')}. Reprocessamento não recomendado.",
            historico=historico_existente.to_dict()
        )
    
    # Se em andamento, permite continuar
    return VerificarConciliacaoResponse(
        ja_conciliado=True,
        pode_reprocessar=True,
        mensagem=f"Data {request.data_referencia} da operadora {request.operadora} tem conciliação em andamento desde {historico_existente.criado_em.strftime('%d/%m/%Y %H:%M')}. Você pode continuar de onde parou.",
        historico=historico_existente.to_dict()
    )


@router.post("/iniciar", response_model=IniciarConciliacaoResponse)
def iniciar_conciliacao(
    request: IniciarConciliacaoRequest,
    db: Session = Depends(get_db),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """
    Inicia novo registro de conciliação.
    
    Cria registro em status 'em_andamento'.
    Será atualizado conforme abas são concluídas.
    """
    current_user, tenant_id = user_and_tenant
    usuario = current_user.email or current_user.username
    
    # Verificar se já existe conciliação em andamento
    existente = db.query(HistoricoConciliacao).filter(
        and_(
            HistoricoConciliacao.tenant_id == tenant_id,
            HistoricoConciliacao.data_referencia == request.data_referencia,
            HistoricoConciliacao.operadora == request.operadora,
            HistoricoConciliacao.status == 'em_andamento'
        )
    ).first()
    
    if existente:
        return IniciarConciliacaoResponse(
            id=existente.id,
            data_referencia=existente.data_referencia,
            operadora=existente.operadora,
            status=existente.status,
            mensagem="Conciliação já estava em andamento. Continuando registro existente."
        )
    
    # Criar novo registro
    novo_historico = HistoricoConciliacao(
        tenant_id=tenant_id,
        data_referencia=request.data_referencia,
        operadora=request.operadora,
        status='em_andamento',
        arquivos_processados=request.arquivos,
        usuario_responsavel=usuario,
        observacoes=request.observacoes
    )
    
    db.add(novo_historico)
    db.commit()
    db.refresh(novo_historico)
    
    return IniciarConciliacaoResponse(
        id=novo_historico.id,
        data_referencia=novo_historico.data_referencia,
        operadora=novo_historico.operadora,
        status=novo_historico.status,
        mensagem=f"Conciliação iniciada para {request.data_referencia} - {request.operadora}"
    )


@router.put("/{historico_id}/aba1", response_model=AtualizarAbaResponse)
def concluir_aba1(
    historico_id: int,
    request: AtualizarAbaRequest,
    db: Session = Depends(get_db),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """Marca Aba 1 (Conciliação de Vendas) como concluída"""
    _current_user, tenant_id = user_and_tenant
    
    historico = db.query(HistoricoConciliacao).filter(
        and_(
            HistoricoConciliacao.id == historico_id,
            HistoricoConciliacao.tenant_id == tenant_id
        )
    ).first()
    
    if not historico:
        raise HTTPException(status_code=404, detail="Histórico não encontrado")
    
    # Atualizar Aba 1
    historico.aba1_concluida = True
    historico.aba1_concluida_em = datetime.now()
    
    # Atualizar totais se fornecido
    if request.totais:
        if not historico.totais:
            historico.totais = {}
        historico.totais.update(request.totais)
    
    if request.observacoes:
        historico.observacoes = request.observacoes
    
    db.commit()
    db.refresh(historico)
    
    todas_concluidas = historico.aba1_concluida and historico.aba2_concluida and historico.aba3_concluida
    
    return AtualizarAbaResponse(
        id=historico.id,
        aba_concluida="aba1",
        concluida_em=historico.aba1_concluida_em,
        todas_concluidas=todas_concluidas,
        mensagem="Aba 1 (Vendas) concluída com sucesso"
    )


@router.put("/{historico_id}/aba2", response_model=AtualizarAbaResponse)
def concluir_aba2(
    historico_id: int,
    request: AtualizarAbaRequest,
    db: Session = Depends(get_db),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """Marca Aba 2 (Validação de Recebimentos) como concluída"""
    _current_user, tenant_id = user_and_tenant
    
    historico = db.query(HistoricoConciliacao).filter(
        and_(
            HistoricoConciliacao.id == historico_id,
            HistoricoConciliacao.tenant_id == tenant_id
        )
    ).first()
    
    if not historico:
        raise HTTPException(status_code=404, detail="Histórico não encontrado")
    
    # Atualizar Aba 2
    historico.aba2_concluida = True
    historico.aba2_concluida_em = datetime.now()
    
    # Atualizar divergências (Aba 2 específico)
    if request.divergencias_encontradas is not None:
        historico.divergencias_encontradas = request.divergencias_encontradas
    if request.divergencias_aceitas is not None:
        historico.divergencias_aceitas = request.divergencias_aceitas
    
    # Atualizar totais
    if request.totais:
        if not historico.totais:
            historico.totais = {}
        historico.totais.update(request.totais)
    
    if request.observacoes:
        historico.observacoes = request.observacoes
    
    db.commit()
    db.refresh(historico)
    
    todas_concluidas = historico.aba1_concluida and historico.aba2_concluida and historico.aba3_concluida
    
    return AtualizarAbaResponse(
        id=historico.id,
        aba_concluida="aba2",
        concluida_em=historico.aba2_concluida_em,
        todas_concluidas=todas_concluidas,
        mensagem="Aba 2 (Recebimentos) concluída com sucesso"
    )


@router.put("/{historico_id}/aba3", response_model=AtualizarAbaResponse)
def concluir_aba3(
    historico_id: int,
    request: AtualizarAbaRequest,
    db: Session = Depends(get_db),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """
    Marca Aba 3 (Amarração Automática) como concluída.
    
    Se todas as 3 abas estiverem concluídas, muda status para 'concluida'.
    """
    _current_user, tenant_id = user_and_tenant
    
    historico = db.query(HistoricoConciliacao).filter(
        and_(
            HistoricoConciliacao.id == historico_id,
            HistoricoConciliacao.tenant_id == tenant_id
        )
    ).first()
    
    if not historico:
        raise HTTPException(status_code=404, detail="Histórico não encontrado")
    
    # Atualizar Aba 3
    historico.aba3_concluida = True
    historico.aba3_concluida_em = datetime.now()
    
    # Atualizar métricas de amarração (Aba 3 específico)
    if request.parcelas_amarradas is not None:
        historico.parcelas_amarradas = request.parcelas_amarradas
    if request.parcelas_orfas is not None:
        historico.parcelas_orfas = request.parcelas_orfas
    
    # Calcular taxa de amarração
    if request.parcelas_amarradas is not None and request.parcelas_orfas is not None:
        total_parcelas = request.parcelas_amarradas + request.parcelas_orfas
        if total_parcelas > 0:
            historico.taxa_amarracao = Decimal(request.parcelas_amarradas / total_parcelas * 100)
    
    # Atualizar totais
    if request.totais:
        if not historico.totais:
            historico.totais = {}
        historico.totais.update(request.totais)
    
    if request.observacoes:
        historico.observacoes = request.observacoes
    
    # Se todas as abas concluídas, finalizar
    todas_concluidas = historico.aba1_concluida and historico.aba2_concluida and historico.aba3_concluida
    if todas_concluidas:
        historico.status = 'concluida'
        historico.concluida_em = datetime.now()
    
    db.commit()
    db.refresh(historico)
    
    mensagem = "Aba 3 (Amarração) concluída"
    if todas_concluidas:
        mensagem += ". 🎉 Conciliação completa finalizada!"
    
    return AtualizarAbaResponse(
        id=historico.id,
        aba_concluida="aba3",
        concluida_em=historico.aba3_concluida_em,
        todas_concluidas=todas_concluidas,
        mensagem=mensagem
    )


@router.get("")
def listar_historico(
    skip: int = 0,
    limit: int = 50,
    operadora: Optional[str] = None,
    status: Optional[str] = None,
    data_inicio: Optional[date] = None,
    data_fim: Optional[date] = None,
    db: Session = Depends(get_db),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """
    Lista histórico de conciliações com filtros.
    
    Filtros:
    - operadora: Filtrar por operadora específica
    - status: em_andamento | concluida | reprocessada | cancelada
    - data_inicio/data_fim: Range de datas conciliadas
    """
    _current_user, tenant_id = user_and_tenant
    
    query = db.query(HistoricoConciliacao).filter(
        HistoricoConciliacao.tenant_id == tenant_id
    )
    
    # Aplicar filtros
    if operadora:
        query = query.filter(HistoricoConciliacao.operadora == operadora)
    if status:
        query = query.filter(HistoricoConciliacao.status == status)
    if data_inicio:
        query = query.filter(HistoricoConciliacao.data_referencia >= data_inicio)
    if data_fim:
        query = query.filter(HistoricoConciliacao.data_referencia <= data_fim)
    
    # Ordenar por mais recente
    query = query.order_by(desc(HistoricoConciliacao.created_at))
    
    # Paginar
    total = query.count()
    historicos = query.offset(skip).limit(limit).all()
    
    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "items": [h.to_dict() for h in historicos]
    }


@router.get("/{historico_id}")
def detalhar_historico(
    historico_id: int,
    db: Session = Depends(get_db),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """Retorna detalhes completos de uma conciliação"""
    _current_user, tenant_id = user_and_tenant
    
    historico = db.query(HistoricoConciliacao).filter(
        and_(
            HistoricoConciliacao.id == historico_id,
            HistoricoConciliacao.tenant_id == tenant_id
        )
    ).first()
    
    if not historico:
        raise HTTPException(status_code=404, detail="Histórico não encontrado")
    
    return historico.to_dict()


@router.delete("/{historico_id}")
def cancelar_conciliacao(
    historico_id: int,
    db: Session = Depends(get_db),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """
    Cancela uma conciliação (marca como cancelada).
    Não pode cancelar conciliações já concluídas.
    """
    _current_user, tenant_id = user_and_tenant
    
    historico = db.query(HistoricoConciliacao).filter(
        and_(
            HistoricoConciliacao.id == historico_id,
            HistoricoConciliacao.tenant_id == tenant_id
        )
    ).first()
    
    if not historico:
        raise HTTPException(status_code=404, detail="Histórico não encontrado")
    
    if historico.status == 'concluida':
        raise HTTPException(
            status_code=400,
            detail="Não é possível cancelar conciliação já concluída"
        )
    
    historico.status = 'cancelada'
    db.commit()
    
    return {"message": "Conciliação cancelada com sucesso", "id": historico_id}
