"""
Rotas da API para o perfil de entregador no app mobile.
Autenticação via token ecommerce_customer + validação is_entregador=True.
"""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session, joinedload

from app.auth.core import ALGORITHM
from app.config import JWT_SECRET_KEY
from app.db import get_session
from app.models import Cliente, User
from app.rotas_entrega_models import RotaEntrega, RotaEntregaParada
from app.schemas.rota_entrega import RotaEntregaResponse
from app.vendas_models import Venda

router = APIRouter(prefix="/ecommerce/entregador", tags=["ecommerce-entregador"])
_security = HTTPBearer()


def _get_entregador_cliente(
    credentials: HTTPAuthorizationCredentials = Depends(_security),
    db: Session = Depends(get_session),
) -> Cliente:
    """Valida o token Bearer e retorna o Cliente com is_entregador=True."""
    auth_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token inválido",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(credentials.credentials, JWT_SECRET_KEY, algorithms=[ALGORITHM])
        user_id = int(payload.get("sub"))
        if payload.get("token_type") != "ecommerce_customer":
            raise auth_exc
    except (JWTError, TypeError, ValueError):
        raise auth_exc

    user = db.query(User).filter(User.id == user_id, User.is_active == True).first()
    if not user:
        raise auth_exc

    cliente = (
        db.query(Cliente)
        .filter(Cliente.tenant_id == str(user.tenant_id), Cliente.user_id == user.id)
        .first()
    )
    if not cliente or not cliente.is_entregador:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso restrito a entregadores",
        )
    return cliente


@router.get("/minhas-rotas", response_model=List[RotaEntregaResponse])
def minhas_rotas(
    filtro_status: Optional[str] = Query(None, alias="status"),
    cliente: Cliente = Depends(_get_entregador_cliente),
    db: Session = Depends(get_session),
):
    """
    Retorna as rotas atribuídas a este entregador (apenas pendente / em_rota / em_andamento
    por padrão; passe ?status=concluida para ver as concluídas).
    """
    from app.api.endpoints.rotas_entrega import ensure_rotas_entrega_schema

    ensure_rotas_entrega_schema(db)

    query = db.query(RotaEntrega).options(
        joinedload(RotaEntrega.entregador),
        joinedload(RotaEntrega.paradas)
        .joinedload(RotaEntregaParada.venda)
        .joinedload(Venda.cliente),
    ).filter(
        RotaEntrega.tenant_id == str(cliente.tenant_id),
        RotaEntrega.entregador_id == cliente.id,
    )

    if filtro_status:
        query = query.filter(RotaEntrega.status == filtro_status)
    else:
        query = query.filter(RotaEntrega.status.in_(["pendente", "em_rota", "em_andamento"]))

    rotas = query.order_by(RotaEntrega.created_at.asc()).all()

    for rota in rotas:
        if rota.paradas:
            rota.paradas = sorted(rota.paradas, key=lambda p: p.ordem)
            for parada in rota.paradas:
                if parada.venda and parada.venda.cliente:
                    parada.cliente_nome = parada.venda.cliente.nome
                    parada.cliente_telefone = parada.venda.cliente.telefone
                    parada.cliente_celular = parada.venda.cliente.celular

    return rotas
