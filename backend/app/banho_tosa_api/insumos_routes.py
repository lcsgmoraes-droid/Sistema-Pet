from decimal import Decimal
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user_and_tenant
from app.banho_tosa_api.insumos_helpers import (
    baixar_estoque_insumo,
    estornar_estoque_insumo_registrado,
    obter_atendimento_ou_404,
    obter_insumo_ou_404,
    obter_produto_ou_404,
    query_insumos,
    serializar_insumo,
    validar_edicao_insumo,
    validar_responsavel,
)
from app.banho_tosa_custos_helpers import dec
from app.banho_tosa_models import BanhoTosaInsumoUsado
from app.banho_tosa_schemas import (
    BanhoTosaInsumoUsadoCreate,
    BanhoTosaInsumoUsadoResponse,
    BanhoTosaInsumoUsadoUpdate,
)
from app.db import get_session
from app.veterinario_core import _get_tenant


router = APIRouter()


@router.get(
    "/atendimentos/{atendimento_id}/insumos",
    response_model=List[BanhoTosaInsumoUsadoResponse],
)
def listar_insumos_atendimento(
    atendimento_id: int,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    _, tenant_id = _get_tenant(current)
    obter_atendimento_ou_404(db, tenant_id, atendimento_id)
    insumos = query_insumos(db, tenant_id, atendimento_id).order_by(BanhoTosaInsumoUsado.id.desc()).all()
    return [serializar_insumo(item) for item in insumos]


@router.post(
    "/atendimentos/{atendimento_id}/insumos",
    response_model=BanhoTosaInsumoUsadoResponse,
    status_code=201,
)
def registrar_insumo_atendimento(
    atendimento_id: int,
    body: BanhoTosaInsumoUsadoCreate,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    user, tenant_id = _get_tenant(current)
    obter_atendimento_ou_404(db, tenant_id, atendimento_id)
    produto = obter_produto_ou_404(db, tenant_id, body.produto_id)
    validar_responsavel(db, tenant_id, body.responsavel_id)

    quantidade_total = dec(body.quantidade_usada) + dec(body.quantidade_desperdicio)
    if quantidade_total <= 0:
        raise HTTPException(status_code=422, detail="Informe quantidade usada ou desperdicio.")

    custo_unitario = body.custo_unitario_snapshot
    if custo_unitario is None:
        custo_unitario = Decimal(str(produto.preco_custo or 0))

    insumo = query_insumos(db, tenant_id, atendimento_id).filter(
        BanhoTosaInsumoUsado.produto_id == produto.id,
    ).first()
    if insumo and insumo.movimentacao_estoque_id:
        raise HTTPException(
            status_code=422,
            detail="Produto ja possui baixa/estorno. Estorne e remova antes de lancar novamente.",
        )

    quantidade_para_baixa = quantidade_total
    if insumo:
        quantidade_para_baixa += dec(insumo.quantidade_usada) + dec(insumo.quantidade_desperdicio)

    if not insumo:
        insumo = BanhoTosaInsumoUsado(
            tenant_id=tenant_id,
            atendimento_id=atendimento_id,
            produto_id=produto.id,
            quantidade_prevista=0,
        )
        db.add(insumo)

    insumo.quantidade_usada = dec(insumo.quantidade_usada) + dec(body.quantidade_usada)
    insumo.quantidade_desperdicio = dec(insumo.quantidade_desperdicio) + dec(body.quantidade_desperdicio)
    insumo.custo_unitario_snapshot = custo_unitario
    insumo.responsavel_id = body.responsavel_id

    if body.baixar_estoque:
        insumo.movimentacao_estoque_id = baixar_estoque_insumo(
            user,
            tenant_id,
            atendimento_id,
            produto,
            quantidade_para_baixa,
            custo_unitario,
            db,
        )

    db.commit()
    insumo = obter_insumo_ou_404(db, tenant_id, atendimento_id, insumo.id)
    return serializar_insumo(insumo)


@router.patch(
    "/atendimentos/{atendimento_id}/insumos/{insumo_id}",
    response_model=BanhoTosaInsumoUsadoResponse,
)
def atualizar_insumo_atendimento(
    atendimento_id: int,
    insumo_id: int,
    body: BanhoTosaInsumoUsadoUpdate,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    _, tenant_id = _get_tenant(current)
    insumo = obter_insumo_ou_404(db, tenant_id, atendimento_id, insumo_id)
    validar_responsavel(db, tenant_id, body.responsavel_id)

    payload = body.model_dump(exclude_unset=True)
    validar_edicao_insumo(insumo, payload)

    for campo, valor in payload.items():
        setattr(insumo, campo, valor)

    db.commit()
    insumo = obter_insumo_ou_404(db, tenant_id, atendimento_id, insumo.id)
    return serializar_insumo(insumo)


@router.post(
    "/atendimentos/{atendimento_id}/insumos/{insumo_id}/estornar-estoque",
    response_model=BanhoTosaInsumoUsadoResponse,
)
def estornar_estoque_insumo(
    atendimento_id: int,
    insumo_id: int,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    user, tenant_id = _get_tenant(current)
    insumo = obter_insumo_ou_404(db, tenant_id, atendimento_id, insumo_id)
    if not insumo.movimentacao_estoque_id:
        raise HTTPException(status_code=422, detail="Insumo nao possui baixa de estoque.")
    if insumo.movimentacao_estorno_id:
        raise HTTPException(status_code=422, detail="Baixa de estoque ja estornada.")

    estornar_estoque_insumo_registrado(user, tenant_id, atendimento_id, insumo, db)
    db.commit()
    insumo = obter_insumo_ou_404(db, tenant_id, atendimento_id, insumo.id)
    return serializar_insumo(insumo)


@router.delete("/atendimentos/{atendimento_id}/insumos/{insumo_id}", status_code=204)
def remover_insumo_atendimento(
    atendimento_id: int,
    insumo_id: int,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    _, tenant_id = _get_tenant(current)
    insumo = obter_insumo_ou_404(db, tenant_id, atendimento_id, insumo_id)
    if insumo.movimentacao_estoque_id and not insumo.movimentacao_estorno_id:
        raise HTTPException(status_code=422, detail="Insumo com baixa de estoque nao pode ser removido sem estorno.")

    db.delete(insumo)
    db.commit()
    return Response(status_code=204)
