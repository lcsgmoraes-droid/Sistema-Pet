"""
Routes para gerenciamento de contas bancárias
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import and_, func, desc
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, Field

from app.db import get_session
from app.auth import get_current_user
from app.auth.dependencies import get_current_user_and_tenant
from app.models import User
from app.financeiro_models import ContaBancaria, MovimentacaoFinanceira

router = APIRouter(prefix="/api/contas-bancarias", tags=["Contas Bancárias"])


# ==================== Schemas ====================

class ContaBancariaCreate(BaseModel):
    nome: str = Field(..., min_length=1, max_length=100)
    tipo: str = Field(..., pattern="^(banco|caixa|digital)$")
    banco: Optional[str] = None
    saldo_inicial: float = Field(default=0, ge=0)
    cor: Optional[str] = Field(None, pattern="^#[0-9A-Fa-f]{6}$")
    icone: Optional[str] = None
    ativa: bool = True


class ContaBancariaUpdate(BaseModel):
    nome: Optional[str] = Field(None, min_length=1, max_length=100)
    tipo: Optional[str] = Field(None, pattern="^(banco|caixa|digital)$")
    banco: Optional[str] = None
    cor: Optional[str] = Field(None, pattern="^#[0-9A-Fa-f]{6}$")
    icone: Optional[str] = None
    ativa: Optional[bool] = None


class AjusteSaldo(BaseModel):
    novo_saldo: float = Field(..., description="Novo saldo da conta")
    descricao: str = Field(..., min_length=1, max_length=500, description="Motivo do ajuste")


class ContaBancariaResponse(BaseModel):
    id: int
    nome: str
    tipo: str
    banco: Optional[str]
    saldo_inicial: float
    saldo_atual: float
    cor: Optional[str]
    icone: Optional[str]
    ativa: bool
    created_at: datetime
    updated_at: datetime
    
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
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """Lista todas as contas bancárias do usuário"""
    current_user, tenant_id = user_and_tenant
    query = db.query(ContaBancaria).filter(ContaBancaria.tenant_id == tenant_id)
    
    if apenas_ativas:
        query = query.filter(ContaBancaria.ativa == True)
    
    contas = query.order_by(ContaBancaria.nome).all()
    
    # Converter saldos (centavos → reais)
    for conta in contas:
        conta.saldo_inicial = conta.saldo_inicial / 100
        conta.saldo_atual = conta.saldo_atual / 100
    
    return contas


@router.get("/{conta_id}", response_model=ContaBancariaResponse)
def obter_conta(
    conta_id: int,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """Obtém detalhes de uma conta específica"""
    current_user, tenant_id = user_and_tenant
    conta = db.query(ContaBancaria).filter(
        and_(
            ContaBancaria.id == conta_id,
            ContaBancaria.tenant_id == tenant_id
        )
    ).first()
    
    if not conta:
        raise HTTPException(status_code=404, detail="Conta não encontrada")
    
    # Converter saldos (centavos → reais)
    conta.saldo_inicial = conta.saldo_inicial / 100
    conta.saldo_atual = conta.saldo_atual / 100
    
    return conta


@router.post("", response_model=ContaBancariaResponse, status_code=201)
def criar_conta(
    conta_data: ContaBancariaCreate,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """Cria uma nova conta bancária"""
    current_user, tenant_id = user_and_tenant
    
    # Verificar se já existe conta com mesmo nome
    existe = db.query(ContaBancaria).filter(
        and_(
            ContaBancaria.nome == conta_data.nome,
            ContaBancaria.tenant_id == tenant_id
        )
    ).first()
    
    if existe:
        raise HTTPException(status_code=400, detail="Já existe uma conta com este nome")
    
    # Converter saldo (reais → centavos)
    saldo_centavos = int(conta_data.saldo_inicial * 100)
    
    # Criar conta
    nova_conta = ContaBancaria(
        nome=conta_data.nome,
        tipo=conta_data.tipo,
        banco=conta_data.banco,
        saldo_inicial=saldo_centavos,
        saldo_atual=saldo_centavos,
        cor=conta_data.cor,
        icone=conta_data.icone,
        ativa=conta_data.ativa,
        tenant_id=tenant_id
    )
    
    db.add(nova_conta)
    db.commit()
    db.refresh(nova_conta)
    
    # Se saldo inicial > 0, criar movimentação de abertura
    if saldo_centavos > 0:
        movimentacao = MovimentacaoFinanceira(
            data_movimento=datetime.utcnow(),
            tipo="entrada",
            valor=saldo_centavos,
            conta_bancaria_id=nova_conta.id,
            origem_tipo="abertura_conta",
            status="realizado",
            descricao=f"Saldo inicial da conta {nova_conta.nome}",
            tenant_id=tenant_id
        )
        db.add(movimentacao)
        db.commit()
    
    # Converter para resposta (centavos → reais)
    nova_conta.saldo_inicial = nova_conta.saldo_inicial / 100
    nova_conta.saldo_atual = nova_conta.saldo_atual / 100
    
    return nova_conta


@router.put("/{conta_id}", response_model=ContaBancariaResponse)
def atualizar_conta(
    conta_id: int,
    conta_data: ContaBancariaUpdate,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """Atualiza dados de uma conta bancária (não altera saldo)"""
    current_user, tenant_id = user_and_tenant
    
    conta = db.query(ContaBancaria).filter(
        and_(
            ContaBancaria.id == conta_id,
            ContaBancaria.tenant_id == tenant_id
        )
    ).first()
    
    if not conta:
        raise HTTPException(status_code=404, detail="Conta não encontrada")
    
    # Atualizar campos
    update_data = conta_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(conta, field, value)
    
    conta.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(conta)
    
    # Converter saldos (centavos → reais)
    conta.saldo_inicial = conta.saldo_inicial / 100
    conta.saldo_atual = conta.saldo_atual / 100
    
    return conta


@router.delete("/{conta_id}")
def excluir_conta(
    conta_id: int,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """Desativa uma conta bancária (soft delete)"""
    current_user, tenant_id = user_and_tenant
    
    conta = db.query(ContaBancaria).filter(
        and_(
            ContaBancaria.id == conta_id,
            ContaBancaria.tenant_id == tenant_id
        )
    ).first()
    
    if not conta:
        raise HTTPException(status_code=404, detail="Conta não encontrada")
    
    # Verificar se tem movimentações
    tem_movimentacoes = db.query(MovimentacaoFinanceira).filter(
        MovimentacaoFinanceira.conta_bancaria_id == conta_id
    ).count() > 0
    
    if tem_movimentacoes:
        # Soft delete - apenas desativar
        conta.ativa = False
        conta.updated_at = datetime.utcnow()
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
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """Ajusta o saldo de uma conta (cria movimentação de ajuste)"""
    current_user, tenant_id = user_and_tenant
    
    conta = db.query(ContaBancaria).filter(
        and_(
            ContaBancaria.id == conta_id,
            ContaBancaria.tenant_id == tenant_id
        )
    ).first()
    
    if not conta:
        raise HTTPException(status_code=404, detail="Conta não encontrada")
    
    # Converter novo saldo (reais → centavos)
    novo_saldo_centavos = int(ajuste.novo_saldo * 100)
    saldo_atual_centavos = conta.saldo_atual
    
    # Calcular diferença
    diferenca = novo_saldo_centavos - saldo_atual_centavos
    
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
        tenant_id=tenant_id
    )
    
    db.add(movimentacao)
    
    # Atualizar saldo da conta
    conta.saldo_atual = novo_saldo_centavos
    conta.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(conta)
    
    return {
        "message": "Saldo ajustado com sucesso",
        "saldo_anterior": saldo_atual_centavos / 100,
        "saldo_novo": novo_saldo_centavos / 100,
        "diferenca": diferenca / 100,
        "movimentacao_id": movimentacao.id
    }


@router.get("/{conta_id}/movimentacoes", response_model=List[MovimentacaoResponse])
def listar_movimentacoes(
    conta_id: int,
    limit: int = 50,
    offset: int = 0,
    tipo: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """Lista movimentações de uma conta (extrato)"""
    current_user, tenant_id = user_and_tenant
    
    # Verificar se conta existe e pertence ao usuário
    conta = db.query(ContaBancaria).filter(
        and_(
            ContaBancaria.id == conta_id,
            ContaBancaria.tenant_id == tenant_id
        )
    ).first()
    
    if not conta:
        raise HTTPException(status_code=404, detail="Conta não encontrada")
    
    # Buscar movimentações
    query = db.query(MovimentacaoFinanceira).filter(
        MovimentacaoFinanceira.conta_bancaria_id == conta_id
    )
    
    if tipo:
        query = query.filter(MovimentacaoFinanceira.tipo == tipo)
    
    if status:
        query = query.filter(MovimentacaoFinanceira.status == status)
    
    movimentacoes = query.order_by(
        desc(MovimentacaoFinanceira.data_movimento)
    ).offset(offset).limit(limit).all()
    
    # Converter valores (centavos → reais)
    for mov in movimentacoes:
        mov.valor = mov.valor / 100
    
    return movimentacoes


@router.get("/resumo/saldos")
def resumo_saldos(
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """Retorna resumo de saldos de todas as contas ativas"""
    current_user, tenant_id = user_and_tenant
    
    contas = db.query(ContaBancaria).filter(
        and_(
            ContaBancaria.tenant_id == tenant_id,
            ContaBancaria.ativa == True
        )
    ).all()
    
    resumo = {
        "total_geral": 0,
        "por_tipo": {
            "banco": 0,
            "caixa": 0,
            "digital": 0
        },
        "contas": []
    }
    
    for conta in contas:
        saldo_reais = conta.saldo_atual / 100
        resumo["total_geral"] += saldo_reais
        
        # Usar get para evitar KeyError com tipos não mapeados
        if conta.tipo in resumo["por_tipo"]:
            resumo["por_tipo"][conta.tipo] += saldo_reais
        
        resumo["contas"].append({
            "id": conta.id,
            "nome": conta.nome,
            "tipo": conta.tipo,
            "saldo": saldo_reais,
            "cor": conta.cor,
            "icone": conta.icone
        })
    
    return resumo
