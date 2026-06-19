"""Rotas de timeline de clientes e fornecedores."""

from datetime import datetime as dt, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user_and_tenant
from app.db import get_session
from app.models import Cliente, Pet

router = APIRouter()


def _validar_tenant_e_obter_usuario(user_and_tenant):
    current_user, tenant_id = user_and_tenant
    return current_user, tenant_id


class TimelineEvento(BaseModel):
    """Evento da timeline do cliente."""

    tipo_evento: str
    evento_id: int
    cliente_id: int
    pet_id: Optional[int] = None
    data_evento: dt
    titulo: str
    descricao: str
    status: str
    cor_badge: str

    class Config:
        from_attributes = True


@router.get("/{cliente_id}/timeline", response_model=List[TimelineEvento])
def obter_timeline_cliente(
    cliente_id: int,
    tipo_evento: Optional[str] = Query(None, description="Filtrar por tipo de evento"),
    pet_id: Optional[int] = Query(
        None, description="Filtrar eventos de um pet específico"
    ),
    limit: int = Query(20, ge=1, le=100, description="Limite de eventos"),
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    Retorna a timeline consolidada do cliente com eventos de:
    - Vendas
    - Contas a receber
    - Pets (cadastro e atualizacoes)

    Ordenacao: mais recente para mais antigo
    """
    _, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)

    cliente = (
        db.query(Cliente)
        .filter(Cliente.id == cliente_id, Cliente.tenant_id == tenant_id)
        .first()
    )

    if not cliente:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Cliente não encontrado"
        )

    return _obter_timeline(
        db, "cliente_timeline", cliente_id, tipo_evento, pet_id, limit
    )


def _obter_timeline(
    db: Session,
    view_name: str,
    entity_id: int,
    tipo_evento: Optional[str],
    pet_id: Optional[int],
    limit: int,
):
    """Busca timeline de qualquer entidade consultando as tabelas diretamente."""
    from app.financeiro_models import ContaReceber
    from app.vendas_models import Venda

    is_cliente = "cliente" in view_name
    eventos: list[TimelineEvento] = []

    if is_cliente and (not tipo_evento or tipo_evento == "venda"):
        vendas_q = (
            db.query(Venda)
            .filter(Venda.cliente_id == entity_id)
            .order_by(Venda.data_venda.desc())
            .limit(limit)
            .all()
        )
        for v in vendas_q:
            cor = {"finalizada": "green", "pendente": "yellow", "cancelada": "red"}.get(
                v.status or "", "gray"
            )
            eventos.append(
                TimelineEvento(
                    tipo_evento="venda",
                    evento_id=v.id,
                    cliente_id=entity_id,
                    pet_id=None,
                    data_evento=v.data_venda or v.created_at,
                    titulo=f"Venda #{v.numero_venda or v.id}",
                    descricao=f"R$ {float(v.total or 0):.2f} - {v.status or ''}",
                    status=v.status or "",
                    cor_badge=cor,
                )
            )

    if is_cliente and (not tipo_evento or tipo_evento == "conta_receber"):
        contas_q = (
            db.query(ContaReceber)
            .filter(ContaReceber.cliente_id == entity_id)
            .order_by(ContaReceber.data_vencimento.desc())
            .limit(limit)
            .all()
        )
        for cr in contas_q:
            cor = {
                "recebido": "green",
                "pendente": "yellow",
                "vencido": "red",
                "cancelado": "gray",
            }.get(cr.status or "", "blue")
            eventos.append(
                TimelineEvento(
                    tipo_evento="conta_receber",
                    evento_id=cr.id,
                    cliente_id=entity_id,
                    pet_id=None,
                    data_evento=cr.data_vencimento or cr.data_emissao or cr.created_at,
                    titulo="Conta a Receber",
                    descricao=f"R$ {float(cr.valor_original or 0):.2f} - {cr.descricao or ''}",
                    status=cr.status or "",
                    cor_badge=cor,
                )
            )

    if is_cliente and (
        not tipo_evento or tipo_evento in ("pet_cadastro", "pet_atualizacao")
    ):
        filtro_pet = [Pet.cliente_id == entity_id]
        if pet_id:
            filtro_pet.append(Pet.id == pet_id)
        pets_q = db.query(Pet).filter(*filtro_pet).all()
        for p in pets_q:
            cor = "blue" if p.ativo else "gray"
            st = "ativo" if p.ativo else "inativo"
            if not tipo_evento or tipo_evento == "pet_cadastro":
                eventos.append(
                    TimelineEvento(
                        tipo_evento="pet_cadastro",
                        evento_id=p.id,
                        cliente_id=entity_id,
                        pet_id=p.id,
                        data_evento=p.created_at,
                        titulo=f"🐾 Pet cadastrado: {p.nome}",
                        descricao=f"{p.especie or ''}{(' - ' + p.raca) if p.raca else ''}",
                        status=st,
                        cor_badge=cor,
                    )
                )
            atualizado_em = p.updated_at.replace(tzinfo=None) if p.updated_at else None
            criado_em = p.created_at.replace(tzinfo=None) if p.created_at else None
            if (
                (not tipo_evento or tipo_evento == "pet_atualizacao")
                and p.updated_at
                and atualizado_em != criado_em
            ):
                eventos.append(
                    TimelineEvento(
                        tipo_evento="pet_atualizacao",
                        evento_id=p.id,
                        cliente_id=entity_id,
                        pet_id=p.id,
                        data_evento=p.updated_at,
                        titulo=f"✏️ Pet atualizado: {p.nome}",
                        descricao="Informações atualizadas",
                        status=st,
                        cor_badge="purple",
                    )
                )

    eventos.sort(key=lambda e: _to_aware(e.data_evento), reverse=True)
    return eventos[:limit]


def _to_aware(data_evento):
    if data_evento is None:
        return dt.min.replace(tzinfo=timezone.utc)
    if data_evento.tzinfo is None:
        return data_evento.replace(tzinfo=timezone.utc)
    return data_evento


@router.get("/fornecedor/{fornecedor_id}/timeline", response_model=List[TimelineEvento])
def obter_timeline_fornecedor(
    fornecedor_id: int,
    tipo_evento: Optional[str] = Query(None, description="Filtrar por tipo de evento"),
    limit: int = Query(20, ge=1, le=100, description="Limite de eventos"),
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    Retorna a timeline consolidada do fornecedor com eventos de:
    - Pedidos de compra
    - Contas a pagar
    - Recebimentos de mercadorias

    Ordenacao: mais recente para mais antigo
    """
    _, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)

    fornecedor = (
        db.query(Cliente)
        .filter(
            Cliente.id == fornecedor_id,
            Cliente.tenant_id == tenant_id,
            Cliente.tipo_cadastro == "fornecedor",
        )
        .first()
    )

    if not fornecedor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Fornecedor não encontrado"
        )

    return _obter_timeline(
        db, "fornecedor_timeline", fornecedor_id, tipo_evento, None, limit
    )
