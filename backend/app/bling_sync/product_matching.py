"""Helpers de normalizacao e match para produtos do Bling."""

import re
from typing import Optional


def _normalizar_codigo_match(valor: Optional[str]) -> str:
    return re.sub(r"[^a-zA-Z0-9]", "", (valor or "").strip()).lower()


def _chave_sku_estrita(valor: Optional[str]) -> str:
    return str(valor or "").strip().lower()


def _item_bling_tem_sku_estrito(item: dict, sku_local: Optional[str]) -> bool:
    sku_normalizado = _chave_sku_estrita(sku_local)
    if not sku_normalizado:
        return False

    return sku_normalizado in {
        chave
        for chave in [
            _chave_sku_estrita(item.get("sku")),
            _chave_sku_estrita(item.get("codigo")),
        ]
        if chave
    }


def _escolher_item_sku_estrito(
    itens: list[dict], codigos_busca: list[str]
) -> Optional[dict]:
    codigos_estritos = {
        chave for chave in [_chave_sku_estrita(codigo) for codigo in codigos_busca] if chave
    }
    if not codigos_estritos:
        return None

    for item in itens:
        chaves_item = {
            chave
            for chave in [
                _chave_sku_estrita(item.get("sku")),
                _chave_sku_estrita(item.get("codigo")),
            ]
            if chave
        }
        if chaves_item.intersection(codigos_estritos):
            return item

    return None


def _texto_limpo(valor: Optional[str]) -> str:
    return str(valor or "").strip()


def _coerce_float(valor, default: float = 0.0) -> float:
    if valor is None:
        return float(default)

    if isinstance(valor, dict):
        for chave in ("saldoFisicoTotal", "saldoVirtualTotal", "quantidade", "valor"):
            if chave in valor:
                return _coerce_float(valor.get(chave), default=default)
        return float(default)

    if isinstance(valor, (int, float)):
        return float(valor)

    texto = str(valor).strip()
    if not texto:
        return float(default)

    if "," in texto and "." in texto:
        if texto.rfind(",") > texto.rfind("."):
            texto = texto.replace(".", "").replace(",", ".")
        else:
            texto = texto.replace(",", "")
    elif "," in texto:
        texto = texto.replace(",", ".")

    try:
        return float(texto)
    except (TypeError, ValueError):
        return float(default)


def _sku_bling(item: dict) -> str:
    return _texto_limpo(item.get("sku") or item.get("codigo"))


def _barcode_bling(item: dict) -> str:
    return _texto_limpo(item.get("codigoBarras") or item.get("gtin"))


def _motivo_faltante_bling(item: dict) -> str:
    sku = _sku_bling(item)
    barcode = _barcode_bling(item)

    if sku and barcode:
        return "Nao existe produto local com esse SKU nem com esse codigo de barras."
    if sku:
        return "O SKU do Bling ainda nao existe no CorePet."
    if barcode:
        return "O codigo de barras do Bling ainda nao existe no CorePet."
    return "O cadastro do Bling esta sem SKU e sem codigo de barras para autocorrecao."


def _acao_faltante_bling(item: dict) -> str:
    return (
        "Criar e vincular"
        if (_sku_bling(item) or _barcode_bling(item))
        else "Revisar cadastro no Bling"
    )


def _montar_codigos_busca(
    codigo_principal: str, codigos_extras: Optional[list[str]] = None
) -> list[str]:
    codigos: list[str] = []
    vistos: set[str] = set()

    for bruto in [codigo_principal, *(codigos_extras or [])]:
        codigo = (bruto or "").strip()
        if not codigo:
            continue

        candidatos = [codigo]
        codigo_normalizado = _normalizar_codigo_match(codigo)
        if codigo_normalizado and codigo_normalizado != codigo:
            candidatos.append(codigo_normalizado)

        for candidato in candidatos:
            chave = candidato.lower()
            if chave in vistos:
                continue
            vistos.add(chave)
            codigos.append(candidato)

    return codigos


def _montar_codigos_busca_estrita(
    codigo_principal: str, codigos_extras: Optional[list[str]] = None
) -> list[str]:
    codigos: list[str] = []
    vistos: set[str] = set()

    for bruto in [codigo_principal, *(codigos_extras or [])]:
        codigo = (bruto or "").strip()
        chave = _chave_sku_estrita(codigo)
        if not codigo or not chave or chave in vistos:
            continue
        vistos.add(chave)
        codigos.append(codigo)

    return codigos


def _escolher_item_melhor_match(itens: list[dict], codigos_busca: list[str]) -> dict:
    if not itens:
        return {}

    codigos_normalizados = {
        _normalizar_codigo_match(codigo)
        for codigo in codigos_busca
        if _normalizar_codigo_match(codigo)
    }

    if not codigos_normalizados:
        return itens[0]

    for item in itens:
        campos_codigo = [
            item.get("codigo"),
            item.get("sku"),
            item.get("codigoBarras"),
            item.get("gtin"),
        ]
        for campo in campos_codigo:
            codigo_item = _normalizar_codigo_match(str(campo or ""))
            if codigo_item and codigo_item in codigos_normalizados:
                return item

    return itens[0]


def _normalizar_termo_busca(valor: Optional[str]) -> str:
    return (valor or "").strip()


def _limpar_texto_busca(valor: str) -> str:
    return re.sub(r"\s+", " ", valor).strip()


def _extrair_lista_produtos_bling(resultado: Optional[dict]) -> list[dict]:
    itens = (resultado or {}).get("data", [])
    produtos: list[dict] = []
    for item in itens:
        if isinstance(item, dict) and isinstance(item.get("produto"), dict):
            produtos.append(item.get("produto") or {})
        elif isinstance(item, dict):
            produtos.append(item)
    return produtos


def _chave_codigo_produto(valor: Optional[str]) -> str:
    return _normalizar_codigo_match(valor)


def _tipo_produto_local(produto) -> str:
    return _texto_limpo(getattr(produto, "tipo_produto", None)).upper() or "SIMPLES"


def _produto_eh_pai(produto) -> bool:
    return _tipo_produto_local(produto) == "PAI"


def _produto_sincroniza_estoque(produto) -> bool:
    return not _produto_eh_pai(produto)


def _chaves_match_produto_local(produto) -> set[str]:
    return {
        chave
        for chave in [
            _chave_codigo_produto(getattr(produto, "codigo", None)),
            _chave_codigo_produto(getattr(produto, "codigo_barras", None)),
            _chave_codigo_produto(getattr(produto, "gtin_ean", None)),
            _chave_codigo_produto(getattr(produto, "gtin_ean_tributario", None)),
        ]
        if chave
    }


def _indexar_produtos_locais_por_codigo(produtos: list) -> dict[str, set[int]]:
    codigos_para_produto: dict[str, set[int]] = {}
    for produto in produtos:
        for chave in _chaves_match_produto_local(produto):
            codigos_para_produto.setdefault(chave, set()).add(produto.id)
    return codigos_para_produto


def _extrair_codigos_bling_item(item: dict) -> set[str]:
    return {
        chave
        for chave in [
            _chave_codigo_produto(item.get("codigo")),
            _chave_codigo_produto(item.get("sku")),
            _chave_codigo_produto(item.get("codigoBarras")),
            _chave_codigo_produto(item.get("gtin")),
        ]
        if chave
    }


def _origem_match_produto_bling(produto, item: dict) -> str:
    codigo_local = _chave_codigo_produto(getattr(produto, "codigo", None))
    barcode_local = (
        _chave_codigo_produto(getattr(produto, "codigo_barras", None))
        or _chave_codigo_produto(getattr(produto, "gtin_ean", None))
        or _chave_codigo_produto(getattr(produto, "gtin_ean_tributario", None))
    )
    chaves_sku_bling = {
        chave
        for chave in [
            _chave_codigo_produto(item.get("sku")),
            _chave_codigo_produto(item.get("codigo")),
        ]
        if chave
    }
    chaves_barcode_bling = {
        chave
        for chave in [
            _chave_codigo_produto(item.get("codigoBarras")),
            _chave_codigo_produto(item.get("gtin")),
        ]
        if chave
    }

    if codigo_local and codigo_local in chaves_sku_bling:
        return "sku"
    if barcode_local and (
        barcode_local in chaves_barcode_bling or barcode_local in chaves_sku_bling
    ):
        return "codigo_barras"
    return "codigo"
