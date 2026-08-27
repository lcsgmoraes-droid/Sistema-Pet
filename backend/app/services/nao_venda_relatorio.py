"""Totalizadores do relatório de atendimentos sem venda."""

from __future__ import annotations

from collections import defaultdict
from decimal import Decimal
from typing import Any, Iterable

from app.nao_venda_constants import MOTIVOS_NAO_VENDA

SEM_FORNECEDOR = "Sem fornecedor informado"
SEM_MARCA = "Sem marca informada"
SEM_SKU = "Produto não cadastrado"


def _numero(valor: Any, casas: int = 4) -> float:
    return round(float(valor or 0), casas)


def _dinheiro(valor: Any) -> float:
    return round(float(valor or 0), 2)


def _texto(valor: Any) -> str:
    return str(valor or "").strip()


def _chave_texto(valor: Any) -> str:
    return _texto(valor).casefold()


def _chave_cliente(registro: Any) -> tuple[str, Any] | None:
    cliente_id = getattr(registro, "cliente_id", None)
    if cliente_id:
        return ("id", cliente_id)

    telefone = "".join(
        caractere
        for caractere in _texto(getattr(registro, "cliente_telefone", None))
        if caractere.isdigit()
    )
    if telefone:
        return ("telefone", telefone)

    nome = _chave_texto(getattr(registro, "cliente_nome", None))
    return ("nome", nome) if nome else None


def _valor_item(item: Any) -> Decimal:
    quantidade = Decimal(str(getattr(item, "quantidade", 0) or 0))
    unitario = Decimal(str(getattr(item, "valor_unitario_estimado", 0) or 0))
    return quantidade * unitario


def montar_relatorio_nao_vendas(registros: Iterable[Any]) -> dict[str, Any]:
    """Monta indicadores, motivos, demanda por produto e detalhes dos atendimentos."""
    registros_lista = list(registros)
    clientes_distintos: set[tuple[str, Any]] = set()
    atendimentos_identificados = 0
    total_itens = 0
    quantidade_total = Decimal("0")
    valor_total = Decimal("0")
    motivos: dict[str, dict[str, Any]] = {}
    produtos: dict[Any, dict[str, Any]] = {}
    detalhes: list[dict[str, Any]] = []

    for registro in registros_lista:
        registro_id = getattr(registro, "id", None)
        chave_cliente = _chave_cliente(registro)
        if chave_cliente:
            atendimentos_identificados += 1
            clientes_distintos.add(chave_cliente)

        itens = list(getattr(registro, "itens", None) or [])
        valor_registro = getattr(registro, "valor_estimado_total", None)
        if valor_registro is None:
            valor_registro = sum((_valor_item(item) for item in itens), Decimal("0"))
        valor_registro = Decimal(str(valor_registro or 0))
        valor_total += valor_registro

        motivo_codigo = _texto(getattr(registro, "motivo", None)) or "outro"
        motivo = motivos.setdefault(
            motivo_codigo,
            {
                "codigo": motivo_codigo,
                "motivo": MOTIVOS_NAO_VENDA.get(motivo_codigo, "Outro motivo"),
                "total_atendimentos": 0,
                "valor_estimado_total": 0.0,
            },
        )
        motivo["total_atendimentos"] += 1
        motivo["valor_estimado_total"] = _dinheiro(
            Decimal(str(motivo["valor_estimado_total"])) + valor_registro
        )

        itens_detalhe: list[dict[str, Any]] = []
        for item in itens:
            total_itens += 1
            quantidade = Decimal(str(getattr(item, "quantidade", 0) or 0))
            valor_item = _valor_item(item)
            quantidade_total += quantidade

            produto_id = getattr(item, "produto_id", None)
            produto_nome = (
                _texto(getattr(item, "produto_nome", None)) or "Produto sem nome"
            )
            sku = _texto(getattr(item, "sku", None)) or SEM_SKU
            marca = _texto(getattr(item, "marca_nome", None)) or SEM_MARCA
            fornecedor = (
                _texto(getattr(item, "fornecedor_nome", None)) or SEM_FORNECEDOR
            )
            chave_produto = produto_id or (
                _chave_texto(fornecedor),
                _chave_texto(marca),
                _chave_texto(sku),
                _chave_texto(produto_nome),
            )

            produto = produtos.setdefault(
                chave_produto,
                {
                    "produto_id": produto_id,
                    "sku": sku,
                    "produto_nome": produto_nome,
                    "marca": marca,
                    "fornecedor": fornecedor,
                    "total_solicitacoes": 0,
                    "quantidade_total": 0.0,
                    "valor_estimado_total": 0.0,
                    "_atendimentos": set(),
                    "_clientes": set(),
                },
            )
            produto["total_solicitacoes"] += 1
            produto["quantidade_total"] = _numero(
                Decimal(str(produto["quantidade_total"])) + quantidade
            )
            produto["valor_estimado_total"] = _dinheiro(
                Decimal(str(produto["valor_estimado_total"])) + valor_item
            )
            produto["_atendimentos"].add(registro_id)
            if chave_cliente:
                produto["_clientes"].add(chave_cliente)

            itens_detalhe.append(
                {
                    "item_id": getattr(item, "id", None),
                    "produto_id": produto_id,
                    "sku": sku,
                    "produto_nome": produto_nome,
                    "marca": marca,
                    "fornecedor": fornecedor,
                    "quantidade": _numero(quantidade),
                    "valor_unitario_estimado": (
                        _dinheiro(getattr(item, "valor_unitario_estimado", None))
                        if getattr(item, "valor_unitario_estimado", None) is not None
                        else None
                    ),
                    "valor_estimado_total": _dinheiro(valor_item),
                    "adicionado_lista_espera": bool(
                        getattr(item, "adicionado_lista_espera", False)
                    ),
                }
            )

        usuario = getattr(registro, "usuario_registrou", None)
        criado_em = getattr(registro, "created_at", None)
        detalhes.append(
            {
                "registro_id": registro_id,
                "data_registro": criado_em.isoformat() if criado_em else None,
                "cliente_id": getattr(registro, "cliente_id", None),
                "cliente_nome": _texto(getattr(registro, "cliente_nome", None))
                or "Cliente não identificado",
                "cliente_telefone": _texto(getattr(registro, "cliente_telefone", None))
                or None,
                "motivo_codigo": motivo_codigo,
                "motivo": MOTIVOS_NAO_VENDA.get(motivo_codigo, "Outro motivo"),
                "observacoes": getattr(registro, "observacoes", None),
                "valor_estimado_total": _dinheiro(valor_registro),
                "usuario_registrou": _texto(getattr(usuario, "nome", None))
                or _texto(getattr(usuario, "email", None))
                or "Usuário não identificado",
                "itens": itens_detalhe,
            }
        )

    total_atendimentos = len(registros_lista)
    motivos_lista = sorted(
        motivos.values(),
        key=lambda item: (-item["total_atendimentos"], _chave_texto(item["motivo"])),
    )
    for motivo in motivos_lista:
        motivo["percentual"] = (
            round(motivo["total_atendimentos"] * 100 / total_atendimentos, 1)
            if total_atendimentos
            else 0.0
        )

    produtos_lista: list[dict[str, Any]] = []
    for produto in produtos.values():
        produto["total_atendimentos"] = len(produto.pop("_atendimentos"))
        produto["total_clientes_identificados"] = len(produto.pop("_clientes"))
        produtos_lista.append(produto)

    produtos_lista.sort(
        key=lambda item: (
            _chave_texto(item["fornecedor"]),
            _chave_texto(item["marca"]),
            _chave_texto(item["produto_nome"]),
        )
    )
    detalhes.sort(key=lambda item: item["data_registro"] or "", reverse=True)

    fornecedores: dict[str, dict[str, Any]] = defaultdict(
        lambda: {
            "produtos": [],
            "quantidade_total": 0.0,
            "valor_estimado_total": 0.0,
            "marcas": defaultdict(
                lambda: {
                    "produtos": [],
                    "quantidade_total": 0.0,
                    "valor_estimado_total": 0.0,
                }
            ),
        }
    )
    for produto in produtos_lista:
        fornecedor = fornecedores[produto["fornecedor"]]
        fornecedor["produtos"].append(produto)
        fornecedor["quantidade_total"] += produto["quantidade_total"]
        fornecedor["valor_estimado_total"] += produto["valor_estimado_total"]

        marca = fornecedor["marcas"][produto["marca"]]
        marca["produtos"].append(produto)
        marca["quantidade_total"] += produto["quantidade_total"]
        marca["valor_estimado_total"] += produto["valor_estimado_total"]

    agrupado = []
    for fornecedor_nome, fornecedor in sorted(
        fornecedores.items(), key=lambda item: _chave_texto(item[0])
    ):
        marcas = []
        for marca_nome, marca in sorted(
            fornecedor["marcas"].items(), key=lambda item: _chave_texto(item[0])
        ):
            marcas.append(
                {
                    "marca": marca_nome,
                    "total_produtos": len(marca["produtos"]),
                    "quantidade_total": _numero(marca["quantidade_total"]),
                    "valor_estimado_total": _dinheiro(marca["valor_estimado_total"]),
                    "produtos": marca["produtos"],
                }
            )
        agrupado.append(
            {
                "fornecedor": fornecedor_nome,
                "total_produtos": len(fornecedor["produtos"]),
                "quantidade_total": _numero(fornecedor["quantidade_total"]),
                "valor_estimado_total": _dinheiro(fornecedor["valor_estimado_total"]),
                "marcas": marcas,
            }
        )

    return {
        "resumo": {
            "total_atendimentos": total_atendimentos,
            "atendimentos_identificados": atendimentos_identificados,
            "clientes_identificados_distintos": len(clientes_distintos),
            "atendimentos_anonimos": total_atendimentos - atendimentos_identificados,
            "total_itens": total_itens,
            "total_produtos_distintos": len(produtos_lista),
            "quantidade_total": _numero(quantidade_total),
            "valor_estimado_total": _dinheiro(valor_total),
        },
        "motivos": motivos_lista,
        "produtos": produtos_lista,
        "agrupado_por_fornecedor": agrupado,
        "detalhes": detalhes,
    }
