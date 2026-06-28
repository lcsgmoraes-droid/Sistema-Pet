"""Pets acessiveis pela agenda veterinaria."""

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from ..auth.dependencies import get_current_user_and_tenant
from ..db import get_session
from ..models import Cliente, Pet
from ..veterinario_core import _all_accessible_tenant_ids, _get_tenant

router = APIRouter()


@router.get("/pets")
def listar_pets_vet(
    busca: Optional[str] = Query(None),
    cliente_id: Optional[int] = Query(None),
    limit: int = Query(500, ge=1, le=1000),
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    """
    Lista os pets acessíveis ao veterinário:
    - pets do próprio tenant (se tiver cadastros próprios)
    - pets de todas as empresas parceiras ativas vinculadas
    """
    user, tenant_id = _get_tenant(current)
    tenant_ids = _all_accessible_tenant_ids(db, tenant_id)

    q = (
        db.query(Pet)
        .join(Cliente)
        .options(joinedload(Pet.cliente))
        .filter(Cliente.tenant_id.in_(tenant_ids), Pet.ativo.is_(True))
    )

    if cliente_id:
        q = q.filter(Pet.cliente_id == cliente_id)

    if busca:
        busca_term = f"%{busca}%"
        q = q.filter(
            or_(
                Pet.nome.ilike(busca_term),
                Pet.raca.ilike(busca_term),
                Cliente.nome.ilike(busca_term),
            )
        )

    pets = q.order_by(Pet.nome).limit(limit).all()

    return [
        {
            "id": p.id,
            "codigo": p.codigo,
            "cliente_id": p.cliente_id,
            "nome": p.nome,
            "especie": p.especie,
            "raca": p.raca,
            "sexo": p.sexo,
            "castrado": p.castrado,
            "data_nascimento": p.data_nascimento,
            "peso": p.peso,
            "porte": p.porte,
            "microchip": p.microchip,
            "alergias": p.alergias,
            "doencas_cronicas": p.doencas_cronicas,
            "medicamentos_continuos": p.medicamentos_continuos,
            "historico_clinico": p.historico_clinico,
            "observacoes": p.observacoes,
            "foto_url": p.foto_url,
            "ativo": p.ativo,
            "tenant_id": str(p.tenant_id),
            "cliente_nome": p.cliente.nome if p.cliente else None,
            "cliente_telefone": p.cliente.telefone if p.cliente else None,
            "cliente_celular": p.cliente.celular if p.cliente else None,
        }
        for p in pets
    ]
