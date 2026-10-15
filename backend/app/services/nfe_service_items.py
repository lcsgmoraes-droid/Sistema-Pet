"""Limites do fluxo de mercadorias, sem alterar a natureza dos servicos."""

import unicodedata


def _campo(item, nome, default=None):
    return (
        item.get(nome, default)
        if isinstance(item, dict)
        else getattr(item, nome, default)
    )


def _normalizado(valor):
    texto = unicodedata.normalize("NFKD", str(valor or "").casefold())
    return " ".join("".join(c for c in texto if not unicodedata.combining(c)).split())


def bloqueio_item_servico(item, *, item_numero=None):
    """Um produto vinculado nao transforma uma linha de servico em mercadoria."""
    if _normalizado(_campo(item, "tipo")) != "servico":
        return None

    produto = _campo(item, "produto")
    descricao = (
        _campo(item, "servico_descricao")
        or _campo(item, "produto_nome")
        or getattr(produto, "nome", None)
        or "Servico"
    )
    taxa_entrega = _normalizado(descricao) in {"taxa de entrega", "taxa entrega"}
    return {
        "campo": "tipo_item",
        "item_id": _campo(item, "id"),
        "item_numero": item_numero,
        "produto_id": _campo(item, "produto_id") or getattr(produto, "id", None),
        "produto_nome": descricao,
        "codigo": "taxa_entrega_como_servico"
        if taxa_entrega
        else "servico_nao_suportado",
        "mensagem": (
            "A taxa de entrega foi lancada como servico. Revise o lancamento de entrega antes de emitir NF-e/NFC-e."
            if taxa_entrega
            else "O fluxo atual de NF-e/NFC-e emite somente mercadorias. Esta venda contem servico e precisa de revisao fiscal."
        ),
    }
