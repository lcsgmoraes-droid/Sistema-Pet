from __future__ import annotations

from typing import Any, Iterable


def _serializar_lote_consumido(lote: Any, quantidade_consumida: Any) -> dict[str, Any]:
    data_validade = getattr(lote, "data_validade", None)
    return {
        "lote_id": lote.id,
        "nome_lote": lote.nome_lote,
        "quantidade_consumida": quantidade_consumida,
        "data_validade": data_validade.isoformat() if data_validade else None,
    }


def _consumir_lotes_fifo_produto(lotes: Iterable[Any], quantidade: Any) -> list[dict[str, Any]]:
    """Consome lotes na ordem recebida preservando o payload legado da rota FIFO."""
    quantidade_restante = quantidade
    lotes_consumidos: list[dict[str, Any]] = []

    for lote in lotes:
        if quantidade_restante <= 0:
            break

        if lote.quantidade_disponivel >= quantidade_restante:
            lote.quantidade_disponivel -= quantidade_restante
            lotes_consumidos.append(
                _serializar_lote_consumido(lote, quantidade_restante)
            )
            quantidade_restante = 0
        else:
            quantidade_consumida = lote.quantidade_disponivel
            lotes_consumidos.append(
                _serializar_lote_consumido(lote, quantidade_consumida)
            )
            quantidade_restante -= quantidade_consumida
            lote.quantidade_disponivel = 0

    return lotes_consumidos
