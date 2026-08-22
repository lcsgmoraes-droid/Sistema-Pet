"""Rotas de estoque para produtos vendidos a granel."""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from .auth.dependencies import get_current_user_and_tenant
from .db import get_session
from .estoque.granel import (
    executar_conversao_granel,
    _normalizar_produto_granel,
    _obter_ou_criar_vinculo_granel,
    _produto_e_granel,
    _serializar_vinculo_granel,
    _validar_produto_origem_granel,
)
from .produtos_models import Produto, ProdutoGranelVinculo


router = APIRouter(prefix="/estoque", tags=["Estoque - Granel"])


class ConversaoGranelRequest(BaseModel):
    """Abre pacote(s) fisico(s) e abastece um produto granel em kg."""

    produto_origem_id: Optional[int] = None
    produto_granel_id: int
    quantidade_pacotes: float = Field(gt=0)
    atualizar_preco_venda_granel: bool = False
    preco_venda_granel: Optional[float] = Field(default=None, ge=0)
    documento: Optional[str] = None
    observacao: Optional[str] = None
    produto_origem_barcode: Optional[str] = None
    produto_granel_barcode: Optional[str] = None


class GranelVinculoRequest(BaseModel):
    """Vincula um produto fechado a um produto granel."""

    produto_origem_id: int
    produto_granel_id: int
    observacao: Optional[str] = None


@router.get("/granel/produtos")
def listar_produtos_granel(
    busca: Optional[str] = None,
    limite: int = 30,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Lista produtos marcados como granel para vinculo/conversao."""
    _current_user, tenant_id = user_and_tenant
    limite = min(max(int(limite or 30), 1), 100)
    query = db.query(Produto).filter(
        Produto.tenant_id == tenant_id,
        or_(Produto.ativo.is_(True), Produto.ativo.is_(None)),
        or_(Produto.e_granel.is_(True), Produto.nome.ilike("%granel%")),
    )
    termo = (busca or "").strip()
    if termo:
        pattern = f"%{termo}%"
        query = query.filter(
            or_(
                Produto.nome.ilike(pattern),
                Produto.codigo.ilike(pattern),
                Produto.codigo_barras.ilike(pattern),
            )
        )

    produtos = query.order_by(Produto.nome.asc()).limit(limite).all()
    return [
        {
            "id": produto.id,
            "codigo": produto.codigo,
            "nome": produto.nome,
            "estoque_atual": float(produto.estoque_atual or 0),
            "preco_custo": float(produto.preco_custo or 0),
            "preco_venda": float(produto.preco_venda or 0),
            "unidade": produto.unidade or "KG",
            "e_granel": True,
        }
        for produto in produtos
    ]


@router.get("/granel/vinculos/origem/{produto_origem_id}")
def listar_vinculos_granel_origem(
    produto_origem_id: int,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Lista graneis vinculados a um produto fechado de origem."""
    _current_user, tenant_id = user_and_tenant
    vinculos = (
        db.query(ProdutoGranelVinculo)
        .options(
            joinedload(ProdutoGranelVinculo.produto_origem),
            joinedload(ProdutoGranelVinculo.produto_granel),
        )
        .filter(
            ProdutoGranelVinculo.tenant_id == tenant_id,
            ProdutoGranelVinculo.produto_origem_id == produto_origem_id,
            ProdutoGranelVinculo.ativo.is_(True),
        )
        .order_by(ProdutoGranelVinculo.updated_at.desc())
        .all()
    )
    return [_serializar_vinculo_granel(vinculo) for vinculo in vinculos]


@router.get("/granel/alertas-preco")
def listar_alertas_preco_granel(
    margem_minima_percentual: float = Query(default=20, ge=0, le=300),
    limite: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Lista graneis vinculados com preco abaixo da margem minima sobre venda/kg da origem."""
    _current_user, tenant_id = user_and_tenant
    fator_margem = 1 + (float(margem_minima_percentual or 0) / 100)

    vinculos = (
        db.query(ProdutoGranelVinculo)
        .options(
            joinedload(ProdutoGranelVinculo.produto_origem),
            joinedload(ProdutoGranelVinculo.produto_granel),
        )
        .filter(
            ProdutoGranelVinculo.tenant_id == tenant_id,
            ProdutoGranelVinculo.ativo.is_(True),
        )
        .all()
    )

    alertas = []
    for vinculo in vinculos:
        origem = vinculo.produto_origem
        granel = vinculo.produto_granel
        if not origem or not granel:
            continue
        if (
            getattr(origem, "ativo", True) is False
            or getattr(granel, "ativo", True) is False
        ):
            continue

        peso_kg = float(getattr(origem, "peso_embalagem", 0) or 0)
        preco_venda_origem = float(getattr(origem, "preco_venda", 0) or 0)
        preco_venda_granel = float(getattr(granel, "preco_venda", 0) or 0)
        custo_origem = float(getattr(origem, "preco_custo", 0) or 0)
        if peso_kg <= 0 or preco_venda_origem <= 0:
            continue

        venda_kg_origem = preco_venda_origem / peso_kg
        custo_kg_origem = custo_origem / peso_kg if custo_origem > 0 else 0
        preco_minimo_granel = venda_kg_origem * fator_margem
        if preco_venda_granel >= preco_minimo_granel:
            continue

        margem_atual_sobre_venda_kg = (
            ((preco_venda_granel / venda_kg_origem) - 1) * 100
            if venda_kg_origem > 0 and preco_venda_granel > 0
            else -100
        )
        margem_atual_sobre_custo_kg = (
            ((preco_venda_granel / custo_kg_origem) - 1) * 100
            if custo_kg_origem > 0 and preco_venda_granel > 0
            else None
        )
        diferenca = preco_minimo_granel - preco_venda_granel
        alertas.append(
            {
                "vinculo_id": vinculo.id,
                "produto_origem_id": origem.id,
                "produto_origem_nome": origem.nome,
                "produto_origem_codigo": getattr(origem, "codigo", None),
                "produto_granel_id": granel.id,
                "produto_granel_nome": granel.nome,
                "produto_granel_codigo": getattr(granel, "codigo", None),
                "peso_por_unidade_kg": round(peso_kg, 3),
                "preco_venda_origem": round(preco_venda_origem, 2),
                "preco_venda_kg_origem": round(venda_kg_origem, 2),
                "custo_kg_origem": round(custo_kg_origem, 2),
                "preco_venda_granel": round(preco_venda_granel, 2),
                "preco_minimo_granel": round(preco_minimo_granel, 2),
                "diferenca_valor": round(diferenca, 2),
                "diferenca_percentual": round(
                    (diferenca / preco_minimo_granel) * 100, 2
                )
                if preco_minimo_granel > 0
                else 0,
                "margem_minima_percentual": round(
                    float(margem_minima_percentual or 0), 2
                ),
                "margem_atual_sobre_venda_kg": round(margem_atual_sobre_venda_kg, 2),
                "margem_atual_sobre_custo_kg": round(margem_atual_sobre_custo_kg, 2)
                if margem_atual_sobre_custo_kg is not None
                else None,
                "criticidade": "CRITICO"
                if preco_venda_granel <= 0 or margem_atual_sobre_venda_kg < 0
                else "ALERTA",
            }
        )

    alertas.sort(
        key=lambda item: (
            0 if item["criticidade"] == "CRITICO" else 1,
            -item["diferenca_valor"],
        )
    )
    total_alertas = len(alertas)
    alertas = alertas[:limite]
    return {
        "margem_minima_percentual": round(float(margem_minima_percentual or 0), 2),
        "total": total_alertas,
        "alertas": alertas,
    }


@router.post("/granel/vinculos", status_code=status.HTTP_201_CREATED)
def criar_vinculo_granel(
    payload: GranelVinculoRequest,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Cria ou reativa vinculo entre produto fechado e produto granel."""
    current_user, tenant_id = user_and_tenant
    produto_origem = (
        db.query(Produto)
        .filter(
            Produto.id == payload.produto_origem_id,
            Produto.tenant_id == tenant_id,
        )
        .first()
    )
    _validar_produto_origem_granel(produto_origem)

    produto_granel = (
        db.query(Produto)
        .filter(
            Produto.id == payload.produto_granel_id,
            Produto.tenant_id == tenant_id,
        )
        .first()
    )
    if not produto_granel:
        raise HTTPException(status_code=404, detail="Produto granel nao encontrado")
    if not _produto_e_granel(produto_granel):
        raise HTTPException(
            status_code=400, detail="Produto informado nao esta marcado como granel"
        )
    _normalizar_produto_granel(produto_granel)

    vinculo = _obter_ou_criar_vinculo_granel(
        db,
        tenant_id,
        current_user,
        produto_origem,
        produto_granel,
        payload.observacao,
    )
    db.commit()
    db.refresh(vinculo)
    return _serializar_vinculo_granel(vinculo)


@router.delete("/granel/vinculos/{vinculo_id}")
def desvincular_granel(
    vinculo_id: int,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Desativa vinculo entre produto fechado e granel sem apagar historico."""
    _current_user, tenant_id = user_and_tenant
    vinculo = (
        db.query(ProdutoGranelVinculo)
        .filter(
            ProdutoGranelVinculo.id == vinculo_id,
            ProdutoGranelVinculo.tenant_id == tenant_id,
        )
        .first()
    )
    if not vinculo:
        raise HTTPException(status_code=404, detail="Vinculo granel nao encontrado")
    vinculo.ativo = False
    vinculo.updated_at = datetime.utcnow()
    db.commit()
    return {"ok": True, "id": vinculo_id}


@router.post("/granel/converter", status_code=status.HTTP_201_CREATED)
def converter_estoque_granel(
    payload: ConversaoGranelRequest,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Converte pacote(s) fechados de origem em estoque fisico granel medido em kg."""
    current_user, tenant_id = user_and_tenant
    from .models import Tenant

    tenant = db.query(Tenant).filter(Tenant.id == str(tenant_id)).first()
    return executar_conversao_granel(
        db,
        tenant_id,
        current_user,
        payload,
        exigir_bipagem=bool(getattr(tenant, "granel_bipagem_obrigatoria", False)),
    )
