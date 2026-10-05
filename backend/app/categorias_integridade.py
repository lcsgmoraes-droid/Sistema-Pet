"""Regras de integridade compartilhadas pelos cadastros de categorias."""

import re
import unicodedata


def normalizar_nome_categoria(nome: str) -> str:
    """Compara nomes sem diferenciar acentos, caixa ou espaços repetidos."""
    texto = unicodedata.normalize("NFKD", str(nome or "").strip().casefold())
    texto = "".join(letra for letra in texto if not unicodedata.combining(letra))
    return re.sub(r"\s+", " ", texto)
