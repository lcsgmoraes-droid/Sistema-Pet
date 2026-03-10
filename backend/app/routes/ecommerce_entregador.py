"""Rotas da API para o perfil de entregador no app mobile."""
from datetime import datetime
from decimal import Decimal
from typing import List, Optional
import secrets

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from pydantic import BaseModel
from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from app.auth.core import ALGORITHM
from app.config import JWT_SECRET_KEY
from app.db import get_session
from app.models import Cliente, ConfiguracaoEntrega, User
from app.rotas_entrega_models import RotaEntrega, RotaEntregaParada
from app.schemas.rota_entrega import RotaEntregaResponse
from app.services.google_maps_service import calcular_rota_otimizada
from app.vendas_models import Venda, VendaItem

router = APIRouter(prefix="/ecommerce/entregador", tags=["ecommerce-entregador"])
_security = HTTPBearer()


class OtimizarSelecionadasPayload(BaseModel):
    venda_ids: List[int]


class CriarRotaPayload(BaseModel):
    venda_ids: List[int]
    retorna_origem: bool = True


class ReordenarParadasPayload(BaseModel):
    parada_ids: List[int]


def _get_entregador_cliente(
    credentials: HTTPAuthorizationCredentials = Depends(_security),
    db: Session = Depends(get_session),
) -> Cliente:
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


@router.get("/entregas-abertas")
def listar_entregas_abertas(
    cliente: Cliente = Depends(_get_entregador_cliente),
    db: Session = Depends(get_session),
):
    vendas = (
        db.query(Venda)
        .options(joinedload(Venda.cliente))
        .filter(
            Venda.tenant_id == str(cliente.tenant_id),
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

    config = db.query(ConfiguracaoEntrega).filter(
        ConfiguracaoEntrega.tenant_id == str(cliente.tenant_id)
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
            Venda.tenant_id == str(cliente.tenant_id),
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

    ensure_rotas_entrega_schema(db)

    if not payload.venda_ids:
        raise HTTPException(status_code=400, detail="Selecione ao menos uma entrega")

    vendas = (
        db.query(Venda)
        .filter(
            Venda.tenant_id == str(cliente.tenant_id),
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
        ConfiguracaoEntrega.tenant_id == str(cliente.tenant_id)
    ).first()
    ponto_origem = _montar_endereco_origem(config)

    rota = RotaEntrega(
        tenant_id=str(cliente.tenant_id),
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
            tenant_id=str(cliente.tenant_id),
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


@router.put("/rotas/{rota_id}/paradas/reordenar")
def reordenar_paradas_rota_entregador(
    rota_id: int,
    payload: ReordenarParadasPayload,
    cliente: Cliente = Depends(_get_entregador_cliente),
    db: Session = Depends(get_session),
):
    rota = db.query(RotaEntrega).filter(
        RotaEntrega.id == rota_id,
        RotaEntrega.tenant_id == str(cliente.tenant_id),
        RotaEntrega.entregador_id == cliente.id,
    ).first()
    if not rota:
        raise HTTPException(status_code=404, detail="Rota não encontrada")
    if rota.status != "pendente":
        raise HTTPException(status_code=400, detail="Só é possível reordenar antes de iniciar a rota")

    paradas = db.query(RotaEntregaParada).filter(
        RotaEntregaParada.rota_id == rota.id,
        RotaEntregaParada.tenant_id == str(cliente.tenant_id),
    ).all()
    paradas_por_id = {p.id: p for p in paradas}

    if set(payload.parada_ids) != set(paradas_por_id.keys()):
        raise HTTPException(status_code=400, detail="Lista de paradas inválida")

    for idx, parada_id in enumerate(payload.parada_ids, start=1):
        paradas_por_id[parada_id].ordem = idx

    db.commit()
    return {"message": "Ordem das paradas atualizada"}


@router.get("/vendas/{venda_id}/detalhes")
def detalhes_venda_entregador(
    venda_id: int,
    cliente: Cliente = Depends(_get_entregador_cliente),
    db: Session = Depends(get_session),
):
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
            Venda.tenant_id == str(cliente.tenant_id),
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
