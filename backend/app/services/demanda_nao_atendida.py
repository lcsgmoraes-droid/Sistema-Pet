"""Consolida a demanda que nao virou venda nos canais da loja."""

from __future__ import annotations

import unicodedata
from datetime import datetime
from decimal import Decimal
from typing import Any, Iterable

from app.services.ecommerce_catalog_health import classify_catalog_product


def _texto(valor: Any) -> str:
    return str(valor or "").strip()


def _normalizar(valor: Any) -> str:
    texto = unicodedata.normalize("NFKD", _texto(valor).casefold())
    sem_acentos = "".join(
        char for char in texto if not unicodedata.combining(char)
    )
    return " ".join(sem_acentos.split())


def _numero(valor: Any, casas: int = 4) -> float:
    return round(float(valor or 0), casas)


def _dinheiro(valor: Any) -> float:
    return round(float(valor or 0), 2)


def _data_iso(valor: Any) -> str | None:
    return valor.isoformat() if isinstance(valor, datetime) else None


def _data_ordem(valor: Any) -> float:
    if not isinstance(valor, datetime):
        return 0.0
    try:
        return valor.timestamp()
    except (OSError, OverflowError, ValueError):
        return 0.0


def _chave_cliente(registro: Any) -> tuple[str, Any] | None:
    cliente_id = getattr(registro, "cliente_id", None)
    if cliente_id:
        return ("id", int(cliente_id))
    telefone = "".join(
        char
        for char in _texto(getattr(registro, "cliente_telefone", None))
        if char.isdigit()
    )
    if telefone:
        return ("telefone", telefone)
    nome = _normalizar(getattr(registro, "cliente_nome", None))
    return ("nome", nome) if nome else None


def _chave_produto_livre(item: Any) -> tuple[str, str, str, str]:
    return (
        _normalizar(getattr(item, "produto_nome", None)),
        _normalizar(getattr(item, "sku", None)),
        _normalizar(getattr(item, "marca_nome", None)),
        _normalizar(getattr(item, "fornecedor_nome", None)),
    )


def _novo_item(*, produto_id: int | None, item: Any = None) -> dict[str, Any]:
    return {
        "produto_id": produto_id,
        "cadastrado": produto_id is not None,
        "produto_nome": _texto(getattr(item, "produto_nome", None))
        or "Produto sem nome",
        "sku": _texto(getattr(item, "sku", None)) or None,
        "marca": _texto(getattr(item, "marca_nome", None)) or None,
        "fornecedor": _texto(getattr(item, "fornecedor_nome", None)) or None,
        "procuras_pdv": 0,
        "atendimentos_pdv": 0,
        "pessoas_identificadas_pdv": 0,
        "procuras_anonimas_pdv": 0,
        "quantidade_procurada": 0.0,
        "valor_estimado_oportunidade": 0.0,
        "aguardando_pdv": 0,
        "aguardando_ecommerce": 0,
        "aguardando_total": 0,
        "quantidade_aguardada_pdv": 0.0,
        "primeira_demanda_em": None,
        "ultima_demanda_em": None,
        "ecommerce": None,
        "_atendimentos": set(),
        "_clientes_pdv": set(),
        "_espera_pdv": set(),
        "_espera_ecommerce": set(),
        "_primeira_ordem": 0.0,
        "_ultima_ordem": 0.0,
    }


def _registrar_data(item: dict[str, Any], data: Any) -> None:
    ordem = _data_ordem(data)
    if not ordem:
        return
    if not item["_primeira_ordem"] or ordem < item["_primeira_ordem"]:
        item["_primeira_ordem"] = ordem
        item["primeira_demanda_em"] = _data_iso(data)
    if ordem > item["_ultima_ordem"]:
        item["_ultima_ordem"] = ordem
        item["ultima_demanda_em"] = _data_iso(data)


def _nome_fornecedor(produto: Any) -> str | None:
    fornecedor = getattr(produto, "fornecedor", None)
    for campo in ("nome_fantasia", "razao_social", "nome"):
        valor = _texto(getattr(fornecedor, campo, None))
        if valor:
            return valor
    return None


def montar_central_demanda_nao_atendida(
    *,
    registros_pdv: Iterable[Any],
    pendencias_pdv: Iterable[Any],
    avisos_ecommerce: Iterable[Any],
    produtos: Iterable[Any],
    tenant: Any,
    busca: str | None = None,
    origem: str = "todos",
    situacao: str = "todos",
) -> dict[str, Any]:
    """Une procuras do PDV e listas de espera sem misturar seus significados."""
    registros = list(registros_pdv or [])
    pendencias = list(pendencias_pdv or [])
    avisos = list(avisos_ecommerce or [])
    produtos_por_id = {int(produto.id): produto for produto in (produtos or [])}
    consolidados: dict[tuple[Any, ...], dict[str, Any]] = {}
    atendimentos_globais: set[int] = set()
    clientes_pdv_globais: set[tuple[str, Any]] = set()
    espera_pdv_global: set[int] = set()
    espera_ecommerce_global: set[str] = set()
    inscricoes_pdv: set[tuple[int, int]] = set()
    inscricoes_ecommerce: set[tuple[int, str]] = set()

    for registro in registros:
        registro_id = getattr(registro, "id", None)
        if registro_id is not None:
            atendimentos_globais.add(int(registro_id))
        cliente = _chave_cliente(registro)
        if cliente:
            clientes_pdv_globais.add(cliente)
        for item_origem in list(getattr(registro, "itens", None) or []):
            produto_id_raw = getattr(item_origem, "produto_id", None)
            produto_id = int(produto_id_raw) if produto_id_raw is not None else None
            chave = ("produto", produto_id) if produto_id is not None else (
                "livre",
                *_chave_produto_livre(item_origem),
            )
            item = consolidados.setdefault(
                chave,
                _novo_item(produto_id=produto_id, item=item_origem),
            )
            item["procuras_pdv"] += 1
            if registro_id is not None:
                item["_atendimentos"].add(int(registro_id))
            if cliente:
                item["_clientes_pdv"].add(cliente)
            else:
                item["procuras_anonimas_pdv"] += 1
            quantidade = Decimal(str(getattr(item_origem, "quantidade", 0) or 0))
            valor = Decimal(
                str(getattr(item_origem, "valor_unitario_estimado", 0) or 0)
            )
            item["quantidade_procurada"] = _numero(
                Decimal(str(item["quantidade_procurada"])) + quantidade
            )
            item["valor_estimado_oportunidade"] = _dinheiro(
                Decimal(str(item["valor_estimado_oportunidade"])) + quantidade * valor
            )
            _registrar_data(item, getattr(registro, "created_at", None))

    for pendencia in pendencias:
        produto_id = int(getattr(pendencia, "produto_id"))
        produto = produtos_por_id.get(produto_id) or getattr(pendencia, "produto", None)
        chave = ("produto", produto_id)
        item = consolidados.setdefault(chave, _novo_item(produto_id=produto_id))
        if produto is not None and item["produto_nome"] == "Produto sem nome":
            item["produto_nome"] = (
                _texto(getattr(produto, "nome", None)) or item["produto_nome"]
            )
        cliente_id = getattr(pendencia, "cliente_id", None)
        if cliente_id is not None:
            cliente_id = int(cliente_id)
            item["_espera_pdv"].add(cliente_id)
            espera_pdv_global.add(cliente_id)
            inscricoes_pdv.add((produto_id, cliente_id))
        item["quantidade_aguardada_pdv"] = _numero(
            Decimal(str(item["quantidade_aguardada_pdv"]))
            + Decimal(str(getattr(pendencia, "quantidade_desejada", 0) or 0))
        )
        _registrar_data(item, getattr(pendencia, "data_registro", None))

    for aviso in avisos:
        produto_id = int(getattr(aviso, "product_id"))
        chave = ("produto", produto_id)
        item = consolidados.setdefault(chave, _novo_item(produto_id=produto_id))
        nome_snapshot = _texto(getattr(aviso, "product_name", None))
        if nome_snapshot and item["produto_nome"] == "Produto sem nome":
            item["produto_nome"] = nome_snapshot
        email = _normalizar(getattr(aviso, "email", None))
        if email:
            item["_espera_ecommerce"].add(email)
            espera_ecommerce_global.add(email)
            inscricoes_ecommerce.add((produto_id, email))
        _registrar_data(item, getattr(aviso, "created_at", None))

    itens: list[dict[str, Any]] = []
    for item in consolidados.values():
        produto = (
            produtos_por_id.get(item["produto_id"]) if item["produto_id"] else None
        )
        if produto is not None:
            item["produto_nome"] = (
                _texto(getattr(produto, "nome", None)) or item["produto_nome"]
            )
            item["sku"] = _texto(getattr(produto, "codigo", None)) or item["sku"]
            marca = getattr(produto, "marca", None)
            item["marca"] = _texto(getattr(marca, "nome", None)) or item["marca"]
            item["fornecedor"] = _nome_fornecedor(produto) or item["fornecedor"]
            item["ecommerce"] = classify_catalog_product(
                produto,
                tenant,
                "ecommerce",
                waitlist_count=len(item["_espera_ecommerce"]),
            )
        elif item["produto_id"] is not None:
            item["cadastrado"] = False

        item["atendimentos_pdv"] = len(item.pop("_atendimentos"))
        item["pessoas_identificadas_pdv"] = len(item.pop("_clientes_pdv"))
        item["aguardando_pdv"] = len(item.pop("_espera_pdv"))
        item["aguardando_ecommerce"] = len(item.pop("_espera_ecommerce"))
        item["aguardando_total"] = item["aguardando_pdv"] + item["aguardando_ecommerce"]
        item.pop("_primeira_ordem")
        ultima_ordem = item.pop("_ultima_ordem")
        item["_ordem"] = ultima_ordem
        itens.append(item)

    resumo = {
        "produtos_com_demanda": len(itens),
        "produtos_nao_cadastrados": sum(not item["cadastrado"] for item in itens),
        "procuras_pdv": sum(item["procuras_pdv"] for item in itens),
        "atendimentos_pdv": len(atendimentos_globais),
        "pessoas_identificadas_pdv": len(clientes_pdv_globais),
        "procuras_anonimas_pdv": sum(item["procuras_anonimas_pdv"] for item in itens),
        "inscricoes_ativas": len(inscricoes_pdv) + len(inscricoes_ecommerce),
        "inscricoes_pdv": len(inscricoes_pdv),
        "inscricoes_ecommerce": len(inscricoes_ecommerce),
        "pessoas_aguardando_pdv": len(espera_pdv_global),
        "pessoas_aguardando_ecommerce": len(espera_ecommerce_global),
        "valor_estimado_oportunidade": _dinheiro(
            sum(Decimal(str(item["valor_estimado_oportunidade"])) for item in itens)
        ),
    }

    busca_normalizada = _normalizar(busca)
    origem = _normalizar(origem) or "todos"
    situacao = _normalizar(situacao) or "todos"

    def corresponde(item: dict[str, Any]) -> bool:
        if busca_normalizada and busca_normalizada not in _normalizar(
            " ".join(
                filter(
                    None,
                    [
                        item["produto_nome"],
                        item["sku"],
                        item["marca"],
                        item["fornecedor"],
                    ],
                )
            )
        ):
            return False
        if origem == "pdv" and not (item["procuras_pdv"] or item["aguardando_pdv"]):
            return False
        if origem == "ecommerce" and not item["aguardando_ecommerce"]:
            return False
        ecommerce = item["ecommerce"] or {}
        if situacao == "aguardando" and not item["aguardando_total"]:
            return False
        if situacao == "nao_cadastrado" and item["cadastrado"]:
            return False
        if (
            situacao == "ausente_ecommerce"
            and item["cadastrado"]
            and ecommerce.get("visivel")
        ):
            return False
        if (
            situacao in {"bloqueado", "esgotado", "pendencias", "pronto"}
            and ecommerce.get("status") != situacao
        ):
            return False
        return True

    itens_filtrados = [item for item in itens if corresponde(item)]
    itens_filtrados.sort(
        key=lambda item: (
            -item["aguardando_total"],
            -item["procuras_pdv"],
            -item.pop("_ordem", 0),
            _normalizar(item["produto_nome"]),
        )
    )
    for item in itens:
        item.pop("_ordem", None)
    return {"resumo": resumo, "total": len(itens_filtrados), "itens": itens_filtrados}
