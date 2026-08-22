"""Respostas deterministicas e politicas puras da conversa de WhatsApp."""

import re
from datetime import date, datetime
from typing import Any, Dict, Optional

from app.whatsapp.catalog_query_helpers import (
    _canonicalize_numeric_measurements,
    _extract_explicit_measurements,
    _normalize_text,
)


MAX_PRODUCT_IMAGES_PER_RESPONSE = 3
CATALOG_SEARCH_CONTEXT_KEY = "pending_catalog_search"
PRODUCT_SEARCH_INTENTS = {
    "consulta_produto",
    "consulta_preco",
    "consulta_estoque",
}
GOLD_BRAND_OPTIONS = {
    "1": "Special Dog Gold",
    "2": "Golden",
    "3": "Bob Dog Gold",
}
GOLD_CLARIFICATION_MESSAGE = (
    "Quando você diz ração Gold, qual marca ou linha procura?\n\n"
    "1. Special Dog Gold\n"
    "2. Golden\n"
    "3. Bob Dog Gold\n\n"
    "Responda com o número ou com o nome."
)


def _catalog_products(function_result: Any) -> list[Dict[str, Any]]:
    if not isinstance(function_result, dict):
        return []
    data = function_result.get("data")
    if not isinstance(data, dict):
        data = function_result
    products = data.get("produtos")
    return [product for product in products or [] if isinstance(product, dict)]


def _format_natural_list(values: list[str]) -> str:
    if len(values) <= 1:
        return "".join(values)
    return f"{', '.join(values[:-1])} e {values[-1]}"


def _measurement_sort_key(value: str) -> tuple[int, float]:
    match = re.fullmatch(r"(\d+(?:[.,]\d+)?)(kg|g|ml|l)", value)
    if not match:
        return (9, float("inf"))
    amount = float(match.group(1).replace(",", "."))
    unit = match.group(2)
    if unit == "kg":
        return (0, amount * 1000)
    if unit == "g":
        return (0, amount)
    if unit == "l":
        return (1, amount * 1000)
    return (1, amount)


def _build_weight_options_response(function_result: Any, catalog_query: str) -> str:
    products = _catalog_products(function_result)
    if not products:
        return _build_catalog_response(function_result, catalog_query)

    measurements = sorted(
        {
            measurement
            for product in products
            for measurement in _extract_explicit_measurements(
                str(product.get("nome") or "")
            )
        },
        key=_measurement_sort_key,
    )
    if not measurements:
        return _build_catalog_response(function_result, catalog_query)

    if len(measurements) == 1:
        return (
            f"Para {catalog_query}, encontrei a embalagem de {measurements[0]} "
            "com estoque. Quer que eu mostre a opção?"
        )
    return (
        f"Para {catalog_query}, encontrei estas embalagens com estoque: "
        f"{_format_natural_list(measurements)}.\n\nQual peso você prefere?"
    )


def _parse_catalog_validity(value: Any) -> Optional[date]:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).date()
    except ValueError:
        return None


def _build_validity_response(
    function_result: Any,
    catalog_query: str,
) -> tuple[str, bool]:
    products = _catalog_products(function_result)
    if not products:
        return _build_catalog_response(function_result, catalog_query), False

    lines = ["Consultei a validade cadastrada do estoque:"]
    needs_human = False
    for product in products[:MAX_PRODUCT_IMAGES_PER_RESPONSE]:
        name = str(product.get("nome") or "Produto").strip()
        validity = _parse_catalog_validity(product.get("validade"))
        if validity and validity > date.today():
            lines.append(f"- {name}: {validity:%d/%m/%Y}")
        else:
            needs_human = True
            lines.append(f"- {name}: precisa de conferência da equipe")

    if needs_human:
        lines.append(
            "Não vou informar uma data sem conferir o lote físico. "
            "Vou chamar a equipe para confirmar certinho."
        )
    elif len(products) > 1:
        lines.append("Qual dessas opções você quis dizer?")
    return "\n\n".join(lines), needs_human


def _restricted_scope_response(message: str) -> Optional[str]:
    """Bloqueia pedidos que possam expor dados ou funcionamento interno."""
    text = " ".join(_normalize_text(message).split())
    restricted_patterns = (
        r"\b(ignore|ignorar|esqueca).{0,30}\b(instrucoes|regras|prompt)\b",
        r"\b(prompt|instrucoes internas|regras internas|mensagem de sistema)\b",
        r"\b(senha|token|api key|chave de api|credencial|segredo)\b",
        r"\b(banco de dados|dump|exporte|exportar).{0,35}\b(dados|clientes|cadastros)\b",
        r"\b(lista|dados|telefone|cpf|endereco|historico|compras).{0,25}\b(outros? clientes?|todos os clientes)\b",
        r"\b(outros? clientes?|todos os clientes).{0,25}\b(lista|dados|telefone|cpf|endereco|historico|compras)\b",
        r"\b(preco de custo|margem de lucro|lucro da loja|dados do fornecedor)\b",
    )
    if not any(re.search(pattern, text) for pattern in restricted_patterns):
        return None
    return (
        "Não consigo acessar ou compartilhar dados internos, credenciais ou "
        "informações de outras pessoas. Posso ajudar com produtos, preços, "
        "estoque, seu próprio histórico e seu pedido."
    )


def _is_generic_gold_query(message: str) -> bool:
    """Identifica 'Gold' sem uma marca/linha suficientemente definida."""
    text = _normalize_text(message)
    if not re.search(r"\bgold\b", text):
        return False
    return not any(brand in text for brand in ("special dog", "bob dog", "golden"))


def _gold_brand_from_reply(message: str) -> Optional[str]:
    text = _normalize_text(message).strip()
    compact_choice = re.sub(r"[^0-9]", "", text)
    if compact_choice in GOLD_BRAND_OPTIONS and len(text) <= 4:
        return GOLD_BRAND_OPTIONS[compact_choice]
    if "special dog" in text:
        return GOLD_BRAND_OPTIONS["1"]
    if "golden" in text:
        return GOLD_BRAND_OPTIONS["2"]
    if "bob dog" in text:
        return GOLD_BRAND_OPTIONS["3"]
    return None


def _confirmation_reply(message: str) -> Optional[bool]:
    """Interpreta confirmações naturais; respostas ambíguas ficam para a IA."""
    text = re.sub(r"[^a-z0-9 ]", " ", _normalize_text(message))
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return None

    negative_pattern = (
        r"\b(?:nao|negativo|errad[oa]|outr[oa]|nenhum[ao]?|desist[io]|"
        r"alterar|mudar|corrigir|trocar|melhor nao)\b"
    )
    if re.search(negative_pattern, text):
        return False

    uncertainty_pattern = r"\b(?:talvez|nao sei|tenho duvida|acho que nao)\b"
    if re.search(uncertainty_pattern, text):
        return None

    affirmative_pattern = (
        r"\b(?:sim|isso|essa|esse|corret[oa]|cert[oa]|perfeit[oa]|beleza|"
        r"fechado|combinado|exatamente|pode sim|pode montar|pode separar|"
        r"pode fazer|manda ver|vamos nessa|confirmo|repete|repetir)\b"
    )
    if text == "pode" or re.search(affirmative_pattern, text):
        return True
    return None


def _recent_purchase_confirmation_message(product_name: str) -> str:
    return (
        "Encontrei no seu histórico de compras:\n\n"
        f"{product_name}\n\n"
        "É essa ração que você procura? Responda sim ou não."
    )


def _replace_generic_gold(original_query: str, brand: str) -> str:
    return re.sub(r"\bgold\b", brand, original_query, count=1, flags=re.IGNORECASE)


def _gold_catalog_query(original_query: str, brand: str) -> str:
    """Monta busca curta; frases completas pioram o ranking do catálogo."""
    normalized_query = _normalize_text(original_query)
    product_type = "Racao" if re.search(r"\bracao\b", normalized_query) else ""
    weight_match = re.search(r"\b\d+(?:[.,]\d+)?\s*kg\b", normalized_query)
    weight = weight_match.group(0).replace(" ", "") if weight_match else ""
    return " ".join(part for part in (product_type, brand, weight) if part)


def _gold_brand_matches_product_caption(brand: str, caption: str) -> bool:
    """Garante que a foto realmente represente a opção de marca exibida."""
    product_name = " ".join(_normalize_text((caption or "").split(" — ", 1)[0]).split())
    normalized_brand = " ".join(_normalize_text(brand).split())
    required_terms = [normalized_brand]
    if normalized_brand in {"special dog gold", "bob dog gold"}:
        required_terms = [normalized_brand.removesuffix(" gold"), "gold"]
    return all(
        re.search(rf"\b{re.escape(term)}\b", product_name) for term in required_terms
    )


def _tool_choice_for_intent(intent: str) -> Any:
    if intent in PRODUCT_SEARCH_INTENTS:
        return {"type": "function", "function": {"name": "buscar_produto"}}
    return "auto"


def _operational_handoff_reason(message: str) -> Optional[tuple[str, str]]:
    """Reconhece casos em que o piloto não possui dados para responder com segurança."""
    text = re.sub(r"\s+", " ", _normalize_text(message)).strip()
    if not text:
        return None

    medical_patterns = (
        r"\b(doente|passando mal|vomitando|vomitou|diarreia|intoxic|envenen|convuls|sangrando|sem comer)\b",
        r"\b(qual|que) (remedio|medicamento).*(dar|usar)\b",
        r"\bposso dar .*\b(remedio|medicamento)\b",
    )
    if any(re.search(pattern, text) for pattern in medical_patterns):
        return (
            "medical_guidance",
            "Cliente pediu orientação de saúde; não indicar medicamento automaticamente",
        )

    return_or_exchange_patterns = (
        r"\b(trocar|troca|devolver|devolucao|reembolso)\b",
        r"\b(veio|mandaram|entregaram) (o |um )?(produto |pedido |item )?errado\b",
        r"\b(produto|pedido|item|racao) errad[oa]\b",
    )
    if any(re.search(pattern, text) for pattern in return_or_exchange_patterns):
        return (
            "return_or_exchange",
            "Cliente relatou troca, devolução, reembolso ou item incorreto",
        )

    delivery_status_patterns = (
        r"\b(ainda nao chegou|nao chegou|ainda nao veio)\b",
        r"\bonde (esta|ta) (o |meu )?pedido\b",
        r"\b(ja saiu|entregador|atrasad|status do pedido|status da entrega|previsao da entrega)\b",
    )
    if any(re.search(pattern, text) for pattern in delivery_status_patterns):
        return (
            "delivery_status",
            "Cliente pediu acompanhamento de uma entrega ou relatou atraso",
        )

    loyalty_patterns = (
        r"\b(voucher|cartao fidelidade|credito em haver|desconto anotado)\b",
        r"\b(cashback|carimbos?)\b",
        r"\b(meu|tenho|saldo).{0,20}\bcredito\b",
        r"\bcredito (da loja|disponivel|de devolucao)\b",
    )
    if any(re.search(pattern, text) for pattern in loyalty_patterns):
        return (
            "loyalty_or_credit",
            "Cliente perguntou sobre fidelidade, voucher, desconto ou crédito",
        )

    store_hours_patterns = (
        r"\b(aberto|aberta|abre|fecha|fechado|fechada).*\b(hora|horas|horario)\b",
        r"\b(ate que horas|horario de funcionamento|qual o horario|qual e o horario)\b",
    )
    if any(re.search(pattern, text) for pattern in store_hours_patterns):
        return (
            "store_hours",
            "Cliente perguntou o horário da loja, ainda não configurado no ERP",
        )

    delivery_policy_patterns = (
        r"\b(entregam|entrega|entregar|frete) hoje\b",
        r"\b(faz|fazem) entrega\b",
        r"\b(consegue|conseguem|pode|podem) entregar\b",
        r"\b(consegue|conseguem|pode|podem) (mandar|enviar).{0,30}\b(hoje|antes|ate)\b",
        r"\b(valor|preco|quanto|taxa).{0,20}\b(entrega|frete)\b",
        r"\b(entrega|frete).{0,20}\b(gratis|gratuita|nao paga)\b",
        r"\b(a partir de|pedido minimo).{0,30}\b(entrega|frete)\b",
    )
    if any(re.search(pattern, text) for pattern in delivery_policy_patterns):
        return (
            "delivery_policy",
            "Cliente perguntou regra, taxa, gratuidade ou disponibilidade de entrega",
        )

    return None


def _is_contextless_product_photo_request(message: str) -> bool:
    """Evita buscar no catálogo por termos vazios como apenas 'opções'."""
    text = re.sub(r"[^a-z0-9 ]", " ", _normalize_text(message))
    text = re.sub(r"\s+", " ", text).strip()
    return text in {
        "manda foto",
        "manda as fotos",
        "manda foto das opcoes",
        "manda fotos das opcoes",
        "pode mandar foto",
        "pode mandar as fotos",
        "quero ver as opcoes",
        "tem foto",
    }


def _format_brl(value: Any) -> str:
    formatted = f"{float(value or 0):,.2f}"
    return "R$ " + formatted.replace(",", "_").replace(".", ",").replace("_", ".")


def _delivery_status_response(delivery: dict[str, Any]) -> Optional[str]:
    status_messages = {
        "pendente": "está aguardando preparação ou saída para entrega",
        "pronto": "está pronto e aguardando saída para entrega",
        "em_rota": "está em rota de entrega",
        "entregue": "consta como entregue",
        "cancelado": "consta com a entrega cancelada",
    }
    status = str(delivery.get("status") or "").strip().lower()
    status_message = status_messages.get(status)
    if not status_message:
        return None

    order_number = str(delivery.get("number") or delivery.get("sale_id") or "").strip()
    response = f"Consultei o CorePet: o pedido {order_number} {status_message}."
    delivered_at = delivery.get("delivered_at")
    if status == "entregue" and isinstance(delivered_at, datetime):
        response += f" A entrega foi registrada em {delivered_at:%d/%m/%Y às %H:%M}."
    return response


def _coupon_description(coupon: dict[str, Any]) -> str:
    coupon_type = str(coupon.get("type") or "")
    if coupon_type == "percent" and coupon.get("discount_percent") is not None:
        benefit = f"{float(coupon['discount_percent']):g}% de desconto"
    elif coupon_type == "fixed" and coupon.get("discount_value") is not None:
        benefit = f"{_format_brl(coupon['discount_value'])} de desconto"
    elif coupon_type == "free_shipping":
        benefit = "entrega grátis"
    elif coupon_type == "gift":
        benefit = "brinde"
    else:
        benefit = "benefício cadastrado"

    valid_until = coupon.get("valid_until")
    validity = (
        f", válido até {valid_until:%d/%m/%Y}"
        if isinstance(valid_until, datetime)
        else ""
    )
    return f"{coupon.get('code')}: {benefit}{validity}"


def _customer_benefits_response(
    benefits: dict[str, Any], message_content: str
) -> Optional[str]:
    text = _normalize_text(message_content)
    coupons = benefits.get("coupons") or []
    store_credit = float(benefits.get("store_credit") or 0)
    cashback = float(benefits.get("cashback") or 0)
    loyalty_stamps = int(benefits.get("loyalty_stamps") or 0)
    asks_credit = "credito" in text
    asks_cashback = "cashback" in text
    asks_loyalty = any(term in text for term in ("voucher", "fidelidade", "carimbo"))

    if not any(
        (
            asks_credit,
            asks_cashback,
            asks_loyalty,
            store_credit > 0,
            cashback > 0,
            loyalty_stamps > 0,
            bool(coupons),
        )
    ):
        return None

    lines = ["Consultei os benefícios vinculados ao seu cadastro:"]
    if asks_credit or store_credit > 0:
        lines.append(f"- Crédito da loja: {_format_brl(store_credit)}")
    if asks_cashback or cashback > 0:
        lines.append(f"- Cashback disponível: {_format_brl(cashback)}")
    if asks_loyalty or loyalty_stamps > 0:
        lines.append(f"- Carimbos disponíveis: {loyalty_stamps}")
    if coupons:
        lines.append("- Cupons ativos:")
        lines.extend(f"  • {_coupon_description(coupon)}" for coupon in coupons)
    elif asks_loyalty:
        return None
    return "\n".join(lines)


def _image_identification_response(message_content: str) -> Optional[str]:
    marker = "[Imagem recebida sem pergunta]"
    if not (message_content or "").startswith(marker):
        return None

    analysis = message_content[len(marker) :].strip()
    analysis = re.sub(
        r"(?is)\n*se precisar.*$",
        "",
        analysis,
    ).strip()
    if not analysis:
        analysis = "Não consegui identificar detalhes com segurança."
    return (
        "Pela foto, consegui identificar:\n\n"
        f"{analysis}\n\n"
        "O que você gostaria de saber sobre esse produto?"
    )


def _image_catalog_query(message_content: str) -> Optional[str]:
    marker = "[Imagem recebida] Pergunta do cliente:"
    if not (message_content or "").startswith(marker):
        return None

    question, _, analysis = message_content[len(marker) :].partition(
        "Leitura visual provisoria:"
    )
    question_normalized = _normalize_text(question)
    product_question_terms = (
        "tem ",
        "vende",
        "preco",
        "valor",
        "quanto",
        "opcao",
        "kg",
        "peso",
        "tamanho",
    )
    if not any(term in question_normalized for term in product_question_terms):
        return None

    def _field(name: str) -> str:
        match = re.search(rf"(?im)^\s*{name}:\s*([^\r\n]+)", analysis)
        if not match:
            return ""
        value = match.group(1).strip()
        if "nao identificado" in _normalize_text(value):
            return ""
        return value

    brand = _field("Marca")
    product_line = _field("Linha")
    product = _field("Produto") if not (brand or product_line) else ""
    measurement_match = re.search(
        r"\b\d+(?:[.,]\d+)?\s*(?:kg|g|ml|l)\b",
        question_normalized,
    )
    measurement = (
        measurement_match.group(0).replace(" ", "") if measurement_match else ""
    )
    query = " ".join(
        part for part in (product, brand, product_line, measurement) if part
    )
    return query or None


def _build_catalog_response(function_result: Any, catalog_query: str) -> str:
    data = function_result.get("data") if isinstance(function_result, dict) else None
    if not isinstance(data, dict):
        data = function_result if isinstance(function_result, dict) else {}
    products = data.get("produtos")
    if not isinstance(products, list):
        products = []

    if not products:
        if data.get("unavailable_found"):
            return f"Encontrei {catalog_query}, mas está sem estoque no momento."
        return f"Não encontrei {catalog_query} no catálogo."

    single_result = len(products) == 1
    opening = (
        f"Encontrei esta opção para {catalog_query}:"
        if single_result
        else f"Encontrei estas opções para {catalog_query}:"
    )
    lines = [opening]
    for index, product in enumerate(
        products[:MAX_PRODUCT_IMAGES_PER_RESPONSE], start=1
    ):
        name = str(product.get("nome") or "Produto").strip()
        price = product.get("preco")
        if isinstance(price, (int, float)):
            price_text = f"R$ {float(price):.2f}".replace(".", ",")
            lines.append(f"{index}. {name} — {price_text}")
        else:
            lines.append(f"{index}. {name}")
    if not single_result:
        lines.append("Qual delas você quis dizer?")
    return "\n\n".join(lines)


def _filter_unavailable_catalog_products(function_result: Any) -> Any:
    """Não oferece item esgotado quando o catálogo informa o estoque atual."""
    if not isinstance(function_result, dict):
        return function_result

    result = dict(function_result)
    nested_data = result.get("data")
    data = dict(nested_data) if isinstance(nested_data, dict) else result
    products = data.get("produtos")
    if not isinstance(products, list):
        return function_result

    def _is_available(product: Any) -> bool:
        if not isinstance(product, dict):
            return False
        if "estoque_disponivel" in product:
            return bool(product.get("estoque_disponivel"))
        if "estoque" not in product:
            return True
        try:
            return float(product.get("estoque") or 0) > 0
        except (TypeError, ValueError):
            return True

    available_products = [product for product in products if _is_available(product)]
    data["produtos"] = available_products
    data["found"] = len(available_products)
    data["unavailable_found"] = bool(products and not available_products)
    if isinstance(nested_data, dict):
        result["data"] = data
    return result


def _preserve_explicit_measurements(query: str, messages: list[Dict[str, Any]]) -> str:
    """Reinsere peso/volume do cliente quando a IA omite isso na tool."""
    query = _canonicalize_numeric_measurements(query)
    last_user_message = next(
        (
            str(message.get("content") or "")
            for message in reversed(messages)
            if message.get("role") == "user"
        ),
        "",
    )
    measurements = _extract_explicit_measurements(last_user_message)
    query_normalized = _normalize_text(query).replace(" ", "")
    missing = [
        measurement.replace(" ", "")
        for measurement in measurements
        if measurement.replace(" ", "") not in query_normalized
    ]
    return " ".join([query.strip(), *missing]).strip()
