"""Rotas da API para o perfil de entregador no app mobile."""
from datetime import datetime
from decimal import Decimal
from types import SimpleNamespace
from typing import List, Optional
from uuid import UUID
import secrets

from fastapi import APIRouter, BackgroundTasks, Body, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from app.db import get_session
from app.models import Cliente, ConfiguracaoEntrega, User
from app.rotas_entrega_models import RotaEntrega, RotaEntregaParada
from app.routes.ecommerce_auth import _activate_user_tenant_context, _get_current_ecommerce_user
from app.schemas.rota_entrega import RotaEntregaResponse, RotaEntregaUpdate
from app.services.google_maps_service import calcular_rota_otimizada
from app.tenancy.context import set_current_tenant
from app.vendas_models import Venda, VendaItem

router = APIRouter(prefix="/ecommerce/entregador", tags=["ecommerce-entregador"])


class OtimizarSelecionadasPayload(BaseModel):
    venda_ids: List[int]


class CriarRotaPayload(BaseModel):
    venda_ids: List[int]
    retorna_origem: bool = True


class ReordenarParadasPayload(BaseModel):
    parada_ids: List[int]


class NaoEntreguePayload(BaseModel):
    motivo: Optional[str] = None


class RegistrarRecebimentoPayload(BaseModel):
    forma_pagamento: str
    numero_parcelas: int = 1


def rota_entregador_permite_reordenar(status_rota: Optional[str]) -> bool:
    return (status_rota or "").strip().lower() not in {"concluida", "cancelada"}


def _get_entregador_cliente(
    current_user: User = Depends(_get_current_ecommerce_user),
    db: Session = Depends(get_session),
) -> Cliente:
    tenant_id = _activate_user_tenant_context(current_user)
    cliente = (
        db.query(Cliente)
        .filter(Cliente.tenant_id == tenant_id, Cliente.user_id == current_user.id)
        .first()
    )
    if not cliente or not cliente.is_entregador:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso restrito a entregadores",
        )
    return cliente


def _activate_cliente_tenant_context(cliente: Cliente) -> str:
    tenant_id = UUID(str(cliente.tenant_id))
    set_current_tenant(tenant_id)
    return str(tenant_id)


def _delivery_actor(cliente: Cliente, tenant_id: str):
    from app.api.endpoints import rotas_entrega as rotas_admin

    return rotas_admin.DeliveryActor(
        user=SimpleNamespace(id=cliente.user_id),
        tenant_id=UUID(str(tenant_id)),
        entregador=cliente,
    )


def _is_int_like(value: object) -> bool:
    return str(value).strip().isdigit()


def _get_rota_do_entregador_or_404(
    db: Session,
    *,
    rota_id,
    tenant_id: str,
    cliente: Cliente,
) -> RotaEntrega:
    rota_ref = str(rota_id).strip()
    rota_filter = (
        RotaEntrega.id == int(rota_ref)
        if _is_int_like(rota_ref)
        else RotaEntrega.numero == rota_ref
    )
    rota = (
        db.query(RotaEntrega)
        .filter(
            rota_filter,
            RotaEntrega.tenant_id == tenant_id,
            RotaEntrega.entregador_id == cliente.id,
        )
        .first()
    )
    if not rota:
        raise HTTPException(status_code=404, detail="Rota nao encontrada")
    return rota


def _get_parada_do_entregador_or_404(
    db: Session,
    *,
    rota_id,
    parada_id: int,
    tenant_id: str,
    cliente: Cliente,
) -> RotaEntregaParada:
    rota = _get_rota_do_entregador_or_404(
        db,
        rota_id=rota_id,
        tenant_id=tenant_id,
        cliente=cliente,
    )
    parada = (
        db.query(RotaEntregaParada)
        .filter(
            RotaEntregaParada.id == parada_id,
            RotaEntregaParada.rota_id == rota.id,
            RotaEntregaParada.tenant_id == tenant_id,
        )
        .first()
    )
    if not parada:
        raise HTTPException(status_code=404, detail="Parada nao encontrada")
    return parada


def _montar_endereco_origem(config: Optional[ConfiguracaoEntrega]) -> Optional[str]:
    if not config:
        return None
    partes = [
        config.logradouro,
        config.numero,
        config.bairro,
        config.cidade,
        config.estado,
        config.cep,
    ]
    endereco = ", ".join([p for p in partes if p])
    return endereco.strip() or None


@router.get("/minhas-rotas", response_model=List[RotaEntregaResponse])
def minhas_rotas(
    filtro_status: Optional[str] = Query(None, alias="status"),
    cliente: Cliente = Depends(_get_entregador_cliente),
    db: Session = Depends(get_session),
):
    from app.api.endpoints.rotas_entrega import ensure_rotas_entrega_schema

    tenant_id = _activate_cliente_tenant_context(cliente)
    ensure_rotas_entrega_schema(db)

    query = db.query(RotaEntrega).options(
        joinedload(RotaEntrega.entregador),
        joinedload(RotaEntrega.paradas)
        .joinedload(RotaEntregaParada.venda)
        .joinedload(Venda.cliente),
    ).filter(
        RotaEntrega.tenant_id == tenant_id,
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


@router.get("/entregas-abertas")
def listar_entregas_abertas(
    cliente: Cliente = Depends(_get_entregador_cliente),
    db: Session = Depends(get_session),
):
    tenant_id = _activate_cliente_tenant_context(cliente)
    vendas = (
        db.query(Venda)
        .options(joinedload(Venda.cliente))
        .filter(
            Venda.tenant_id == tenant_id,
            Venda.tem_entrega == True,
            or_(Venda.status_entrega == "pendente", Venda.status_entrega == None),
            Venda.endereco_entrega.isnot(None),
            or_(Venda.entregador_id == cliente.id, Venda.entregador_id == None),
        )
        .order_by(Venda.ordem_entrega_otimizada.asc().nullslast(), Venda.created_at.asc())
        .all()
    )

    return [
        {
            "id": v.id,
            "numero_venda": v.numero_venda,
            "cliente_nome": v.cliente.nome if v.cliente else "Cliente não cadastrado",
            "endereco_entrega": v.endereco_entrega,
            "ordem_otimizada": v.ordem_entrega_otimizada,
            "data_venda": v.data_venda.isoformat() if v.data_venda else None,
            "total": float(v.total or 0),
            "taxa_entrega": float(v.taxa_entrega or 0),
        }
        for v in vendas
    ]


@router.post("/entregas-abertas/otimizar-selecionadas")
def otimizar_entregas_selecionadas(
    payload: OtimizarSelecionadasPayload,
    cliente: Cliente = Depends(_get_entregador_cliente),
    db: Session = Depends(get_session),
):
    if not payload.venda_ids:
        raise HTTPException(status_code=400, detail="Selecione ao menos uma entrega")

    tenant_id = _activate_cliente_tenant_context(cliente)
    config = db.query(ConfiguracaoEntrega).filter(
        ConfiguracaoEntrega.tenant_id == tenant_id
    ).first()
    origem = _montar_endereco_origem(config)
    if not origem:
        raise HTTPException(
            status_code=400,
            detail="Configure o endereço da loja em Configurações > Entregas",
        )

    vendas = (
        db.query(Venda)
        .filter(
            Venda.tenant_id == tenant_id,
            Venda.id.in_(payload.venda_ids),
            Venda.tem_entrega == True,
            or_(Venda.status_entrega == "pendente", Venda.status_entrega == None),
            Venda.endereco_entrega.isnot(None),
            or_(Venda.entregador_id == cliente.id, Venda.entregador_id == None),
        )
        .order_by(Venda.created_at.asc())
        .all()
    )

    if len(vendas) != len(payload.venda_ids):
        raise HTTPException(status_code=400, detail="Uma ou mais entregas não podem ser otimizadas")

    if len(vendas) == 1:
        vendas[0].ordem_entrega_otimizada = 1
        db.commit()
        return {"message": "Apenas 1 entrega selecionada", "total_otimizado": 1}

    destinos = [v.endereco_entrega for v in vendas]
    ordem_indices, _ = calcular_rota_otimizada(origem, destinos)

    for posicao, indice_original in enumerate(ordem_indices, start=1):
        vendas[indice_original].ordem_entrega_otimizada = posicao

    db.commit()
    return {
        "message": "Entregas selecionadas otimizadas com sucesso",
        "total_otimizado": len(ordem_indices),
    }


@router.post("/rotas", response_model=RotaEntregaResponse)
def criar_rota_por_entregador(
    payload: CriarRotaPayload,
    cliente: Cliente = Depends(_get_entregador_cliente),
    db: Session = Depends(get_session),
):
    from app.api.endpoints.rotas_entrega import ensure_rotas_entrega_schema

    tenant_id = _activate_cliente_tenant_context(cliente)
    tenant_uuid = UUID(str(tenant_id))
    ensure_rotas_entrega_schema(db)

    if not payload.venda_ids:
        raise HTTPException(status_code=400, detail="Selecione ao menos uma entrega")

    vendas = (
        db.query(Venda)
        .filter(
            Venda.tenant_id == tenant_id,
            Venda.id.in_(payload.venda_ids),
            Venda.tem_entrega == True,
            or_(Venda.status_entrega == "pendente", Venda.status_entrega == None),
            Venda.endereco_entrega.isnot(None),
            or_(Venda.entregador_id == cliente.id, Venda.entregador_id == None),
        )
        .order_by(Venda.ordem_entrega_otimizada.asc().nullslast(), Venda.created_at.asc())
        .all()
    )

    if len(vendas) != len(payload.venda_ids):
        raise HTTPException(status_code=400, detail="Uma ou mais entregas não podem entrar na rota")

    config = db.query(ConfiguracaoEntrega).filter(
        ConfiguracaoEntrega.tenant_id == tenant_id
    ).first()
    ponto_origem = _montar_endereco_origem(config)

    rota = RotaEntrega(
        tenant_id=tenant_uuid,
        entregador_id=cliente.id,
        moto_da_loja=not bool(cliente.moto_propria),
        status="pendente",
        created_by=cliente.user_id,
        ponto_inicial_rota=ponto_origem,
        ponto_final_rota=ponto_origem if payload.retorna_origem else None,
        retorna_origem=payload.retorna_origem,
    )
    # Campo numero em rotas_entrega é VARCHAR(20); manter identificador curto e único
    rota.numero = f"R{datetime.now().strftime('%y%m%d%H%M%S')}{secrets.token_hex(3).upper()}"
    rota.token_rastreio = secrets.token_urlsafe(32)

    db.add(rota)
    db.flush()

    for idx, venda in enumerate(vendas, start=1):
        parada = RotaEntregaParada(
            tenant_id=tenant_uuid,
            rota_id=rota.id,
            venda_id=venda.id,
            ordem=idx,
            endereco=venda.endereco_entrega,
            status="pendente",
        )
        db.add(parada)
        venda.entregador_id = cliente.id
        venda.status_entrega = "em_rota"

    taxa_total = sum(Decimal(v.taxa_entrega or 0) for v in vendas)
    rota.taxa_entrega_cliente = taxa_total if taxa_total > 0 else None

    db.commit()
    db.refresh(rota)

    if rota.paradas:
        rota.paradas = sorted(rota.paradas, key=lambda p: p.ordem)
        for parada in rota.paradas:
            if parada.venda and parada.venda.cliente:
                parada.cliente_nome = parada.venda.cliente.nome
                parada.cliente_telefone = parada.venda.cliente.telefone
                parada.cliente_celular = parada.venda.cliente.celular

    return rota


@router.get("/rotas/{rota_id}", response_model=RotaEntregaResponse)
def obter_rota_entregador(
    rota_id: str,
    cliente: Cliente = Depends(_get_entregador_cliente),
    db: Session = Depends(get_session),
):
    from app.api.endpoints import rotas_entrega as rotas_admin

    tenant_id = _activate_cliente_tenant_context(cliente)
    rota = _get_rota_do_entregador_or_404(
        db,
        rota_id=rota_id,
        tenant_id=tenant_id,
        cliente=cliente,
    )
    return rotas_admin.obter_rota(
        rota_id=rota.id,
        db=db,
        actor=_delivery_actor(cliente, tenant_id),
    )


@router.post("/rotas/{rota_id}/iniciar", response_model=RotaEntregaResponse)
def iniciar_rota_entregador(
    rota_id: str,
    km_inicial: Optional[float] = None,
    lat_inicio: Optional[float] = None,
    lon_inicio: Optional[float] = None,
    cliente: Cliente = Depends(_get_entregador_cliente),
    db: Session = Depends(get_session),
):
    from app.api.endpoints import rotas_entrega as rotas_admin

    tenant_id = _activate_cliente_tenant_context(cliente)
    rota = _get_rota_do_entregador_or_404(
        db,
        rota_id=rota_id,
        tenant_id=tenant_id,
        cliente=cliente,
    )
    return rotas_admin.iniciar_rota(
        rota_id=rota.id,
        km_inicial=km_inicial,
        lat_inicio=lat_inicio,
        lon_inicio=lon_inicio,
        db=db,
        actor=_delivery_actor(cliente, tenant_id),
    )


@router.post("/rotas/{rota_id}/atualizar-localizacao")
def atualizar_localizacao_rota_entregador(
    rota_id: str,
    lat: float,
    lon: float,
    cliente: Cliente = Depends(_get_entregador_cliente),
    db: Session = Depends(get_session),
):
    from app.api.endpoints import rotas_entrega as rotas_admin

    tenant_id = _activate_cliente_tenant_context(cliente)
    rota = _get_rota_do_entregador_or_404(
        db,
        rota_id=rota_id,
        tenant_id=tenant_id,
        cliente=cliente,
    )
    return rotas_admin.atualizar_localizacao_rota(
        rota_id=rota.id,
        lat=lat,
        lon=lon,
        db=db,
        actor=_delivery_actor(cliente, tenant_id),
    )


@router.post("/rotas/{rota_id}/paradas/{parada_id}/marcar-entregue")
def marcar_parada_entregue_entregador(
    rota_id: str,
    parada_id: int,
    background_tasks: BackgroundTasks,
    tentativa: bool = False,
    km_entrega: Optional[float] = None,
    lat_entrega: Optional[float] = None,
    lon_entrega: Optional[float] = None,
    cliente: Cliente = Depends(_get_entregador_cliente),
    db: Session = Depends(get_session),
):
    from app.api.endpoints import rotas_entrega as rotas_admin

    tenant_id = _activate_cliente_tenant_context(cliente)
    parada = _get_parada_do_entregador_or_404(
        db,
        rota_id=rota_id,
        parada_id=parada_id,
        tenant_id=tenant_id,
        cliente=cliente,
    )
    return rotas_admin.marcar_parada_entregue(
        rota_id=parada.rota_id,
        parada_id=parada_id,
        tentativa=tentativa,
        km_entrega=km_entrega,
        lat_entrega=lat_entrega,
        lon_entrega=lon_entrega,
        background_tasks=background_tasks,
        db=db,
        actor=_delivery_actor(cliente, tenant_id),
    )


@router.post("/rotas/{rota_id}/paradas/{parada_id}/registrar-recebimento")
def registrar_recebimento_entregador_mobile(
    rota_id: str,
    parada_id: int,
    payload: RegistrarRecebimentoPayload,
    cliente: Cliente = Depends(_get_entregador_cliente),
    db: Session = Depends(get_session),
):
    from app.api.endpoints import rotas_entrega as rotas_admin

    tenant_id = _activate_cliente_tenant_context(cliente)
    parada = _get_parada_do_entregador_or_404(
        db,
        rota_id=rota_id,
        parada_id=parada_id,
        tenant_id=tenant_id,
        cliente=cliente,
    )
    return rotas_admin.registrar_recebimento_entregador(
        rota_id=parada.rota_id,
        parada_id=parada_id,
        payload=payload,
        db=db,
        actor=_delivery_actor(cliente, tenant_id),
    )


@router.post("/rotas/{rota_id}/fechar", response_model=RotaEntregaResponse)
def fechar_rota_entregador(
    rota_id: str,
    payload: RotaEntregaUpdate,
    cliente: Cliente = Depends(_get_entregador_cliente),
    db: Session = Depends(get_session),
):
    from app.api.endpoints import rotas_entrega as rotas_admin

    tenant_id = _activate_cliente_tenant_context(cliente)
    rota = _get_rota_do_entregador_or_404(
        db,
        rota_id=rota_id,
        tenant_id=tenant_id,
        cliente=cliente,
    )
    return rotas_admin.fechar_rota(
        rota_id=rota.id,
        payload=payload,
        db=db,
        actor=_delivery_actor(cliente, tenant_id),
    )


@router.put("/rotas/{rota_id}/paradas/reordenar")
def reordenar_paradas_rota_entregador(
    rota_id: str,
    payload: ReordenarParadasPayload,
    cliente: Cliente = Depends(_get_entregador_cliente),
    db: Session = Depends(get_session),
):
    tenant_id = _activate_cliente_tenant_context(cliente)
    rota_ref = str(rota_id).strip()
    rota_filter = (
        RotaEntrega.id == int(rota_ref)
        if _is_int_like(rota_ref)
        else RotaEntrega.numero == rota_ref
    )
    rota = db.query(RotaEntrega).filter(
        rota_filter,
        RotaEntrega.tenant_id == tenant_id,
        RotaEntrega.entregador_id == cliente.id,
    ).first()
    if not rota:
        raise HTTPException(status_code=404, detail="Rota não encontrada")
    if not rota_entregador_permite_reordenar(rota.status):
        raise HTTPException(
            status_code=400,
            detail="Rota encerrada nao pode ser reordenada",
        )

    paradas = db.query(RotaEntregaParada).filter(
        RotaEntregaParada.rota_id == rota.id,
        RotaEntregaParada.tenant_id == tenant_id,
    ).all()
    paradas_por_id = {p.id: p for p in paradas}

    if set(payload.parada_ids) != set(paradas_por_id.keys()):
        raise HTTPException(status_code=400, detail="Lista de paradas inválida")

    for idx, parada_id in enumerate(payload.parada_ids, start=1):
        paradas_por_id[parada_id].ordem = idx

    db.commit()
    return {"message": "Ordem das paradas atualizada"}


@router.post("/rotas/{rota_id}/paradas/{parada_id}/nao-entregue")
def marcar_parada_nao_entregue_entregador(
    rota_id: str,
    parada_id: int,
    motivo: Optional[str] = Query(None),
    payload: Optional[NaoEntreguePayload] = Body(default=None),
    cliente: Cliente = Depends(_get_entregador_cliente),
    db: Session = Depends(get_session),
):
    from app.api.endpoints.rotas_entrega import ensure_rotas_entrega_schema

    tenant_id = _activate_cliente_tenant_context(cliente)
    ensure_rotas_entrega_schema(db)

    rota_ref = str(rota_id).strip()
    rota_filter = (
        RotaEntrega.id == int(rota_ref)
        if _is_int_like(rota_ref)
        else RotaEntrega.numero == rota_ref
    )
    rota = db.query(RotaEntrega).filter(
        rota_filter,
        RotaEntrega.tenant_id == tenant_id,
        RotaEntrega.entregador_id == cliente.id,
    ).first()
    if not rota:
        raise HTTPException(status_code=404, detail="Rota nao encontrada")
    if rota.status in ("concluida", "cancelada"):
        raise HTTPException(status_code=400, detail="Rota ja foi encerrada")

    parada = db.query(RotaEntregaParada).filter(
        RotaEntregaParada.id == parada_id,
        RotaEntregaParada.rota_id == rota.id,
        RotaEntregaParada.tenant_id == tenant_id,
    ).first()
    if not parada:
        raise HTTPException(status_code=404, detail="Parada nao encontrada")

    motivo_final = (motivo or (payload.motivo if payload else "") or "").strip()
    if motivo_final:
        obs_existente = parada.observacoes or ""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        parada.observacoes = f"{obs_existente}\n[{timestamp}] Nao entregue: {motivo_final}".strip()

    venda_id = parada.venda_id
    venda = db.query(Venda).filter(
        Venda.id == venda_id,
        Venda.tenant_id == tenant_id,
    ).first()
    if venda:
        venda.status_entrega = "pendente"

    db.delete(parada)
    db.commit()

    return {
        "message": "Entrega marcada como nao realizada. Venda voltou para entregas em aberto.",
        "venda_id": venda_id,
    }


@router.get("/vendas/{venda_id}/detalhes")
def detalhes_venda_entregador(
    venda_id: int,
    cliente: Cliente = Depends(_get_entregador_cliente),
    db: Session = Depends(get_session),
):
    tenant_id = _activate_cliente_tenant_context(cliente)
    venda = (
        db.query(Venda)
        .options(
            joinedload(Venda.cliente),
            joinedload(Venda.itens).joinedload(VendaItem.produto),
            joinedload(Venda.pagamentos),
            joinedload(Venda.baixas),
        )
        .filter(
            Venda.id == venda_id,
            Venda.tenant_id == tenant_id,
            Venda.tem_entrega == True,
            or_(Venda.entregador_id == cliente.id, Venda.entregador_id == None),
        )
        .first()
    )
    if not venda:
        raise HTTPException(status_code=404, detail="Venda não encontrada")

    data = venda.to_dict()

    forma_pagamento = data.get("forma_pagamento")
    if not forma_pagamento and venda.baixas:
        baixa_recente = sorted(venda.baixas, key=lambda b: b.data_baixa or datetime.min)[-1]
        forma_pagamento = baixa_recente.forma_pagamento

    data["forma_pagamento"] = forma_pagamento
    if forma_pagamento and data.get("status_pagamento") == "pendente":
        data["status_pagamento"] = "parcial"

    return data
