"""
Routes para gerenciamento de Cargos (RH)
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from decimal import Decimal
from pydantic import BaseModel, Field
from uuid import UUID

from app.db import get_session
from app.cargo_models import Cargo
from app.models import Cliente
from app.auth.dependencies import get_current_user_and_tenant

router = APIRouter(prefix="/cargos", tags=["RH - Cargos"])


# Schemas
class CargoCreate(BaseModel):
    nome: str = Field(..., min_length=1, max_length=100)
    descricao: Optional[str] = None
    salario_base: Decimal = Field(..., gt=0)
    regime_remuneracao: str = Field(default="clt", pattern="^(clt|sem_encargos|estagio|informal)$")
    gera_encargos: bool = True
    inss_patronal_percentual: Optional[Decimal] = Field(default=Decimal("20.00"), ge=0, le=100)
    fgts_percentual: Optional[Decimal] = Field(default=Decimal("8.00"), ge=0, le=100)
    inss_funcionario_percentual: Optional[Decimal] = Field(default=Decimal("0.00"), ge=0, le=100)
    inss_funcionario_valor: Optional[Decimal] = Field(default=Decimal("0.00"), ge=0)
    desconto_transporte_valor: Optional[Decimal] = Field(default=Decimal("0.00"), ge=0)
    outros_descontos_valor: Optional[Decimal] = Field(default=Decimal("0.00"), ge=0)
    gera_ferias: bool = True
    gera_decimo_terceiro: bool = True
    ativo: bool = True

    model_config = {"from_attributes": True}


class CargoUpdate(BaseModel):
    nome: Optional[str] = Field(None, min_length=1, max_length=100)
    descricao: Optional[str] = None
    salario_base: Optional[Decimal] = Field(None, gt=0)
    regime_remuneracao: Optional[str] = Field(None, pattern="^(clt|sem_encargos|estagio|informal)$")
    gera_encargos: Optional[bool] = None
    inss_patronal_percentual: Optional[Decimal] = Field(None, ge=0, le=100)
    fgts_percentual: Optional[Decimal] = Field(None, ge=0, le=100)
    inss_funcionario_percentual: Optional[Decimal] = Field(None, ge=0, le=100)
    inss_funcionario_valor: Optional[Decimal] = Field(None, ge=0)
    desconto_transporte_valor: Optional[Decimal] = Field(None, ge=0)
    outros_descontos_valor: Optional[Decimal] = Field(None, ge=0)
    gera_ferias: Optional[bool] = None
    gera_decimo_terceiro: Optional[bool] = None
    ativo: Optional[bool] = None

    model_config = {"from_attributes": True}


class CargoResponse(BaseModel):
    id: int
    tenant_id: UUID
    nome: str
    descricao: Optional[str]
    salario_base: Decimal
    regime_remuneracao: str
    gera_encargos: bool
    inss_patronal_percentual: Decimal
    fgts_percentual: Decimal
    inss_funcionario_percentual: Decimal
    inss_funcionario_valor: Decimal
    desconto_transporte_valor: Decimal
    outros_descontos_valor: Decimal
    gera_ferias: bool
    gera_decimo_terceiro: bool
    ativo: bool
    total_funcionarios: int = 0

    model_config = {"from_attributes": True}


def _cargo_response_dict(cargo: Cargo, total_funcionarios: int = 0) -> dict:
    return {
        "id": cargo.id,
        "tenant_id": cargo.tenant_id,
        "nome": cargo.nome,
        "descricao": cargo.descricao,
        "salario_base": cargo.salario_base,
        "regime_remuneracao": cargo.regime_remuneracao,
        "gera_encargos": cargo.gera_encargos,
        "inss_patronal_percentual": cargo.inss_patronal_percentual,
        "fgts_percentual": cargo.fgts_percentual,
        "inss_funcionario_percentual": cargo.inss_funcionario_percentual,
        "inss_funcionario_valor": cargo.inss_funcionario_valor,
        "desconto_transporte_valor": cargo.desconto_transporte_valor,
        "outros_descontos_valor": cargo.outros_descontos_valor,
        "gera_ferias": cargo.gera_ferias,
        "gera_decimo_terceiro": cargo.gera_decimo_terceiro,
        "ativo": cargo.ativo,
        "total_funcionarios": total_funcionarios,
    }


# Endpoints
@router.get("", response_model=List[CargoResponse])
async def listar_cargos(
    ativo: Optional[bool] = Query(None, description="Filtrar por status ativo/inativo"),
    db: Session = Depends(get_session),
    current_user_and_tenant=Depends(get_current_user_and_tenant)
):
    """
    Lista todos os cargos do tenant.
    """
    user, tenant_id = current_user_and_tenant
    
    # Contar funcionários por cargo
    query = db.query(
        Cargo,
        func.count(Cliente.id).label('total_funcionarios')
    ).outerjoin(
        Cliente,
        (Cargo.id == Cliente.cargo_id) &
        (Cliente.tipo_cadastro == 'funcionario') &
        (Cliente.ativo == True)
    ).filter(
        Cargo.tenant_id == tenant_id
    )
    
    if ativo is not None:
        query = query.filter(Cargo.ativo == ativo)
    
    query = query.group_by(Cargo.id).order_by(Cargo.nome)
    
    result = query.all()
    
    cargos_response = []
    for cargo, total_func in result:
        cargos_response.append(CargoResponse(**_cargo_response_dict(cargo, total_func)))
    
    return cargos_response


@router.get("/{cargo_id}", response_model=CargoResponse)
async def obter_cargo(
    cargo_id: int,
    db: Session = Depends(get_session),
    current_user_and_tenant=Depends(get_current_user_and_tenant)
):
    """
    Obtém detalhes de um cargo específico.
    """
    user, tenant_id = current_user_and_tenant
    
    cargo = db.query(Cargo).filter(
        Cargo.id == cargo_id,
        Cargo.tenant_id == tenant_id
    ).first()
    
    if not cargo:
        raise HTTPException(status_code=404, detail="Cargo não encontrado")
    
    # Contar funcionários
    from app.models import Cliente
    total_funcionarios = db.query(Cliente).filter(
        Cliente.tenant_id == tenant_id,
        Cliente.cargo_id == cargo_id,
        Cliente.tipo_cadastro == "funcionario",
        Cliente.ativo == True
    ).count()
    
    return CargoResponse(**_cargo_response_dict(cargo, total_funcionarios))


@router.post("", response_model=CargoResponse, status_code=201)
async def criar_cargo(
    cargo_data: CargoCreate,
    db: Session = Depends(get_session),
    current_user_and_tenant=Depends(get_current_user_and_tenant)
):
    """
    Cria um novo cargo.
    """
    user, tenant_id = current_user_and_tenant
    
    # Verificar se já existe cargo com esse nome
    cargo_existente = db.query(Cargo).filter(
        Cargo.tenant_id == tenant_id,
        func.lower(Cargo.nome) == func.lower(cargo_data.nome),
        Cargo.ativo == True
    ).first()
    
    if cargo_existente:
        raise HTTPException(
            status_code=400,
            detail=f"Já existe um cargo ativo com o nome '{cargo_data.nome}'"
        )
    
    # Criar cargo
    cargo = Cargo(
        tenant_id=tenant_id,
        nome=cargo_data.nome.strip(),
        descricao=cargo_data.descricao.strip() if cargo_data.descricao else None,
        salario_base=cargo_data.salario_base,
        regime_remuneracao=cargo_data.regime_remuneracao,
        gera_encargos=cargo_data.gera_encargos,
        inss_patronal_percentual=cargo_data.inss_patronal_percentual,
        fgts_percentual=cargo_data.fgts_percentual,
        inss_funcionario_percentual=cargo_data.inss_funcionario_percentual,
        inss_funcionario_valor=cargo_data.inss_funcionario_valor,
        desconto_transporte_valor=cargo_data.desconto_transporte_valor,
        outros_descontos_valor=cargo_data.outros_descontos_valor,
        gera_ferias=cargo_data.gera_ferias,
        gera_decimo_terceiro=cargo_data.gera_decimo_terceiro,
        ativo=cargo_data.ativo
    )
    
    db.add(cargo)
    db.commit()
    db.refresh(cargo)
    
    return CargoResponse(**_cargo_response_dict(cargo, 0))


@router.put("/{cargo_id}", response_model=CargoResponse)
async def atualizar_cargo(
    cargo_id: int,
    cargo_data: CargoUpdate,
    db: Session = Depends(get_session),
    current_user_and_tenant=Depends(get_current_user_and_tenant)
):
    """
    Atualiza um cargo existente.
    """
    user, tenant_id = current_user_and_tenant
    
    cargo = db.query(Cargo).filter(
        Cargo.id == cargo_id,
        Cargo.tenant_id == tenant_id
    ).first()
    
    if not cargo:
        raise HTTPException(status_code=404, detail="Cargo não encontrado")
    
    # Verificar duplicação de nome
    if cargo_data.nome and cargo_data.nome != cargo.nome:
        cargo_existente = db.query(Cargo).filter(
            Cargo.tenant_id == tenant_id,
            func.lower(Cargo.nome) == func.lower(cargo_data.nome),
            Cargo.id != cargo_id,
            Cargo.ativo == True
        ).first()
        
        if cargo_existente:
            raise HTTPException(
                status_code=400,
                detail=f"Já existe um cargo ativo com o nome '{cargo_data.nome}'"
            )
    
    # Atualizar campos
    update_data = cargo_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if field == "nome" and value:
            setattr(cargo, field, value.strip())
        elif field == "descricao" and value:
            setattr(cargo, field, value.strip())
        else:
            setattr(cargo, field, value)
    
    db.commit()
    db.refresh(cargo)
    
    # Contar funcionários
    from app.models import Cliente
    total_funcionarios = db.query(Cliente).filter(
        Cliente.tenant_id == tenant_id,
        Cliente.cargo_id == cargo_id,
        Cliente.tipo_cadastro == "funcionario",
        Cliente.ativo == True
    ).count()
    
    return CargoResponse(**_cargo_response_dict(cargo, total_funcionarios))


@router.patch("/{cargo_id}/status")
async def alterar_status_cargo(
    cargo_id: int,
    ativo: bool,
    db: Session = Depends(get_session),
    current_user_and_tenant=Depends(get_current_user_and_tenant)
):
    """
    Altera o status ativo/inativo de um cargo.
    """
    user, tenant_id = current_user_and_tenant
    
    cargo = db.query(Cargo).filter(
        Cargo.id == cargo_id,
        Cargo.tenant_id == tenant_id
    ).first()
    
    if not cargo:
        raise HTTPException(status_code=404, detail="Cargo não encontrado")
    
    cargo.ativo = ativo
    db.commit()
    
    return {"message": f"Cargo {'ativado' if ativo else 'inativado'} com sucesso"}


@router.delete("/{cargo_id}")
async def deletar_cargo(
    cargo_id: int,
    db: Session = Depends(get_session),
    current_user_and_tenant=Depends(get_current_user_and_tenant)
):
    """
    Inativa um cargo (não remove fisicamente se houver funcionários associados).
    """
    user, tenant_id = current_user_and_tenant
    
    cargo = db.query(Cargo).filter(
        Cargo.id == cargo_id,
        Cargo.tenant_id == tenant_id
    ).first()
    
    if not cargo:
        raise HTTPException(status_code=404, detail="Cargo não encontrado")
    
    # Verificar se há funcionários ativos usando este cargo
    from app.models import Cliente
    funcionarios_ativos = db.query(Cliente).filter(
        Cliente.tenant_id == tenant_id,
        Cliente.cargo_id == cargo_id,
        Cliente.tipo_cadastro == "funcionario",
        Cliente.ativo == True
    ).count()
    
    if funcionarios_ativos > 0:
        # Apenas inativar
        cargo.ativo = False
        db.commit()
        return {
            "message": f"Cargo inativado com sucesso. {funcionarios_ativos} funcionário(s) ainda vinculado(s)."
        }
    else:
        # Pode remover fisicamente
        db.delete(cargo)
        db.commit()
        return {"message": "Cargo removido com sucesso"}
