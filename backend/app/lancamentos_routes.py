"""
Rotas para Lançamentos Manuais e Recorrentes do Fluxo de Caixa
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, extract
from datetime import datetime, timedelta
from typing import Optional, List
from pydantic import BaseModel
from decimal import Decimal

from .db import get_session
from .auth import get_current_user
from .auth.dependencies import get_current_user_and_tenant
from app.utils.logger import logger
from .financeiro_models import (
    LancamentoManual, 
    LancamentoRecorrente,
    ContaBancaria,
    CategoriaFinanceira,
    ContaPagar,
    ContaReceber
)

router = APIRouter(prefix="/lancamentos", tags=["Lançamentos"])


# ============= SCHEMAS =============

class LancamentoManualCreate(BaseModel):
    tipo: str  # 'entrada' ou 'saida'
    valor: float
    descricao: str
    data_lancamento: str  # YYYY-MM-DD
    data_prevista: Optional[str] = None
    data_efetivacao: Optional[str] = None
    categoria_id: Optional[int] = None
    conta_bancaria_id: Optional[int] = None
    status: str = 'previsto'  # previsto ou realizado
    observacoes: Optional[str] = None
    gerado_automaticamente: bool = False
    confianca_ia: Optional[float] = None


class LancamentoManualUpdate(BaseModel):
    tipo: Optional[str] = None
    valor: Optional[float] = None
    descricao: Optional[str] = None
    data_lancamento: Optional[str] = None
    data_prevista: Optional[str] = None
    data_efetivacao: Optional[str] = None
    categoria_id: Optional[int] = None
    conta_bancaria_id: Optional[int] = None
    status: Optional[str] = None
    observacoes: Optional[str] = None


class LancamentoManualResponse(BaseModel):
    id: int
    tipo: str
    valor: float
    descricao: str
    data_lancamento: str
    data_prevista: Optional[str]
    data_efetivacao: Optional[str]
    categoria_id: Optional[int]
    categoria_nome: Optional[str]
    conta_bancaria_id: Optional[int]
    conta_bancaria_nome: Optional[str]
    status: str
    observacoes: Optional[str]
    gerado_automaticamente: bool
    confianca_ia: Optional[float]
    criado_em: str
    atualizado_em: str

    model_config = {"from_attributes": True}


class LancamentoRecorrenteCreate(BaseModel):
    tipo: str  # 'entrada' ou 'saida'
    descricao: str
    valor_medio: float
    categoria_id: Optional[int] = None
    conta_bancaria_id: Optional[int] = None
    frequencia: str = 'mensal'  # mensal, semanal, anual
    dia_vencimento: int
    data_inicio: str
    data_fim: Optional[str] = None
    gerar_automaticamente: bool = True
    gerar_com_antecedencia_dias: int = 5
    permite_ajuste_ia: bool = False
    observacoes: Optional[str] = None


class LancamentoRecorrenteUpdate(BaseModel):
    tipo: Optional[str] = None
    descricao: Optional[str] = None
    valor_medio: Optional[float] = None
    categoria_id: Optional[int] = None
    conta_bancaria_id: Optional[int] = None
    frequencia: Optional[str] = None
    dia_vencimento: Optional[int] = None
    data_inicio: Optional[str] = None
    data_fim: Optional[str] = None
    gerar_automaticamente: Optional[bool] = None
    gerar_com_antecedencia_dias: Optional[int] = None
    permite_ajuste_ia: Optional[bool] = None
    observacoes: Optional[str] = None
    ativo: Optional[bool] = None


class LancamentoRecorrenteResponse(BaseModel):
    id: int
    tipo: str
    descricao: str
    valor_medio: float
    categoria_id: Optional[int]
    categoria_nome: Optional[str]
    conta_bancaria_id: Optional[int]
    conta_bancaria_nome: Optional[str]
    frequencia: str
    dia_vencimento: int
    data_inicio: str
    data_fim: Optional[str]
    gerar_automaticamente: bool
    gerar_com_antecedencia_dias: int
    ultimo_mes_gerado: Optional[str]
    permite_ajuste_ia: bool
    observacoes: Optional[str]
    ativo: bool
    criado_em: str
    atualizado_em: str

    model_config = {"from_attributes": True}


# ============= LANÇAMENTOS MANUAIS =============

@router.post("/manuais", response_model=LancamentoManualResponse)
def criar_lancamento_manual(
    lancamento: LancamentoManualCreate,
    db: Session = Depends(get_session),
    auth = Depends(get_current_user_and_tenant)
):
    """Criar novo lançamento manual"""
    current_user, tenant_id = auth
    
    # Validar tipo
    if lancamento.tipo not in ['entrada', 'saida']:
        raise HTTPException(status_code=400, detail="Tipo deve ser 'entrada' ou 'saida'")
    
    # Validar status
    if lancamento.status not in ['previsto', 'realizado']:
        raise HTTPException(status_code=400, detail="Status deve ser 'previsto' ou 'realizado'")
    
    # Converter datas
    data_lancamento = datetime.strptime(lancamento.data_lancamento, "%Y-%m-%d").date()
    data_prevista = datetime.strptime(lancamento.data_prevista, "%Y-%m-%d").date() if lancamento.data_prevista else None
    data_efetivacao = datetime.strptime(lancamento.data_efetivacao, "%Y-%m-%d").date() if lancamento.data_efetivacao else None
    
    # Criar lançamento
    novo_lancamento = LancamentoManual(
        tipo=lancamento.tipo,
        valor=Decimal(str(lancamento.valor)),
        descricao=lancamento.descricao,
        data_lancamento=data_lancamento,
        data_prevista=data_prevista,
        data_efetivacao=data_efetivacao,
        categoria_id=lancamento.categoria_id,
        conta_bancaria_id=lancamento.conta_bancaria_id,
        status=lancamento.status,
        observacoes=lancamento.observacoes,
        gerado_automaticamente=lancamento.gerado_automaticamente,
        confianca_ia=lancamento.confianca_ia
    )
    
    db.add(novo_lancamento)
    db.commit()
    db.refresh(novo_lancamento)
    
    # INTEGRAÇÃO: Criar conta a pagar ou receber correspondente
    try:
        if lancamento.tipo == 'saida':
            # Criar conta a pagar
            conta_pagar = ContaPagar(
                descricao=lancamento.descricao,
                categoria_id=lancamento.categoria_id,
                valor_original=Decimal(str(lancamento.valor)),
                valor_final=Decimal(str(lancamento.valor)),
                valor_pago=Decimal(str(lancamento.valor)) if lancamento.status == 'realizado' else Decimal('0'),
                data_emissao=data_lancamento,
                data_vencimento=data_prevista or data_lancamento,
                data_pagamento=data_efetivacao if lancamento.status == 'realizado' else None,
                status='pago' if lancamento.status == 'realizado' else 'pendente',
                observacoes=f"Gerado automaticamente do lançamento manual #{novo_lancamento.id}. {lancamento.observacoes or ''}",
                user_id=current_user.id
            )
            db.add(conta_pagar)
        
        elif lancamento.tipo == 'entrada':
            # Criar conta a receber
            conta_receber = ContaReceber(
                descricao=lancamento.descricao,
                categoria_id=lancamento.categoria_id,
                dre_subcategoria_id=1,  # TODO: Mapear baseado na categoria
                canal='loja_fisica',  # Lançamento manual = loja física
                valor_original=Decimal(str(lancamento.valor)),
                valor_final=Decimal(str(lancamento.valor)),
                valor_recebido=Decimal(str(lancamento.valor)) if lancamento.status == 'realizado' else Decimal('0'),
                data_emissao=data_lancamento,
                data_vencimento=data_prevista or data_lancamento,
                data_recebimento=data_efetivacao if lancamento.status == 'realizado' else None,
                status='recebido' if lancamento.status == 'realizado' else 'pendente',
                observacoes=f"Gerado automaticamente do lançamento manual #{novo_lancamento.id}. {lancamento.observacoes or ''}",
                user_id=current_user.id
            )
            db.add(conta_receber)
        
        db.commit()
    except Exception as e:
        # Se falhar a integração, não impede o lançamento de ser criado
        logger.info(f"⚠️  Aviso: Erro ao criar conta a pagar/receber integrada: {e}")
        db.rollback()
        db.refresh(novo_lancamento)  # Garantir que o lançamento ainda existe
    
    return _build_lancamento_manual_response(novo_lancamento, db)


@router.get("/manuais", response_model=List[LancamentoManualResponse])
def listar_lancamentos_manuais(
    data_inicio: Optional[str] = None,
    data_fim: Optional[str] = None,
    tipo: Optional[str] = None,
    status: Optional[str] = None,
    categoria_id: Optional[int] = None,
    conta_bancaria_id: Optional[int] = None,
    db: Session = Depends(get_session),
    auth = Depends(get_current_user_and_tenant)
):
    """Listar lançamentos manuais com filtros"""
    current_user, tenant_id = auth
    
    query = db.query(LancamentoManual)
    
    # Aplicar filtros
    if data_inicio:
        data_inicio_dt = datetime.strptime(data_inicio, "%Y-%m-%d").date()
        query = query.filter(LancamentoManual.data_lancamento >= data_inicio_dt)
    
    if data_fim:
        data_fim_dt = datetime.strptime(data_fim, "%Y-%m-%d").date()
        query = query.filter(LancamentoManual.data_lancamento <= data_fim_dt)
    
    if tipo:
        query = query.filter(LancamentoManual.tipo == tipo)
    
    if status:
        query = query.filter(LancamentoManual.status == status)
    
    if categoria_id:
        query = query.filter(LancamentoManual.categoria_id == categoria_id)
    
    if conta_bancaria_id:
        query = query.filter(LancamentoManual.conta_bancaria_id == conta_bancaria_id)
    
    lancamentos = query.order_by(LancamentoManual.data_lancamento.desc()).all()
    
    return [_build_lancamento_manual_response(l, db) for l in lancamentos]


@router.get("/manuais/{lancamento_id}", response_model=LancamentoManualResponse)
def obter_lancamento_manual(
    lancamento_id: int,
    db: Session = Depends(get_session),
    auth = Depends(get_current_user_and_tenant)
):
    """Obter detalhes de um lançamento manual"""
    current_user, tenant_id = auth
    
    lancamento = db.query(LancamentoManual).filter(LancamentoManual.id == lancamento_id).first()
    
    if not lancamento:
        raise HTTPException(status_code=404, detail="Lançamento não encontrado")
    
    return _build_lancamento_manual_response(lancamento, db)


@router.put("/manuais/{lancamento_id}", response_model=LancamentoManualResponse)
def atualizar_lancamento_manual(
    lancamento_id: int,
    lancamento_update: LancamentoManualUpdate,
    db: Session = Depends(get_session),
    auth = Depends(get_current_user_and_tenant)
):
    """Atualizar lançamento manual"""
    current_user, tenant_id = auth
    
    lancamento = db.query(LancamentoManual).filter(LancamentoManual.id == lancamento_id).first()
    
    if not lancamento:
        raise HTTPException(status_code=404, detail="Lançamento não encontrado")
    
    # Atualizar campos fornecidos
    update_data = lancamento_update.model_dump(exclude_unset=True)
    
    for field, value in update_data.items():
        if field in ['data_lancamento', 'data_prevista', 'data_efetivacao'] and value:
            value = datetime.strptime(value, "%Y-%m-%d").date()
        elif field == 'valor' and value:
            value = Decimal(str(value))
        setattr(lancamento, field, value)
    
    lancamento.atualizado_em = datetime.utcnow()
    
    db.commit()
    db.refresh(lancamento)
    
    return _build_lancamento_manual_response(lancamento, db)


@router.delete("/manuais/{lancamento_id}")
def excluir_lancamento_manual(
    lancamento_id: int,
    db: Session = Depends(get_session),
    auth = Depends(get_current_user_and_tenant)
):
    """Excluir lançamento manual"""
    current_user, tenant_id = auth
    
    lancamento = db.query(LancamentoManual).filter(LancamentoManual.id == lancamento_id).first()
    
    if not lancamento:
        raise HTTPException(status_code=404, detail="Lançamento não encontrado")
    
    db.delete(lancamento)
    db.commit()
    
    return {"message": "Lançamento excluído com sucesso"}


# ============= LANÇAMENTOS RECORRENTES =============

@router.post("/recorrentes", response_model=LancamentoRecorrenteResponse)
def criar_lancamento_recorrente(
    lancamento: LancamentoRecorrenteCreate,
    db: Session = Depends(get_session),
    auth = Depends(get_current_user_and_tenant)
):
    """Criar novo lançamento recorrente"""
    current_user, tenant_id = auth
    
    # Validar tipo
    if lancamento.tipo not in ['entrada', 'saida']:
        raise HTTPException(status_code=400, detail="Tipo deve ser 'entrada' ou 'saida'")
    
    # Validar frequência
    if lancamento.frequencia not in ['mensal', 'semanal', 'anual']:
        raise HTTPException(status_code=400, detail="Frequência deve ser 'mensal', 'semanal' ou 'anual'")
    
    # Converter datas
    data_inicio = datetime.strptime(lancamento.data_inicio, "%Y-%m-%d").date()
    data_fim = datetime.strptime(lancamento.data_fim, "%Y-%m-%d").date() if lancamento.data_fim else None
    
    # Criar lançamento recorrente
    novo_lancamento = LancamentoRecorrente(
        tipo=lancamento.tipo,
        descricao=lancamento.descricao,
        valor_medio=Decimal(str(lancamento.valor_medio)),
        categoria_id=lancamento.categoria_id,
        conta_bancaria_id=lancamento.conta_bancaria_id,
        frequencia=lancamento.frequencia,
        dia_vencimento=lancamento.dia_vencimento,
        data_inicio=data_inicio,
        data_fim=data_fim,
        gerar_automaticamente=lancamento.gerar_automaticamente,
        gerar_com_antecedencia_dias=lancamento.gerar_com_antecedencia_dias,
        permite_ajuste_ia=lancamento.permite_ajuste_ia,
        observacoes=lancamento.observacoes
    )
    
    db.add(novo_lancamento)
    db.commit()
    db.refresh(novo_lancamento)
    
    return _build_lancamento_recorrente_response(novo_lancamento, db)


@router.get("/recorrentes", response_model=List[LancamentoRecorrenteResponse])
def listar_lancamentos_recorrentes(
    tipo: Optional[str] = None,
    ativo: Optional[bool] = None,
    categoria_id: Optional[int] = None,
    db: Session = Depends(get_session),
    auth = Depends(get_current_user_and_tenant)
):
    """Listar lançamentos recorrentes"""
    current_user, tenant_id = auth
    
    query = db.query(LancamentoRecorrente)
    
    if tipo:
        query = query.filter(LancamentoRecorrente.tipo == tipo)
    
    if ativo is not None:
        query = query.filter(LancamentoRecorrente.ativo == ativo)
    
    if categoria_id:
        query = query.filter(LancamentoRecorrente.categoria_id == categoria_id)
    
    lancamentos = query.order_by(LancamentoRecorrente.descricao).all()
    
    return [_build_lancamento_recorrente_response(l, db) for l in lancamentos]


@router.get("/recorrentes/{lancamento_id}", response_model=LancamentoRecorrenteResponse)
def obter_lancamento_recorrente(
    lancamento_id: int,
    db: Session = Depends(get_session),
    auth = Depends(get_current_user_and_tenant)
):
    """Obter detalhes de um lançamento recorrente"""
    current_user, tenant_id = auth
    
    lancamento = db.query(LancamentoRecorrente).filter(LancamentoRecorrente.id == lancamento_id).first()
    
    if not lancamento:
        raise HTTPException(status_code=404, detail="Lançamento recorrente não encontrado")
    
    return _build_lancamento_recorrente_response(lancamento, db)


@router.put("/recorrentes/{lancamento_id}", response_model=LancamentoRecorrenteResponse)
def atualizar_lancamento_recorrente(
    lancamento_id: int,
    lancamento_update: LancamentoRecorrenteUpdate,
    db: Session = Depends(get_session),
    auth = Depends(get_current_user_and_tenant)
):
    """Atualizar lançamento recorrente"""
    current_user, tenant_id = auth
    
    lancamento = db.query(LancamentoRecorrente).filter(LancamentoRecorrente.id == lancamento_id).first()
    
    if not lancamento:
        raise HTTPException(status_code=404, detail="Lançamento recorrente não encontrado")
    
    # Atualizar campos fornecidos
    update_data = lancamento_update.model_dump(exclude_unset=True)
    
    for field, value in update_data.items():
        if field in ['data_inicio', 'data_fim'] and value:
            value = datetime.strptime(value, "%Y-%m-%d").date()
        elif field == 'valor_medio' and value:
            value = Decimal(str(value))
        setattr(lancamento, field, value)
    
    lancamento.atualizado_em = datetime.utcnow()
    
    db.commit()
    db.refresh(lancamento)
    
    return _build_lancamento_recorrente_response(lancamento, db)


@router.delete("/recorrentes/{lancamento_id}")
def excluir_lancamento_recorrente(
    lancamento_id: int,
    db: Session = Depends(get_session),
    auth = Depends(get_current_user_and_tenant)
):
    """Excluir lançamento recorrente"""
    current_user, tenant_id = auth
    
    lancamento = db.query(LancamentoRecorrente).filter(LancamentoRecorrente.id == lancamento_id).first()
    
    if not lancamento:
        raise HTTPException(status_code=404, detail="Lançamento recorrente não encontrado")
    
    db.delete(lancamento)
    db.commit()
    
    return {"message": "Lançamento recorrente excluído com sucesso"}


@router.post("/recorrentes/{lancamento_id}/gerar")
def gerar_proximas_parcelas(
    lancamento_id: int,
    meses: int = 3,
    db: Session = Depends(get_session),
    auth = Depends(get_current_user_and_tenant)
):
    """Gerar próximas parcelas de um lançamento recorrente"""
    current_user, tenant_id = auth
    
    lancamento = db.query(LancamentoRecorrente).filter(LancamentoRecorrente.id == lancamento_id).first()
    
    if not lancamento:
        raise HTTPException(status_code=404, detail="Lançamento recorrente não encontrado")
    
    if not lancamento.ativo:
        raise HTTPException(status_code=400, detail="Lançamento recorrente está inativo")
    
    # Determinar data inicial para geração
    if lancamento.ultimo_mes_gerado:
        data_inicial = lancamento.ultimo_mes_gerado
    else:
        data_inicial = lancamento.data_inicio
    
    parcelas_criadas = []
    
    # Gerar parcelas para os próximos meses
    for i in range(1, meses + 1):
        # Calcular próxima data
        if lancamento.frequencia == 'mensal':
            mes_atual = data_inicial.month + i
            ano_atual = data_inicial.year
            
            while mes_atual > 12:
                mes_atual -= 12
                ano_atual += 1
            
            # Ajustar dia se necessário
            import calendar
            ultimo_dia_mes = calendar.monthrange(ano_atual, mes_atual)[1]
            dia = min(lancamento.dia_vencimento, ultimo_dia_mes)
            
            proxima_data = datetime(ano_atual, mes_atual, dia).date()
        
        # Verificar se já passou da data_fim
        if lancamento.data_fim and proxima_data > lancamento.data_fim:
            break
        
        # Verificar se já existe lançamento para esta data
        existe = db.query(LancamentoManual).filter(
            and_(
                LancamentoManual.descricao.like(f"%{lancamento.descricao}%"),
                LancamentoManual.data_lancamento == proxima_data
            )
        ).first()
        
        if not existe:
            # Criar novo lançamento manual
            novo_lancamento = LancamentoManual(
                tipo=lancamento.tipo,
                valor=lancamento.valor_medio,
                descricao=f"{lancamento.descricao} - {proxima_data.strftime('%m/%Y')}",
                data_lancamento=proxima_data,
                data_prevista=proxima_data,
                categoria_id=lancamento.categoria_id,
                conta_bancaria_id=lancamento.conta_bancaria_id,
                status='previsto',
                gerado_automaticamente=True,
                observacoes=f"Gerado automaticamente de lançamento recorrente #{lancamento.id}"
            )
            
            db.add(novo_lancamento)
            parcelas_criadas.append(novo_lancamento)
    
    # Atualizar último_mes_gerado
    if parcelas_criadas:
        ultima_data = max(p.data_lancamento for p in parcelas_criadas)
        lancamento.ultimo_mes_gerado = ultima_data
    
    db.commit()
    
    return {
        "message": f"{len(parcelas_criadas)} parcela(s) gerada(s) com sucesso",
        "parcelas": len(parcelas_criadas)
    }


# ============= FUNÇÕES AUXILIARES =============

def _build_lancamento_manual_response(lancamento: LancamentoManual, db: Session) -> dict:
    """Construir resposta com dados relacionados"""
    
    categoria_nome = None
    if lancamento.categoria_id:
        categoria = db.query(CategoriaFinanceira).filter(CategoriaFinanceira.id == lancamento.categoria_id).first()
        if categoria:
            categoria_nome = categoria.nome
    
    conta_nome = None
    if lancamento.conta_bancaria_id:
        conta = db.query(ContaBancaria).filter(ContaBancaria.id == lancamento.conta_bancaria_id).first()
        if conta:
            conta_nome = conta.nome
    
    return {
        "id": lancamento.id,
        "tipo": lancamento.tipo,
        "valor": float(lancamento.valor),
        "descricao": lancamento.descricao,
        "data_lancamento": lancamento.data_lancamento.isoformat(),
        "data_prevista": lancamento.data_prevista.isoformat() if lancamento.data_prevista else None,
        "data_efetivacao": lancamento.data_efetivacao.isoformat() if lancamento.data_efetivacao else None,
        "categoria_id": lancamento.categoria_id,
        "categoria_nome": categoria_nome,
        "conta_bancaria_id": lancamento.conta_bancaria_id,
        "conta_bancaria_nome": conta_nome,
        "status": lancamento.status,
        "observacoes": lancamento.observacoes,
        "gerado_automaticamente": lancamento.gerado_automaticamente,
        "confianca_ia": lancamento.confianca_ia,
        "criado_em": lancamento.criado_em.isoformat(),
        "atualizado_em": lancamento.atualizado_em.isoformat()
    }


def _build_lancamento_recorrente_response(lancamento: LancamentoRecorrente, db: Session) -> dict:
    """Construir resposta com dados relacionados"""
    
    categoria_nome = None
    if lancamento.categoria_id:
        categoria = db.query(CategoriaFinanceira).filter(CategoriaFinanceira.id == lancamento.categoria_id).first()
        if categoria:
            categoria_nome = categoria.nome
    
    conta_nome = None
    if lancamento.conta_bancaria_id:
        conta = db.query(ContaBancaria).filter(ContaBancaria.id == lancamento.conta_bancaria_id).first()
        if conta:
            conta_nome = conta.nome
    
    return {
        "id": lancamento.id,
        "tipo": lancamento.tipo,
        "descricao": lancamento.descricao,
        "valor_medio": float(lancamento.valor_medio),
        "categoria_id": lancamento.categoria_id,
        "categoria_nome": categoria_nome,
        "conta_bancaria_id": lancamento.conta_bancaria_id,
        "conta_bancaria_nome": conta_nome,
        "frequencia": lancamento.frequencia,
        "dia_vencimento": lancamento.dia_vencimento,
        "data_inicio": lancamento.data_inicio.isoformat(),
        "data_fim": lancamento.data_fim.isoformat() if lancamento.data_fim else None,
        "gerar_automaticamente": lancamento.gerar_automaticamente,
        "gerar_com_antecedencia_dias": lancamento.gerar_com_antecedencia_dias,
        "ultimo_mes_gerado": lancamento.ultimo_mes_gerado.isoformat() if lancamento.ultimo_mes_gerado else None,
        "permite_ajuste_ia": lancamento.permite_ajuste_ia,
        "observacoes": lancamento.observacoes,
        "ativo": lancamento.ativo,
        "criado_em": lancamento.criado_em.isoformat(),
        "atualizado_em": lancamento.atualizado_em.isoformat()
    }
