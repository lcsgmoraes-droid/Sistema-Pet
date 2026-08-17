"""
Message Processor - Orquestrador Principal

Orquestra todo o fluxo de processamento:
1. Classificar intenção
2. Construir contexto
3. Decidir ação
4. Chamar IA (se necessário)
5. Executar functions (se chamadas)
6. Enviar resposta
7. Registrar métricas
"""

import json
import logging
import os
import re
import unicodedata
import uuid
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from datetime import datetime
from types import SimpleNamespace

from app.ai.intent_classifier import IntentClassifier, IntentRouter
from app.ai.context_builder import ContextBuilder
from app.ai.llm_client import (
    LLMClient,
    PromptBuilder,
    AVAILABLE_FUNCTIONS_PHASE1_READ_ONLY,
)
from app.whatsapp.sender import send_whatsapp_message
from app.whatsapp.models import (
    WhatsAppSession,
    WhatsAppMessage,
    WhatsAppMetric,
    TenantWhatsAppConfig,
)
from app.whatsapp.handoff_manager import HandoffManager
from app.whatsapp.tenant_context import whatsapp_tenant_context
from app.whatsapp.customer_context_service import (
    load_customer_benefits,
    load_latest_delivery,
    load_latest_purchase,
    load_store_hours,
    resolve_session_customer,
)
from app.whatsapp.order_drafts import (
    HISTORY_ITEM_SELECTION_CONTEXT_KEY,
    ORDER_DRAFT_CONTEXT_KEY,
    build_order_draft_message,
    draft_product_media,
    extract_history_quantity_request,
    extract_multi_item_order,
    extract_single_item_order,
    format_draft_item,
    is_safe_product_image_url,
    is_generic_reorder_request,
    purchase_items_as_draft,
)
from app.whatsapp.order_checkout import (
    ORDER_CHECKOUT_CONTEXT_KEY,
    ORDER_ITEM_SELECTION_CONTEXT_KEY,
    benefits_lines,
    build_checkout_summary,
    is_final_order_confirmation,
    is_order_cancellation,
    is_order_checkout_request,
    parse_fulfillment_choice,
    parse_payment_choice,
    payment_methods_message,
)
from app.whatsapp.remote_corepet_client import (
    create_remote_order,
    fetch_remote_order_preview,
)

logger = logging.getLogger(__name__)

MAX_PRODUCT_IMAGES_PER_RESPONSE = 3
CATALOG_SEARCH_CONTEXT_KEY = "pending_catalog_search"
MARKDOWN_IMAGE_PATTERN = re.compile(r"!\[[^\]]*\]\((https?://[^)\s]+)\)")
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


def _extract_product_media(function_result: Any) -> list[Dict[str, str]]:
    """Extrai fotos dos produtos retornados pelas functions de catálogo."""
    if not isinstance(function_result, dict):
        return []

    data = function_result.get("data")
    if not isinstance(data, dict):
        data = function_result

    products = data.get("produtos")
    if not isinstance(products, list):
        return []

    media: list[Dict[str, str]] = []
    for product in products:
        if not isinstance(product, dict):
            continue
        image_url = str(product.get("imagem_url") or "").strip()
        if not is_safe_product_image_url(image_url):
            continue

        name = str(product.get("nome") or "Produto").strip()
        price = product.get("preco")
        caption = name
        if isinstance(price, (int, float)):
            caption += f" — R$ {float(price):.2f}".replace(".", ",")
        media.append({"image_url": image_url, "caption": caption})

    return media


def _clean_response_image_links(
    response: str, product_media: list[Dict[str, str]]
) -> str:
    """Remove links de imagem do texto quando a foto será anexada de verdade."""
    cleaned = MARKDOWN_IMAGE_PATTERN.sub("", response or "")
    for item in product_media:
        image_url = item.get("image_url") or ""
        if image_url:
            cleaned = cleaned.replace(image_url, "")

    cleaned = re.sub(r"(?m)^\s*-\s*$", "", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


def _normalize_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value or "")
    without_accents = "".join(
        char for char in normalized if not unicodedata.combining(char)
    )
    return without_accents.lower()


def _strip_audio_marker(value: str) -> str:
    """Remove o marcador interno sem apagar o texto transcrito do cliente."""
    return re.sub(
        r"^\s*\[audio do cliente\]\s*",
        "",
        value or "",
        flags=re.IGNORECASE,
    ).strip()


MEASUREMENT_NUMBER_WORDS = {
    "meio": 0.5,
    "um": 1,
    "uma": 1,
    "dois": 2,
    "duas": 2,
    "tres": 3,
    "quatro": 4,
    "cinco": 5,
    "seis": 6,
    "sete": 7,
    "oito": 8,
    "nove": 9,
    "dez": 10,
    "onze": 11,
    "doze": 12,
    "treze": 13,
    "quatorze": 14,
    "catorze": 14,
    "quinze": 15,
    "dezesseis": 16,
    "dezessete": 17,
    "dezoito": 18,
    "dezenove": 19,
    "vinte": 20,
    "vinte e cinco": 25,
}
MEASUREMENT_UNITS = {
    "kg": "kg",
    "quilo": "kg",
    "quilos": "kg",
    "g": "g",
    "grama": "g",
    "gramas": "g",
    "ml": "ml",
    "mililitro": "ml",
    "mililitros": "ml",
    "l": "l",
    "litro": "l",
    "litros": "l",
}


def _format_measurement_number(value: float) -> str:
    if float(value).is_integer():
        return str(int(value))
    return str(value).replace(".", ",")


def _canonicalize_numeric_measurements(value: str) -> str:
    unit_pattern = "|".join(
        sorted((re.escape(unit) for unit in MEASUREMENT_UNITS), key=len, reverse=True)
    )

    def _replace(match: re.Match) -> str:
        number, unit = match.groups()
        return f"{number}{MEASUREMENT_UNITS[_normalize_text(unit)]}"

    return re.sub(
        rf"\b(\d+(?:[.,]\d+)?)\s*({unit_pattern})\b",
        _replace,
        value or "",
        flags=re.IGNORECASE,
    )


def _extract_explicit_measurements(value: str) -> list[str]:
    """Normaliza medidas digitadas ou faladas, como 'três quilos' -> '3kg'."""
    text = " ".join(_normalize_text(_strip_audio_marker(value)).split())
    measurements: list[str] = []

    unit_pattern = "|".join(
        sorted((re.escape(unit) for unit in MEASUREMENT_UNITS), key=len, reverse=True)
    )
    for number, unit in re.findall(
        rf"\b(\d+(?:[.,]\d+)?)\s*({unit_pattern})\b",
        text,
    ):
        measurements.append(f"{number}{MEASUREMENT_UNITS[unit]}")

    word_pattern = "|".join(
        sorted(
            (re.escape(word) for word in MEASUREMENT_NUMBER_WORDS),
            key=len,
            reverse=True,
        )
    )
    for number_word, half_suffix, unit in re.findall(
        rf"\b({word_pattern})(\s+e\s+meio)?\s+({unit_pattern})\b",
        text,
    ):
        number = float(MEASUREMENT_NUMBER_WORDS[number_word])
        if half_suffix:
            number += 0.5
        measurements.append(
            f"{_format_measurement_number(number)}{MEASUREMENT_UNITS[unit]}"
        )

    unique_measurements: list[str] = []
    for measurement in measurements:
        if measurement not in unique_measurements:
            unique_measurements.append(measurement)
    return unique_measurements


def _remove_explicit_measurements(value: str) -> str:
    text = value or ""
    for measurement in _extract_explicit_measurements(text):
        match = re.fullmatch(r"(\d+(?:[.,]\d+)?)(kg|g|ml|l)", measurement)
        if not match:
            continue
        number, canonical_unit = match.groups()
        unit_variants = {
            "kg": "kg|quilo|quilos",
            "g": "g|grama|gramas",
            "ml": "ml|mililitro|mililitros",
            "l": "l|litro|litros",
        }[canonical_unit]
        text = re.sub(
            rf"\b{re.escape(number)}\s*(?:{unit_variants})\b",
            " ",
            text,
            flags=re.IGNORECASE,
        )
    return " ".join(text.split())


def _catalog_followup_query(message: str, previous_query: str) -> Optional[str]:
    """Combina detalhes curtos com o último produto, sem depender da memória da IA."""
    measurements = _extract_explicit_measurements(message)
    if not measurements or not (previous_query or "").strip():
        return None

    plain = _normalize_text(_strip_audio_marker(message))
    tokens = re.findall(r"[a-z0-9]+", plain)
    generic_tokens = {
        "audio",
        "cliente",
        "eu",
        "quero",
        "queria",
        "prefiro",
        "pode",
        "ser",
        "tem",
        "teria",
        "o",
        "a",
        "os",
        "as",
        "um",
        "uma",
        "de",
        "da",
        "do",
        "das",
        "dos",
        "com",
        "pacote",
        "embalagem",
        "opcao",
        "esse",
        "essa",
        "aquele",
        "aquela",
        "qual",
        "e",
        *MEASUREMENT_NUMBER_WORDS.keys(),
        *MEASUREMENT_UNITS.keys(),
    }
    descriptors = {
        "adulto",
        "adultos",
        "filhote",
        "filhotes",
        "mini",
        "bits",
        "frango",
        "carne",
        "arroz",
        "cao",
        "caes",
        "gato",
        "gatos",
    }
    remaining = [
        token
        for token in tokens
        if token not in generic_tokens
        and not token.isdigit()
        and not re.fullmatch(r"\d+(?:kg|g|ml|l)", token)
    ]
    if any(token not in descriptors for token in remaining):
        return None

    base_query = _remove_explicit_measurements(previous_query)
    base_query = re.sub(r"\bgranel\b", " ", base_query, flags=re.IGNORECASE)
    return " ".join([base_query.strip(), *remaining, *measurements]).strip()


def _product_query_from_choice_phrase(message: str) -> Optional[str]:
    """Extrai produto/marca de escolhas curtas sem presumir um pedido fechado."""
    original = re.sub(r"\s+", " ", message or "").strip(" .!?")
    normalized = _normalize_text(original)
    match = re.fullmatch(
        r"(?:eu\s+)?(?:quero|queria|prefiro|pode\s+ser|vou\s+querer)\s+(.+)",
        normalized,
    )
    if not match:
        return None

    normalized_candidate = re.sub(r"^(?:a|o|uma|um)\s+", "", match.group(1)).strip()
    if not normalized_candidate or re.search(r"\d", normalized_candidate):
        return None

    operational_terms = (
        "atendente",
        "atendimento",
        "fechar",
        "finalizar",
        "pedido",
        "entrega",
        "entregar",
        "pagamento",
        "pagar",
        "pix",
        "cartao",
        "dinheiro",
        "comprar",
    )
    if any(
        re.search(rf"\b{re.escape(term)}\b", normalized_candidate)
        for term in operational_terms
    ):
        return None
    if normalized_candidate in {"isso", "essa", "esse", "aquela", "aquele"}:
        return None

    original_match = re.fullmatch(
        r"(?:eu\s+)?(?:quero|queria|prefiro|pode\s+ser|vou\s+querer)\s+(.+)",
        original,
        flags=re.IGNORECASE,
    )
    if not original_match:
        return normalized_candidate
    return re.sub(
        r"^(?:a|o|uma|um)\s+", "", original_match.group(1), flags=re.IGNORECASE
    ).strip()


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
    """Interpreta respostas curtas de confirmação sem recorrer à IA."""
    text = re.sub(r"[^a-z0-9 ]", " ", _normalize_text(message))
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return None

    negative_replies = {
        "nao",
        "nao e",
        "nao e essa",
        "nao e esse",
        "outra",
        "outro",
        "nenhuma",
        "nenhum",
    }
    affirmative_replies = {
        "sim",
        "isso",
        "essa",
        "esse",
        "e essa",
        "e esse",
        "correto",
        "correta",
        "quero repetir",
        "quero repetir o pedido",
        "pode repetir",
        "pode repetir o pedido",
        "repete",
        "repete o pedido",
        "quero o mesmo pedido",
    }
    if text in negative_replies or text.startswith("nao "):
        return False
    if text in affirmative_replies:
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


class MessageProcessor:
    """
    Processador principal de mensagens WhatsApp.
    """

    def __init__(self, db: Session, tenant_id: str):
        self.db = db
        self.tenant_id = tenant_id

        # Buscar config
        with whatsapp_tenant_context(tenant_id):
            config = (
                db.query(TenantWhatsAppConfig)
                .filter(TenantWhatsAppConfig.tenant_id == tenant_id)
                .first()
            )

        fallback_openai_key = os.getenv("OPENAI_API_KEY", "")
        if not config:
            logger.warning(
                "Tenant %s sem tenant_whatsapp_config; aplicando fallback para piloto",
                tenant_id,
            )
            self.config = SimpleNamespace(
                openai_api_key=fallback_openai_key,
                model_preference=(os.getenv("WHATSAPP_OPENAI_MODEL") or "gpt-4o-mini"),
                auto_response_enabled=True,
                bot_name="Assistente",
            )
        else:
            self.config = config
            if not self.config.openai_api_key and fallback_openai_key:
                self.config = SimpleNamespace(
                    openai_api_key=fallback_openai_key,
                    model_preference=(
                        os.getenv("WHATSAPP_OPENAI_MODEL")
                        or getattr(config, "model_preference", None)
                        or "gpt-4o-mini"
                    ),
                    auto_response_enabled=getattr(
                        config, "auto_response_enabled", True
                    ),
                    bot_name=getattr(config, "bot_name", "Assistente"),
                )

        self.ai_enabled = bool(self.config.openai_api_key)
        preferred_model = (
            os.getenv("WHATSAPP_OPENAI_MODEL")
            or getattr(self.config, "model_preference", None)
            or "gpt-4o-mini"
        )

        # Inicializar componentes
        self.intent_classifier = (
            IntentClassifier(self.config.openai_api_key, model=preferred_model)
            if self.ai_enabled
            else None
        )
        self.context_builder = ContextBuilder(db)
        self.llm_client = (
            LLMClient(
                self.config.openai_api_key,
                default_model=preferred_model,
                advanced_model=preferred_model,
            )
            if self.ai_enabled
            else None
        )
        self.router = IntentRouter()

    @staticmethod
    def _is_explicit_human_request(message: str) -> bool:
        """Detecta pedido explícito de atendimento humano."""
        text = (message or "").lower()
        triggers = [
            "atendente",
            "atendimento humano",
            "humano",
            "falar com pessoa",
            "falar com humano",
            "falar com atendente",
            "quero suporte humano",
            "transferir para humano",
        ]
        return any(trigger in text for trigger in triggers)

    async def _build_context(
        self, session_id: str, message_content: str
    ) -> Dict[str, Any]:
        try:
            return await self.context_builder.build_context(
                tenant_id=self.tenant_id,
                session_id=session_id,
                message=message_content,
            )
        except Exception as context_error:
            logger.warning(
                f"Falha ao construir contexto, seguindo com contexto mínimo: {context_error}"
            )
            self.db.rollback()
            return {}

    async def _detect_intent(
        self, message_content: str, context: Dict[str, Any]
    ) -> tuple[str, float]:
        if not self.ai_enabled:
            result = IntentClassifier._fallback_classification(message_content)
            return result["intent"], result["confidence"]

        intent_result = await self.intent_classifier.classify(
            message=message_content,
            context=context,
        )
        return intent_result["intent"], intent_result["confidence"]

    def _save_message_intent(self, message_id: str, intent: str) -> None:
        msg = self.db.query(WhatsAppMessage).get(message_id)
        if not msg:
            return

        try:
            msg.intent_detected = intent
            self.db.commit()
        except Exception as intent_save_error:
            logger.warning(f"Falha ao salvar intent na mensagem: {intent_save_error}")
            self.db.rollback()

    def _save_session_intent(self, session_id: str, intent: str) -> None:
        session = self.db.query(WhatsAppSession).get(session_id)
        if not session:
            return

        try:
            session.last_intent = intent
            self.db.commit()
        except Exception as session_save_error:
            logger.warning(f"Falha ao salvar intent na sessão: {session_save_error}")
            self.db.rollback()

    def _save_detected_intent(
        self, message_id: str, session_id: str, intent: str
    ) -> None:
        self._save_message_intent(message_id, intent)
        self._save_session_intent(session_id, intent)

    def _load_session_context(self, session: WhatsAppSession) -> Dict[str, Any]:
        try:
            parsed = json.loads(session.context or "{}")
            return parsed if isinstance(parsed, dict) else {}
        except (TypeError, ValueError):
            return {}

    def _save_session_context(
        self, session: WhatsAppSession, context: Dict[str, Any]
    ) -> None:
        session.context = json.dumps(context, ensure_ascii=False)
        self.db.commit()

    def _remember_catalog_search(
        self,
        session_id: str,
        catalog_query: str,
        function_result: Any,
    ) -> None:
        """Guarda o produto pesquisado para entender refinamentos na próxima fala."""
        if not getattr(self, "db", None):
            return
        session = self.db.query(WhatsAppSession).get(session_id)
        if not session:
            return

        data = (
            function_result.get("data") if isinstance(function_result, dict) else None
        )
        if not isinstance(data, dict):
            data = function_result if isinstance(function_result, dict) else {}
        products = data.get("produtos")
        if not isinstance(products, list):
            products = []

        session_context = self._load_session_context(session)
        session_context[CATALOG_SEARCH_CONTEXT_KEY] = {
            "query": catalog_query,
            "options": [
                {
                    "id": product.get("id"),
                    "nome": product.get("nome"),
                    "estoque": product.get("estoque"),
                    "preco": product.get("preco"),
                    "imagem_url": product.get("imagem_url") or "",
                }
                for product in products[:MAX_PRODUCT_IMAGES_PER_RESPONSE]
                if isinstance(product, dict)
            ],
        }
        self._save_session_context(session, session_context)

    def _resolve_catalog_followup(
        self, session_id: str, message_content: str
    ) -> Optional[str]:
        """Aplica peso/variação curta ao último produto consultado na sessão."""
        if not getattr(self, "db", None):
            return None
        session = self.db.query(WhatsAppSession).get(session_id)
        if not session:
            return None
        session_context = self._load_session_context(session)
        pending = session_context.get(CATALOG_SEARCH_CONTEXT_KEY)
        if not isinstance(pending, dict):
            return None
        return _catalog_followup_query(
            message_content,
            str(pending.get("query") or ""),
        )

    def _resolve_customer_for_session(self, session: WhatsAppSession):
        try:
            customer = resolve_session_customer(
                self.db,
                tenant_id=self.tenant_id,
                session=session,
            )
            if (
                customer
                and not session.cliente_id
                and not getattr(customer, "_remote_source", False)
            ):
                session.cliente_id = customer.id
                self.db.commit()
            return customer
        except Exception as customer_error:
            logger.warning(
                "Falha ao identificar cliente da sessão %s: %s",
                session.id,
                customer_error,
            )
            self.db.rollback()
            return None

    @staticmethod
    def _checkout_item(item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        product_id = item.get("product_id") or item.get("id")
        if product_id in (None, ""):
            return None
        return {
            "product_id": int(product_id),
            "name": str(item.get("name") or item.get("nome") or "Produto"),
            "quantity": float(item.get("quantity") or 1),
            "unit": str(item.get("unit") or "x"),
            "unit_price": item.get("unit_price") or item.get("preco"),
            "image_url": str(item.get("image_url") or item.get("imagem_url") or ""),
        }

    async def _start_order_checkout(
        self,
        *,
        session: WhatsAppSession,
        session_context: Dict[str, Any],
        items: list[Dict[str, Any]],
        source: str,
    ) -> Dict[str, Any]:
        checkout_items = [self._checkout_item(item) for item in items]
        if not checkout_items or any(item is None for item in checkout_items):
            return await self._send_response(
                session_id=session.id,
                response=(
                    "Antes de fechar, preciso identificar exatamente cada produto no "
                    "catálogo. Envie um produto por vez com o nome e a embalagem."
                ),
                intent="pedido_produto_nao_identificado",
                model_used="deterministic_checkout_missing_product",
                tokens_input=0,
                tokens_output=0,
                processing_time_ms=0,
            )

        requested_items = [
            {"product_id": item["product_id"], "quantity": item["quantity"]}
            for item in checkout_items
            if item is not None
        ]
        preview = fetch_remote_order_preview(
            self.tenant_id,
            phone=session.phone_number,
            items=requested_items,
        )
        if not preview or not preview.get("success"):
            rejection_detail = re.sub(
                r"\s+", " ", str((preview or {}).get("detail") or "")
            ).strip()
            if rejection_detail:
                return await self._transfer_to_human(
                    session_id=session.id,
                    reason="order_preview_rejected",
                    reason_details=rejection_detail,
                    customer_message=(
                        f"Não consigo continuar com este pedido: {rejection_detail} "
                        "Nenhuma venda foi lançada. Vou encaminhar você para um "
                        "atendente humano ajudar com uma alternativa. ⏳"
                    ),
                )
            return await self._send_response(
                session_id=session.id,
                response=(
                    "Não consegui preparar o resumo no CorePet agora. O pedido não foi "
                    "lançado. Pode tentar novamente em instantes."
                ),
                intent="pedido_preview_indisponivel",
                model_used="deterministic_checkout_preview_error",
                tokens_input=0,
                tokens_output=0,
                processing_time_ms=0,
            )

        payment_methods = preview.get("payment_methods") or []
        if not payment_methods:
            return await self._send_response(
                session_id=session.id,
                response=(
                    "Não encontrei formas de pagamento ativas no CorePet. O pedido não "
                    "foi lançado; primeiro é preciso configurar ao menos uma forma."
                ),
                intent="pedido_sem_forma_pagamento",
                model_used="deterministic_checkout_no_payment",
                tokens_input=0,
                tokens_output=0,
                processing_time_ms=0,
            )

        session_context[ORDER_CHECKOUT_CONTEXT_KEY] = {
            "stage": "fulfillment",
            "source": source,
            "items": requested_items,
            "preview": preview,
            "idempotency_key": str(uuid.uuid4()),
        }
        session_context.pop(ORDER_DRAFT_CONTEXT_KEY, None)
        session_context.pop(ORDER_ITEM_SELECTION_CONTEXT_KEY, None)
        self._save_session_context(session, session_context)
        return await self._send_response(
            session_id=session.id,
            response=(
                "Perfeito. Como você prefere receber?\n\n"
                "1. Entrega\n\n"
                "2. Retirada na loja\n\n"
                "Responda 1 ou 2."
            ),
            intent="pedido_escolha_entrega",
            model_used="deterministic_checkout_fulfillment",
            tokens_input=0,
            tokens_output=0,
            processing_time_ms=0,
        )

    async def _handle_pending_checkout(
        self,
        *,
        session: WhatsAppSession,
        session_context: Dict[str, Any],
        checkout: Dict[str, Any],
        message_content: str,
    ) -> Dict[str, Any]:
        if is_order_cancellation(message_content):
            session_context.pop(ORDER_CHECKOUT_CONTEXT_KEY, None)
            self._save_session_context(session, session_context)
            return await self._send_response(
                session_id=session.id,
                response="Certo, cancelei este fechamento. Nenhuma venda foi lançada.",
                intent="pedido_cancelado_antes_confirmacao",
                model_used="deterministic_checkout_cancel",
                tokens_input=0,
                tokens_output=0,
                processing_time_ms=0,
            )

        stage = str(checkout.get("stage") or "fulfillment")
        preview = checkout.get("preview") or {}
        if stage == "fulfillment":
            fulfillment = parse_fulfillment_choice(message_content)
            if not fulfillment:
                response = "Escolha 1 para entrega ou 2 para retirada na loja."
            else:
                checkout["fulfillment"] = fulfillment
                registered_address = str(
                    (preview.get("customer") or {}).get("delivery_address") or ""
                ).strip()
                if fulfillment == "delivery" and not registered_address:
                    checkout["stage"] = "delivery_address"
                    response = "Qual é o endereço completo para a entrega?"
                else:
                    if fulfillment == "delivery":
                        checkout["delivery_address"] = registered_address
                    checkout["stage"] = "payment"
                    response = payment_methods_message(
                        preview.get("payment_methods") or []
                    )
            self._save_session_context(session, session_context)
            return await self._send_response(
                session_id=session.id,
                response=response,
                intent="pedido_escolha_entrega",
                model_used="deterministic_checkout_fulfillment",
                tokens_input=0,
                tokens_output=0,
                processing_time_ms=0,
            )

        if stage == "delivery_address":
            delivery_address = re.sub(r"\s+", " ", message_content or "").strip()
            if len(delivery_address) < 8:
                response = "Envie o endereço completo para a entrega."
            else:
                checkout["delivery_address"] = delivery_address
                checkout["stage"] = "payment"
                response = payment_methods_message(preview.get("payment_methods") or [])
            self._save_session_context(session, session_context)
            return await self._send_response(
                session_id=session.id,
                response=response,
                intent="pedido_endereco_entrega",
                model_used="deterministic_checkout_address",
                tokens_input=0,
                tokens_output=0,
                processing_time_ms=0,
            )

        if stage == "payment":
            payment_method = parse_payment_choice(
                message_content, preview.get("payment_methods") or []
            )
            if not payment_method:
                response = payment_methods_message(preview.get("payment_methods") or [])
            else:
                checkout["payment_method"] = payment_method
                checkout["stage"] = "confirmation"
                response = build_checkout_summary(checkout)
            self._save_session_context(session, session_context)
            return await self._send_response(
                session_id=session.id,
                response=response,
                intent="pedido_escolha_pagamento",
                model_used="deterministic_checkout_payment",
                tokens_input=0,
                tokens_output=0,
                processing_time_ms=0,
            )

        if not is_final_order_confirmation(message_content):
            return await self._send_response(
                session_id=session.id,
                response=(
                    "A venda ainda não foi lançada. Responda OK ou CONFIRMAR para lançar ou "
                    "CANCELAR para desistir."
                ),
                intent="pedido_aguardando_confirmacao_final",
                model_used="deterministic_checkout_confirmation",
                tokens_input=0,
                tokens_output=0,
                processing_time_ms=0,
            )

        created = create_remote_order(
            self.tenant_id,
            phone=session.phone_number,
            items=checkout.get("items") or [],
            fulfillment=str(checkout.get("fulfillment") or "pickup"),
            payment_method=checkout.get("payment_method") or {},
            delivery_address=checkout.get("delivery_address"),
            idempotency_key=str(checkout.get("idempotency_key") or ""),
        )
        if not created or not created.get("success"):
            return await self._send_response(
                session_id=session.id,
                response=(
                    "Não consegui lançar a venda no CorePet agora. Nenhuma nova venda "
                    "foi confirmada; pode responder CONFIRMAR para tentar novamente."
                ),
                intent="pedido_criacao_indisponivel",
                model_used="deterministic_checkout_create_error",
                tokens_input=0,
                tokens_output=0,
                processing_time_ms=0,
            )

        session_context.pop(ORDER_CHECKOUT_CONTEXT_KEY, None)
        session_context.pop(ORDER_DRAFT_CONTEXT_KEY, None)
        session_context.pop(CATALOG_SEARCH_CONTEXT_KEY, None)
        self._save_session_context(session, session_context)
        fulfillment_label = (
            "entrega"
            if created.get("fulfillment") == "delivery"
            else "retirada na loja"
        )
        payment = created.get("payment_method") or checkout.get("payment_method") or {}
        lines = [
            f"Pronto! A venda {created.get('number')} foi lançada no CorePet como aberta para conferência.",
            f"Total dos produtos: {_format_brl(created.get('total'))}",
            f"Modalidade: {fulfillment_label}",
            f"Pagamento informado: {payment.get('name') or payment.get('nome') or payment.get('key')}",
            "Benefícios previstos após a finalização:",
            *benefits_lines(created.get("benefits") or []),
            "O pagamento ainda não foi marcado como recebido.",
        ]
        return await self._send_response(
            session_id=session.id,
            response="\n\n".join(lines),
            intent="pedido_venda_aberta_criada",
            model_used="deterministic_checkout_created",
            tokens_input=0,
            tokens_output=0,
            processing_time_ms=0,
        )

    async def _handle_order_checkout_flow(
        self,
        *,
        session: WhatsAppSession,
        session_context: Dict[str, Any],
        message_content: str,
    ) -> Optional[Dict[str, Any]]:
        pending_checkout = session_context.get(ORDER_CHECKOUT_CONTEXT_KEY)
        if isinstance(pending_checkout, dict):
            return await self._handle_pending_checkout(
                session=session,
                session_context=session_context,
                checkout=pending_checkout,
                message_content=message_content,
            )

        pending_selection = session_context.get(ORDER_ITEM_SELECTION_CONTEXT_KEY)
        if isinstance(pending_selection, dict):
            selected_text = re.sub(r"\D", "", message_content or "")
            options = pending_selection.get("options") or []
            if selected_text and len(selected_text) <= 2:
                selected_index = int(selected_text) - 1
                if 0 <= selected_index < len(options):
                    return await self._start_order_checkout(
                        session=session,
                        session_context=session_context,
                        items=[options[selected_index]],
                        source="catalog_selection",
                    )
            return await self._send_response(
                session_id=session.id,
                response="Escolha o número do produto que deseja comprar.",
                intent="pedido_escolha_produto",
                model_used="deterministic_checkout_product_selection",
                tokens_input=0,
                tokens_output=0,
                processing_time_ms=0,
            )

        if not is_order_checkout_request(message_content):
            return None

        catalog_context = session_context.get(CATALOG_SEARCH_CONTEXT_KEY)
        options = (
            catalog_context.get("options") if isinstance(catalog_context, dict) else []
        ) or []
        options = [
            option
            for option in options
            if isinstance(option, dict) and float(option.get("estoque") or 0) > 0
        ]
        if len(options) == 1:
            return await self._start_order_checkout(
                session=session,
                session_context=session_context,
                items=[options[0]],
                source="catalog_single_result",
            )
        if len(options) > 1:
            session_context[ORDER_ITEM_SELECTION_CONTEXT_KEY] = {"options": options}
            self._save_session_context(session, session_context)
            lines = ["Qual destes produtos você deseja comprar?"]
            lines.extend(
                f"{index}. {option.get('nome')} — {_format_brl(option.get('preco'))}"
                for index, option in enumerate(options, start=1)
            )
            lines.append("Responda com o número.")
            return await self._send_response(
                session_id=session.id,
                response="\n\n".join(lines),
                intent="pedido_escolha_produto",
                model_used="deterministic_checkout_product_selection",
                tokens_input=0,
                tokens_output=0,
                processing_time_ms=0,
                product_media=draft_product_media(options),
            )
        return await self._send_response(
            session_id=session.id,
            response=(
                "Qual produto você deseja comprar? Envie o nome e a embalagem para eu "
                "consultar o catálogo antes de fechar."
            ),
            intent="pedido_sem_produto_selecionado",
            model_used="deterministic_checkout_missing_selection",
            tokens_input=0,
            tokens_output=0,
            processing_time_ms=0,
        )

    async def _send_order_draft(
        self,
        *,
        session: WhatsAppSession,
        session_context: Dict[str, Any],
        items: list[Dict[str, Any]],
        source: str,
        from_history: bool,
    ) -> Dict[str, Any]:
        session_context[ORDER_DRAFT_CONTEXT_KEY] = {
            "source": source,
            "items": items,
        }
        session_context.pop(HISTORY_ITEM_SELECTION_CONTEXT_KEY, None)
        self._save_session_context(session, session_context)
        return await self._send_response(
            session_id=session.id,
            response=build_order_draft_message(
                items,
                from_history=from_history,
            ),
            intent="rascunho_pedido",
            model_used="deterministic_order_draft",
            tokens_input=0,
            tokens_output=0,
            processing_time_ms=0,
            product_media=draft_product_media(items),
        )

    async def _handle_single_item_order(
        self,
        *,
        session: WhatsAppSession,
        session_context: Dict[str, Any],
        requested_item: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Pesquisa um pedido unitário antes de decidir por atendimento humano."""
        catalog_query = str(requested_item.get("catalog_query") or "").strip()
        result = await self._execute_function(
            function_name="buscar_produto",
            arguments={"termo": catalog_query, "limit": 5},
            context={},
            session_id=session.id,
        )
        result = _filter_unavailable_catalog_products(result)
        self._remember_catalog_search(session.id, catalog_query, result)

        data = result.get("data") if isinstance(result, dict) else None
        if not isinstance(data, dict):
            data = result if isinstance(result, dict) else {}
        products = data.get("produtos")
        if not isinstance(products, list):
            products = []

        if not products:
            unavailable = bool(data.get("unavailable_found"))
            explanation = (
                f"Encontrei {catalog_query}, mas está sem estoque no momento."
                if unavailable
                else f"Não consegui identificar {catalog_query} no catálogo."
            )
            return await self._transfer_to_human(
                session_id=session.id,
                reason=(
                    "product_out_of_stock"
                    if unavailable
                    else "product_not_identified"
                ),
                reason_details=(
                    f"Pedido explícito não resolvido automaticamente: {catalog_query}"
                ),
                customer_message=(
                    f"{explanation} Vou encaminhar você para um atendente humano "
                    "continuar o atendimento. ⏳"
                ),
            )

        options = [
            {
                "product_id": product.get("id"),
                "name": str(product.get("nome") or "Produto"),
                "quantity": float(requested_item.get("quantity") or 1),
                "unit": str(requested_item.get("unit") or "x"),
                "unit_price": product.get("preco"),
                "image_url": str(product.get("imagem_url") or ""),
            }
            for product in products[:MAX_PRODUCT_IMAGES_PER_RESPONSE]
            if isinstance(product, dict) and product.get("id") not in (None, "")
        ]
        if len(options) == 1:
            return await self._send_order_draft(
                session=session,
                session_context=session_context,
                items=options,
                source="single_item_catalog",
                from_history=False,
            )

        session_context[HISTORY_ITEM_SELECTION_CONTEXT_KEY] = {
            "source": "single_item_catalog",
            "quantity": requested_item.get("quantity", 1),
            "unit": requested_item.get("unit") or "x",
            "options": options,
        }
        session_context.pop(ORDER_DRAFT_CONTEXT_KEY, None)
        self._save_session_context(session, session_context)
        options_text = "\n\n".join(
            f"{index}. {option['name']}"
            for index, option in enumerate(options, start=1)
        )
        return await self._send_response(
            session_id=session.id,
            response=(
                "Encontrei mais de uma opção para esse pedido:\n\n"
                f"{options_text}\n\nResponda com o número do produto."
            ),
            intent="clarificacao_item_catalogo",
            model_used="deterministic_catalog_order_selection",
            tokens_input=0,
            tokens_output=0,
            processing_time_ms=0,
            product_media=draft_product_media(options),
        )

    async def _handle_order_draft_flow(
        self, session_id: str, message_content: str
    ) -> Optional[Dict[str, Any]]:
        """Monta e confirma pedidos sem gravar uma venda automaticamente."""
        session = self.db.query(WhatsAppSession).get(session_id)
        if not session:
            return None

        session_context = self._load_session_context(session)
        checkout_result = await self._handle_order_checkout_flow(
            session=session,
            session_context=session_context,
            message_content=message_content,
        )
        if checkout_result:
            return checkout_result

        pending_selection = session_context.get(HISTORY_ITEM_SELECTION_CONTEXT_KEY)
        if isinstance(pending_selection, dict):
            normalized_reply = re.sub(r"[^0-9]", "", message_content or "")
            options = pending_selection.get("options") or []
            if normalized_reply and len(normalized_reply) <= 2:
                selected_index = int(normalized_reply) - 1
                if 0 <= selected_index < len(options):
                    selected = dict(options[selected_index])
                    selected["quantity"] = pending_selection.get("quantity", 1)
                    selected["unit"] = pending_selection.get("unit") or "x"
                    selection_source = str(
                        pending_selection.get("source") or "history_quantity"
                    )
                    return await self._send_order_draft(
                        session=session,
                        session_context=session_context,
                        items=[selected],
                        source=selection_source,
                        from_history=selection_source != "single_item_catalog",
                    )
            if _confirmation_reply(message_content) is not None:
                return await self._send_response(
                    session_id=session_id,
                    response="Escolha o número do produto da lista para eu montar o pedido.",
                    intent="clarificacao_item_historico",
                    model_used="deterministic_history_selection",
                    tokens_input=0,
                    tokens_output=0,
                    processing_time_ms=0,
                    product_media=draft_product_media(options),
                )

        pending_draft = session_context.get(ORDER_DRAFT_CONTEXT_KEY)
        if isinstance(pending_draft, dict):
            confirmation = _confirmation_reply(message_content)
            if confirmation is True:
                items = pending_draft.get("items") or []
                source = str(pending_draft.get("source") or "whatsapp")
                return await self._start_order_checkout(
                    session=session,
                    session_context=session_context,
                    items=items,
                    source=source,
                )
            if confirmation is False:
                session_context.pop(ORDER_DRAFT_CONTEXT_KEY, None)
                self._save_session_context(session, session_context)
                return await self._send_response(
                    session_id=session_id,
                    response="Certo. Envie a lista completa corrigida, com a quantidade de cada item.",
                    intent="correcao_rascunho_pedido",
                    model_used="deterministic_order_correction",
                    tokens_input=0,
                    tokens_output=0,
                    processing_time_ms=0,
                )
            if any(
                term in _normalize_text(message_content)
                for term in ("alterar", "corrigir", "troca o item", "muda o item")
            ):
                return await self._send_response(
                    session_id=session_id,
                    response="Envie a lista completa corrigida, com a quantidade de cada item.",
                    intent="correcao_rascunho_pedido",
                    model_used="deterministic_order_correction",
                    tokens_input=0,
                    tokens_output=0,
                    processing_time_ms=0,
                )

        multi_items = extract_multi_item_order(message_content)
        if multi_items:
            return await self._send_order_draft(
                session=session,
                session_context=session_context,
                items=multi_items,
                source="multi_item_message",
                from_history=False,
            )

        single_item = extract_single_item_order(message_content)
        if single_item:
            return await self._handle_single_item_order(
                session=session,
                session_context=session_context,
                requested_item=single_item,
            )

        quantity_request = extract_history_quantity_request(message_content)
        if not quantity_request and not is_generic_reorder_request(message_content):
            return None

        customer = self._resolve_customer_for_session(session)
        if not customer:
            return await self._send_response(
                session_id=session_id,
                response=(
                    "Não encontrei compras vinculadas a este número no CorePet. "
                    "Se quiser, me diga qual produto você procura e eu consulto o catálogo."
                ),
                intent="recompra_cliente_nao_identificado",
                model_used="deterministic_reorder_not_identified",
                tokens_input=0,
                tokens_output=0,
                processing_time_ms=0,
            )

        try:
            purchase = load_latest_purchase(
                self.db,
                tenant_id=self.tenant_id,
                customer_id=customer.id,
            )
        except Exception as history_error:
            logger.warning("Falha ao consultar última compra: %s", history_error)
            self.db.rollback()
            purchase = None
        if not purchase:
            return await self._send_response(
                session_id=session_id,
                response=(
                    "Não encontrei uma compra concluída vinculada a este número. "
                    "Se quiser, me diga qual produto você procura e eu consulto o catálogo."
                ),
                intent="recompra_historico_nao_encontrado",
                model_used="deterministic_reorder_history_not_found",
                tokens_input=0,
                tokens_output=0,
                processing_time_ms=0,
            )

        items = purchase_items_as_draft(purchase)
        if quantity_request and len(items) > 1:
            session_context[HISTORY_ITEM_SELECTION_CONTEXT_KEY] = {
                "quantity": quantity_request["quantity"],
                "unit": quantity_request["unit"],
                "options": items,
            }
            self._save_session_context(session, session_context)
            options_text = "\n\n".join(
                f"{index}. {format_draft_item(item)}"
                for index, item in enumerate(items, start=1)
            )
            return await self._send_response(
                session_id=session_id,
                response=(
                    "Encontrei estes itens na sua compra mais recente. "
                    "De qual deles você quer "
                    f"{int(quantity_request['quantity']) if quantity_request['quantity'].is_integer() else quantity_request['quantity']} "
                    f"{quantity_request['unit']}?\n\n{options_text}\n\nResponda com o número."
                ),
                intent="clarificacao_item_historico",
                model_used="deterministic_history_selection",
                tokens_input=0,
                tokens_output=0,
                processing_time_ms=0,
                product_media=draft_product_media(items),
            )

        if quantity_request and items:
            items[0]["quantity"] = quantity_request["quantity"]
            items[0]["unit"] = quantity_request["unit"]

        return await self._send_order_draft(
            session=session,
            session_context=session_context,
            items=items,
            source="purchase_history",
            from_history=True,
        )

    async def _handle_real_operational_request(
        self,
        *,
        session_id: str,
        message_content: str,
        reason: str,
    ) -> Optional[Dict[str, Any]]:
        """Responde usando o CorePet; retorna None quando falta dado confiável."""
        try:
            if reason == "store_hours":
                hours = load_store_hours(self.db, tenant_id=self.tenant_id)
                if not hours:
                    return None
                return await self._send_response(
                    session_id=session_id,
                    response=(
                        "O horário cadastrado no CorePet é das "
                        f"{hours['start']} às {hours['end']}."
                    ),
                    intent="consulta_horario_loja",
                    model_used="corepet_store_hours",
                    tokens_input=0,
                    tokens_output=0,
                    processing_time_ms=0,
                )

            if reason not in {"delivery_status", "loyalty_or_credit"}:
                return None

            session = self.db.query(WhatsAppSession).get(session_id)
            if not session:
                return None
            customer = self._resolve_customer_for_session(session)
            if not customer:
                return None

            if reason == "delivery_status":
                delivery = load_latest_delivery(
                    self.db,
                    tenant_id=self.tenant_id,
                    customer_id=customer.id,
                )
                response = _delivery_status_response(delivery) if delivery else None
                if not response:
                    return None
                return await self._send_response(
                    session_id=session_id,
                    response=response,
                    intent="consulta_status_entrega",
                    model_used="corepet_delivery_status",
                    tokens_input=0,
                    tokens_output=0,
                    processing_time_ms=0,
                )

            benefits = load_customer_benefits(
                self.db,
                tenant_id=self.tenant_id,
                customer=customer,
            )
            response = _customer_benefits_response(benefits, message_content)
            if not response:
                return None
            return await self._send_response(
                session_id=session_id,
                response=response,
                intent="consulta_beneficios_cliente",
                model_used="corepet_customer_benefits",
                tokens_input=0,
                tokens_output=0,
                processing_time_ms=0,
            )
        except Exception as operational_error:
            logger.warning(
                "Falha na consulta operacional %s: %s",
                reason,
                operational_error,
            )
            self.db.rollback()
            return None

    async def _get_gold_clarification_media(
        self, session_id: str, original_query: str
    ) -> list[Dict[str, str]]:
        """Busca no catálogo uma foto representativa para cada opção de marca."""
        media: list[Dict[str, str]] = []
        for choice, brand in GOLD_BRAND_OPTIONS.items():
            result = await self._execute_function(
                function_name="buscar_produto",
                arguments={
                    "termo": _gold_catalog_query(original_query, brand),
                    "limit": 1,
                },
                context={},
                session_id=session_id,
            )
            candidates = _extract_product_media(result)
            matching_candidate = next(
                (
                    candidate
                    for candidate in candidates
                    if _gold_brand_matches_product_caption(
                        brand, candidate.get("caption", "")
                    )
                ),
                None,
            )
            if not matching_candidate:
                continue
            media.append(
                {
                    "image_url": matching_candidate["image_url"],
                    "caption": f"{choice}. {brand}",
                }
            )
        return media

    def _find_recent_gold_purchase(
        self, session: WhatsAppSession, original_query: str
    ) -> Optional[str]:
        """Retorna a compra Gold mais recente do cliente, respeitando peso e tenant."""
        if not session.cliente_id:
            return None

        from sqlalchemy import func

        from app.produtos_models import Produto
        from app.vendas_models import Venda, VendaItem

        try:
            with whatsapp_tenant_context(self.tenant_id):
                query = (
                    self.db.query(Produto.nome)
                    .join(VendaItem, VendaItem.produto_id == Produto.id)
                    .join(Venda, Venda.id == VendaItem.venda_id)
                    .filter(
                        Produto.tenant_id == self.tenant_id,
                        VendaItem.tenant_id == self.tenant_id,
                        Venda.tenant_id == self.tenant_id,
                        Venda.cliente_id == session.cliente_id,
                        Venda.status != "cancelada",
                        VendaItem.tipo == "produto",
                        Produto.situacao.is_(True),
                        Produto.nome.ilike("%gold%"),
                    )
                )

                weight_match = re.search(
                    r"\b\d+(?:[.,]\d+)?\s*kg\b",
                    _normalize_text(original_query),
                )
                if weight_match:
                    normalized_weight = weight_match.group(0).replace(" ", "")
                    query = query.filter(
                        func.replace(func.lower(Produto.nome), " ", "").like(
                            f"%{normalized_weight}%"
                        )
                    )

                recent = query.order_by(
                    Venda.data_venda.desc(), VendaItem.id.desc()
                ).first()
                return str(recent.nome).strip() if recent and recent.nome else None
        except Exception as history_error:
            logger.warning(
                "Falha ao consultar histórico de produto da sessão %s: %s",
                session.id,
                history_error,
            )
            self.db.rollback()
            return None

    async def _get_recent_purchase_media(
        self, session_id: str, product_name: str
    ) -> list[Dict[str, str]]:
        result = await self._execute_function(
            function_name="buscar_produto",
            arguments={"termo": product_name, "limit": 5},
            context={},
            session_id=session_id,
        )
        media = _extract_product_media(result)
        if not media:
            return []

        normalized_name = _normalize_text(product_name)
        exact = next(
            (
                item
                for item in media
                if _normalize_text(item.get("caption", "").split(" — ", 1)[0])
                == normalized_name
            ),
            media[0],
        )
        return [{"image_url": exact["image_url"], "caption": product_name}]

    async def _send_gold_brand_clarification(
        self,
        session_id: str,
        original_query: str,
    ) -> Dict[str, Any]:
        return await self._send_response(
            session_id=session_id,
            response=GOLD_CLARIFICATION_MESSAGE,
            intent="clarificacao_produto",
            model_used="deterministic_clarification",
            tokens_input=0,
            tokens_output=0,
            processing_time_ms=0,
            product_media=await self._get_gold_clarification_media(
                session_id, original_query
            ),
        )

    async def _handle_product_clarification(
        self, session_id: str, message_content: str
    ) -> tuple[Optional[Dict[str, Any]], str, bool]:
        """Conduz ambiguidades de produto em etapas, antes de consultar a IA."""
        session = self.db.query(WhatsAppSession).get(session_id)
        if not session:
            return None, message_content, False

        session_context = self._load_session_context(session)
        pending = session_context.get("pending_product_clarification")
        if (
            isinstance(pending, dict)
            and pending.get("type") == "recent_gold_confirmation"
        ):
            original_query = str(pending.get("original_query") or "ração Gold")
            product_name = str(pending.get("product_name") or "").strip()
            brand = _gold_brand_from_reply(message_content)
            if brand:
                session_context.pop("pending_product_clarification", None)
                self._save_session_context(session, session_context)
                current_measurements = _extract_explicit_measurements(message_content)
                detailed_query = " ".join(
                    [
                        (
                            _remove_explicit_measurements(original_query)
                            if current_measurements
                            else original_query
                        ),
                        *current_measurements,
                    ]
                )
                return None, _gold_catalog_query(detailed_query, brand), True

            confirmation = _confirmation_reply(message_content)
            if confirmation is True and product_name:
                session_context.pop("pending_product_clarification", None)
                self._save_session_context(session, session_context)
                return None, product_name, True

            if confirmation is False:
                session_context["pending_product_clarification"] = {
                    "type": "gold_brand",
                    "original_query": original_query,
                }
                self._save_session_context(session, session_context)
                return (
                    await self._send_gold_brand_clarification(
                        session_id, original_query
                    ),
                    message_content,
                    False,
                )

            return (
                await self._send_response(
                    session_id=session_id,
                    response=_recent_purchase_confirmation_message(product_name),
                    intent="clarificacao_produto_historico",
                    model_used="deterministic_purchase_history",
                    tokens_input=0,
                    tokens_output=0,
                    processing_time_ms=0,
                    product_media=await self._get_recent_purchase_media(
                        session_id, product_name
                    ),
                ),
                message_content,
                False,
            )

        if isinstance(pending, dict) and pending.get("type") == "gold_brand":
            brand = _gold_brand_from_reply(message_content)
            if brand:
                original_query = str(pending.get("original_query") or "ração Gold")
                session_context.pop("pending_product_clarification", None)
                self._save_session_context(session, session_context)
                current_measurements = _extract_explicit_measurements(message_content)
                detailed_query = " ".join(
                    [
                        (
                            _remove_explicit_measurements(original_query)
                            if current_measurements
                            else original_query
                        ),
                        *current_measurements,
                    ]
                )
                return None, _gold_catalog_query(detailed_query, brand), True

            original_query = str(pending.get("original_query") or "ração Gold")
            return (
                await self._send_gold_brand_clarification(session_id, original_query),
                message_content,
                False,
            )

        if not _is_generic_gold_query(message_content):
            return None, message_content, False

        recent_product = self._find_recent_gold_purchase(session, message_content)
        if recent_product:
            session_context["pending_product_clarification"] = {
                "type": "recent_gold_confirmation",
                "original_query": message_content,
                "product_name": recent_product,
            }
            self._save_session_context(session, session_context)
            return (
                await self._send_response(
                    session_id=session_id,
                    response=_recent_purchase_confirmation_message(recent_product),
                    intent="clarificacao_produto_historico",
                    model_used="deterministic_purchase_history",
                    tokens_input=0,
                    tokens_output=0,
                    processing_time_ms=0,
                    product_media=await self._get_recent_purchase_media(
                        session_id, recent_product
                    ),
                ),
                message_content,
                False,
            )

        session_context["pending_product_clarification"] = {
            "type": "gold_brand",
            "original_query": message_content,
        }
        self._save_session_context(session, session_context)
        return (
            await self._send_gold_brand_clarification(session_id, message_content),
            message_content,
            False,
        )

    async def _maybe_transfer_to_human(
        self,
        session_id: str,
        message_content: str,
        intent: str,
        confidence: float,
    ) -> Optional[Dict[str, Any]]:
        if self._is_explicit_human_request(message_content):
            return await self._transfer_to_human(
                session_id=session_id,
                reason="manual_request",
                reason_details="Pedido explícito do cliente por atendente humano",
            )

        if self.router.should_transfer_to_human(intent, confidence):
            return await self._transfer_to_human(session_id, intent)

        return None

    async def _send_basic_mode_response(
        self, session_id: str, intent: str
    ) -> Dict[str, Any]:
        return await self._send_response(
            session_id=session_id,
            response=(
                "Recebi sua mensagem e já vou te ajudar. "
                "No momento estou em modo básico e em seguida um atendente assume se necessário."
            ),
            intent=intent,
            model_used="fallback_no_openai",
            tokens_input=0,
            tokens_output=0,
            processing_time_ms=0,
        )

    async def _handle_processing_error(
        self, session_id: str, error: Exception
    ) -> Dict[str, Any]:
        logger.error(f"❌ Erro ao processar mensagem: {error}")
        self.db.rollback()
        fallback_message = await send_whatsapp_message(
            db=self.db,
            tenant_id=self.tenant_id,
            session_id=session_id,
            message="Recebi sua mensagem e já estou te atendendo. Pode me enviar novamente em texto curto?",
        )
        if fallback_message:
            return {"action": "fallback_responded", "error": str(error)}
        return {"action": "error", "error": str(error)}

    async def process_message(
        self, session_id: str, message_id: str, message_content: str
    ) -> Dict[str, Any]:
        with whatsapp_tenant_context(self.tenant_id):
            return await self._process_message_with_context(
                session_id=session_id,
                message_id=message_id,
                message_content=message_content,
            )

    async def _process_message_with_context(
        self, session_id: str, message_id: str, message_content: str
    ) -> Dict[str, Any]:
        """
        Processa mensagem completa.

        Args:
            session_id: ID da sessão
            message_id: ID da mensagem no banco
            message_content: Conteúdo da mensagem

        Returns:
            Resultado do processamento
        """
        start_time = datetime.utcnow()

        try:
            logger.info(f"🔄 Processando mensagem: session={session_id}")

            # 0. Verificar se auto-response está habilitado
            if not self.config.auto_response_enabled:
                logger.info("Auto-response desabilitado")
                return {"action": "skipped", "reason": "auto_response_disabled"}

            order_draft_result = await self._handle_order_draft_flow(
                session_id=session_id,
                message_content=message_content,
            )
            if order_draft_result:
                self._save_detected_intent(
                    message_id,
                    session_id,
                    str(order_draft_result.get("reason") or "rascunho_pedido"),
                )
                return order_draft_result

            operational_handoff = _operational_handoff_reason(message_content)
            if operational_handoff:
                reason, reason_details = operational_handoff
                self._save_detected_intent(message_id, session_id, reason)
                operational_result = await self._handle_real_operational_request(
                    session_id=session_id,
                    message_content=message_content,
                    reason=reason,
                )
                if operational_result:
                    return operational_result
                return await self._transfer_to_human(
                    session_id=session_id,
                    reason=reason,
                    reason_details=reason_details,
                )

            if _is_contextless_product_photo_request(message_content):
                self._save_detected_intent(
                    message_id, session_id, "clarificacao_foto_produto"
                )
                return await self._send_response(
                    session_id=session_id,
                    response=("Claro. De qual produto você gostaria de ver as fotos?"),
                    intent="clarificacao_foto_produto",
                    model_used="deterministic_photo_clarification",
                    tokens_input=0,
                    tokens_output=0,
                    processing_time_ms=0,
                )

            image_response = _image_identification_response(message_content)
            if image_response:
                return await self._send_response(
                    session_id=session_id,
                    response=image_response,
                    intent="identificacao_imagem",
                    model_used="deterministic_image_identification",
                    tokens_input=0,
                    tokens_output=0,
                    processing_time_ms=0,
                )

            image_catalog_query = _image_catalog_query(message_content)
            if image_catalog_query:
                message_content = image_catalog_query

            catalog_followup_query = self._resolve_catalog_followup(
                session_id, message_content
            )
            if catalog_followup_query:
                message_content = catalog_followup_query

            product_choice_query = _product_query_from_choice_phrase(
                _strip_audio_marker(message_content)
            )
            if product_choice_query:
                message_content = product_choice_query

            (
                clarification_result,
                message_content,
                product_query_resolved,
            ) = await self._handle_product_clarification(
                session_id=session_id,
                message_content=message_content,
            )
            if clarification_result:
                return clarification_result
            product_query_resolved = bool(
                product_query_resolved
                or image_catalog_query
                or catalog_followup_query
                or product_choice_query
            )

            # 1. Construir contexto
            context = await self._build_context(session_id, message_content)

            # 2. Classificar intenção
            if product_query_resolved:
                intent, confidence = "consulta_produto", 1.0
            else:
                intent, confidence = await self._detect_intent(message_content, context)

            # Atualizar mensagem e sessão com intent detectado
            self._save_detected_intent(message_id, session_id, intent)

            # 3. Verificar se deve transferir para humano
            transfer_result = await self._maybe_transfer_to_human(
                session_id=session_id,
                message_content=message_content,
                intent=intent,
                confidence=confidence,
            )
            if transfer_result:
                return transfer_result

            # 4. Resposta rápida (sem IA) para intents simples
            quick_response = self.router.get_quick_response(
                intent, bot_name=self.config.bot_name or "Assistente"
            )

            if quick_response:
                return await self._send_response(
                    session_id=session_id,
                    response=quick_response,
                    intent=intent,
                    model_used="quick_response",
                    tokens_input=0,
                    tokens_output=0,
                    processing_time_ms=0,
                )

            # 5. Processar com IA
            if not self.ai_enabled:
                return await self._send_basic_mode_response(session_id, intent)

            return await self._process_with_ai(
                session_id=session_id,
                message_content=message_content,
                context=context,
                intent=intent,
                catalog_query_override=(
                    message_content if product_query_resolved else None
                ),
            )

        except Exception as e:
            return await self._handle_processing_error(session_id, e)

        finally:
            # Registrar métrica
            processing_time = (datetime.utcnow() - start_time).total_seconds()
            await self._log_metric("processing_time", processing_time)

    # ========================================================================
    # PROCESSAMENTO COM IA
    # ========================================================================

    async def _process_with_ai(
        self,
        session_id: str,
        message_content: str,
        context: Dict[str, Any],
        intent: str,
        catalog_query_override: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Processa mensagem com IA (GPT).
        """
        try:
            # 1. Construir system prompt
            system_prompt = PromptBuilder.build_system_prompt(context)

            # 2. Construir histórico
            history_messages = PromptBuilder.format_conversation_history(
                context.get("historico_conversa", [])
            )

            # 3. Mensagem atual
            current_message = {"role": "user", "content": message_content}

            # 4. Montar messages completo
            messages = [
                {"role": "system", "content": system_prompt},
                *history_messages,
                current_message,
            ]

            if catalog_query_override:
                return await self._handle_deterministic_product_lookup(
                    session_id=session_id,
                    catalog_query=catalog_query_override,
                    context=context,
                )

            # 5. Decidir modelo
            model = None
            if self.router.should_use_advanced_model(intent, context):
                model = self.llm_client.advanced_model

            # 6. Chamar LLM
            response = await self.llm_client.chat_completion(
                messages=messages,
                model=model,
                temperature=0.7,
                max_tokens=500,
                functions=AVAILABLE_FUNCTIONS_PHASE1_READ_ONLY,
                function_call=_tool_choice_for_intent(intent),
            )

            # 7. Verificar se chamou function
            if response.get("tool_calls"):
                return await self._handle_function_calls(
                    session_id=session_id,
                    tool_calls=response["tool_calls"],
                    context=context,
                    messages=messages,
                    response=response,
                )

            # 8. Resposta direta (sem function call)
            return await self._send_response(
                session_id=session_id,
                response=response["content"],
                intent=intent,
                model_used=response["model_used"],
                tokens_input=response["tokens_input"],
                tokens_output=response["tokens_output"],
                processing_time_ms=response["processing_time_ms"],
            )

        except Exception as e:
            logger.error(f"Erro no processamento IA: {e}")
            self.db.rollback()
            # Fallback
            return await self._send_response(
                session_id=session_id,
                response="Desculpe, tive um problema técnico. Pode repetir sua pergunta? 🙏",
                intent=intent,
                model_used="fallback",
                tokens_input=0,
                tokens_output=0,
                processing_time_ms=0,
            )

    # ========================================================================
    # FUNCTION CALLING
    # ========================================================================

    async def _handle_deterministic_product_lookup(
        self, session_id: str, catalog_query: str, context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Lista resultados reais sem permitir que a IA presuma uma compra."""
        result = await self._execute_function(
            function_name="buscar_produto",
            arguments={"termo": catalog_query},
            context=context,
            session_id=session_id,
        )
        result = _filter_unavailable_catalog_products(result)
        self._remember_catalog_search(session_id, catalog_query, result)

        return await self._send_response(
            session_id=session_id,
            response=_build_catalog_response(result, catalog_query),
            intent="function_executed",
            model_used="deterministic_catalog",
            tokens_input=0,
            tokens_output=0,
            processing_time_ms=0,
            product_media=_extract_product_media(result),
        )

    async def _handle_function_calls(
        self,
        session_id: str,
        tool_calls: list,
        context: Dict,
        messages: list,
        response: Dict,
    ) -> Dict[str, Any]:
        """
        Executa function calls e retorna resposta final.
        """
        logger.info(f"🔧 Function calls: {[tc['function'] for tc in tool_calls]}")

        # Executar cada function
        function_results = []
        product_media: list[Dict[str, str]] = []
        catalog_result: Optional[Dict[str, Any]] = None
        catalog_query = "produto solicitado"

        for tool_call in tool_calls:
            function_name = tool_call["function"]
            arguments = dict(tool_call["arguments"])
            if function_name == "buscar_produto":
                arguments["termo"] = _preserve_explicit_measurements(
                    str(arguments.get("termo") or "produto"), messages
                )
                # A categoria sugerida pela IA pode não refletir a categoria
                # cadastrada no ERP e já ocultou embalagens exatas no piloto.
                arguments.pop("categoria", None)

            # Executar function
            result = await self._execute_function(
                function_name=function_name,
                arguments=arguments,
                context=context,
                session_id=session_id,
            )
            if function_name == "buscar_produto":
                result = _filter_unavailable_catalog_products(result)
            product_media.extend(_extract_product_media(result))
            if function_name == "buscar_produto" and isinstance(result, dict):
                catalog_result = result
                catalog_query = str(arguments.get("termo") or catalog_query).strip()

            function_results.append(
                {
                    "tool_call_id": tool_call["id"],
                    "role": "tool",
                    "name": function_name,
                    "content": str(result),
                }
            )

        if catalog_result is not None:
            self._remember_catalog_search(session_id, catalog_query, catalog_result)
            return await self._send_response(
                session_id=session_id,
                response=_build_catalog_response(catalog_result, catalog_query),
                intent="function_executed",
                model_used=response.get("model_used") or "deterministic_catalog",
                tokens_input=response.get("tokens_input", 0),
                tokens_output=response.get("tokens_output", 0),
                processing_time_ms=response.get("processing_time_ms", 0),
                product_media=product_media,
            )

        # Chamar IA novamente com resultados das functions
        # OBRIGATÓRIO: adicionar primeiro a mensagem do assistente com tool_calls
        # (a API da OpenAI exige que toda mensagem "tool" seja precedida por
        #  uma mensagem "assistant" contendo os tool_calls correspondentes)
        messages.append(
            {
                "role": "assistant",
                "content": response.get("content"),
                "tool_calls": [
                    {
                        "id": tc["id"],
                        "type": "function",
                        "function": {
                            "name": tc["function"],
                            "arguments": json.dumps(
                                tc["arguments"], ensure_ascii=False
                            ),
                        },
                    }
                    for tc in tool_calls
                ],
            }
        )
        messages.extend(function_results)

        if product_media and messages and messages[0].get("role") == "system":
            messages[0]["content"] += (
                "\n\nAs fotos dos produtos serão enviadas pelo sistema como anexos do "
                "WhatsApp. Não inclua URLs nem sintaxe Markdown de imagem na resposta."
            )

        final_response = await self.llm_client.chat_completion(
            messages=messages, temperature=0.7, max_tokens=500
        )

        # Enviar resposta final
        return await self._send_response(
            session_id=session_id,
            response=final_response["content"],
            intent="function_executed",
            model_used=final_response["model_used"],
            tokens_input=response["tokens_input"] + final_response["tokens_input"],
            tokens_output=response["tokens_output"] + final_response["tokens_output"],
            processing_time_ms=response["processing_time_ms"]
            + final_response["processing_time_ms"],
            product_media=product_media,
        )

    async def _execute_function(
        self, function_name: str, arguments: Dict, context: Dict, session_id: str
    ) -> Any:
        """
        Executa function call usando handlers reais.
        """
        logger.info(f"🔧 Executando function: {function_name}({arguments})")

        # Importar handlers
        from app.whatsapp.function_handlers import execute_function

        # Executar function real
        try:
            result = execute_function(
                function_name=function_name,
                db=self.db,
                tenant_id=self.tenant_id,
                session_id=session_id,
                **arguments,
            )

            logger.info(f"✅ Function {function_name} executada: {result}")
            return result

        except Exception as e:
            logger.error(f"❌ Erro ao executar {function_name}: {e}")
            return {"error": str(e)}

    # ========================================================================
    # HELPERS
    # ========================================================================

    async def _send_response(
        self,
        session_id: str,
        response: str,
        intent: str,
        model_used: str,
        tokens_input: int,
        tokens_output: int,
        processing_time_ms: int,
        product_media: Optional[list[Dict[str, str]]] = None,
    ) -> Dict[str, Any]:
        """
        Envia resposta via WhatsApp e registra no banco.
        """
        unique_media: list[Dict[str, str]] = []
        seen_urls: set[str] = set()
        for item in product_media or []:
            image_url = str(item.get("image_url") or "").strip()
            if not image_url or image_url in seen_urls:
                continue
            seen_urls.add(image_url)
            unique_media.append(item)

        unique_media = unique_media[:MAX_PRODUCT_IMAGES_PER_RESPONSE]
        clean_response = _clean_response_image_links(response, unique_media)

        # Enviar texto via WhatsApp
        message = await send_whatsapp_message(
            db=self.db,
            tenant_id=self.tenant_id,
            session_id=session_id,
            message=clean_response,
        )

        if not message:
            logger.error("Falha ao enviar mensagem")
            return {"action": "error", "error": "send_failed"}

        # Atualizar mensagem com métricas de IA
        message.model_used = model_used
        message.tokens_input = tokens_input
        message.tokens_output = tokens_output
        message.processing_time_ms = processing_time_ms
        self.db.commit()

        images_sent = 0
        for item in unique_media:
            image_message = await send_whatsapp_message(
                db=self.db,
                tenant_id=self.tenant_id,
                session_id=session_id,
                message=item.get("caption") or "Foto do produto",
                message_type="image",
                image_url=item["image_url"],
            )
            if image_message:
                images_sent += 1
            else:
                logger.warning("Falha ao enviar imagem de produto")

        # Registrar métricas
        await self._log_metric("message_sent", 1)
        await self._log_metric("tokens_used", tokens_input + tokens_output)

        logger.info(
            "✅ Resposta enviada: %s chars, %s imagens",
            len(clean_response),
            images_sent,
        )

        return {
            "action": "responded",
            "message_id": message.id,
            "intent": intent,
            "model": model_used,
            "tokens": tokens_input + tokens_output,
            "images_sent": images_sent,
        }

    async def _transfer_to_human(
        self,
        session_id: str,
        reason: str,
        reason_details: Optional[str] = None,
        customer_message: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Transfere conversa para atendente humano.
        """
        session = self.db.query(WhatsAppSession).get(session_id)
        handoff = None

        if session:
            session.status = "waiting_human"

            handoff_manager = HandoffManager(self.db, self.tenant_id)
            existing_handoff = handoff_manager.get_active_handoff(session_id)

            if existing_handoff:
                handoff = existing_handoff
            else:
                handoff = handoff_manager.create_handoff(
                    session_id=session_id,
                    phone_number=session.phone_number,
                    reason=reason,
                    priority=(
                        "high"
                        if reason in {"reclamacao", "manual_request"}
                        else "medium"
                    ),
                    reason_details=reason_details
                    or f"Transferência automática por intent: {reason}",
                )

            self.db.commit()

        transfer_messages = {
            "medical_guidance": (
                "Para a segurança do seu pet, não vou indicar medicamento sem "
                "avaliação. Vou chamar um atendente para orientar o próximo passo. ⏳"
            ),
            "delivery_status": (
                "Vou chamar um atendente para verificar sua entrega. Um momento, por favor. ⏳"
            ),
        }

        # Enviar mensagem de transferência
        await send_whatsapp_message(
            db=self.db,
            tenant_id=self.tenant_id,
            session_id=session_id,
            message=transfer_messages.get(
                reason,
                customer_message
                or "Um momento! Estou transferindo você para um atendente humano. ⏳",
            ),
        )

        logger.info(f"👤 Transferido para humano: {reason}")

        return {
            "action": "transferred_to_human",
            "reason": reason,
            "handoff_id": str(handoff.id) if handoff else None,
        }

    async def _log_metric(self, metric_type: str, value: float):
        with whatsapp_tenant_context(self.tenant_id):
            return await self._log_metric_with_context(metric_type, value)

    async def _log_metric_with_context(self, metric_type: str, value: float):
        """Registra métrica no banco."""
        try:
            metric = WhatsAppMetric(
                tenant_id=self.tenant_id,
                metric_type=metric_type,
                value=value,
                timestamp=datetime.utcnow(),
            )
            self.db.add(metric)
            self.db.commit()
        except Exception as e:
            logger.warning(f"Erro ao registrar métrica: {e}")
