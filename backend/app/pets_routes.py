"""
Módulo dedicado para gestão de PETS
Separado do cadastro de clientes para permitir evolução veterinária
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_, and_, func
from typing import List, Optional
from datetime import datetime as dt
import secrets

from .db import get_session
from .auth import get_current_user
from .auth.dependencies import get_current_user_and_tenant
from .models import User, Pet, Cliente

from pydantic import BaseModel, Field


# ============================================================
# SCHEMAS
# ============================================================

class PetBase(BaseModel):
    """Dados base do pet"""
    nome: str = Field(..., min_length=1, max_length=255)
    especie: str = Field(..., min_length=1, max_length=50)
    raca: Optional[str] = Field(None, max_length=100)
    sexo: Optional[str] = Field(None, max_length=10)
    castrado: bool = False
    
    # Características
    data_nascimento: Optional[dt] = None
    idade_aproximada: Optional[int] = None  # em meses
    peso: Optional[float] = None
    cor: Optional[str] = Field(None, max_length=100)
    porte: Optional[str] = Field(None, max_length=20)
    
    # Saúde
    microchip: Optional[str] = Field(None, max_length=50)
    alergias: Optional[str] = None
    doencas_cronicas: Optional[str] = None
    medicamentos_continuos: Optional[str] = None
    historico_clinico: Optional[str] = None
    
    # Outros
    observacoes: Optional[str] = None
    foto_url: Optional[str] = Field(None, max_length=500)
    ativo: bool = True


class PetCreate(PetBase):
    """Schema para criação de pet"""
    cliente_id: int = Field(..., gt=0)


class PetUpdate(PetBase):
    """Schema para atualização de pet (todos os campos opcionais)"""
    nome: Optional[str] = Field(None, min_length=1, max_length=255)
    especie: Optional[str] = Field(None, min_length=1, max_length=50)
    cliente_id: Optional[int] = Field(None, gt=0)


class PetResponse(PetBase):
    """Schema de resposta do pet"""
    id: int
    codigo: str
    cliente_id: int
    user_id: int
    created_at: dt
    updated_at: dt
    
    # Dados do cliente (tutor)
    cliente_nome: Optional[str] = None
    cliente_telefone: Optional[str] = None
    cliente_celular: Optional[str] = None

    class Config:
        from_attributes = True


class PetListItem(BaseModel):
    """Item simplificado para listagem"""
    id: int
    codigo: str
    nome: str
    especie: str
    raca: Optional[str]
    sexo: Optional[str]
    ativo: bool
    cliente_id: int
    cliente_nome: str
    created_at: dt

    class Config:
        from_attributes = True


# ============================================================
# ROUTER
# ============================================================

router = APIRouter(
    prefix="/pets",
    tags=["pets"]
)


# ============================================================
# HELPERS
# ============================================================

def gerar_codigo_pet(db: Session, user_id: int) -> str:
    """Gera código único para o pet"""
    while True:
        codigo = f"PET-{secrets.token_hex(4).upper()}"
        existe = db.query(Pet).filter(
            Pet.codigo == codigo,
            Pet.user_id == user_id
        ).first()
        if not existe:
            return codigo


def enriquecer_pet_response(pet: Pet) -> dict:
    """Adiciona dados do cliente ao response"""
    pet_dict = {
        "id": pet.id,
        "codigo": pet.codigo,
        "cliente_id": pet.cliente_id,
        "user_id": pet.user_id,
        "nome": pet.nome,
        "especie": pet.especie,
        "raca": pet.raca,
        "sexo": pet.sexo,
        "castrado": pet.castrado,
        "data_nascimento": pet.data_nascimento,
        "idade_aproximada": pet.idade_aproximada,
        "peso": pet.peso,
        "cor": pet.cor,
        "porte": pet.porte,
        "microchip": pet.microchip,
        "alergias": pet.alergias,
        "doencas_cronicas": pet.doencas_cronicas,
        "medicamentos_continuos": pet.medicamentos_continuos,
        "historico_clinico": pet.historico_clinico,
        "observacoes": pet.observacoes,
        "foto_url": pet.foto_url,
        "ativo": pet.ativo,
        "created_at": pet.created_at,
        "updated_at": pet.updated_at,
        "cliente_nome": pet.cliente.nome if pet.cliente else None,
        "cliente_telefone": pet.cliente.telefone if pet.cliente else None,
        "cliente_celular": pet.cliente.celular if pet.cliente else None,
    }
    return pet_dict


# ============================================================
# ENDPOINTS
# ============================================================

@router.get("", response_model=List[PetResponse])
def listar_pets(
    busca: Optional[str] = Query(None, description="Busca por nome do pet, raça, microchip ou nome do tutor"),
    cliente_id: Optional[int] = Query(None, description="Filtrar por cliente"),
    especie: Optional[str] = Query(None, description="Filtrar por espécie"),
    ativo: Optional[bool] = Query(None, description="Filtrar por status ativo/inativo"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """
    Lista todos os pets do tenant com filtros
    """
    current_user, tenant_id = user_and_tenant
    
    # Filtrar por tenant_id (multi-tenant)
    query = db.query(Pet).join(Cliente).filter(Cliente.tenant_id == tenant_id)
    query = query.options(joinedload(Pet.cliente))
    
    # Filtros
    if cliente_id:
        query = query.filter(Pet.cliente_id == cliente_id)
    
    if especie:
        query = query.filter(Pet.especie.ilike(f"%{especie}%"))
    
    if ativo is not None:
        query = query.filter(Pet.ativo == ativo)
    
    if busca:
        busca_term = f"%{busca}%"
        # Join com Cliente para buscar pelo nome do tutor também
        query = query.join(Pet.cliente).filter(
            or_(
                Pet.nome.ilike(busca_term),
                Pet.raca.ilike(busca_term),
                Pet.microchip.ilike(busca_term),
                Pet.codigo.ilike(busca_term),
                Cliente.nome.ilike(busca_term)  # Busca pelo nome do tutor
            )
        )
    
    # Ordenação: pets ativos primeiro, depois por nome
    query = query.order_by(Pet.ativo.desc(), Pet.nome.asc())
    
    pets = query.offset(skip).limit(limit).all()
    
    return [enriquecer_pet_response(pet) for pet in pets]


@router.post("", response_model=PetResponse, status_code=status.HTTP_201_CREATED)
def criar_pet(
    pet_data: PetCreate,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """
    Cria um novo pet
    """
    current_user, tenant_id = user_and_tenant
    
    # Validar se cliente existe e pertence ao tenant
    cliente = db.query(Cliente).filter(
        Cliente.id == pet_data.cliente_id,
        Cliente.tenant_id == tenant_id
    ).first()
    
    if not cliente:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cliente não encontrado"
        )
    
    # Gerar código único
    codigo = gerar_codigo_pet(db, current_user.id)
    
    # Criar pet
    novo_pet = Pet(
        user_id=current_user.id,
        tenant_id=tenant_id,
        cliente_id=pet_data.cliente_id,
        codigo=codigo,
        nome=pet_data.nome,
        especie=pet_data.especie,
        raca=pet_data.raca,
        sexo=pet_data.sexo,
        castrado=pet_data.castrado,
        data_nascimento=pet_data.data_nascimento,
        idade_aproximada=pet_data.idade_aproximada,
        peso=pet_data.peso,
        cor=pet_data.cor,
        porte=pet_data.porte,
        microchip=pet_data.microchip,
        alergias=pet_data.alergias,
        doencas_cronicas=pet_data.doencas_cronicas,
        medicamentos_continuos=pet_data.medicamentos_continuos,
        historico_clinico=pet_data.historico_clinico,
        observacoes=pet_data.observacoes,
        foto_url=pet_data.foto_url,
        ativo=pet_data.ativo
    )
    
    db.add(novo_pet)
    db.commit()
    db.refresh(novo_pet)
    
    # Carregar relacionamento
    db.refresh(novo_pet)
    pet_com_cliente = db.query(Pet).options(
        joinedload(Pet.cliente)
    ).filter(Pet.id == novo_pet.id).first()
    
    return enriquecer_pet_response(pet_com_cliente)


@router.get("/{pet_id}", response_model=PetResponse)
def obter_pet(
    pet_id: int,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """
    Obtém detalhes de um pet específico
    """
    current_user, tenant_id = user_and_tenant
    
    pet = db.query(Pet).options(
        joinedload(Pet.cliente)
    ).join(Cliente).filter(
        Pet.id == pet_id,
        Cliente.tenant_id == tenant_id
    ).first()
    
    if not pet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pet não encontrado"
        )
    
    return enriquecer_pet_response(pet)


@router.put("/{pet_id}", response_model=PetResponse)
def atualizar_pet(
    pet_id: int,
    pet_data: PetUpdate,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """
    Atualiza dados de um pet
    """
    current_user, tenant_id = user_and_tenant
    
    pet = db.query(Pet).join(Cliente).filter(
        Pet.id == pet_id,
        Cliente.tenant_id == tenant_id
    ).first()
    
    if not pet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pet não encontrado"
        )
    
    # Se mudou o cliente, validar
    if pet_data.cliente_id and pet_data.cliente_id != pet.cliente_id:
        novo_cliente = db.query(Cliente).filter(
            Cliente.id == pet_data.cliente_id,
            Cliente.tenant_id == tenant_id
        ).first()
        
        if not novo_cliente:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Novo cliente não encontrado"
            )
    
    # Atualizar campos fornecidos
    update_data = pet_data.model_dump(exclude_unset=True)
    
    # Se idade_aproximada foi fornecida, converter para data_nascimento
    if 'idade_aproximada' in update_data and update_data['idade_aproximada'] is not None:
        idade_meses = update_data['idade_aproximada']
        hoje = dt.now()
        # Calcular data de nascimento subtraindo os meses
        anos = idade_meses // 12
        meses = idade_meses % 12
        ano_nascimento = hoje.year - anos
        mes_nascimento = hoje.month - meses
        
        # Ajustar se o mês ficar negativo
        if mes_nascimento <= 0:
            mes_nascimento += 12
            ano_nascimento -= 1
        
        # Usar dia 1 como padrão
        pet.data_nascimento = dt(ano_nascimento, mes_nascimento, 1)
        # Remover idade_aproximada do update_data pois já foi processada
        del update_data['idade_aproximada']
    
    for field, value in update_data.items():
        setattr(pet, field, value)
    
    pet.updated_at = dt.now()
    
    db.commit()
    db.refresh(pet)
    
    # Carregar com relacionamento
    pet_com_cliente = db.query(Pet).options(
        joinedload(Pet.cliente)
    ).filter(Pet.id == pet.id).first()
    
    return enriquecer_pet_response(pet_com_cliente)


@router.delete("/{pet_id}", status_code=status.HTTP_204_NO_CONTENT)
def excluir_pet(
    pet_id: int,
    soft_delete: bool = Query(True, description="Se True, apenas desativa. Se False, exclui permanentemente"),
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """
    Exclui ou desativa um pet (soft delete por padrão)
    """
    current_user, tenant_id = user_and_tenant
    
    pet = db.query(Pet).join(Cliente).filter(
        Pet.id == pet_id,
        Cliente.tenant_id == tenant_id
    ).first()
    
    if not pet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pet não encontrado"
        )
    
    if soft_delete:
        # Soft delete: apenas marca como inativo
        pet.ativo = False
        pet.updated_at = dt.now()
        db.commit()
    else:
        # Hard delete: remove permanentemente
        db.delete(pet)
        db.commit()
    
    return None


@router.post("/{pet_id}/ativar", response_model=PetResponse)
def ativar_pet(
    pet_id: int,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """
    Reativa um pet desativado
    """
    current_user, tenant_id = user_and_tenant
    
    pet = db.query(Pet).join(Cliente).filter(
        Pet.id == pet_id,
        Cliente.tenant_id == tenant_id
    ).first()
    
    if not pet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pet não encontrado"
        )
    
    pet.ativo = True
    pet.updated_at = dt.now()
    db.commit()
    db.refresh(pet)
    
    pet_com_cliente = db.query(Pet).options(
        joinedload(Pet.cliente)
    ).filter(Pet.id == pet.id).first()
    
    return enriquecer_pet_response(pet_com_cliente)


@router.get("/cliente/{cliente_id}", response_model=List[PetResponse])
def listar_pets_por_cliente(
    cliente_id: int,
    incluir_inativos: bool = Query(False, description="Incluir pets inativos"),
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """
    Lista todos os pets de um cliente específico
    """
    current_user, tenant_id = user_and_tenant
    
    # Validar cliente
    cliente = db.query(Cliente).filter(
        Cliente.id == cliente_id,
        Cliente.tenant_id == tenant_id
    ).first()
    
    if not cliente:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cliente não encontrado"
        )
    
    query = db.query(Pet).options(
        joinedload(Pet.cliente)
    ).join(Cliente).filter(
        Pet.cliente_id == cliente_id,
        Cliente.tenant_id == tenant_id
    )
    
    if not incluir_inativos:
        query = query.filter(Pet.ativo == True)
    
    pets = query.order_by(Pet.ativo.desc(), Pet.nome.asc()).all()
    
    return [enriquecer_pet_response(pet) for pet in pets]
