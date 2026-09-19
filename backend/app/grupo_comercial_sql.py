"""Expressões SQL compatíveis com IDs de empresa UUID e VARCHAR legado."""

from sqlalchemy import String, cast, func


def empresa_id_sql(coluna):
    """Normaliza uma coluna de empresa para comparação entre esquemas históricos."""
    return func.replace(cast(coluna, String), "-", "")


def empresa_id_igual(coluna, value):
    return empresa_id_sql(coluna) == str(value).replace("-", "")
