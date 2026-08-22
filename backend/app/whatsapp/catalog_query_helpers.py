"""Interpretacao pura de consultas de catalogo recebidas pelo WhatsApp."""

import re
import unicodedata
from typing import Optional


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


def _special_catalog_request_query(
    message: str,
    *,
    request_type: str,
) -> tuple[bool, str]:
    """Extrai o produto de perguntas sobre validade ou opções de embalagem."""
    normalized = _normalize_text(_strip_audio_marker(message))
    if request_type == "validity":
        requested = bool(
            re.search(
                r"\b(validade|vencimento|vence|vencer|data de validade)\b",
                normalized,
            )
        )
        stop_words = {
            "qual",
            "quais",
            "a",
            "o",
            "as",
            "os",
            "da",
            "do",
            "das",
            "dos",
            "de",
            "dessa",
            "desse",
            "desta",
            "deste",
            "essa",
            "esse",
            "validade",
            "vencimento",
            "vence",
            "vencer",
            "data",
            "quando",
            "tem",
            "me",
            "informa",
            "informar",
        }
    elif request_type == "weights":
        requested = bool(
            re.search(
                r"\b(quais?|opcoes?)\b.{0,18}\b(pesos?|tamanhos?|embalagens?)\b",
                normalized,
            )
            or re.search(
                r"\btem\b.{0,22}\bquantos?\s*(?:kg|quilo|quilos)?\b",
                normalized,
            )
            or re.search(
                r"\b(?:pesos?|tamanhos?|embalagens?)\s+disponiveis\b", normalized
            )
        )
        stop_words = {
            "qual",
            "quais",
            "que",
            "a",
            "o",
            "as",
            "os",
            "da",
            "do",
            "das",
            "dos",
            "de",
            "dessa",
            "desse",
            "desta",
            "deste",
            "essa",
            "esse",
            "opcao",
            "opcoes",
            "peso",
            "pesos",
            "tamanho",
            "tamanhos",
            "embalagem",
            "embalagens",
            "pacote",
            "pacotes",
            "saco",
            "sacos",
            "disponivel",
            "disponiveis",
            "tem",
            "quantos",
            "quanto",
            "kg",
            "quilo",
            "quilos",
            "g",
            "grama",
            "gramas",
            "ml",
            "mililitro",
            "mililitros",
            "l",
            "litro",
            "litros",
        }
    else:
        return False, ""

    if not requested:
        return False, ""

    tokens = re.findall(r"\d+(?:[.,]\d+)?(?:kg|g|ml|l)|[a-z0-9]+", normalized)
    query_tokens = [token for token in tokens if token not in stop_words]
    query = _canonicalize_numeric_measurements(" ".join(query_tokens))
    if query in {"produto", "racao", "essa racao", "esse produto"}:
        query = ""
    return True, query.strip()
