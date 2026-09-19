"""Rotas de pet-mestre — camada geral do grupo comercial, Checkpoint 3.
Aditivo: não altera nenhuma rota existente de cadastro/prontuário de pet.
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user_and_tenant
from app.db import get_session
from app.grupo_comercial_contexto import obter_grupo_id_ativo
from app.models_cadastros import Pet
from app.pet_mestre_service import (
    desvincular_pet_mestre,
    sugerir_pet_mestre,
    vincular_pet_mestre,
)

router = APIRouter(prefix="/pet-mestre", tags=["Pet mestre"])


class PetMestreSugestaoResponse(BaseModel):
    id: int
    nome: str
    especie: str
    raca: Optional[str] = None


class VincularPetMestreRequest(BaseModel):
    mestre_id: Optional[int] = None
    """Vincula a este pet-mestre existente do grupo; se omitido, promove o
    próprio pet local a um mestre novo."""


@router.get("/sugestao", response_model=Optional[PetMestreSugestaoResponse])
def sugerir_mestre_pet(
    microchip: Optional[str] = None,
    nome: Optional[str] = None,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    _current_user, tenant_id = user_and_tenant
    grupo_id = obter_grupo_id_ativo(db, tenant_id)
    if grupo_id is None:
        return None
    return sugerir_pet_mestre(db, grupo_id, microchip=microchip, nome=nome)


@router.post("/{pet_id}/vincular", response_model=PetMestreSugestaoResponse)
def vincular_mestre_pet(
    pet_id: int,
    payload: VincularPetMestreRequest,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    current_user, tenant_id = user_and_tenant
    pet = db.query(Pet).filter(Pet.id == pet_id, Pet.tenant_id == tenant_id).first()
    if not pet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Pet não encontrado"
        )
    grupo_id = obter_grupo_id_ativo(db, tenant_id)
    if grupo_id is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Esta loja não tem grupo comercial ativo.",
        )
    return vincular_pet_mestre(
        db,
        pet=pet,
        grupo_id=grupo_id,
        usuario_id=current_user.id,
        pet_mestre_id=payload.mestre_id,
    )


@router.delete("/{pet_id}/vincular", status_code=status.HTTP_204_NO_CONTENT)
def remover_vinculo_mestre_pet(
    pet_id: int,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    _current_user, tenant_id = user_and_tenant
    pet = db.query(Pet).filter(Pet.id == pet_id, Pet.tenant_id == tenant_id).first()
    if not pet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Pet não encontrado"
        )
    desvincular_pet_mestre(db, pet=pet)
    return None
