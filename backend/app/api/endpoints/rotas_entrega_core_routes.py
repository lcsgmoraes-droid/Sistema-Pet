import secrets
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import case, exists, func, or_, select, text
from sqlalchemy.orm import Query as SqlAlchemyQuery
from sqlalchemy.orm import Session, joinedload

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
    paradas = sorted(rota.paradas or [], key=lambda p: p.ordem)
    rota.paradas = paradas
    rota.total_entregas = len(paradas) if paradas else (1 if rota.venda_id else 0)
    rota.entregas_concluidas = sum(
        1 for parada in paradas if parada.status == "entregue"
    )
    if not paradas:
        rota.entregas_concluidas = (
            rota.total_entregas if rota.status == "concluida" else 0
        )
        vendas_legadas = []
        if rota.venda_id:
            venda = (
                db.query(Venda)
                .options(joinedload(Venda.cliente), joinedload(Venda.pagamentos))
                .filter(Venda.id == rota.venda_id, Venda.tenant_id == tenant_id)
                .first()
            )
            if venda:
                vendas_legadas.append(venda)
        _hidratar_resumo_financeiro_rota(rota, vendas_legadas)
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

    vendas_por_id = {}
    for parada in paradas:
        dist_row = dist_por_parada.get(parada.id)
        if dist_row:
            parada.distancia_trecho_real_km = dist_row[1]
            parada.distancia_acumulada_real_km = dist_row[2]
        if parada.venda and parada.venda.cliente:
            parada.cliente_nome = parada.venda.cliente.nome
            parada.cliente_telefone = parada.venda.cliente.telefone
            parada.cliente_celular = parada.venda.cliente.celular
        if parada.venda:
            venda = parada.venda
            vendas_por_id[venda.id] = venda
            pagamentos = list(venda.pagamentos or [])
            valor_pago = sum(
                (Decimal(str(pagamento.valor or 0)) for pagamento in pagamentos),
                Decimal("0"),
            )
            total_venda = Decimal(str(venda.total or 0))
            parada.numero_venda = venda.numero_venda
            parada.valor_venda = total_venda
            parada.taxa_entrega = Decimal(str(venda.taxa_entrega or 0))
            parada.data_venda = venda.data_venda
            parada.forma_pagamento = (
                pagamentos[0].forma_pagamento if pagamentos else None
            )
            parada.valor_pago = valor_pago
            parada.status_pagamento = (
                "pago"
                if valor_pago >= total_venda
                else "parcial"
                if valor_pago > 0
                else "pendente"
            )
            parada.observacoes_entrega = venda.observacoes_entrega
            parada.canal_venda = venda.canal

    _hidratar_resumo_financeiro_rota(rota, list(vendas_por_id.values()))


def _hidratar_resumo_financeiro_rota(rota: RotaEntrega, vendas: list[Venda]) -> None:
    valor_total = sum(
        (Decimal(str(venda.total or 0)) for venda in vendas), Decimal("0")
    )
    taxa_total_vendas = sum(
        (Decimal(str(venda.taxa_entrega or 0)) for venda in vendas), Decimal("0")
    )
    taxa_total = (
        Decimal(str(rota.taxa_entrega_cliente))
        if rota.taxa_entrega_cliente is not None
        else taxa_total_vendas
    )

    custo_total = Decimal(str(rota.custo_real or 0))
    custo_moto = Decimal(str(rota.custo_moto or 0))
    quantidade = int(getattr(rota, "total_entregas", 0) or 0)

    rota.valor_total_vendas = valor_total
    rota.taxa_total_entregas = taxa_total
    rota.custo_entregador = max(custo_total - custo_moto, Decimal("0"))
    rota.custo_por_entrega = (
        (custo_total / Decimal(quantidade)).quantize(Decimal("0.01"))
        if quantidade > 0
        else Decimal("0")
    )
    rota.duracao_minutos = None
    if rota.data_inicio and rota.data_conclusao:
        segundos = max((rota.data_conclusao - rota.data_inicio).total_seconds(), 0)
        rota.duracao_minutos = round(segundos / 60)


def aplicar_filtros_ordenacao_rotas(
    query: SqlAlchemyQuery,
    *,
    tenant_id,
    data_inicio: Optional[date] = None,
    data_fim: Optional[date] = None,
    busca: Optional[str] = None,
    ordenar_por: str = "data",
    direcao: str = "asc",
) -> SqlAlchemyQuery:
    data_referencia = func.coalesce(RotaEntrega.data_conclusao, RotaEntrega.created_at)
    if data_inicio:
        query = query.filter(data_referencia >= datetime.combine(data_inicio, time.min))
    if data_fim:
        limite_fim = datetime.combine(data_fim + timedelta(days=1), time.min)
        query = query.filter(data_referencia < limite_fim)

    termo = (busca or "").strip()
    if termo:
        padrao = f"%{termo}%"
        query = query.filter(
            or_(
                RotaEntrega.numero.ilike(padrao),
                RotaEntrega.endereco_destino.ilike(padrao),
                RotaEntrega.entregador.has(Cliente.nome.ilike(padrao)),
                RotaEntrega.paradas.any(
                    or_(
                        RotaEntregaParada.endereco.ilike(padrao),
                        RotaEntregaParada.venda.has(Venda.numero_venda.ilike(padrao)),
                        RotaEntregaParada.venda.has(
                            Venda.cliente.has(Cliente.nome.ilike(padrao))
                        ),
                    )
                ),
                exists().where(
                    Venda.id == RotaEntrega.venda_id,
                    Venda.tenant_id == tenant_id,
                    or_(
                        Venda.numero_venda.ilike(padrao),
                        Venda.endereco_entrega.ilike(padrao),
                        Venda.cliente.has(Cliente.nome.ilike(padrao)),
                    ),
                ),
            )
        )

    quantidade_paradas = (
        select(func.count(RotaEntregaParada.id))
        .where(
            RotaEntregaParada.rota_id == RotaEntrega.id,
            RotaEntregaParada.tenant_id == tenant_id,
        )
        .correlate(RotaEntrega)
        .scalar_subquery()
    )
    quantidade_entregas = case(
        (quantidade_paradas > 0, quantidade_paradas),
        (RotaEntrega.venda_id.isnot(None), 1),
        else_=0,
    )
    entregador_nome = (
        select(Cliente.nome)
        .where(
            Cliente.id == RotaEntrega.entregador_id,
            Cliente.tenant_id == tenant_id,
        )
        .correlate(RotaEntrega)
        .scalar_subquery()
    )
    ordenacoes = {
        "data": data_referencia,
        "data_conclusao": data_referencia,
        "numero": RotaEntrega.numero,
        "entregador": entregador_nome,
        "entregas": quantidade_entregas,
        "custo": func.coalesce(RotaEntrega.custo_real, 0),
        "distancia": func.coalesce(
            RotaEntrega.distancia_real, RotaEntrega.distancia_prevista, 0
        ),
    }
    expressao = ordenacoes.get(ordenar_por, data_referencia)
    ordem = expressao.desc() if direcao.lower() == "desc" else expressao.asc()
    return query.order_by(ordem, RotaEntrega.id.desc())


@router.get("/", response_model=List[RotaEntregaResponse])
def listar_rotas(
    status: Optional[str] = Query(None, description="Filtrar por status"),
    data_inicio: Optional[date] = Query(None, description="Data inicial"),
    data_fim: Optional[date] = Query(None, description="Data final"),
    entregador_id: Optional[int] = Query(None, description="Filtrar por entregador"),
    busca: Optional[str] = Query(None, description="Rota, venda, cliente ou endereco"),
    ordenar_por: str = Query("data", description="Campo de ordenacao"),
    direcao: str = Query("asc", pattern="^(asc|desc)$"),
    limite: int = Query(200, ge=1, le=500),
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    Lista rotas de entrega do tenant.

    OTIMIZAÇÃO: Não otimiza automaticamente para economizar chamadas à API.
    Use POST /rotas-entrega/otimizar para otimizar manualmente.
    """
    user, tenant_id = user_and_tenant
    ensure_rotas_entrega_schema(db)

    query = (
        db.query(RotaEntrega)
        .options(
            joinedload(RotaEntrega.entregador),
            joinedload(RotaEntrega.paradas)
            .joinedload(RotaEntregaParada.venda)
            .joinedload(Venda.cliente),
            joinedload(RotaEntrega.paradas)
            .joinedload(RotaEntregaParada.venda)
            .selectinload(Venda.pagamentos),
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

    if entregador_id:
        query = query.filter(RotaEntrega.entregador_id == entregador_id)

    query = aplicar_filtros_ordenacao_rotas(
        query,
        tenant_id=tenant_id,
        data_inicio=data_inicio,
        data_fim=data_fim,
        busca=busca,
        ordenar_por=ordenar_por,
        direcao=direcao,
    )
    rotas = query.limit(limite).all()

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

    CRITÉRIO: tem_entrega = true E status_entrega = 'pendente', 'pronto' ou NULL
    Exclui vendas que já estão em rota, entregues ou canceladas.

    Retorna em ordem:
    1. Vendas com ordem_entrega_otimizada (já otimizadas)
    2. Vendas novas sem ordem (cronológico)

    Economiza chamadas à API: só otimiza quando usuário clicar no botão.
    """
    user, tenant_id = user_and_tenant

    # Buscar vendas com entrega pendente
    # CRITÉRIO: tem_entrega = true E status_entrega = 'pendente', 'pronto' ou NULL
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

    rota = (
        db.query(RotaEntrega)
        .options(
            joinedload(RotaEntrega.entregador),
            joinedload(RotaEntrega.paradas)
            .joinedload(RotaEntregaParada.venda)
            .joinedload(Venda.cliente),
            joinedload(RotaEntrega.paradas)
            .joinedload(RotaEntregaParada.venda)
            .selectinload(Venda.pagamentos),
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
