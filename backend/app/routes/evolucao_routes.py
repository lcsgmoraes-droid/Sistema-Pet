"""Area autenticada de novidades e projetos do CorePet no ERP."""

from fastapi import APIRouter, Depends

from app.auth import get_current_user
from app.evolucao_corepet import listar_evolucao_corepet
from app.models import User


router = APIRouter(prefix="/evolucao", tags=["Evolucao CorePet"])


@router.get("")
def listar_evolucao_erp(_current_user: User = Depends(get_current_user)):
    return listar_evolucao_corepet("erp")
