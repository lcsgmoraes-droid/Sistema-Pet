"""Lancamento de granel pelo app do funcionario."""

from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.db import get_session
from app.estoque.granel import (
    _produto_e_granel,
    _validar_produto_origem_granel,
    executar_conversao_granel,
)
from app.models import Tenant, User
from app.produtos_models import Produto, ProdutoGranelVinculo
from app.routes.ecommerce_auth import _get_current_ecommerce_user

from .auth import _get_funcionario_operacional_or_403
from .produtos import _barcode_filters_for_produto


router = APIRouter()


class FuncionarioGranelConversaoRequest(BaseModel):
    produto_origem_id: int
    produto_granel_id: int
    quantidade_pacotes: float = Field(gt=0)
    produto_origem_barcode: Optional[str] = None
    produto_granel_barcode: Optional[str] = None
    observacao: Optional[str] = Field(default=None, max_length=500)


def _config_bipagem_granel(db: Session, tenant_id) -> bool:
    tenant = db.query(Tenant).filter(Tenant.id == str(tenant_id)).first()
    return bool(getattr(tenant, "granel_bipagem_obrigatoria", False))


def _serializar_produto_granel_app(produto: Produto) -> dict:
    return {
        "id": produto.id,
        "codigo": produto.codigo,
        "codigo_barras": produto.codigo_barras or produto.gtin_ean,
        "nome": produto.nome,
        "estoque_atual": float(produto.estoque_atual or 0),
        "peso_embalagem": float(produto.peso_embalagem or 0),
        "unidade": produto.unidade,
        "e_granel": _produto_e_granel(produto),
    }


def _validar_produto_etapa_granel(
    db: Session,
    tenant_id,
    produto: Produto | None,
    etapa: Literal["origem", "granel"],
    produto_origem_id: int | None,
) -> Produto:
    if not produto:
        raise HTTPException(status_code=404, detail="Produto nao encontrado no ERP.")
    if etapa == "origem":
        _validar_produto_origem_granel(produto)
        possui_vinculo = (
            db.query(ProdutoGranelVinculo.id)
            .filter(
                ProdutoGranelVinculo.tenant_id == tenant_id,
                ProdutoGranelVinculo.produto_origem_id == produto.id,
                ProdutoGranelVinculo.ativo.is_(True),
            )
            .first()
        )
        if not possui_vinculo:
            raise HTTPException(
                status_code=400,
                detail="Este produto pai nao possui produto granel vinculado.",
            )
        return produto

    if not produto_origem_id:
        raise HTTPException(status_code=400, detail="Bipe primeiro o produto pai.")
    vinculo = (
        db.query(ProdutoGranelVinculo)
        .filter(
            ProdutoGranelVinculo.tenant_id == tenant_id,
            ProdutoGranelVinculo.produto_origem_id == produto_origem_id,
            ProdutoGranelVinculo.produto_granel_id == produto.id,
            ProdutoGranelVinculo.ativo.is_(True),
        )
        .first()
    )
    if not vinculo:
        raise HTTPException(
            status_code=400, detail="Produto granel nao corresponde ao produto pai."
        )
    return produto


@router.get("/funcionario/granel/config")
def obter_config_granel_funcionario(
    current_user: User = Depends(_get_current_ecommerce_user),
    db: Session = Depends(get_session),
):
    _funcionario, tenant_id = _get_funcionario_operacional_or_403(db, current_user)
    return {"bipagem_obrigatoria": _config_bipagem_granel(db, tenant_id)}


@router.get("/funcionario/granel/produtos/barcode/{barcode}")
def buscar_produto_granel_funcionario_barcode(
    barcode: str,
    etapa: Literal["origem", "granel"] = Query(...),
    produto_origem_id: Optional[int] = Query(default=None),
    current_user: User = Depends(_get_current_ecommerce_user),
    db: Session = Depends(get_session),
):
    _funcionario, tenant_id = _get_funcionario_operacional_or_403(db, current_user)
    produto = (
        db.query(Produto)
        .filter(
            Produto.tenant_id == tenant_id,
            or_(Produto.ativo.is_(True), Produto.ativo.is_(None)),
            _barcode_filters_for_produto(barcode),
        )
        .first()
    )
    produto = _validar_produto_etapa_granel(
        db, tenant_id, produto, etapa, produto_origem_id
    )
    return _serializar_produto_granel_app(produto)


@router.get("/funcionario/granel/produtos/buscar")
def buscar_produtos_granel_funcionario(
    termo: str = Query(..., min_length=2),
    etapa: Literal["origem", "granel"] = Query(...),
    produto_origem_id: Optional[int] = Query(default=None),
    current_user: User = Depends(_get_current_ecommerce_user),
    db: Session = Depends(get_session),
):
    _funcionario, tenant_id = _get_funcionario_operacional_or_403(db, current_user)
    if _config_bipagem_granel(db, tenant_id):
        raise HTTPException(
            status_code=403,
            detail="A empresa exige bipagem para o lancamento de granel.",
        )
    pattern = f"%{termo.strip()}%"
    query = db.query(Produto).filter(
        Produto.tenant_id == tenant_id,
        or_(Produto.ativo.is_(True), Produto.ativo.is_(None)),
        or_(
            Produto.nome.ilike(pattern),
            Produto.codigo.ilike(pattern),
            Produto.codigo_barras.ilike(pattern),
            Produto.gtin_ean.ilike(pattern),
        ),
    )
    if etapa == "origem":
        query = query.join(
            ProdutoGranelVinculo,
            ProdutoGranelVinculo.produto_origem_id == Produto.id,
        ).filter(
            ProdutoGranelVinculo.tenant_id == tenant_id,
            ProdutoGranelVinculo.ativo.is_(True),
        )
    else:
        if not produto_origem_id:
            raise HTTPException(
                status_code=400, detail="Selecione primeiro o produto pai."
            )
        query = query.join(
            ProdutoGranelVinculo,
            ProdutoGranelVinculo.produto_granel_id == Produto.id,
        ).filter(
            ProdutoGranelVinculo.tenant_id == tenant_id,
            ProdutoGranelVinculo.produto_origem_id == produto_origem_id,
            ProdutoGranelVinculo.ativo.is_(True),
        )
    produtos = query.distinct().order_by(Produto.nome.asc()).limit(20).all()
    return [_serializar_produto_granel_app(produto) for produto in produtos]


@router.post(
    "/funcionario/granel/converter",
    status_code=status.HTTP_201_CREATED,
)
def converter_granel_funcionario(
    payload: FuncionarioGranelConversaoRequest,
    current_user: User = Depends(_get_current_ecommerce_user),
    db: Session = Depends(get_session),
):
    _funcionario, tenant_id = _get_funcionario_operacional_or_403(db, current_user)
    return executar_conversao_granel(
        db,
        tenant_id,
        current_user,
        payload,
        exigir_bipagem=_config_bipagem_granel(db, tenant_id),
    )
