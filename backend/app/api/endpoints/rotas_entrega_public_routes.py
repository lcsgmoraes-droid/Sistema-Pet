from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.endpoints.rotas_entrega_tracking import montar_rastreio_publico
from app.db import get_session


router = APIRouter(prefix="/rotas-entrega", tags=["Entregas - Rastreio"])


@router.get("/rastreio/{token}")
def rastreio_publico(
    token: str,
    db: Session = Depends(get_session),
):
    """Rastreio publico por token opaco, sem exigir login no ERP."""
    return montar_rastreio_publico(db, token)
