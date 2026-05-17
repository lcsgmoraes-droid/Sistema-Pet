from __future__ import annotations

from typing import Optional

from sqlalchemy import case, func, or_

from app.produtos_models import Categoria, Departamento, Marca, Produto


PRODUTO_SKU_COLUMN = getattr(Produto, "sku", None)


def _build_produto_search_order_clause(termo_busca: Optional[str]):
    """Prioriza codigo exato e prefixos quando houver busca."""
    termo = (termo_busca or "").strip()
    if not termo:
        return [Produto.created_at.desc()]

    termo_lower = termo.lower()
    if PRODUTO_SKU_COLUMN is None:
        return [
            case(
                (func.lower(func.coalesce(Produto.codigo, "")) == termo_lower, 1),
                (func.lower(func.coalesce(Produto.codigo_barras, "")) == termo_lower, 2),
                (func.lower(func.coalesce(Produto.nome, "")) == termo_lower, 3),
                (Produto.codigo.ilike(f"{termo}%"), 4),
                (Produto.codigo_barras.ilike(f"{termo}%"), 5),
                (Produto.nome.ilike(f"{termo}%"), 6),
                (Produto.codigo.ilike(f"%{termo}%"), 7),
                (Produto.codigo_barras.ilike(f"%{termo}%"), 8),
                (Produto.nome.ilike(f"%{termo}%"), 9),
                else_=10,
            ),
            Produto.nome.asc(),
            Produto.created_at.desc(),
        ]

    return [
        case(
            (func.lower(func.coalesce(Produto.codigo, "")) == termo_lower, 1),
            (func.lower(func.coalesce(PRODUTO_SKU_COLUMN, "")) == termo_lower, 2),
            (func.lower(func.coalesce(Produto.codigo_barras, "")) == termo_lower, 3),
            (func.lower(func.coalesce(Produto.nome, "")) == termo_lower, 4),
            (Produto.codigo.ilike(f"{termo}%"), 5),
            (PRODUTO_SKU_COLUMN.ilike(f"{termo}%"), 6),
            (Produto.codigo_barras.ilike(f"{termo}%"), 7),
            (Produto.nome.ilike(f"{termo}%"), 8),
            (Produto.codigo.ilike(f"%{termo}%"), 9),
            (PRODUTO_SKU_COLUMN.ilike(f"%{termo}%"), 10),
            (Produto.codigo_barras.ilike(f"%{termo}%"), 11),
            (Produto.nome.ilike(f"%{termo}%"), 12),
            else_=13,
        ),
        Produto.nome.asc(),
        Produto.created_at.desc(),
    ]


def _only_digits(value: Optional[str]) -> str:
    return "".join(ch for ch in str(value or "") if ch.isdigit())


def _should_use_digit_fallback(value: Optional[str]) -> bool:
    termo = str(value or "").strip()
    return bool(termo) and not any(ch.isalpha() for ch in termo)


def _digits_expr(column):
    return func.regexp_replace(func.coalesce(column, ""), "[^0-9]", "", "g")


def _unaccent_text(column):
    return func.unaccent(func.coalesce(column, ""))


def _unaccent_ilike(column, pattern: str):
    return _unaccent_text(column).ilike(func.unaccent(pattern))


def _produto_search_conditions(palavra: str):
    """Busca por texto e tambem por codigos numericos normalizados."""
    termo = (palavra or "").strip()
    busca_pattern = f"%{termo}%"
    conditions = [
        _unaccent_ilike(Produto.nome, busca_pattern),
        _unaccent_ilike(Produto.codigo, busca_pattern),
        _unaccent_ilike(Produto.codigo_barras, busca_pattern),
        Produto.marca.has(_unaccent_ilike(Marca.nome, busca_pattern)),
        Produto.categoria.has(_unaccent_ilike(Categoria.nome, busca_pattern)),
        Produto.departamento.has(_unaccent_ilike(Departamento.nome, busca_pattern)),
    ]

    if PRODUTO_SKU_COLUMN is not None:
        conditions.append(_unaccent_ilike(PRODUTO_SKU_COLUMN, busca_pattern))

    digitos = _only_digits(termo)
    if len(digitos) >= 4 and _should_use_digit_fallback(termo):
        digitos_pattern = f"%{digitos}%"
        conditions.extend(
            [
                _digits_expr(Produto.codigo).ilike(digitos_pattern),
                _digits_expr(Produto.codigo_barras).ilike(digitos_pattern),
            ]
        )

        if PRODUTO_SKU_COLUMN is not None:
            conditions.append(_digits_expr(PRODUTO_SKU_COLUMN).ilike(digitos_pattern))

    return or_(*conditions)


def _produto_search_conditions_fast(palavra: str):
    """Busca leve para PDV/autocomplete, sem unaccent nem joins por tecla."""
    termo = (palavra or "").strip()
    if not termo:
        return True

    prefix_pattern = f"{termo}%"
    contains_pattern = f"%{termo}%"
    conditions = [
        Produto.codigo.ilike(prefix_pattern),
        Produto.codigo_barras.ilike(prefix_pattern),
        Produto.nome.ilike(contains_pattern),
    ]

    if PRODUTO_SKU_COLUMN is not None:
        conditions.append(PRODUTO_SKU_COLUMN.ilike(prefix_pattern))

    digitos = _only_digits(termo)
    if len(digitos) >= 4 and _should_use_digit_fallback(termo):
        digits_prefix = f"{digitos}%"
        conditions.extend(
            [
                Produto.codigo == termo,
                Produto.codigo_barras == termo,
                _digits_expr(Produto.codigo).like(digits_prefix),
                _digits_expr(Produto.codigo_barras).like(digits_prefix),
            ]
        )
        if PRODUTO_SKU_COLUMN is not None:
            conditions.extend(
                [
                    PRODUTO_SKU_COLUMN == termo,
                    _digits_expr(PRODUTO_SKU_COLUMN).like(digits_prefix),
                ]
            )

    return or_(*conditions)

