"""Relaciona rejeições a campos da nota sem transformar o histórico em bloqueio."""

from __future__ import annotations

import re
import unicodedata
from types import SimpleNamespace

from app.bling_integration_fiscal import _resolver_fiscal_item_nfe, _sugerir_ncm


def _text(value):
    return str(value or "").strip()


def _normalized(value):
    value = unicodedata.normalize("NFKD", _text(value).casefold())
    return "".join(char for char in value if not unicodedata.combining(char))


def _item_number(message):
    # Não aceite índices negativos ou parciais: nItem:0/999 não pode escolher
    # o primeiro/último produto nem recair no único produto da venda.
    match = re.search(r"\bnitem\s*[:=]\s*(-?\d+)(?![\w.])", message, re.IGNORECASE)
    if match is None and re.search(r"\bnitem\s*[:=]", message, re.IGNORECASE):
        return 0
    if match is None:
        match = re.search(
            r"\bitem\s*(?:numero|n[ºo.]?)?\s*[:#=]?\s*(-?\d+)\b", message, re.IGNORECASE
        )
    return (
        int(match.group(1))
        if match and len(match.group(1)) <= 8
        else (0 if match else None)
    )


def _fields(message, code=None):
    normalized = _normalized(message)
    if str(code or "") in {"777", "778"} or "ncm" in normalized:
        return ["ncm"]
    if str(code or "") == "386" or ("cfop" in normalized and "csosn" in normalized):
        return ["cfop", "cst_icms"]
    if (
        str(code or "") == "600"
        or "csosn" in normalized
        or ("cst" in normalized and "icms" in normalized)
    ):
        return ["cst_icms"]
    patterns = (
        ("cfop", ("cfop",)),
        ("cest", ("cest",)),
        ("origem_mercadoria", ("origem", "mercadoria")),
        ("pis_cst", ("pis",)),
        ("cofins_cst", ("cofins",)),
        ("cliente.codigo_municipio", ("municipio", "destinat")),
        ("cliente.inscricao_estadual", ("inscricao estadual", "destinat")),
        ("cliente.cpf_cnpj", ("cpf",)),
        ("cliente.cpf_cnpj", ("cnpj", "destinat")),
        ("cliente.cep", ("cep", "destinat")),
    )
    return [
        field for field, terms in patterns if all(term in normalized for term in terms)
    ][:1] or ["intnfe"]


def _guidance(field):
    return {
        "ncm": "Confira o NCM vigente na base fiscal pela descrição, material e uso do produto; confirme a classificação antes de reenviar.",
        "cfop": "Confira o CFOP correspondente à operação e ao estado do destinatário.",
        "cst_icms": "Confira o CSOSN/CST de ICMS conforme o regime da empresa e a tributação do produto.",
        "cest": "Confira o CEST aplicável ao produto na base fiscal.",
        "origem_mercadoria": "Confira a origem da mercadoria no documento de compra.",
        "pis_cst": "Confira o CST de PIS e a tributação aplicável ao produto.",
        "cofins_cst": "Confira o CST de COFINS e a tributação aplicável ao produto.",
        "cliente.cpf_cnpj": "Confira o CPF/CNPJ do destinatário no cadastro do cliente.",
        "cliente.codigo_municipio": "Confira o código IBGE de sete dígitos do município do destinatário.",
        "cliente.inscricao_estadual": "Confira a inscrição estadual e a condição de contribuinte do destinatário.",
        "cliente.cep": "Confira o CEP do endereço do destinatário.",
    }.get(field, "Revise o motivo informado pelo emissor antes de reenviar a nota.")


def _sale_items(venda):
    # A emissão usa a posição na venda. Uma linha de serviço não deve deslocar
    # o nItem para outro produto, mesmo em uma venda antiga inválida.
    return list(getattr(venda, "itens", None) or [])


def _select_item(venda, number):
    items = _sale_items(venda)
    if number is not None:
        if number < 1 or number > len(items):
            return None, number
        item = items[number - 1]
        if _normalized(getattr(item, "tipo", None)) != "produto" or not getattr(
            item, "produto", None
        ):
            return None, number
        return item, number
    products = [
        (index, item)
        for index, item in enumerate(items, start=1)
        if _normalized(getattr(item, "tipo", None)) == "produto"
        and getattr(item, "produto", None)
    ]
    return (products[0][1], products[0][0]) if len(products) == 1 else (None, None)


def effective_fiscal_context(db, venda, item):
    """Lê a mesma fonte fiscal usada na emissão, inclusive FIFO já registrado."""
    from app.intnfe.emission import _lot_from_recorded_fifo

    lot = getattr(item, "lote", None)
    inferred = _lot_from_recorded_fifo(db, venda, item)
    if inferred is not None:
        lot = inferred
    fiscal_item = SimpleNamespace(produto=item.produto, lote=lot)
    fiscal = _resolver_fiscal_item_nfe(db, venda, fiscal_item) or {}
    return fiscal, lot


def _suggestion(db, venda, item, number, field, fiscal, validation):
    current = _text(fiscal.get(field))
    product_occurrences = sum(
        getattr(getattr(row, "produto", None), "id", None) == item.produto.id
        for row in _sale_items(venda)
    )
    for correction in (validation or {}).get("correcoes", []) + (validation or {}).get(
        "bloqueios", []
    ):
        same_item = correction.get("item_id") in (
            None,
            getattr(item, "id", None),
        ) and correction.get("item_numero") in (None, number)
        if (
            product_occurrences > 1
            and correction.get("item_id") is None
            and correction.get("item_numero") is None
        ):
            same_item = False
        if (
            same_item
            and correction.get("campo") == field
            and correction.get("produto_id") == item.produto.id
            and correction.get("valor_sugerido") is not None
            and _text(correction["valor_sugerido"]) != current
            and correction.get("fonte_sugestao") != "historico_de_produtos_semelhantes"
        ):
            return {
                key: correction[key]
                for key in (
                    "valor_sugerido",
                    "fonte_sugestao",
                    "confianca",
                    "confianca_percentual",
                )
                if key in correction
            }
    if field != "ncm":
        return {}
    description = _normalized(getattr(item.produto, "nome", None))
    if all(term in description for term in ("luva", "procedimento", "latex")):
        if current == "40151200":
            return {}
        return {
            "valor_sugerido": "40151200",
            "fonte_sugestao": "referencia_oficial_luvas_de_procedimento",
            "fonte_url": "https://legislacao.fazenda.sp.gov.br/Paginas/RC31692_2025.aspx",
            "confianca": "baixa",
            "confianca_percentual": 45,
            "preenchimento_automatico": False,
            "motivo_sugestao": (
                "Possível NCM para luvas de borracha dos tipos utilizados em medicina, cirurgia, "
                "odontologia ou veterinária. Confira embalagem, composição, finalidade e NF de "
                "entrada; outras luvas podem ter classificação diferente."
            ),
        }
    # Sugestões são opcionais e nunca podem invalidar a leitura da nota.
    suggestion = None
    if db is not None:
        try:
            with db.begin_nested():
                suggestion = _sugerir_ncm(
                    item.produto, fiscal, db, getattr(venda, "tenant_id", None)
                )
        except Exception:
            pass
    if suggestion and _text(suggestion.get("valor")) != _text(fiscal.get("ncm")):
        return {
            "valor_sugerido": suggestion["valor"],
            "fonte_sugestao": suggestion.get("fonte_sugestao"),
            "confianca": suggestion.get("confianca"),
            "confianca_percentual": suggestion.get("confianca_percentual"),
            "preenchimento_automatico": False,
        }
    return {}


def message_corrections(
    venda, message, *, code=None, db=None, items=None, validation=None
):
    """Identifica o campo somente quando a mensagem/código oferece evidência."""
    number = _item_number(_text(message))
    item, number = _select_item(venda, number)
    fields = _fields(message, code)
    fiscal, lot = {}, None
    details = None
    if item is not None:
        details = next(
            (row for row in (items or []) if row.get("item_numero") == number), None
        )
        try:
            fiscal, lot = effective_fiscal_context(db, venda, item)
        except Exception:
            # Exibir o erro continua possível se o cadastro/lote estiver incompleto.
            pass
    corrections = []
    for field in fields:
        correction = {
            "campo": field,
            "mensagem": _text(message),
            "motivo": _guidance(field),
            "codigo_rejeicao": _text(code) or None,
            "origem": "rejeicao_sefaz",
            "historico": True,
            "preenchimento_automatico": False,
        }
        if number is not None:
            correction["item_numero"] = number
        if item is not None and not field.startswith("cliente.") and field != "intnfe":
            product = item.produto
            aliases = {"cst_icms": "icms", "pis_cst": "pis", "cofins_cst": "cofins"}
            value = (
                (details or {}).get(aliases.get(field, field))
                if details
                else fiscal.get(field)
            )
            if field == "cfop" and not details:
                value = fiscal.get("cfop")
            correction.update(
                produto_id=product.id,
                produto_nome=getattr(product, "nome", None),
                produto_tipo=getattr(product, "tipo_produto", None),
                sku=_text(getattr(product, "codigo", None))
                or _text(getattr(product, "codigo_barras", None))
                or str(product.id),
                item_id=getattr(item, "id", None),
                lote_id=(
                    (details or {}).get("lote_id")
                    if details
                    else getattr(lot, "id", None)
                ),
                valor_atual=value,
            )
            suggestion_fiscal = {**fiscal, field: value}
            correction.update(
                _suggestion(
                    db, venda, item, number, field, suggestion_fiscal, validation
                )
            )
        elif field.startswith("cliente."):
            customer = getattr(venda, "cliente", None)
            attribute = field.split(".", 1)[1]
            value = (
                (getattr(customer, "cnpj", None) or getattr(customer, "cpf", None))
                if attribute == "cpf_cnpj"
                else getattr(customer, attribute, None)
            )
            correction.update(
                cliente_id=getattr(customer, "id", None), valor_atual=value
            )
        corrections.append(correction)
    return corrections


def rejection_diagnostics(venda, *, db=None, items=None, validation=None):
    """O histórico orienta a revisão; só a pré-validação atual bloqueia o envio."""
    if _normalized(getattr(venda, "nfe_status", None)) != "rejeitada":
        return None
    code = getattr(venda, "nfe_codigo_erro", None)
    message = getattr(venda, "nfe_motivo_rejeicao", None)
    if not code and not message:
        return None
    return {
        "codigo": code,
        "motivo": message,
        "correcoes": message_corrections(
            venda, message, code=code, db=db, items=items, validation=validation
        ),
    }


def enrich_validation_items(venda, validation):
    """Mantém a identidade da linha, inclusive quando um produto se repete."""
    sale_items = _sale_items(venda)
    for key in ("correcoes", "bloqueios"):
        enriched = []
        for correction in validation.get(key, []):
            product_id = correction.get("produto_id")
            if product_id is None:
                enriched.append(correction)
                continue
            candidates = [
                (index, item)
                for index, item in enumerate(sale_items, start=1)
                if getattr(item, "produto_id", None) == product_id
                or getattr(getattr(item, "produto", None), "id", None) == product_id
            ]
            if correction.get("item_id") is not None:
                candidates = [
                    (index, item)
                    for index, item in candidates
                    if getattr(item, "id", None) == correction["item_id"]
                ]
            if correction.get("item_numero") is not None:
                candidates = [
                    (index, item)
                    for index, item in candidates
                    if index == correction["item_numero"]
                ]
            if not candidates:
                enriched.append(correction)
                continue
            # Se uma validação antiga trouxe só produto_id, a pendência vale
            # para cada linha desse produto; não escolha arbitrariamente uma.
            enriched.extend(
                {
                    **correction,
                    "item_id": getattr(item, "id", None),
                    "item_numero": index,
                    "lote_id": getattr(item, "lote_id", None),
                }
                for index, item in candidates
            )
        validation[key] = enriched
    return validation
