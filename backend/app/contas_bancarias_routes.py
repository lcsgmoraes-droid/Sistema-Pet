"""
Routes para gerenciamento de contas bancárias
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc
from typing import List, Optional
from datetime import date, datetime
from decimal import Decimal
from pydantic import BaseModel, Field

from app.db import get_session
from app.auth.dependencies import get_current_user_and_tenant
from app.financeiro_models import ContaBancaria, MovimentacaoFinanceira
from app.financeiro.virada_bancaria_historica import (
    CONFIRM_TOKEN_VIRADA_BANCARIA,
    executar_virada_bancaria_historica,
)

router = APIRouter(prefix="/contas-bancarias", tags=["Contas Bancárias"])


# ==================== Schemas ====================


class ContaBancariaCreate(BaseModel):
    nome: str = Field(..., min_length=1, max_length=100)
    tipo: str = Field(..., pattern="^(banco|caixa|digital)$")
    banco: Optional[str] = None
    saldo_inicial: float = Field(default=0, ge=0)
    cor: Optional[str] = Field(None, pattern="^#[0-9A-Fa-f]{6}$")
    icone: Optional[str] = None
    instituicao_bancaria: bool = False
    ativa: bool = True


class ContaBancariaUpdate(BaseModel):
    nome: Optional[str] = Field(None, min_length=1, max_length=100)
    tipo: Optional[str] = Field(None, pattern="^(banco|caixa|digital)$")
    banco: Optional[str] = None
    cor: Optional[str] = Field(None, pattern="^#[0-9A-Fa-f]{6}$")
    icone: Optional[str] = None
    instituicao_bancaria: Optional[bool] = None
    ativa: Optional[bool] = None


class AjusteSaldo(BaseModel):
    novo_saldo: float = Field(..., description="Novo saldo da conta")
    descricao: str = Field(
        ..., min_length=1, max_length=500, description="Motivo do ajuste"
    )


class ViradaHistoricaApply(BaseModel):
    data_corte: date
    conta_bancaria_id: int
    saldo_real: Decimal
    expected_saldo_atual: Decimal
    baixar_historico: bool = True
    ajustar_saldo: bool = True
    confirmacao: str = Field(..., min_length=1)


class ContaBancariaResponse(BaseModel):
    id: int
    nome: str
    tipo: str
    banco: Optional[str]
    saldo_inicial: float
    saldo_atual: float
    cor: Optional[str]
    icone: Optional[str]
    instituicao_bancaria: bool = False
    ativa: bool
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class MovimentacaoResponse(BaseModel):
    id: int
    data_movimento: datetime
    tipo: str
    valor: float
    origem_tipo: Optional[str]
    origem_id: Optional[int]
    origem_venda: Optional[str]
    status: str
    documento: Optional[str]
    descricao: Optional[str]
    categoria_id: Optional[int]
    forma_pagamento_id: Optional[int]
    created_at: datetime

    model_config = {"from_attributes": True}


# ==================== Rotas ====================


@router.get("", response_model=List[ContaBancariaResponse])
def listar_contas(
    apenas_ativas: bool = True,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Lista todas as contas bancárias do usuário"""
    current_user, tenant_id = user_and_tenant
    query = db.query(ContaBancaria).filter(ContaBancaria.tenant_id == tenant_id)

    if apenas_ativas:
        query = query.filter(ContaBancaria.ativa.is_(True))

    contas = query.order_by(ContaBancaria.nome).all()

    return contas


@router.get("/virada-historica/previa")
def prever_virada_bancaria_historica(
    data_corte: date,
    conta_bancaria_id: Optional[int] = None,
    saldo_real: Optional[Decimal] = None,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Preve baixas historicas e ajuste de saldo sem persistir alteracoes."""
    _current_user, tenant_id = user_and_tenant

    try:
        return executar_virada_bancaria_historica(
            db,
            tenant_id=str(tenant_id),
            data_corte=data_corte,
            conta_bancaria_id=conta_bancaria_id,
            saldo_real=saldo_real,
            apply_baixas=False,
            apply_saldo=False,
            confirm_token=None,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/virada-historica/aplicar")
def aplicar_virada_bancaria_historica(
    payload: ViradaHistoricaApply,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Aplica a virada historica com token literal e saldo atual esperado."""
    _current_user, tenant_id = user_and_tenant

    if not payload.baixar_historico and not payload.ajustar_saldo:
        raise HTTPException(
            status_code=400,
            detail="Selecione ao menos uma acao para aplicar na virada historica.",
        )

    if payload.confirmacao != CONFIRM_TOKEN_VIRADA_BANCARIA:
        raise HTTPException(
            status_code=400,
            detail=f"confirmacao deve ser {CONFIRM_TOKEN_VIRADA_BANCARIA}",
        )

    try:
        resultado = executar_virada_bancaria_historica(
            db,
            tenant_id=str(tenant_id),
            data_corte=payload.data_corte,
            conta_bancaria_id=payload.conta_bancaria_id,
            saldo_real=payload.saldo_real,
            expected_saldo_atual=payload.expected_saldo_atual,
            apply_baixas=payload.baixar_historico,
            apply_saldo=payload.ajustar_saldo,
            confirm_token=payload.confirmacao,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if not resultado.get("ok", False):
        raise HTTPException(
            status_code=400,
            detail=resultado.get("error", "Nao foi possivel aplicar a virada."),
        )

    return resultado


@router.get("/{conta_id}", response_model=ContaBancariaResponse)
def obter_conta(
    conta_id: int,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Obtém detalhes de uma conta específica"""
    current_user, tenant_id = user_and_tenant
    conta = (
        db.query(ContaBancaria)
        .filter(
            and_(ContaBancaria.id == conta_id, ContaBancaria.tenant_id == tenant_id)
        )
        .first()
    )

    if not conta:
        raise HTTPException(status_code=404, detail="Conta não encontrada")

    return conta


@router.post("", response_model=ContaBancariaResponse, status_code=201)
def criar_conta(
    conta_data: ContaBancariaCreate,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Cria uma nova conta bancária"""
    try:
        current_user, tenant_id = user_and_tenant

        # Log para debug MELHORADO
        print(f"[DEBUG] user_and_tenant type: {type(user_and_tenant)}")
        print(f"[DEBUG] current_user type: {type(current_user)}")
        print(f"[DEBUG] current_user: {current_user}")
        print(
            f"[DEBUG] current_user.id: {getattr(current_user, 'id', 'NO ID ATTRIBUTE')}"
        )
        print(f"[DEBUG] tenant_id: {tenant_id}")
        print(f"[DEBUG] Dados: {conta_data.model_dump()}")

        # Verificar se já existe conta com mesmo nome
        existe = (
            db.query(ContaBancaria)
            .filter(
                and_(
                    ContaBancaria.nome == conta_data.nome,
                    ContaBancaria.tenant_id == tenant_id,
                )
            )
            .first()
        )

        if existe:
            raise HTTPException(
                status_code=400, detail="Já existe uma conta com este nome"
            )

        # Saldo é armazenado em reais usando Decimal para compatibilidade com Numeric.
        saldo_decimal = Decimal(str(conta_data.saldo_inicial))

        # CORREÇÃO CRÍTICA: Garantir que user_id não seja None
        user_id = current_user.id if hasattr(current_user, "id") else None
        if user_id is None:
            raise HTTPException(
                status_code=500,
                detail=f"Erro interno: user_id não disponível. current_user={current_user}",
            )

        # Criar conta
        # NOTA: tenant_id deve ser passado explicitamente (não há auto-inject configurado)
        nova_conta = ContaBancaria(
            nome=conta_data.nome,
            tipo=conta_data.tipo,
            banco=conta_data.banco,
            saldo_inicial=saldo_decimal,
            saldo_atual=saldo_decimal,
            cor=conta_data.cor,
            icone=conta_data.icone,
            ativa=conta_data.ativa,
            user_id=user_id,
            tenant_id=tenant_id,
        )

        db.add(nova_conta)
        db.commit()
        db.refresh(nova_conta)

        # Se saldo inicial > 0, criar movimentação de abertura
        if saldo_decimal > 0:
            movimentacao = MovimentacaoFinanceira(
                data_movimento=datetime.utcnow(),
                tipo="entrada",
                valor=saldo_decimal,
                conta_bancaria_id=nova_conta.id,
                origem_tipo="abertura_conta",
                status="realizado",
                descricao=f"Saldo inicial da conta {nova_conta.nome}",
                user_id=user_id,
                tenant_id=tenant_id,
            )
            db.add(movimentacao)
            db.commit()

        # Converter para resposta - já está em formato correto (Decimal)
        nova_conta.saldo_inicial = float(nova_conta.saldo_inicial)
        nova_conta.saldo_atual = float(nova_conta.saldo_atual)

        print(f"[DEBUG] Conta criada com sucesso - ID: {nova_conta.id}")
        return nova_conta

    except HTTPException:
        raise
    except Exception as e:
        print(f"[ERROR] Erro ao criar conta: {str(e)}")
        import traceback

        traceback.print_exc()
        db.rollback()
        raise HTTPException(
            status_code=500, detail=f"Erro interno ao criar conta: {str(e)}"
        )


@router.put("/{conta_id}", response_model=ContaBancariaResponse)
def atualizar_conta(
    conta_id: int,
    conta_data: ContaBancariaUpdate,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Atualiza dados de uma conta bancária (não altera saldo)"""
    try:
        current_user, tenant_id = user_and_tenant

        print(
            f"[DEBUG] Atualizando conta {conta_id} - User: {current_user.id}, Tenant: {tenant_id}"
        )

        conta = (
            db.query(ContaBancaria)
            .filter(
                and_(ContaBancaria.id == conta_id, ContaBancaria.tenant_id == tenant_id)
            )
            .first()
        )

        if not conta:
            raise HTTPException(status_code=404, detail="Conta não encontrada")

        # Atualizar campos
        update_data = conta_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(conta, field, value)

        db.commit()
        db.refresh(conta)

        print(f"[DEBUG] Conta {conta_id} atualizada com sucesso")
        return conta

    except HTTPException:
        raise
    except Exception as e:
        print(f"[ERROR] Erro ao atualizar conta: {str(e)}")
        import traceback

        traceback.print_exc()
        db.rollback()
        raise HTTPException(
            status_code=500, detail=f"Erro interno ao atualizar conta: {str(e)}"
        )


@router.delete("/{conta_id}")
def excluir_conta(
    conta_id: int,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Desativa uma conta bancária (soft delete)"""
    current_user, tenant_id = user_and_tenant

    conta = (
        db.query(ContaBancaria)
        .filter(
            and_(ContaBancaria.id == conta_id, ContaBancaria.tenant_id == tenant_id)
        )
        .first()
    )

    if not conta:
        raise HTTPException(status_code=404, detail="Conta não encontrada")

    # Verificar se tem movimentações
    tem_movimentacoes = (
        db.query(MovimentacaoFinanceira)
        .filter(
            and_(
                MovimentacaoFinanceira.conta_bancaria_id == conta_id,
                MovimentacaoFinanceira.tenant_id == tenant_id,
            )
        )
        .count()
        > 0
    )

    if tem_movimentacoes:
        # Soft delete - apenas desativar
        conta.ativa = False
        db.commit()
        return {"message": "Conta desativada com sucesso (possui movimentações)"}
    else:
        # Hard delete - pode excluir
        db.delete(conta)
        db.commit()
        return {"message": "Conta excluída com sucesso"}


@router.post("/{conta_id}/ajustar-saldo")
def ajustar_saldo(
    conta_id: int,
    ajuste: AjusteSaldo,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Ajusta o saldo de uma conta (cria movimentação de ajuste)"""
    current_user, tenant_id = user_and_tenant

    conta = (
        db.query(ContaBancaria)
        .filter(
            and_(ContaBancaria.id == conta_id, ContaBancaria.tenant_id == tenant_id)
        )
        .first()
    )

    if not conta:
        raise HTTPException(status_code=404, detail="Conta não encontrada")

    novo_saldo = Decimal(str(ajuste.novo_saldo)).quantize(Decimal("0.01"))
    saldo_atual = Decimal(str(conta.saldo_atual or 0)).quantize(Decimal("0.01"))

    # Calcular diferença
    diferenca = novo_saldo - saldo_atual

    if diferenca == 0:
        raise HTTPException(status_code=400, detail="Novo saldo é igual ao saldo atual")

    # Determinar tipo de movimentação
    tipo_mov = "entrada" if diferenca > 0 else "saida"
    valor_absoluto = abs(diferenca)

    # Criar movimentação de ajuste
    movimentacao = MovimentacaoFinanceira(
        data_movimento=datetime.utcnow(),
        tipo=tipo_mov,
        valor=valor_absoluto,
        conta_bancaria_id=conta_id,
        origem_tipo="ajuste_manual",
        status="realizado",
        descricao=f"Ajuste de saldo: {ajuste.descricao}",
        user_id=current_user.id,
        tenant_id=tenant_id,
    )

    db.add(movimentacao)

    # Atualizar saldo da conta
    conta.saldo_atual = novo_saldo

    db.commit()
    db.refresh(conta)

    return {
        "message": "Saldo ajustado com sucesso",
        "saldo_anterior": float(saldo_atual),
        "saldo_novo": float(novo_saldo),
        "diferenca": float(diferenca),
        "movimentacao_id": movimentacao.id,
    }


@router.get("/{conta_id}/movimentacoes", response_model=List[MovimentacaoResponse])
def listar_movimentacoes(
    conta_id: int,
    limit: int = 50,
    offset: int = 0,
    tipo: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Lista movimentações de uma conta (extrato)"""
    current_user, tenant_id = user_and_tenant

    # Verificar se conta existe e pertence ao usuário
    conta = (
        db.query(ContaBancaria)
        .filter(
            and_(ContaBancaria.id == conta_id, ContaBancaria.tenant_id == tenant_id)
        )
        .first()
    )

    if not conta:
        raise HTTPException(status_code=404, detail="Conta não encontrada")

    # Buscar movimentações
    query = db.query(MovimentacaoFinanceira).filter(
        and_(
            MovimentacaoFinanceira.conta_bancaria_id == conta_id,
            MovimentacaoFinanceira.tenant_id == tenant_id,
        )
    )

    if tipo:
        query = query.filter(MovimentacaoFinanceira.tipo == tipo)

    if status:
        query = query.filter(MovimentacaoFinanceira.status == status)

    movimentacoes = (
        query.order_by(desc(MovimentacaoFinanceira.data_movimento))
        .offset(offset)
        .limit(limit)
        .all()
    )

    return movimentacoes


@router.get("/resumo/saldos")
def resumo_saldos(
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Retorna resumo de saldos de todas as contas ativas"""
    current_user, tenant_id = user_and_tenant

    contas = (
        db.query(ContaBancaria)
        .filter(
            and_(ContaBancaria.tenant_id == tenant_id, ContaBancaria.ativa.is_(True))
        )
        .all()
    )

    resumo = {
        "total_geral": 0,
        "por_tipo": {"banco": 0, "caixa": 0, "digital": 0},
        "contas": [],
    }

    for conta in contas:
        saldo_reais = float(conta.saldo_atual or 0)
        resumo["total_geral"] += saldo_reais

        # Usar get para evitar KeyError com tipos não mapeados
        if conta.tipo in resumo["por_tipo"]:
            resumo["por_tipo"][conta.tipo] += saldo_reais

        resumo["contas"].append(
            {
                "id": conta.id,
                "nome": conta.nome,
                "tipo": conta.tipo,
                "saldo": saldo_reais,
                "cor": conta.cor,
                "icone": conta.icone,
            }
        )

    return resumo
