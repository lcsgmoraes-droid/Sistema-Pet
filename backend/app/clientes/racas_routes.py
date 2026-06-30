"""Rotas de racas usadas pelo modulo de clientes e pets."""

from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user_and_tenant
from app.db import get_session
from app.models import Raca

router = APIRouter()


@router.get("/racas-teste")
def list_racas_teste(especie: str = ""):
    """Teste simples sem dependencias."""
    return [
        {"id": 1, "nome": "Labrador", "especie": "Cão"},
        {"id": 2, "nome": "Siamês", "especie": "Gato"},
    ]


@router.get("/racas")
def list_racas(
    especie: Optional[str] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Listar racas cadastradas, com filtro por especie."""
    _current_user, _tenant_id = user_and_tenant
    query = db.query(Raca).filter(Raca.ativo)

    if especie:
        query = query.filter(Raca.especie == especie)

    if search:
        query = query.filter(Raca.nome.ilike(f"%{search}%"))

    racas = query.order_by(Raca.nome).all()
    return [{"id": r.id, "nome": r.nome, "especie": r.especie} for r in racas]
