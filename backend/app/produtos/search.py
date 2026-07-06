from __future__ import annotations

from typing import Optional

from sqlalchemy import case, func, or_

from app.produtos_models import Categoria, Departamento, Marca, Produto


PRODUTO_SKU_COLUMN = getattr(Produto, "sku", None)
PRODUTO_GTIN_COLUMNS = [
    column
    for column in [
        getattr(Produto, "gtin_ean", None),
        getattr(Produto, "gtin_ean_tributario", None),
    ]
    if column is not None
]
PRODUTO_EAN_ALTERNATIVO_COLUMN = getattr(Produto, "codigos_barras_alternativos", None)
PRODUTO_CODIGO_EXATO_COLUMNS = [
    column
    for column in [
        Produto.codigo,
        PRODUTO_SKU_COLUMN,
        Produto.codigo_barras,
        *PRODUTO_GTIN_COLUMNS,
    ]
    if column is not None
]
PRODUTO_EAN_SEARCH_COLUMNS = [
    column
    for column in [
        Produto.codigo_barras,
        *PRODUTO_GTIN_COLUMNS,
        PRODUTO_EAN_ALTERNATIVO_COLUMN,
    ]
    if column is not None
]


def _build_produto_search_order_clause(termo_busca: Optional[str]):
    """Prioriza codigo exato e prefixos quando houver busca."""
    termo = (termo_busca or "").strip()
    if not termo:
        return [Produto.created_at.desc()]

    termo_lower = termo.lower()
    contains_pattern = f"%{termo}%"
    prefix_pattern = f"{termo}%"
    order_cases = []
    prioridade = 1

    for column in PRODUTO_CODIGO_EXATO_COLUMNS:
        order_cases.append(
            (func.lower(func.coalesce(column, "")) == termo_lower, prioridade)
        )
        prioridade += 1

    if PRODUTO_EAN_ALTERNATIVO_COLUMN is not None:
        order_cases.append(
            (PRODUTO_EAN_ALTERNATIVO_COLUMN.ilike(contains_pattern), prioridade)
        )
        prioridade += 1

    digitos = _only_digits(termo)
    if (
        PRODUTO_EAN_ALTERNATIVO_COLUMN is not None
        and len(digitos) >= 4
        and _should_use_digit_fallback(termo)
    ):
        order_cases.append(
            (
                _digits_expr(PRODUTO_EAN_ALTERNATIVO_COLUMN).ilike(f"%{digitos}%"),
                prioridade,
            )
        )
        prioridade += 1

    order_cases.append(
        (func.lower(func.coalesce(Produto.nome, "")) == termo_lower, prioridade)
    )
    prioridade += 1

    for column in PRODUTO_CODIGO_EXATO_COLUMNS:
        order_cases.append((column.ilike(prefix_pattern), prioridade))
        prioridade += 1

    if PRODUTO_EAN_ALTERNATIVO_COLUMN is not None:
        order_cases.append(
            (PRODUTO_EAN_ALTERNATIVO_COLUMN.ilike(contains_pattern), prioridade)
        )
        prioridade += 1

    order_cases.append((Produto.nome.ilike(prefix_pattern), prioridade))
    prioridade += 1

    for column in PRODUTO_CODIGO_EXATO_COLUMNS:
        order_cases.append((column.ilike(contains_pattern), prioridade))
        prioridade += 1

    order_cases.append((Produto.nome.ilike(contains_pattern), prioridade))
    prioridade += 1

    return [
        case(*order_cases, else_=prioridade),
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
        *[
            _unaccent_ilike(column, busca_pattern)
            for column in PRODUTO_EAN_SEARCH_COLUMNS
        ],
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
                *[
                    _digits_expr(column).ilike(digitos_pattern)
                    for column in PRODUTO_EAN_SEARCH_COLUMNS
                ],
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
        *[
            column.ilike(prefix_pattern)
            for column in PRODUTO_EAN_SEARCH_COLUMNS
            if column is not PRODUTO_EAN_ALTERNATIVO_COLUMN
        ],
        Produto.nome.ilike(contains_pattern),
    ]

    if PRODUTO_SKU_COLUMN is not None:
        conditions.append(PRODUTO_SKU_COLUMN.ilike(prefix_pattern))

    if PRODUTO_EAN_ALTERNATIVO_COLUMN is not None:
        conditions.append(PRODUTO_EAN_ALTERNATIVO_COLUMN.ilike(contains_pattern))

    digitos = _only_digits(termo)
    if len(digitos) >= 4 and _should_use_digit_fallback(termo):
        digits_prefix = f"{digitos}%"
        digits_contains = f"%{digitos}%"
        conditions.extend(
            [
                Produto.codigo == termo,
                *[
                    column == termo
                    for column in PRODUTO_EAN_SEARCH_COLUMNS
                    if column is not PRODUTO_EAN_ALTERNATIVO_COLUMN
                ],
                _digits_expr(Produto.codigo).like(digits_prefix),
                *[
                    _digits_expr(column).like(digits_prefix)
                    for column in PRODUTO_EAN_SEARCH_COLUMNS
                    if column is not PRODUTO_EAN_ALTERNATIVO_COLUMN
                ],
            ]
        )
        if PRODUTO_EAN_ALTERNATIVO_COLUMN is not None:
            conditions.append(
                _digits_expr(PRODUTO_EAN_ALTERNATIVO_COLUMN).like(digits_contains)
            )
        if PRODUTO_SKU_COLUMN is not None:
            conditions.extend(
                [
                    PRODUTO_SKU_COLUMN == termo,
                    _digits_expr(PRODUTO_SKU_COLUMN).like(digits_prefix),
                ]
            )

    return or_(*conditions)
