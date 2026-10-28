"""Classificacao comum de kits e variacoes com composicao nas vendas."""


def tipo_kit_estoque(produto):
    """Variacao sem composicao usa saldo proprio; KIT legado e virtual."""
    tipo_produto = getattr(produto, "tipo_produto", None)
    tipo_kit = getattr(produto, "tipo_kit", None)
    if tipo_produto == "KIT":
        return tipo_kit or "VIRTUAL"
    if tipo_produto == "VARIACAO" and tipo_kit:
        return tipo_kit
    return None
