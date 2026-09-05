"""Cadastro rapido de produtos no perfil operacional, para completar no ERP."""

from decimal import Decimal
import logging
from typing import Literal
from uuid import UUID, uuid4, uuid5

from fastapi import APIRouter, Depends, HTTPException, Query, Response
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
from app.services.produto_service import ProdutoService, normalizar_sku_produto
from app.routes.app_mobile_funcionario_produto_imagens import router as imagens_router

router = APIRouter(prefix="/funcionario/produtos")
router.include_router(imagens_router)
logger = logging.getLogger(__name__)


class ProdutoRapidoRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    codigo_barras: str | None = Field(
        default=None, min_length=1, max_length=20, pattern=r"^[A-Za-z0-9 ._/-]+$"
    )
    chave_cadastro: UUID | None = None
    nome: str = Field(min_length=1, max_length=200)
    codigo: str | None = Field(default=None, max_length=50)
    descricao_curta: str | None = Field(default=None, max_length=1000)
    preco_venda: Decimal = Field(gt=0, max_digits=10, decimal_places=2)
    preco_custo: Decimal = Field(
        default=Decimal("0"), ge=0, max_digits=10, decimal_places=2
    )
    unidade: Literal["UN", "KG", "CX", "PC", "LT"] = "UN"

    @field_validator("codigo_barras", mode="before")
    @classmethod
    def normalizar_codigo_barras(cls, valor):
        return None if isinstance(valor, str) and not valor.strip() else valor

    @field_validator("codigo", mode="before")
    @classmethod
    def normalizar_codigo(cls, valor):
        return normalizar_sku_produto(valor) if str(valor or "").strip() else None


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
    descricao_curta: str | None = None
    imagem_principal: str | None = None

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


def _buscar_sku(db: Session, tenant_id: UUID, codigo: str) -> Produto | None:
    return (
        db.query(Produto)
        .filter(
            Produto.tenant_id == tenant_id,
            func.lower(func.trim(Produto.codigo)) == codigo.lower(),
        )
        .first()
    )


class SkuDisponibilidadeResponse(BaseModel):
    codigo: str
    disponivel: bool
    produto: ProdutoRapidoResponse | None = None


@router.get("/consultar-sku", response_model=SkuDisponibilidadeResponse)
def consultar_sku_produto_rapido(
    codigo: str = Query(min_length=1, max_length=50),
    current_user: User = Depends(_get_current_ecommerce_user),
    db: Session = Depends(get_session),
):
    _, tenant_id = _get_funcionario_operacional_or_403(db, current_user)
    if not codigo.strip():
        raise HTTPException(status_code=400, detail="Informe o SKU para consultar.")
    codigo = normalizar_sku_produto(codigo)
    produto = _buscar_sku(db, UUID(tenant_id), codigo)
    return {
        "codigo": codigo,
        "disponivel": produto is None,
        "produto": produto,
    }


def _sku_indisponivel() -> HTTPException:
    return HTTPException(
        status_code=409,
        detail={
            "campo": "codigo",
            "mensagem": "Este SKU ja esta em uso. Escolha outro ou deixe vazio para gerar automaticamente.",
        },
    )


@router.post("/rapido", response_model=ProdutoRapidoResponse, status_code=201)
def criar_produto_rapido(
    payload: ProdutoRapidoRequest,
    response: Response,
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
    # Sem SKU manual, a mesma tentativa conserva a identidade mesmo sem EAN.
    # A chave fica representada no SKU normal, sem nova tabela ou migration.
    sku_repetivel = (
        f"APP-{uuid5(tenant_uuid, str(payload.chave_cadastro)).hex.upper()}"
        if payload.chave_cadastro and not payload.codigo
        else None
    )
    if sku_repetivel:
        confirmado = _buscar_sku(db, tenant_uuid, sku_repetivel)
        if confirmado:
            response.status_code = 200
            return confirmado

    existente = (
        _buscar_produto_existente(db, tenant_uuid, payload.codigo_barras)
        if payload.codigo_barras
        else None
    )
    if existente:
        raise HTTPException(
            status_code=409,
            detail={
                "mensagem": "Este codigo ja esta cadastrado no ERP.",
                "campo": "codigo_barras",
                "produto": ProdutoRapidoResponse.model_validate(existente).model_dump(),
            },
        )

    codigo = payload.codigo or sku_repetivel or f"APP-{uuid4().hex[:16].upper()}"
    if _buscar_sku(db, tenant_uuid, codigo):
        raise _sku_indisponivel()

    dados = {
        **payload.model_dump(exclude={"chave_cadastro"}),
        "preco_venda": float(payload.preco_venda),
        "preco_custo": float(payload.preco_custo),
        "codigo": codigo,
        "user_id": current_user.id,
        "tipo": "produto",
        "tipo_produto": "SIMPLES",
        "ativo": True,
        "situacao": True,
        "estoque_atual": 0,
        "anunciar_app": False,
        "anunciar_ecommerce": False,
    }
    try:
        return ProdutoService.create_produto(dados=dados, db=db, tenant_id=tenant_uuid)
    except ValueError as exc:
        # O indice unico do ERP continua sendo a barreira final para outra criacao
        # que ocorrer entre a consulta e o commit, inclusive fora do app.
        db.rollback()
        if _buscar_sku(db, tenant_uuid, codigo):
            raise _sku_indisponivel() from exc
        logger.exception("Falha ao cadastrar produto pelo app")
        raise HTTPException(
            status_code=500,
            detail="Nao foi possivel salvar o produto. Tente novamente.",
        ) from exc
