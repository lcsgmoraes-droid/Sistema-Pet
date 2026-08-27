"""Montagem do relatorio operacional da lista de espera de estoque."""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Iterable

SEM_FORNECEDOR = "Sem fornecedor"
SEM_MARCA = "Sem marca"


def _nome_fornecedor(fornecedor: Any) -> str:
    if not fornecedor:
        return SEM_FORNECEDOR
    return (
        getattr(fornecedor, "nome_fantasia", None)
        or getattr(fornecedor, "razao_social", None)
        or getattr(fornecedor, "nome", None)
        or SEM_FORNECEDOR
    )


def _nome_marca(produto: Any) -> str:
    marca = getattr(produto, "marca", None)
    return getattr(marca, "nome", None) or SEM_MARCA


def _quantidade(valor: Any) -> float:
    return round(float(valor or 0), 4)


def _chave_texto(valor: Any) -> str:
    return str(valor or "").casefold()


def montar_relatorio_lista_espera(pendencias: Iterable[Any]) -> dict[str, Any]:
    """Gera totais por SKU e detalhes cliente x produto para a lista ativa."""
    detalhes: list[dict[str, Any]] = []
    produtos: dict[Any, dict[str, Any]] = {}
    clientes_gerais: set[Any] = set()

    for pendencia in pendencias:
        produto = getattr(pendencia, "produto", None)
        cliente = getattr(pendencia, "cliente", None)
        if not produto or not cliente:
            continue

        produto_id = getattr(produto, "id", None)
        cliente_id = getattr(cliente, "id", None)
        marca = _nome_marca(produto)
        fornecedor = _nome_fornecedor(getattr(produto, "fornecedor", None))
        quantidade = _quantidade(getattr(pendencia, "quantidade_desejada", 0))
        chave_produto = produto_id or (
            getattr(produto, "codigo", None),
            getattr(produto, "nome", None),
        )

        clientes_gerais.add(cliente_id)
        if chave_produto not in produtos:
            produtos[chave_produto] = {
                "produto_id": produto_id,
                "sku": getattr(produto, "codigo", None) or "Sem SKU",
                "produto_nome": getattr(produto, "nome", None) or "Produto sem nome",
                "marca": marca,
                "fornecedor": fornecedor,
                "total_registros": 0,
                "quantidade_total": 0.0,
                "_clientes": set(),
            }

        totalizador = produtos[chave_produto]
        totalizador["total_registros"] += 1
        totalizador["quantidade_total"] = _quantidade(
            totalizador["quantidade_total"] + quantidade
        )
        totalizador["_clientes"].add(cliente_id)

        data_registro = getattr(pendencia, "data_registro", None)
        detalhes.append(
            {
                "pendencia_id": getattr(pendencia, "id", None),
                "cliente_id": cliente_id,
                "cliente_nome": getattr(cliente, "nome", None) or "Cliente sem nome",
                "cliente_telefone": getattr(cliente, "celular", None)
                or getattr(cliente, "telefone", None),
                "produto_id": produto_id,
                "sku": getattr(produto, "codigo", None) or "Sem SKU",
                "produto_nome": getattr(produto, "nome", None) or "Produto sem nome",
                "marca": marca,
                "fornecedor": fornecedor,
                "quantidade_desejada": quantidade,
                "status": getattr(pendencia, "status", None),
                "prioridade": int(getattr(pendencia, "prioridade", 0) or 0),
                "data_registro": data_registro.isoformat() if data_registro else None,
            }
        )

    produtos_lista: list[dict[str, Any]] = []
    for totalizador in produtos.values():
        clientes = totalizador.pop("_clientes")
        totalizador["total_clientes"] = len(clientes)
        totalizador["_clientes_ids"] = clientes
        produtos_lista.append(totalizador)

    produtos_lista.sort(
        key=lambda item: (
            _chave_texto(item["fornecedor"]),
            _chave_texto(item["marca"]),
            _chave_texto(item["produto_nome"]),
            _chave_texto(item["sku"]),
        )
    )
    detalhes.sort(
        key=lambda item: (
            _chave_texto(item["fornecedor"]),
            _chave_texto(item["marca"]),
            _chave_texto(item["produto_nome"]),
            _chave_texto(item["cliente_nome"]),
        )
    )

    fornecedores: dict[str, dict[str, Any]] = defaultdict(
        lambda: {
            "produtos": [],
            "clientes": set(),
            "quantidade_total": 0.0,
            "marcas": defaultdict(
                lambda: {
                    "produtos": [],
                    "clientes": set(),
                    "quantidade_total": 0.0,
                }
            ),
        }
    )

    for produto in produtos_lista:
        grupo_fornecedor = fornecedores[produto["fornecedor"]]
        grupo_fornecedor["produtos"].append(produto)
        grupo_fornecedor["clientes"].update(produto["_clientes_ids"])
        grupo_fornecedor["quantidade_total"] += produto["quantidade_total"]

        grupo_marca = grupo_fornecedor["marcas"][produto["marca"]]
        grupo_marca["produtos"].append(produto)
        grupo_marca["clientes"].update(produto["_clientes_ids"])
        grupo_marca["quantidade_total"] += produto["quantidade_total"]

    agrupado_por_fornecedor = []
    for fornecedor, dados_fornecedor in sorted(
        fornecedores.items(), key=lambda item: _chave_texto(item[0])
    ):
        marcas = []
        for marca, dados_marca in sorted(
            dados_fornecedor["marcas"].items(), key=lambda item: _chave_texto(item[0])
        ):
            produtos_marca = []
            for produto in dados_marca["produtos"]:
                produtos_marca.append(
                    {
                        chave: valor
                        for chave, valor in produto.items()
                        if not chave.startswith("_")
                    }
                )
            marcas.append(
                {
                    "marca": marca,
                    "total_skus": len(produtos_marca),
                    "total_clientes": len(dados_marca["clientes"]),
                    "quantidade_total": _quantidade(dados_marca["quantidade_total"]),
                    "produtos": produtos_marca,
                }
            )

        agrupado_por_fornecedor.append(
            {
                "fornecedor": fornecedor,
                "total_skus": len(dados_fornecedor["produtos"]),
                "total_clientes": len(dados_fornecedor["clientes"]),
                "quantidade_total": _quantidade(dados_fornecedor["quantidade_total"]),
                "marcas": marcas,
            }
        )

    produtos_publicos = [
        {chave: valor for chave, valor in produto.items() if not chave.startswith("_")}
        for produto in produtos_lista
    ]
    return {
        "resumo": {
            "total_registros": len(detalhes),
            "total_clientes": len(clientes_gerais),
            "total_skus": len(produtos_publicos),
            "quantidade_total": _quantidade(
                sum(item["quantidade_total"] for item in produtos_publicos)
            ),
        },
        "produtos": produtos_publicos,
        "agrupado_por_fornecedor": agrupado_por_fornecedor,
        "detalhes": detalhes,
    }
