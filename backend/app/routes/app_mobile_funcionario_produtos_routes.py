"""Cadastro rapido de produtos no perfil operacional, para completar no ERP."""

from decimal import Decimal
from typing import Literal
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import func, or_, text
from sqlalchemy.orm import Session

from app.db import get_session
from app.models import User
from app.produtos.search import _valores_codigo_produto
from app.produtos_models import Produto
from app.routes.app_mobile_funcionario_pdv.auth import (
    _get_funcionario_operacional_or_403,
)
from app.routes.ecommerce_auth import _get_current_ecommerce_user
from app.services.produto_service import ProdutoService

router = APIRouter(prefix="/funcionario/produtos")


class ProdutoRapidoRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    codigo_barras: str = Field(
        min_length=1, max_length=20, pattern=r"^[A-Za-z0-9 ._/-]+$"
    )
    nome: str = Field(min_length=1, max_length=200)
    preco_venda: Decimal = Field(gt=0, max_digits=10, decimal_places=2)
    preco_custo: Decimal = Field(
        default=Decimal("0"), ge=0, max_digits=10, decimal_places=2
    )
    unidade: Literal["UN", "KG", "CX", "PC", "LT"] = "UN"


class ProdutoRapidoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nome: str
    codigo: str
    codigo_barras: str | None = None
    unidade: str
    preco_venda: float | None = None
    ativo: bool
    situacao: bool | None = None

    @field_validator("unidade", mode="before")
    @classmethod
    def unidade_legada(cls, valor):
        return valor or "UN"

    @field_validator("ativo", mode="before")
    @classmethod
    def status_legado(cls, valor):
        return bool(valor)


def _codigo_comparavel(valor: str) -> str:
    codigo = valor.strip().casefold()
    # UPC/EAN podem chegar com zeros de preenchimento diferentes em Android/iOS.
    if codigo.isascii() and codigo.isdigit():
        return codigo.lstrip("0") or "0"
    return codigo


def _buscar_produto_existente(
    db: Session, tenant_id: UUID, codigo: str
) -> Produto | None:
    codigo = codigo.strip()
    chave = _codigo_comparavel(codigo)
    colunas = [
        Produto.codigo,
        Produto.codigo_barras,
        Produto.gtin_ean,
        Produto.gtin_ean_tributario,
    ]
    filtros = [func.lower(func.trim(coluna)) == codigo.casefold() for coluna in colunas]
    if codigo.isascii() and codigo.isdigit():
        filtros.extend(
            func.ltrim(func.trim(coluna), "0") == codigo.lstrip("0")
            for coluna in colunas
        )
    filtros.append(
        func.lower(Produto.codigos_barras_alternativos).contains(chave, autoescape=True)
    )
    candidatos = (
        db.query(Produto)
        .filter(Produto.tenant_id == tenant_id, or_(*filtros))
        .order_by(Produto.id.asc())
        .all()
    )
    # Conferir cada codigo completo: um EAN alternativo nao pode casar por trecho.
    return next(
        (
            produto
            for produto in candidatos
            if any(
                _codigo_comparavel(valor) == chave
                for valor in _valores_codigo_produto(produto)
            )
        ),
        None,
    )


@router.get("/consultar-codigo", response_model=ProdutoRapidoResponse | None)
def consultar_codigo_produto_rapido(
    codigo: str = Query(min_length=1, max_length=20),
    current_user: User = Depends(_get_current_ecommerce_user),
    db: Session = Depends(get_session),
):
    _, tenant_id = _get_funcionario_operacional_or_403(db, current_user)
    if not codigo.strip():
        raise HTTPException(status_code=400, detail="Informe o codigo de barras.")
    # Inclui inativos e produtos fora do catalogo publico para evitar duplicidade.
    return _buscar_produto_existente(db, UUID(tenant_id), codigo)


@router.post("/rapido", response_model=ProdutoRapidoResponse, status_code=201)
def criar_produto_rapido(
    payload: ProdutoRapidoRequest,
    current_user: User = Depends(_get_current_ecommerce_user),
    db: Session = Depends(get_session),
):
    _, tenant_id = _get_funcionario_operacional_or_403(db, current_user)
    tenant_uuid = UUID(tenant_id)
    # Serializa cadastros mobile da empresa ate o commit do service, inclusive
    # tentativas repetidas depois de timeout e leituras simultaneas em dois aparelhos.
    if db.get_bind().dialect.name == "postgresql":
        db.execute(
            text("SELECT pg_advisory_xact_lock(hashtextextended(:chave, 0))"),
            {"chave": f"produto-rapido:{tenant_id}"},
        )
    existente = _buscar_produto_existente(db, tenant_uuid, payload.codigo_barras)
    if existente:
        raise HTTPException(
            status_code=409,
            detail={
                "mensagem": "Este codigo ja esta cadastrado no ERP.",
                "produto": ProdutoRapidoResponse.model_validate(existente).model_dump(),
            },
        )

    dados = {
        **payload.model_dump(),
        "preco_venda": float(payload.preco_venda),
        "preco_custo": float(payload.preco_custo),
        "codigo": f"APP-{uuid4().hex[:16].upper()}",
        "user_id": current_user.id,
        "tipo": "produto",
        "tipo_produto": "SIMPLES",
        "ativo": True,
        "situacao": True,
        "estoque_atual": 0,
        "anunciar_app": False,
        "anunciar_ecommerce": False,
    }
    return ProdutoService.create_produto(dados=dados, db=db, tenant_id=tenant_uuid)
