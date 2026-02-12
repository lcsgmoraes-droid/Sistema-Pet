from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db import get_session
from app.auth.dependencies import get_current_user_and_tenant
from app.models_configuracao_custo_moto import ConfiguracaoCustoMoto
from app.schemas.configuracao_custo_moto import (
    ConfiguracaoCustoMotoUpdate,
    ConfiguracaoCustoMotoResponse,
)

router = APIRouter(prefix="/configuracoes/custo-moto", tags=["Custos da Moto"])


@router.get("", response_model=ConfiguracaoCustoMotoResponse)
def get_config(db: Session = Depends(get_session), user_and_tenant=Depends(get_current_user_and_tenant)):
    user, tenant_id = user_and_tenant
    config = (
        db.query(ConfiguracaoCustoMoto)
        .filter(ConfiguracaoCustoMoto.tenant_id == tenant_id)
        .first()
    )

    if not config:
        config = ConfiguracaoCustoMoto(
            tenant_id=tenant_id,
            preco_combustivel=0,
            km_por_litro=1,
        )
        db.add(config)
        db.commit()
        db.refresh(config)

    return config


@router.put("", response_model=ConfiguracaoCustoMotoResponse)
def update_config(
    payload: ConfiguracaoCustoMotoUpdate,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    user, tenant_id = user_and_tenant
    config = (
        db.query(ConfiguracaoCustoMoto)
        .filter(ConfiguracaoCustoMoto.tenant_id == tenant_id)
        .first()
    )

    if not config:
        config = ConfiguracaoCustoMoto(tenant_id=tenant_id)
        db.add(config)

    for field, value in payload.dict(exclude_unset=True).items():
        setattr(config, field, value)

    db.commit()
    db.refresh(config)
    return config
