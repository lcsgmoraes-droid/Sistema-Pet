"""normalize corrupted financial text accents

Revision ID: mn20260503a1
Revises: mm20260502a1
Create Date: 2026-05-03 00:00:00.000000
"""

from alembic import op


revision = "mn20260503a1"
down_revision = "mm20260502a1"
branch_labels = None
depends_on = None


REPLACEMENTS = (
    ("Jo??o", "João"),
    ("jo??o", "joão"),
    ("f??rias", "férias"),
    ("F??rias", "Férias"),
    ("Sal??rio", "Salário"),
    ("sal??rio", "salário"),
    ("13??", "13º"),
    ("1??", "1ª"),
    ("2??", "2ª"),
    ("Provis??o", "Provisão"),
    ("provis??o", "provisão"),
    ("cont??bil", "contábil"),
    ("Energia El??trica", "Energia Elétrica"),
    ("??gua", "Água"),
    ("Alimenta????o", "Alimentação"),
    ("Servi??os", "Serviços"),
    ("Veterin??rias", "Veterinárias"),
    ("Arrecada????o", "Arrecadação"),
    ("ter??o", "terço"),
)


TEXT_COLUMNS_BY_TABLE = {
    "clientes": (
        "nome",
        "razao_social",
        "nome_fantasia",
        "responsavel",
        "parceiro_observacoes",
        "endereco",
        "endereco_entrega",
        "endereco_entrega_2",
        "observacoes",
    ),
    "contas_pagar": (
        "descricao",
        "documento",
        "observacoes",
    ),
    "categorias_financeiras": (
        "nome",
        "descricao",
    ),
}


def _quote_identifier(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'


def _literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def _replace_expression(column_sql: str) -> str:
    expression = column_sql
    for wrong, right in REPLACEMENTS:
        expression = f"replace({expression}, {_literal(wrong)}, {_literal(right)})"
    return expression


def _normalize_column(table_name: str, column_name: str) -> None:
    table_sql = _quote_identifier(table_name)
    column_sql = _quote_identifier(column_name)
    expression = _replace_expression(column_sql)
    predicates = [
        f"{column_sql} LIKE {_literal('%' + wrong + '%')}"
        for wrong, _right in REPLACEMENTS
    ]
    op.execute(
        f"""
        UPDATE {table_sql}
           SET {column_sql} = {expression}
         WHERE {column_sql} IS NOT NULL
           AND ({" OR ".join(predicates)})
        """
    )


def upgrade() -> None:
    for table_name, column_names in TEXT_COLUMNS_BY_TABLE.items():
        for column_name in column_names:
            _normalize_column(table_name, column_name)

    op.execute(
        """
        COMMENT ON COLUMN contas_pagar.dre_subcategoria_id IS
        'ID da subcategoria DRE (fonte da verdade contábil)'
        """
    )


def downgrade() -> None:
    # Data cleanup is intentionally not reverted.
    pass
