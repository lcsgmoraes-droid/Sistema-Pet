"""
Rotas para Lançamentos Manuais e Recorrentes do Fluxo de Caixa
"""

import calendar

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import and_
from datetime import date, datetime, timedelta
from typing import Optional, List
from pydantic import BaseModel
from decimal import Decimal

from .db import get_session
from .auth.dependencies import get_current_user_and_tenant
from app.utils.logger import logger
from .financeiro_models import (
    LancamentoManual,
    LancamentoRecorrente,
    ContaBancaria,
    CategoriaFinanceira,
    ContaPagar,
    ContaReceber,
)

router = APIRouter(prefix="/lancamentos", tags=["Lançamentos"])


def _parse_date(value: Optional[str]) -> Optional[date]:
    if not value:
        return None
    return datetime.strptime(value, "%Y-%m-%d").date()


def _realizado_em_from_date(value: Optional[date]) -> Optional[datetime]:
    if not value:
        return None
    return datetime.combine(value, datetime.min.time())


def _format_date(value) -> Optional[str]:
    if not value:
        return None
    return value.isoformat()


def _format_datetime(value) -> str:
    if not value:
        return ""
    return value.isoformat()


def _base_recorrencia(lancamento: LancamentoRecorrente) -> date:
    if not lancamento.ultimo_mes_gerado:
        return lancamento.data_inicio

    if isinstance(lancamento.ultimo_mes_gerado, date):
        return lancamento.ultimo_mes_gerado

    ultimo_mes = str(lancamento.ultimo_mes_gerado)
    if len(ultimo_mes) == 7:
        return datetime.strptime(f"{ultimo_mes}-01", "%Y-%m-%d").date()

    return datetime.strptime(ultimo_mes[:10], "%Y-%m-%d").date()


def _data_com_dia_seguro(ano: int, mes: int, dia_vencimento: int) -> date:
    ultimo_dia_mes = calendar.monthrange(ano, mes)[1]
    dia = min(dia_vencimento, ultimo_dia_mes)
    return date(ano, mes, dia)


def _proxima_data_recorrente(
    lancamento: LancamentoRecorrente, data_inicial: date, indice: int
) -> date:
    if lancamento.frequencia == "semanal":
        return data_inicial + timedelta(weeks=indice)

    if lancamento.frequencia == "anual":
        return _data_com_dia_seguro(
            data_inicial.year + indice,
            data_inicial.month,
            lancamento.dia_vencimento,
        )

    if lancamento.frequencia != "mensal":
        raise HTTPException(status_code=400, detail="Frequência inválida")

    mes_atual = data_inicial.month + indice
    ano_atual = data_inicial.year
    while mes_atual > 12:
        mes_atual -= 12
        ano_atual += 1

    return _data_com_dia_seguro(ano_atual, mes_atual, lancamento.dia_vencimento)


def _get_lancamento_manual_or_404(
    db: Session, tenant_id, lancamento_id: int
) -> LancamentoManual:
    lancamento = (
        db.query(LancamentoManual)
        .filter(
            LancamentoManual.id == lancamento_id,
            LancamentoManual.tenant_id == tenant_id,
        )
        .first()
    )

    if not lancamento:
        raise HTTPException(status_code=404, detail="Lançamento não encontrado")

    return lancamento


def _get_lancamento_recorrente_or_404(
    db: Session, tenant_id, lancamento_id: int
) -> LancamentoRecorrente:
    lancamento = (
        db.query(LancamentoRecorrente)
        .filter(
            LancamentoRecorrente.id == lancamento_id,
            LancamentoRecorrente.tenant_id == tenant_id,
        )
        .first()
    )

    if not lancamento:
        raise HTTPException(
            status_code=404, detail="Lançamento recorrente não encontrado"
        )

    return lancamento


def _aplicar_update_lancamento(lancamento, update_data: dict, normalizar_campo) -> None:
    for field, value in update_data.items():
        normalizado = normalizar_campo(lancamento, field, value)
        if normalizado is None:
            continue
        field, value = normalizado
        setattr(lancamento, field, value)

    lancamento.updated_at = datetime.utcnow()


def _normalizar_campo_manual(lancamento: LancamentoManual, field: str, value):
    if field == "data_lancamento":
        return field, _parse_date(value)
    if field == "data_prevista":
        lancamento.data_competencia = _parse_date(value)
        return None
    if field == "data_efetivacao":
        lancamento.realizado_em = _realizado_em_from_date(_parse_date(value))
        return None
    if field == "valor" and value:
        return field, Decimal(str(value))
    return field, value


def _normalizar_campo_recorrente(_lancamento, field: str, value):
    if field in ["data_inicio", "data_fim"] and value:
        return field, _parse_date(value)
    if field == "valor_medio" and value:
        return field, Decimal(str(value))
    if field == "gerar_automaticamente":
        return "ativo", value
    return field, value


def _atualizar_lancamento_manual_campos(
    lancamento: LancamentoManual, update_data: dict
) -> None:
    _aplicar_update_lancamento(lancamento, update_data, _normalizar_campo_manual)
    if lancamento.status == "realizado" and not lancamento.realizado_em:
        lancamento.realizado_em = datetime.utcnow()


def _atualizar_lancamento_recorrente_campos(
    lancamento: LancamentoRecorrente, update_data: dict
) -> None:
    _aplicar_update_lancamento(lancamento, update_data, _normalizar_campo_recorrente)


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
    status: str = "previsto"  # previsto ou realizado
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
    frequencia: str = "mensal"  # mensal, semanal, anual
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
    auth=Depends(get_current_user_and_tenant),
):
    """Criar novo lançamento manual"""
    current_user, tenant_id = auth

    # Validar tipo
    if lancamento.tipo not in ["entrada", "saida"]:
        raise HTTPException(
            status_code=400, detail="Tipo deve ser 'entrada' ou 'saida'"
        )

    # Validar status
    if lancamento.status not in ["previsto", "realizado"]:
        raise HTTPException(
            status_code=400, detail="Status deve ser 'previsto' ou 'realizado'"
        )

    # Converter datas da API legada para as colunas atuais do modelo
    data_lancamento = _parse_date(lancamento.data_lancamento)
    data_prevista = _parse_date(lancamento.data_prevista)
    data_efetivacao = _parse_date(lancamento.data_efetivacao)
    data_realizacao = data_efetivacao or (
        data_lancamento if lancamento.status == "realizado" else None
    )
    realizado_em = _realizado_em_from_date(data_realizacao)

    # Criar lançamento
    novo_lancamento = LancamentoManual(
        tipo=lancamento.tipo,
        valor=Decimal(str(lancamento.valor)),
        descricao=lancamento.descricao,
        data_lancamento=data_lancamento,
        data_competencia=data_prevista or data_lancamento,
        realizado_em=realizado_em,
        categoria_id=lancamento.categoria_id,
        conta_bancaria_id=lancamento.conta_bancaria_id,
        status=lancamento.status,
        observacoes=lancamento.observacoes,
        gerado_automaticamente=lancamento.gerado_automaticamente,
        confianca_ia=lancamento.confianca_ia,
        user_id=current_user.id,
        tenant_id=tenant_id,
    )

    db.add(novo_lancamento)
    db.commit()
    db.refresh(novo_lancamento)

    # INTEGRAÇÃO: Criar conta a pagar ou receber correspondente
    try:
        if lancamento.tipo == "saida":
            # Criar conta a pagar
            conta_pagar = ContaPagar(
                descricao=lancamento.descricao,
                categoria_id=lancamento.categoria_id,
                valor_original=Decimal(str(lancamento.valor)),
                valor_final=Decimal(str(lancamento.valor)),
                valor_pago=Decimal(str(lancamento.valor))
                if lancamento.status == "realizado"
                else Decimal("0"),
                data_emissao=data_lancamento,
                data_vencimento=data_prevista or data_lancamento,
                data_pagamento=data_realizacao
                if lancamento.status == "realizado"
                else None,
                status="pago" if lancamento.status == "realizado" else "pendente",
                observacoes=f"Gerado automaticamente do lançamento manual #{novo_lancamento.id}. {lancamento.observacoes or ''}",
                user_id=current_user.id,
                tenant_id=tenant_id,
            )
            db.add(conta_pagar)

        elif lancamento.tipo == "entrada":
            # Criar conta a receber
            conta_receber = ContaReceber(
                descricao=lancamento.descricao,
                categoria_id=lancamento.categoria_id,
                dre_subcategoria_id=1,  # TODO: Mapear baseado na categoria
                canal="loja_fisica",  # Lançamento manual = loja física
                valor_original=Decimal(str(lancamento.valor)),
                valor_final=Decimal(str(lancamento.valor)),
                valor_recebido=Decimal(str(lancamento.valor))
                if lancamento.status == "realizado"
                else Decimal("0"),
                data_emissao=data_lancamento,
                data_vencimento=data_prevista or data_lancamento,
                data_recebimento=data_realizacao
                if lancamento.status == "realizado"
                else None,
                status="recebido" if lancamento.status == "realizado" else "pendente",
                observacoes=f"Gerado automaticamente do lançamento manual #{novo_lancamento.id}. {lancamento.observacoes or ''}",
                user_id=current_user.id,
                tenant_id=tenant_id,
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
    auth=Depends(get_current_user_and_tenant),
):
    """Listar lançamentos manuais com filtros"""
    _current_user, tenant_id = auth

    query = db.query(LancamentoManual).filter(LancamentoManual.tenant_id == tenant_id)

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

    return [
        _build_lancamento_manual_response(lancamento, db) for lancamento in lancamentos
    ]


@router.get("/manuais/{lancamento_id}", response_model=LancamentoManualResponse)
def obter_lancamento_manual(
    lancamento_id: int,
    db: Session = Depends(get_session),
    auth=Depends(get_current_user_and_tenant),
):
    """Obter detalhes de um lançamento manual"""
    _current_user, tenant_id = auth

    lancamento = _get_lancamento_manual_or_404(db, tenant_id, lancamento_id)

    return _build_lancamento_manual_response(lancamento, db)


@router.put("/manuais/{lancamento_id}", response_model=LancamentoManualResponse)
def atualizar_lancamento_manual(
    lancamento_id: int,
    lancamento_update: LancamentoManualUpdate,
    db: Session = Depends(get_session),
    auth=Depends(get_current_user_and_tenant),
):
    """Atualizar lançamento manual"""
    _current_user, tenant_id = auth

    lancamento = _get_lancamento_manual_or_404(db, tenant_id, lancamento_id)

    # Atualizar campos fornecidos
    update_data = lancamento_update.model_dump(exclude_unset=True)
    _atualizar_lancamento_manual_campos(lancamento, update_data)

    db.commit()
    db.refresh(lancamento)

    return _build_lancamento_manual_response(lancamento, db)


@router.delete("/manuais/{lancamento_id}")
def excluir_lancamento_manual(
    lancamento_id: int,
    db: Session = Depends(get_session),
    auth=Depends(get_current_user_and_tenant),
):
    """Excluir lançamento manual"""
    _current_user, tenant_id = auth

    lancamento = _get_lancamento_manual_or_404(db, tenant_id, lancamento_id)

    db.delete(lancamento)
    db.commit()

    return {"message": "Lançamento excluído com sucesso"}


# ============= LANÇAMENTOS RECORRENTES =============


@router.post("/recorrentes", response_model=LancamentoRecorrenteResponse)
def criar_lancamento_recorrente(
    lancamento: LancamentoRecorrenteCreate,
    db: Session = Depends(get_session),
    auth=Depends(get_current_user_and_tenant),
):
    """Criar novo lançamento recorrente"""
    current_user, tenant_id = auth

    # Validar tipo
    if lancamento.tipo not in ["entrada", "saida"]:
        raise HTTPException(
            status_code=400, detail="Tipo deve ser 'entrada' ou 'saida'"
        )

    # Validar frequência
    if lancamento.frequencia not in ["mensal", "semanal", "anual"]:
        raise HTTPException(
            status_code=400, detail="Frequência deve ser 'mensal', 'semanal' ou 'anual'"
        )

    # Converter datas
    data_inicio = _parse_date(lancamento.data_inicio)
    data_fim = _parse_date(lancamento.data_fim)

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
        ativo=lancamento.gerar_automaticamente,
        gerar_com_antecedencia_dias=lancamento.gerar_com_antecedencia_dias,
        permite_ajuste_ia=lancamento.permite_ajuste_ia,
        observacoes=lancamento.observacoes,
        user_id=current_user.id,
        tenant_id=tenant_id,
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
    auth=Depends(get_current_user_and_tenant),
):
    """Listar lançamentos recorrentes"""
    _current_user, tenant_id = auth

    query = db.query(LancamentoRecorrente).filter(
        LancamentoRecorrente.tenant_id == tenant_id
    )

    if tipo:
        query = query.filter(LancamentoRecorrente.tipo == tipo)

    if ativo is not None:
        query = query.filter(LancamentoRecorrente.ativo == ativo)

    if categoria_id:
        query = query.filter(LancamentoRecorrente.categoria_id == categoria_id)

    lancamentos = query.order_by(LancamentoRecorrente.descricao).all()

    return [
        _build_lancamento_recorrente_response(lancamento, db)
        for lancamento in lancamentos
    ]


@router.get("/recorrentes/{lancamento_id}", response_model=LancamentoRecorrenteResponse)
def obter_lancamento_recorrente(
    lancamento_id: int,
    db: Session = Depends(get_session),
    auth=Depends(get_current_user_and_tenant),
):
    """Obter detalhes de um lançamento recorrente"""
    _current_user, tenant_id = auth

    lancamento = _get_lancamento_recorrente_or_404(db, tenant_id, lancamento_id)

    return _build_lancamento_recorrente_response(lancamento, db)


@router.put("/recorrentes/{lancamento_id}", response_model=LancamentoRecorrenteResponse)
def atualizar_lancamento_recorrente(
    lancamento_id: int,
    lancamento_update: LancamentoRecorrenteUpdate,
    db: Session = Depends(get_session),
    auth=Depends(get_current_user_and_tenant),
):
    """Atualizar lançamento recorrente"""
    _current_user, tenant_id = auth

    lancamento = _get_lancamento_recorrente_or_404(db, tenant_id, lancamento_id)

    # Atualizar campos fornecidos
    update_data = lancamento_update.model_dump(exclude_unset=True)
    _atualizar_lancamento_recorrente_campos(lancamento, update_data)

    db.commit()
    db.refresh(lancamento)

    return _build_lancamento_recorrente_response(lancamento, db)


@router.delete("/recorrentes/{lancamento_id}")
def excluir_lancamento_recorrente(
    lancamento_id: int,
    db: Session = Depends(get_session),
    auth=Depends(get_current_user_and_tenant),
):
    """Excluir lançamento recorrente"""
    _current_user, tenant_id = auth

    lancamento = _get_lancamento_recorrente_or_404(db, tenant_id, lancamento_id)

    db.delete(lancamento)
    db.commit()

    return {"message": "Lançamento recorrente excluído com sucesso"}


@router.post("/recorrentes/{lancamento_id}/gerar")
def gerar_proximas_parcelas(
    lancamento_id: int,
    meses: int = 3,
    db: Session = Depends(get_session),
    auth=Depends(get_current_user_and_tenant),
):
    """Gerar próximas parcelas de um lançamento recorrente"""
    current_user, tenant_id = auth

    lancamento = _get_lancamento_recorrente_or_404(db, tenant_id, lancamento_id)

    if not lancamento.ativo:
        raise HTTPException(
            status_code=400, detail="Lançamento recorrente está inativo"
        )

    # Determinar data inicial para geração
    data_inicial = _base_recorrencia(lancamento)

    parcelas_criadas = []

    # Gerar parcelas para os próximos meses
    for i in range(1, meses + 1):
        proxima_data = _proxima_data_recorrente(lancamento, data_inicial, i)

        # Verificar se já passou da data_fim
        if lancamento.data_fim and proxima_data > lancamento.data_fim:
            break

        # Verificar se já existe lançamento para esta data
        existe = (
            db.query(LancamentoManual)
            .filter(
                and_(
                    LancamentoManual.tenant_id == tenant_id,
                    LancamentoManual.lancamento_recorrente_id == lancamento.id,
                    LancamentoManual.data_lancamento == proxima_data,
                )
            )
            .first()
        )

        if not existe:
            # Criar novo lançamento manual
            novo_lancamento = LancamentoManual(
                tipo=lancamento.tipo,
                valor=lancamento.valor_medio,
                descricao=f"{lancamento.descricao} - {proxima_data.strftime('%m/%Y')}",
                data_lancamento=proxima_data,
                data_competencia=proxima_data,
                categoria_id=lancamento.categoria_id,
                conta_bancaria_id=lancamento.conta_bancaria_id,
                status="previsto",
                gerado_automaticamente=True,
                lancamento_recorrente_id=lancamento.id,
                user_id=current_user.id,
                tenant_id=tenant_id,
                observacoes=f"Gerado automaticamente de lançamento recorrente #{lancamento.id}",
            )

            db.add(novo_lancamento)
            parcelas_criadas.append(novo_lancamento)

    # Atualizar último_mes_gerado
    if parcelas_criadas:
        ultima_data = max(p.data_lancamento for p in parcelas_criadas)
        lancamento.ultimo_mes_gerado = ultima_data.strftime("%Y-%m")

    db.commit()

    return {
        "message": f"{len(parcelas_criadas)} parcela(s) gerada(s) com sucesso",
        "parcelas": len(parcelas_criadas),
    }


# ============= FUNÇÕES AUXILIARES =============


def _build_lancamento_manual_response(
    lancamento: LancamentoManual, db: Session
) -> dict:
    """Construir resposta com dados relacionados"""

    categoria_nome = None
    if lancamento.categoria_id:
        categoria = (
            db.query(CategoriaFinanceira)
            .filter(
                CategoriaFinanceira.id == lancamento.categoria_id,
                CategoriaFinanceira.tenant_id == lancamento.tenant_id,
            )
            .first()
        )
        if categoria:
            categoria_nome = categoria.nome

    conta_nome = None
    if lancamento.conta_bancaria_id:
        conta = (
            db.query(ContaBancaria)
            .filter(
                ContaBancaria.id == lancamento.conta_bancaria_id,
                ContaBancaria.tenant_id == lancamento.tenant_id,
            )
            .first()
        )
        if conta:
            conta_nome = conta.nome

    return {
        "id": lancamento.id,
        "tipo": lancamento.tipo,
        "valor": float(lancamento.valor),
        "descricao": lancamento.descricao,
        "data_lancamento": lancamento.data_lancamento.isoformat(),
        "data_prevista": _format_date(lancamento.data_competencia),
        "data_efetivacao": _format_date(lancamento.realizado_em.date())
        if lancamento.realizado_em
        else None,
        "categoria_id": lancamento.categoria_id,
        "categoria_nome": categoria_nome,
        "conta_bancaria_id": lancamento.conta_bancaria_id,
        "conta_bancaria_nome": conta_nome,
        "status": lancamento.status,
        "observacoes": lancamento.observacoes,
        "gerado_automaticamente": lancamento.gerado_automaticamente,
        "confianca_ia": lancamento.confianca_ia,
        "criado_em": _format_datetime(lancamento.created_at),
        "atualizado_em": _format_datetime(lancamento.updated_at),
    }


def _build_lancamento_recorrente_response(
    lancamento: LancamentoRecorrente, db: Session
) -> dict:
    """Construir resposta com dados relacionados"""

    categoria_nome = None
    if lancamento.categoria_id:
        categoria = (
            db.query(CategoriaFinanceira)
            .filter(
                CategoriaFinanceira.id == lancamento.categoria_id,
                CategoriaFinanceira.tenant_id == lancamento.tenant_id,
            )
            .first()
        )
        if categoria:
            categoria_nome = categoria.nome

    conta_nome = None
    if lancamento.conta_bancaria_id:
        conta = (
            db.query(ContaBancaria)
            .filter(
                ContaBancaria.id == lancamento.conta_bancaria_id,
                ContaBancaria.tenant_id == lancamento.tenant_id,
            )
            .first()
        )
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
        "gerar_automaticamente": lancamento.ativo,
        "gerar_com_antecedencia_dias": lancamento.gerar_com_antecedencia_dias,
        "ultimo_mes_gerado": lancamento.ultimo_mes_gerado,
        "permite_ajuste_ia": lancamento.permite_ajuste_ia,
        "observacoes": lancamento.observacoes,
        "ativo": lancamento.ativo,
        "criado_em": _format_datetime(lancamento.created_at),
        "atualizado_em": _format_datetime(lancamento.updated_at),
    }
