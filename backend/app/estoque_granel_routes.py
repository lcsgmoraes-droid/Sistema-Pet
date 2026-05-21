"""Rotas de estoque para produtos vendidos a granel."""

from datetime import datetime
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from .auth.dependencies import get_current_user_and_tenant
from .bling_estoque_sync import sincronizar_bling_background
from .db import get_session
from .estoque.granel import (
    _normalizar_produto_granel,
    _obter_ou_criar_vinculo_granel,
    _produto_e_granel,
    _resolver_origem_por_payload_granel,
    _serializar_vinculo_granel,
    _validar_produto_origem_granel,
)
from .produtos_models import (
    EstoqueMovimentacao,
    GranelConversao,
    Produto,
    ProdutoGranelVinculo,
)


logger = logging.getLogger(__name__)
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
        if getattr(origem, "ativo", True) is False or getattr(granel, "ativo", True) is False:
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
                "diferenca_percentual": round((diferenca / preco_minimo_granel) * 100, 2)
                if preco_minimo_granel > 0
                else 0,
                "margem_minima_percentual": round(float(margem_minima_percentual or 0), 2),
                "margem_atual_sobre_venda_kg": round(margem_atual_sobre_venda_kg, 2),
                "margem_atual_sobre_custo_kg": round(margem_atual_sobre_custo_kg, 2)
                if margem_atual_sobre_custo_kg is not None
                else None,
                "criticidade": "CRITICO"
                if preco_venda_granel <= 0 or margem_atual_sobre_venda_kg < 0
                else "ALERTA",
            }
        )

    alertas.sort(key=lambda item: (0 if item["criticidade"] == "CRITICO" else 1, -item["diferenca_valor"]))
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
        raise HTTPException(status_code=400, detail="Produto informado nao esta marcado como granel")
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

    produto_base = _resolver_origem_por_payload_granel(db, tenant_id, payload)
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
        raise HTTPException(status_code=400, detail="Produto informado nao esta marcado como granel")

    peso_pacote_kg = _validar_produto_origem_granel(produto_base)
    _normalizar_produto_granel(produto_granel)
    vinculo = _obter_ou_criar_vinculo_granel(
        db,
        tenant_id,
        current_user,
        produto_base,
        produto_granel,
        None,
    )

    quantidade_pacotes = float(payload.quantidade_pacotes or 0)
    estoque_base_anterior = float(produto_base.estoque_atual or 0)
    if estoque_base_anterior < quantidade_pacotes:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Estoque insuficiente do produto base '{produto_base.nome}'. "
                f"Disponivel: {estoque_base_anterior}, solicitado: {quantidade_pacotes} pacote(s)."
            ),
        )

    quantidade_kg = quantidade_pacotes * peso_pacote_kg
    estoque_granel_anterior = float(produto_granel.estoque_atual or 0)
    custo_pacote = float(produto_base.preco_custo or 0)
    custo_kg = custo_pacote / peso_pacote_kg if peso_pacote_kg > 0 else 0
    custo_granel_anterior = float(produto_granel.preco_custo or 0)
    preco_venda_granel_anterior = float(produto_granel.preco_venda or 0)
    preco_venda_granel_atualizado = bool(
        payload.atualizar_preco_venda_granel and payload.preco_venda_granel is not None
    )

    produto_base.estoque_atual = estoque_base_anterior - quantidade_pacotes
    produto_granel.estoque_atual = estoque_granel_anterior + quantidade_kg
    if produto_granel.estoque_atual > 0:
        produto_granel.preco_custo = (
            (estoque_granel_anterior * custo_granel_anterior) + (quantidade_kg * custo_kg)
        ) / produto_granel.estoque_atual
    if preco_venda_granel_atualizado:
        produto_granel.preco_venda = float(payload.preco_venda_granel or 0)

    conversao = GranelConversao(
        produto_granel_id=produto_granel.id,
        produto_origem_id=produto_base.id,
        quantidade_origem=quantidade_pacotes,
        peso_por_unidade_kg=peso_pacote_kg,
        quantidade_granel_kg=quantidade_kg,
        estoque_origem_anterior=estoque_base_anterior,
        estoque_origem_novo=produto_base.estoque_atual,
        estoque_granel_anterior=estoque_granel_anterior,
        estoque_granel_novo=produto_granel.estoque_atual,
        documento=payload.documento,
        observacao=payload.observacao,
        user_id=current_user.id,
        tenant_id=tenant_id,
    )
    db.add(conversao)
    db.flush()

    mov_saida_base = EstoqueMovimentacao(
        produto_id=produto_base.id,
        tipo="saida",
        motivo="conversao_granel",
        quantidade=quantidade_pacotes,
        quantidade_anterior=estoque_base_anterior,
        quantidade_nova=produto_base.estoque_atual,
        custo_unitario=custo_pacote,
        valor_total=quantidade_pacotes * custo_pacote,
        documento=payload.documento,
        referencia_id=conversao.id,
        referencia_tipo="conversao_granel",
        observacao=f"Conversao para granel '{produto_granel.nome}' ({quantidade_kg:.3f} kg)",
        user_id=current_user.id,
        tenant_id=tenant_id,
    )
    mov_entrada_granel = EstoqueMovimentacao(
        produto_id=produto_granel.id,
        tipo="entrada",
        motivo="conversao_granel",
        quantidade=quantidade_kg,
        quantidade_anterior=estoque_granel_anterior,
        quantidade_nova=produto_granel.estoque_atual,
        custo_unitario=custo_kg,
        valor_total=quantidade_kg * custo_kg,
        documento=payload.documento,
        referencia_id=conversao.id,
        referencia_tipo="conversao_granel",
        observacao=payload.observacao
        or f"Entrada granel a partir de {quantidade_pacotes:g} pacote(s) de '{produto_base.nome}'",
        user_id=current_user.id,
        tenant_id=tenant_id,
    )
    db.add(mov_saida_base)
    db.add(mov_entrada_granel)
    db.commit()

    try:
        sincronizar_bling_background(produto_base.id, produto_base.estoque_atual, "conversao_granel_saida")
        sincronizar_bling_background(produto_granel.id, produto_granel.estoque_atual, "conversao_granel_entrada")
    except Exception as e_sync:
        logger.warning(f"[BLING-SYNC] Erro ao agendar sync (conversao granel): {e_sync}")

    return {
        "id": conversao.id,
        "produto_granel_id": produto_granel.id,
        "produto_granel_nome": produto_granel.nome,
        "produto_origem_id": produto_base.id,
        "produto_origem_nome": produto_base.nome,
        "vinculo_id": vinculo.id,
        "quantidade_pacotes": quantidade_pacotes,
        "peso_por_unidade_kg": peso_pacote_kg,
        "quantidade_granel_kg": quantidade_kg,
        "custo_por_kg": custo_kg,
        "preco_venda_granel_anterior": preco_venda_granel_anterior,
        "preco_venda_granel_novo": float(produto_granel.preco_venda or 0),
        "preco_venda_granel_atualizado": preco_venda_granel_atualizado,
        "estoque_origem_anterior": estoque_base_anterior,
        "estoque_origem_novo": float(produto_base.estoque_atual or 0),
        "estoque_granel_anterior": estoque_granel_anterior,
        "estoque_granel_novo": float(produto_granel.estoque_atual or 0),
        "movimentacoes": {
            "saida_origem_id": mov_saida_base.id,
            "entrada_granel_id": mov_entrada_granel.id,
        },
    }
