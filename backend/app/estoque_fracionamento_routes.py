"""Rotas de conversao de embalagens fechadas para estoque clinico."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from .auth.dependencies import get_current_user_and_tenant
from .db import get_session
from .estoque.fracionamento_clinico import (
    executar_fracionamento_clinico,
    listar_lotes_disponiveis_fracionamento,
    serializar_vinculo_fracionamento,
    sugerir_fracionamento_clinico,
)
from .produtos_models import (
    EstoqueFracionamentoConversao,
    EstoqueFracionamentoVinculo,
    Produto,
)


router = APIRouter(
    prefix="/estoque/fracionamento-clinico",
    tags=["Estoque - Fracionamento Clinico"],
)


class FracionamentoClinicoRequest(BaseModel):
    produto_origem_id: int
    produto_destino_id: int
    quantidade_origem: int = Field(default=1, gt=0)
    fator_conversao: float = Field(gt=0)
    validade_apos_abertura_dias: Optional[int] = Field(default=None, ge=1, le=3650)
    lote_origem_id: Optional[int] = None
    documento: Optional[str] = Field(default=None, max_length=50)
    observacao: Optional[str] = Field(default=None, max_length=1000)


def _produto_payload(produto: Produto) -> dict:
    return {
        "id": produto.id,
        "codigo": produto.codigo,
        "nome": produto.nome,
        "unidade": (produto.unidade or "UN").upper(),
        "estoque_atual": float(produto.estoque_atual or 0),
        "preco_custo": float(produto.preco_custo or 0),
        "preco_venda": float(produto.preco_venda or 0),
    }


@router.get("/produtos")
def listar_produtos_destino_fracionamento(
    produto_origem_id: int,
    busca: Optional[str] = None,
    limite: int = Query(default=40, ge=1, le=100),
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    _user, tenant_id = current
    query = db.query(Produto).filter(
        Produto.tenant_id == tenant_id,
        Produto.id != produto_origem_id,
        Produto.ativo.is_(True),
        Produto.situacao.is_(True),
        or_(Produto.e_granel.is_(False), Produto.e_granel.is_(None)),
        Produto.tipo_produto.in_(("SIMPLES", "VARIACAO")),
    )
    termo = (busca or "").strip()
    if termo:
        pattern = f"%{termo}%"
        query = query.filter(
            or_(Produto.nome.ilike(pattern), Produto.codigo.ilike(pattern))
        )
    produtos = query.order_by(Produto.nome.asc()).limit(limite).all()
    return [
        _produto_payload(produto) for produto in produtos if produto.controlar_estoque
    ]


@router.get("/origens/{produto_origem_id}")
def obter_contexto_fracionamento(
    produto_origem_id: int,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    _user, tenant_id = current
    origem = (
        db.query(Produto)
        .filter(
            Produto.tenant_id == tenant_id,
            Produto.id == produto_origem_id,
        )
        .first()
    )
    if not origem:
        raise HTTPException(status_code=404, detail="Produto de origem nao encontrado")
    vinculos = (
        db.query(EstoqueFracionamentoVinculo)
        .options(
            joinedload(EstoqueFracionamentoVinculo.produto_origem),
            joinedload(EstoqueFracionamentoVinculo.produto_destino),
        )
        .filter(
            EstoqueFracionamentoVinculo.tenant_id == tenant_id,
            EstoqueFracionamentoVinculo.produto_origem_id == produto_origem_id,
            EstoqueFracionamentoVinculo.ativo.is_(True),
        )
        .order_by(EstoqueFracionamentoVinculo.updated_at.desc())
        .all()
    )
    return {
        "produto_origem": _produto_payload(origem),
        "vinculos": [serializar_vinculo_fracionamento(item) for item in vinculos],
        "lotes": listar_lotes_disponiveis_fracionamento(
            db, tenant_id=tenant_id, produto_id=produto_origem_id
        ),
    }


@router.get("/destinos/{produto_destino_id}/sugestao")
def obter_sugestao_fracionamento(
    produto_destino_id: int,
    quantidade_necessaria: float = Query(gt=0),
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    _user, tenant_id = current
    return sugerir_fracionamento_clinico(
        db,
        tenant_id=tenant_id,
        produto_destino_id=produto_destino_id,
        quantidade_necessaria=quantidade_necessaria,
    )


@router.get("/conversoes")
def listar_conversoes_fracionamento(
    produto_id: Optional[int] = None,
    limite: int = Query(default=30, ge=1, le=100),
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    _user, tenant_id = current
    query = (
        db.query(EstoqueFracionamentoConversao)
        .options(
            joinedload(EstoqueFracionamentoConversao.produto_origem),
            joinedload(EstoqueFracionamentoConversao.produto_destino),
        )
        .filter(EstoqueFracionamentoConversao.tenant_id == tenant_id)
    )
    if produto_id:
        query = query.filter(
            or_(
                EstoqueFracionamentoConversao.produto_origem_id == produto_id,
                EstoqueFracionamentoConversao.produto_destino_id == produto_id,
            )
        )
    conversoes = (
        query.order_by(EstoqueFracionamentoConversao.created_at.desc())
        .limit(limite)
        .all()
    )
    return [
        {
            "id": item.id,
            "produto_origem": _produto_payload(item.produto_origem),
            "produto_destino": _produto_payload(item.produto_destino),
            "quantidade_origem": item.quantidade_origem,
            "fator_conversao": item.fator_conversao,
            "quantidade_destino": item.quantidade_destino,
            "unidade_origem": item.unidade_origem,
            "unidade_destino": item.unidade_destino,
            "aberto_em": item.aberto_em,
            "validade_apos_abertura_em": item.validade_apos_abertura_em,
            "documento": item.documento,
            "observacao": item.observacao,
            "status": item.status,
        }
        for item in conversoes
    ]


@router.post("/converter", status_code=status.HTTP_201_CREATED)
def converter_estoque_para_uso_clinico(
    payload: FracionamentoClinicoRequest,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    user, tenant_id = current
    return executar_fracionamento_clinico(
        db,
        tenant_id=tenant_id,
        current_user=user,
        payload=payload,
    )
