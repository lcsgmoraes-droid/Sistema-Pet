"""Rotas de pets vinculadas a clientes."""

from datetime import datetime as dt
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user_and_tenant
from app.audit_log import log_create, log_delete, log_update
from app.db import get_session
from app.models import Cliente, Pet
from app.pet_clinical_utils import normalize_pet_clinical_payload
from app.clientes.schemas import PetCreate, PetResponse, PetUpdate

router = APIRouter()


def _validar_tenant_e_obter_usuario(user_and_tenant):
    current_user, tenant_id = user_and_tenant
    return current_user, tenant_id


def _obter_cliente_ou_404(db: Session, cliente_id: int, tenant_id: str):
    cliente = (
        db.query(Cliente)
        .filter(Cliente.id == cliente_id, Cliente.tenant_id == tenant_id)
        .first()
    )
    if not cliente:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Cliente n??o encontrado"
        )
    return cliente

# ========== SERIALIZACAO DE PETS ==========
def _pet_response_dict(pet: Pet) -> dict:
    idade_meses = None
    if pet.data_nascimento:
        hoje = dt.now()
        idade_meses = (hoje.year - pet.data_nascimento.year) * 12 + (
            hoje.month - pet.data_nascimento.month
        )

    return {
        "id": pet.id,
        "codigo": pet.codigo,
        "nome": pet.nome,
        "especie": pet.especie,
        "raca": pet.raca,
        "sexo": pet.sexo,
        "data_nascimento": pet.data_nascimento,
        "idade_aproximada": pet.idade_aproximada,
        "castrado": pet.castrado,
        "castrado_data": pet.castrado_data,
        "cor": pet.cor,
        "porte": pet.porte,
        "peso": pet.peso,
        "peso_kg": pet.peso,
        "idade_meses": idade_meses,
        "microchip": pet.microchip,
        "alergias": pet.alergias,
        "alergias_lista": pet.alergias_lista or [],
        "doencas_cronicas": pet.doencas_cronicas,
        "condicoes_cronicas_lista": pet.condicoes_cronicas_lista or [],
        "medicamentos_continuos": pet.medicamentos_continuos,
        "medicamentos_continuos_lista": pet.medicamentos_continuos_lista or [],
        "restricoes_alimentares_lista": pet.restricoes_alimentares_lista or [],
        "historico_clinico": pet.historico_clinico,
        "tipo_sanguineo": pet.tipo_sanguineo,
        "pedigree_registro": pet.pedigree_registro,
        "observacoes": pet.observacoes,
        "foto_url": pet.foto_url,
        "ativo": pet.ativo,
        "created_at": pet.created_at,
        "updated_at": pet.updated_at,
    }

# ==================== PETS ====================


@router.post(
    "/{cliente_id}/pets",
    response_model=PetResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_pet(
    cliente_id: int,
    pet_data: PetCreate,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Criar novo pet para um cliente"""
    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)
    cliente = _obter_cliente_ou_404(db, cliente_id, tenant_id)

    # Gerar cÃ³digo Ãºnico para o pet baseado no cÃ³digo do cliente
    codigo_pet = f"{cliente.codigo}-PET-{db.query(Pet).filter(Pet.cliente_id == cliente_id).count() + 1:04d}"
    pet_payload = normalize_pet_clinical_payload(pet_data.model_dump())

    # Criar pet
    novo_pet = Pet(
        cliente_id=cliente_id,
        user_id=current_user.id,
        tenant_id=tenant_id,
        codigo=codigo_pet,
        **pet_payload,
    )

    db.add(novo_pet)
    db.commit()
    db.refresh(novo_pet)

    # Log de auditoria
    log_create(
        db,
        current_user.id,
        "pet",
        novo_pet.id,
        {"cliente_id": cliente_id, **pet_payload},
    )

    return novo_pet


@router.get("/pets/todos", response_model=List[PetResponse])
def listar_todos_pets(
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Listar todos os pets do usuÃ¡rio (de todos os clientes)"""
    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)

    pets = (
        db.query(Pet)
        .join(Cliente)
        .filter(Cliente.tenant_id == tenant_id)
        .order_by(Pet.nome)
        .all()
    )

    return pets


@router.get("/{cliente_id}/pets", response_model=List[PetResponse])
def list_pets_by_cliente(
    cliente_id: int,
    ativo: Optional[bool] = None,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Listar pets de um cliente"""
    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)
    _obter_cliente_ou_404(db, cliente_id, tenant_id)

    query = db.query(Pet).filter(Pet.cliente_id == cliente_id)

    if ativo is not None:
        query = query.filter(Pet.ativo == ativo)

    pets = query.order_by(Pet.nome).all()
    return pets


@router.get("/pets/{pet_id}", response_model=PetResponse)
def get_pet(
    pet_id: int,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Obter pet por ID"""
    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)

    pet = (
        db.query(Pet)
        .join(Cliente)
        .filter(Pet.id == pet_id, Cliente.tenant_id == tenant_id)
        .first()
    )

    if not pet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Pet nÃ£o encontrado"
        )

    return _pet_response_dict(pet)


@router.put("/pets/{pet_id}", response_model=PetResponse)
def update_pet(
    pet_id: int,
    pet_data: PetUpdate,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Atualizar pet"""
    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)

    pet = (
        db.query(Pet)
        .join(Cliente)
        .filter(Pet.id == pet_id, Cliente.tenant_id == tenant_id)
        .first()
    )

    if not pet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Pet nÃ£o encontrado"
        )

    # Capturar dados antigos para auditoria
    old_data = {
        "nome": pet.nome,
        "especie": pet.especie,
        "raca": pet.raca,
        "sexo": pet.sexo,
        "data_nascimento": pet.data_nascimento.isoformat()
        if pet.data_nascimento
        else None,
        "cor": pet.cor,
        "peso": pet.peso,
        "observacoes": pet.observacoes,
    }

    # Atualizar campos
    update_data = normalize_pet_clinical_payload(
        pet_data.model_dump(exclude_unset=True)
    )

    # Se idade_aproximada foi fornecida, converter para data_nascimento
    if (
        "idade_aproximada" in update_data
        and update_data["idade_aproximada"] is not None
    ):
        idade_meses = update_data["idade_aproximada"]
        hoje = dt.utcnow()
        # Calcular data de nascimento subtraindo os meses
        anos = idade_meses // 12
        meses = idade_meses % 12
        ano_nascimento = hoje.year - anos
        mes_nascimento = hoje.month - meses

        # Ajustar se o mÃªs ficar negativo
        if mes_nascimento <= 0:
            mes_nascimento += 12
            ano_nascimento -= 1

        # Usar dia 1 como padrÃ£o
        pet.data_nascimento = dt(ano_nascimento, mes_nascimento, 1)
        # Remover idade_aproximada do update_data pois jÃ¡ foi processada
        del update_data["idade_aproximada"]

    for field, value in update_data.items():
        setattr(pet, field, value)

    pet.updated_at = dt.utcnow()
    db.commit()
    db.refresh(pet)

    # Log de auditoria com old_data e new_data
    log_update(db, current_user, "pet", pet.id, old_data, update_data)

    return _pet_response_dict(pet)


@router.delete("/pets/{pet_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_pet(
    pet_id: int,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Desativar pet (soft delete)"""
    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)

    pet = (
        db.query(Pet)
        .join(Cliente)
        .filter(Pet.id == pet_id, Cliente.tenant_id == tenant_id)
        .first()
    )

    if not pet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Pet nÃ£o encontrado"
        )

    # Soft delete
    pet.ativo = False
    pet.updated_at = dt.utcnow()
    db.commit()

    # Log de auditoria
    log_delete(
        db,
        current_user.id,
        "pet",
        pet.id,
        {"nome": pet.nome, "especie": pet.especie, "cliente_id": pet.cliente_id},
    )

    return None
