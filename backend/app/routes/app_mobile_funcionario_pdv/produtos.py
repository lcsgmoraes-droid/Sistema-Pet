"""Busca e serializacao de produtos do PDV mobile."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import and_, case, func, or_, true
from sqlalchemy.orm import Session

from app.db import get_session
from app.models import User
from app.produtos_models import Produto
from app.routes.ecommerce_auth import _get_current_ecommerce_user

from .auth import _get_funcionario_operacional_or_403
from .schemas import FuncionarioPdvProdutoResponse

router = APIRouter()


def _barcode_filters_for_produto(barcode: str) -> list:
    barcode = (barcode or "").strip()
    barcode_digits = "".join(ch for ch in barcode if ch.isdigit())
    codigo_barras_digits = func.regexp_replace(
        func.coalesce(Produto.codigo_barras, ""), r"\D", "", "g"
    )
    gtin_digits = func.regexp_replace(
        func.coalesce(Produto.gtin_ean, ""), r"\D", "", "g"
    )
    gtin_tributario_digits = func.regexp_replace(
        func.coalesce(Produto.gtin_ean_tributario, ""), r"\D", "", "g"
    )
    filtros_codigo = [
        Produto.codigo_barras == barcode,
        Produto.gtin_ean == barcode,
        Produto.gtin_ean_tributario == barcode,
        Produto.codigo == barcode,
        Produto.codigos_barras_alternativos.ilike(f"%{barcode}%"),
    ]
    if barcode_digits:
        filtros_codigo.extend(
            [
                codigo_barras_digits == barcode_digits,
                gtin_digits == barcode_digits,
                gtin_tributario_digits == barcode_digits,
                Produto.codigo == barcode_digits,
                Produto.codigos_barras_alternativos.ilike(f"%{barcode_digits}%"),
            ]
        )
    return filtros_codigo


def _tokens_busca_produto_funcionario(termo: str) -> list[str]:
    texto = (termo or "").strip()
    for separador in ["/", "\\", "-", "_", ".", ",", ";", ":", "|", "(", ")"]:
        texto = texto.replace(separador, " ")
    return [token for token in texto.split() if len(token.strip()) >= 2]


def _termo_parece_codigo_produto_funcionario(termo: str) -> bool:
    texto = (termo or "").strip()
    if not texto or any(ch.isspace() for ch in texto):
        return False
    return any(ch.isdigit() for ch in texto)


def _produto_busca_texto_funcionario(termo: str):
    return or_(
        Produto.nome.ilike(f"%{termo}%"),
        Produto.codigo.ilike(f"%{termo}%"),
        Produto.codigo_barras.ilike(f"%{termo}%"),
        Produto.gtin_ean.ilike(f"%{termo}%"),
        Produto.gtin_ean_tributario.ilike(f"%{termo}%"),
        Produto.codigos_barras_alternativos.ilike(f"%{termo}%"),
    )


def _produto_busca_filtros_funcionario(termo: str) -> list:
    termo = (termo or "").strip()
    tokens = _tokens_busca_produto_funcionario(termo)
    filtros = [_produto_busca_texto_funcionario(termo)]

    if len(tokens) > 1:
        filtros.append(
            and_(*[_produto_busca_texto_funcionario(token) for token in tokens])
        )

    if _termo_parece_codigo_produto_funcionario(termo):
        filtros.extend(_barcode_filters_for_produto(termo))

    return filtros


def _produto_busca_rank_funcionario(termo: str):
    termo = (termo or "").strip()
    tokens = _tokens_busca_produto_funcionario(termo)
    condicoes = []

    if _termo_parece_codigo_produto_funcionario(termo):
        condicoes.extend(
            [
                (Produto.codigo == termo, 0),
                (Produto.codigo_barras == termo, 0),
                (Produto.gtin_ean == termo, 0),
                (Produto.gtin_ean_tributario == termo, 0),
            ]
        )

    condicoes.append((Produto.nome.ilike(f"%{termo}%"), 1))
    if len(tokens) > 1:
        condicoes.append(
            (and_(*[Produto.nome.ilike(f"%{token}%") for token in tokens]), 2)
        )
        condicoes.append(
            (and_(*[_produto_busca_texto_funcionario(token) for token in tokens]), 3)
        )

    condicoes.extend(
        [
            (Produto.codigo.ilike(f"%{termo}%"), 4),
            (Produto.codigo_barras.ilike(f"%{termo}%"), 5),
            (Produto.gtin_ean.ilike(f"%{termo}%"), 5),
            (Produto.codigos_barras_alternativos.ilike(f"%{termo}%"), 6),
        ]
    )
    return case(*condicoes, else_=9)


def _serialize_funcionario_pdv_produto(produto: Produto) -> dict:
    vendavel = (
        bool(produto.ativo)
        and produto.situacao is not False
        and produto.tipo_produto in ["SIMPLES", "VARIACAO", "KIT"]
    )
    return {
        "id": produto.id,
        "nome": produto.nome,
        "codigo": produto.codigo,
        "codigo_barras": produto.codigo_barras,
        "unidade": produto.unidade or "UN",
        "preco_venda": float(produto.preco_venda or 0),
        "estoque_atual": float(produto.estoque_atual or 0),
        "imagem_url": produto.imagem_principal,
        "tipo_produto": produto.tipo_produto,
        "tipo_kit": produto.tipo_kit,
        "vendavel": vendavel,
        "aviso": None if vendavel else "Produto nao vendavel no PDV.",
    }


def _normalizar_barcode_obrigatorio_funcionario_pdv(barcode: str) -> str:
    barcode_normalizado = (barcode or "").strip()
    if not barcode_normalizado:
        raise HTTPException(status_code=400, detail="Codigo de barras obrigatorio.")
    return barcode_normalizado


def _buscar_produto_pdv_por_barcode(
    db: Session, tenant_id: str, barcode: str
) -> Optional[Produto]:
    prioridade_estoque = case((func.coalesce(Produto.estoque_atual, 0) > 0, 0), else_=1)
    return (
        db.query(Produto)
        .filter(
            Produto.tenant_id == tenant_id,
            Produto.ativo == true(),
            Produto.situacao.is_not(False),
            Produto.tipo_produto.in_(["SIMPLES", "VARIACAO", "KIT"]),
            or_(*_barcode_filters_for_produto(barcode)),
        )
        .order_by(prioridade_estoque.asc(), Produto.nome.asc(), Produto.id.asc())
        .first()
    )


@router.get(
    "/funcionario/pdv/produtos/buscar",
    response_model=list[FuncionarioPdvProdutoResponse],
)
def buscar_produtos_funcionario_pdv(
    q: str = "",
    current_user: User = Depends(_get_current_ecommerce_user),
    db: Session = Depends(get_session),
):
    _funcionario, tenant_id = _get_funcionario_operacional_or_403(db, current_user)
    termo = (q or "").strip()
    if len(termo) < 2:
        return []

    filtros = _produto_busca_filtros_funcionario(termo)
    rank_busca = _produto_busca_rank_funcionario(termo)
    prioridade_estoque = case((func.coalesce(Produto.estoque_atual, 0) > 0, 0), else_=1)
    produtos = (
        db.query(Produto)
        .filter(
            Produto.tenant_id == tenant_id,
            Produto.ativo.is_(True),
            Produto.situacao.is_not(False),
            Produto.tipo_produto.in_(["SIMPLES", "VARIACAO", "KIT"]),
            or_(*filtros),
        )
        .order_by(rank_busca.asc(), prioridade_estoque.asc(), Produto.nome.asc())
        .limit(20)
        .all()
    )
    return [_serialize_funcionario_pdv_produto(produto) for produto in produtos]


@router.get(
    "/funcionario/pdv/produtos/barcode/{barcode}",
    response_model=FuncionarioPdvProdutoResponse,
)
def buscar_produto_funcionario_pdv_barcode(
    barcode: str,
    current_user: User = Depends(_get_current_ecommerce_user),
    db: Session = Depends(get_session),
):
    _funcionario, tenant_id = _get_funcionario_operacional_or_403(db, current_user)
    produto = _buscar_produto_pdv_por_barcode(
        db,
        tenant_id,
        _normalizar_barcode_obrigatorio_funcionario_pdv(barcode),
    )
    if not produto:
        raise HTTPException(
            status_code=404, detail="Produto ERP nao encontrado para este codigo."
        )
    return _serialize_funcionario_pdv_produto(produto)
