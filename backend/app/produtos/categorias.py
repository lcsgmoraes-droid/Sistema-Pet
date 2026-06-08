from __future__ import annotations

from typing import Any


def _calcular_niveis_categorias(categoria_por_id: dict[int, Any]) -> dict[int, int]:
    niveis_cache: dict[int, int] = {}

    def calcular_nivel(categoria_id: int) -> int:
        nivel_cache = niveis_cache.get(categoria_id)
        if nivel_cache is not None:
            return nivel_cache

        nivel = 1
        atual = categoria_por_id.get(categoria_id)
        visitados = set()

        while atual and atual.categoria_pai_id and atual.categoria_pai_id not in visitados:
            visitados.add(atual.id)
            nivel += 1
            atual = categoria_por_id.get(atual.categoria_pai_id)

        niveis_cache[categoria_id] = nivel
        return nivel

    return {categoria_id: calcular_nivel(categoria_id) for categoria_id in categoria_por_id}


def _construir_arvore_categorias(categorias: list[Any], pai_id=None) -> list[dict[str, Any]]:
    resultado = []
    for categoria in categorias:
        if categoria.categoria_pai_id == pai_id:
            resultado.append(
                {
                    "id": categoria.id,
                    "nome": categoria.nome,
                    "descricao": categoria.descricao,
                    "icone": categoria.icone,
                    "cor": categoria.cor,
                    "ordem": categoria.ordem,
                    "subcategorias": _construir_arvore_categorias(categorias, categoria.id),
                }
            )
    return resultado
