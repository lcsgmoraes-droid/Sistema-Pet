"""Ajudantes para nao gravar dados pessoais do tutor nos logs."""


def mascarar_telefone(valor) -> str:
    """Mostra so os 4 ultimos digitos: 5511999998888 -> *********8888.

    Identificadores internos do WhatsApp (@lid) mantem o sufixo.
    """
    texto = str(valor or "")
    digitos = "".join(c for c in texto if c.isdigit())
    mascarado = "****" if len(digitos) <= 4 else "*" * (len(digitos) - 4) + digitos[-4:]
    return f"{mascarado}@lid" if "@lid" in texto else mascarado
