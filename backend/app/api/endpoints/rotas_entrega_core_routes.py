import secrets
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.endpoints.rotas_entrega_auth import (
    DeliveryActor,
    _activate_delivery_actor_tenant,
    _rota_filters_for_actor,
    get_delivery_actor_and_tenant,
)
from app.api.endpoints.rotas_entrega_schema import ensure_rotas_entrega_schema
from app.api.endpoints.rotas_entrega_tracking import montar_rastreio_publico
from app.auth.dependencies import get_current_user_and_tenant
from app.db import get_session
from app.models import Cliente
from app.rotas_entrega_models import RotaEntrega, RotaEntregaParada
from app.schemas.rota_entrega import RotaEntregaResponse, RotaEntregaUpdate
from app.vendas_models import Venda

router = APIRouter()


def _hidratar_localizacao_rota(db: Session, rota: RotaEntrega, tenant_id: int) -> bool:
    loc = db.execute(
        text(
            """
            SELECT lat_atual, lon_atual, localizacao_atualizada_em, token_rastreio
                 , distancia_total_km_real, distancia_retorno_km_real
            FROM rotas_entrega
            WHERE id = :rid AND tenant_id = :tenant
            """
        ),
        {"rid": rota.id, "tenant": tenant_id},
    ).fetchone()
    if not loc:
        return False

    rota.lat_atual = loc[0]
    rota.lon_atual = loc[1]
    rota.localizacao_atualizada_em = loc[2]
    token_rastreio = loc[3]
    rota.distancia_total_km_real = loc[4]
    rota.distancia_retorno_km_real = loc[5]
    if loc[4] is not None:
        total_real = float(loc[4])
        retorno_real = float(loc[5] or 0)
        rota.distancia_ate_ultima_entrega_km_real = max(total_real - retorno_real, 0)
    if not token_rastreio:
        token_rastreio = secrets.token_urlsafe(32)
        db.execute(
            text(
                """
                UPDATE rotas_entrega
                SET token_rastreio = :token
                WHERE id = :rid AND tenant_id = :tenant
                """
            ),
            {"token": token_rastreio, "rid": rota.id, "tenant": tenant_id},
        )
        rota.token_rastreio = token_rastreio
        return True

    rota.token_rastreio = token_rastreio
    return False


def _hidratar_paradas_rota(db: Session, rota: RotaEntrega, tenant_id: int) -> None:
    if not rota.paradas:
        return

    dist_rows = db.execute(
        text(
            """
            SELECT id, distancia_trecho_real_km, distancia_acumulada_real_km
            FROM rotas_entrega_paradas
            WHERE rota_id = :rid AND tenant_id = :tenant
            """
        ),
        {"rid": rota.id, "tenant": tenant_id},
    ).fetchall()
    dist_por_parada = {row[0]: row for row in dist_rows}

    rota.paradas = sorted(rota.paradas, key=lambda p: p.ordem)
    for parada in rota.paradas:
        dist_row = dist_por_parada.get(parada.id)
        if dist_row:
            parada.distancia_trecho_real_km = dist_row[1]
            parada.distancia_acumulada_real_km = dist_row[2]
        if parada.venda and parada.venda.cliente:
            parada.cliente_nome = parada.venda.cliente.nome
            parada.cliente_telefone = parada.venda.cliente.telefone
            parada.cliente_celular = parada.venda.cliente.celular


@router.get("/", response_model=List[RotaEntregaResponse])
def listar_rotas(
    status: Optional[str] = Query(None, description="Filtrar por status"),
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    Lista rotas de entrega do tenant.

    OTIMIZAÇÃO: Não otimiza automaticamente para economizar chamadas à API.
    Use POST /rotas-entrega/otimizar para otimizar manualmente.
    """
    from sqlalchemy.orm import joinedload
    from app.vendas_models import Venda

    user, tenant_id = user_and_tenant
    ensure_rotas_entrega_schema(db)

    query = (
        db.query(RotaEntrega)
        .options(
            joinedload(RotaEntrega.entregador),
            joinedload(RotaEntrega.paradas)
            .joinedload(RotaEntregaParada.venda)
            .joinedload(Venda.cliente),
        )
        .filter(RotaEntrega.tenant_id == tenant_id)
    )

    if status:
        query = query.filter(RotaEntrega.status == status)
    else:
        # Se não especificou status, mostra apenas rotas ativas (exclui concluídas)
        query = query.filter(
            RotaEntrega.status.in_(["pendente", "em_rota", "em_andamento"])
        )

    # Ordenar: rotas com paradas otimizadas primeiro, depois por data
    rotas = query.order_by(RotaEntrega.created_at.asc()).all()

    # Se a rota tem paradas, ordenar internamente pelas paradas.ordem
    # E incluir dados do cliente para exibição
    for rota in rotas:
        # Carregar localização atual sem depender de mapeamento ORM de colunas legadas.
        _hidratar_localizacao_rota(db, rota, tenant_id)

        _hidratar_paradas_rota(db, rota, tenant_id)

    db.commit()
    return rotas


@router.get("/vendas-pendentes/listar")
def listar_vendas_pendentes_entrega(
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    Lista vendas com entrega pendente (sem rota criada ainda).

    CRITÉRIO: tem_entrega = true E status_entrega = 'pendente' ou NULL
    Exclui vendas que já estão em rota, entregues ou canceladas.

    Retorna em ordem:
    1. Vendas com ordem_entrega_otimizada (já otimizadas)
    2. Vendas novas sem ordem (cronológico)

    Economiza chamadas à API: só otimiza quando usuário clicar no botão.
    """
    user, tenant_id = user_and_tenant

    # Buscar vendas com entrega pendente
    # CRITÉRIO: tem_entrega = true E status_entrega = 'pendente' ou NULL
    # Exclui: 'em_rota', 'entregue', 'cancelada'
    vendas = (
        db.query(Venda)
        .filter(
            Venda.tenant_id == tenant_id,
            Venda.tem_entrega.is_(True),
            # Aceita vendas fora de rota, inclusive pedido online ja separado.
            Venda.status_entrega.in_(["pendente", "pronto"])
            | Venda.status_entrega.is_(None),
        )
        .order_by(
            # Primeiro: vendas com ordem otimizada
            Venda.ordem_entrega_otimizada.asc().nullslast(),
            # Depois: vendas novas por data
            Venda.created_at.asc(),
        )
        .all()
    )

    return [
        {
            "id": v.id,
            "numero_venda": v.numero_venda,
            "cliente_id": v.cliente_id,
            "cliente_nome": v.cliente.nome if v.cliente else "Cliente não cadastrado",
            "endereco_entrega": v.endereco_entrega,
            "taxa_entrega": float(v.taxa_entrega) if v.taxa_entrega else 0,
            "distancia_km": float(v.distancia_km) if v.distancia_km else None,
            "ordem_otimizada": v.ordem_entrega_otimizada,
            "data_venda": v.data_venda.isoformat() if v.data_venda else None,
            "total": float(v.total) if v.total else 0,
            "entregador_id": v.entregador_id,
            "entregador_nome": v.entregador.nome if v.entregador else None,
        }
        for v in vendas
    ]


@router.get("/{rota_id}", response_model=RotaEntregaResponse)
def obter_rota(
    rota_id: str,
    db: Session = Depends(get_session),
    actor: DeliveryActor = Depends(get_delivery_actor_and_tenant),
):
    """
    Obtém detalhes de uma rota específica.
    """
    tenant_id = _activate_delivery_actor_tenant(actor)
    ensure_rotas_entrega_schema(db)

    from sqlalchemy.orm import joinedload

    rota = (
        db.query(RotaEntrega)
        .options(
            joinedload(RotaEntrega.entregador),
            joinedload(RotaEntrega.paradas)
            .joinedload(RotaEntregaParada.venda)
            .joinedload(Venda.cliente),
        )
        .filter(*_rota_filters_for_actor(actor, rota_id))
        .first()
    )

    if not rota:
        raise HTTPException(status_code=404, detail="Rota não encontrada")

    if _hidratar_localizacao_rota(db, rota, tenant_id):
        db.commit()
    _hidratar_paradas_rota(db, rota, tenant_id)

    return rota


@router.put("/{rota_id}", response_model=RotaEntregaResponse)
def atualizar_rota(
    rota_id: int,
    payload: RotaEntregaUpdate,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    Atualiza dados de uma rota (status, observações, etc).
    """
    user, tenant_id = user_and_tenant
    ensure_rotas_entrega_schema(db)

    rota = (
        db.query(RotaEntrega)
        .filter(RotaEntrega.id == rota_id, RotaEntrega.tenant_id == tenant_id)
        .first()
    )

    if not rota:
        raise HTTPException(status_code=404, detail="Rota não encontrada")

    if rota.status == "concluida":
        raise HTTPException(
            status_code=400, detail="Rota concluída não pode ser alterada"
        )

    # Atualizar campos fornecidos
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(rota, field, value)

    db.commit()
    db.refresh(rota)

    rota.entregador = db.query(Cliente).filter(Cliente.id == rota.entregador_id).first()

    return rota


@router.get("/rastreio/{token}")
def rastreio_publico(
    token: str,
    db: Session = Depends(get_session),
):
    """
    Endpoint público para rastreamento de rota por token.
    Retorna última posição GPS e status das paradas (sem dados sensíveis).
    """
    ensure_rotas_entrega_schema(db)
    return montar_rastreio_publico(db, token)
