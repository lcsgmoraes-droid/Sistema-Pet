from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user_and_tenant
from app.banho_tosa_api.utils import obter_ou_criar_configuracao
from app.banho_tosa_schemas import BanhoTosaConfiguracaoResponse, BanhoTosaConfiguracaoUpdate
from app.db import get_session
from app.veterinario_core import _get_tenant


router = APIRouter()


@router.get("/configuracao", response_model=BanhoTosaConfiguracaoResponse)
def obter_configuracao(
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    _, tenant_id = _get_tenant(current)
    return obter_ou_criar_configuracao(db, tenant_id)


@router.patch("/configuracao", response_model=BanhoTosaConfiguracaoResponse)
def atualizar_configuracao(
    body: BanhoTosaConfiguracaoUpdate,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    _, tenant_id = _get_tenant(current)
    config = obter_ou_criar_configuracao(db, tenant_id)

    for campo, valor in body.model_dump(exclude_unset=True).items():
        setattr(config, campo, valor)

    db.commit()
    db.refresh(config)
    return config
