"""Pure, bounded Financial V3 CSV parser; no DB, network, PII or inferred titles.

Contract: docs/IFOOD_FINANCIAL_DEV.md and official Financial V3 On-demand guide.
The provider is deprecating titulo in favor of id_saldo: they are separate IDs.
"""

import csv
from datetime import date
from decimal import Decimal, InvalidOperation
import gzip
import io
import re
from uuid import UUID
import zlib

MAX_COMPRESSED_BYTES = 8_000_000
MAX_UNCOMPRESSED_BYTES = 32_000_000
MAX_ROWS = 100_000
MAX_CELL = 4096
CENT = Decimal("0.01")
MONEY_LIMIT = Decimal("999999999999.99")
ID = re.compile(r"^[A-Za-z0-9_-]{1,100}$")
MONEY = re.compile(
    r"^[+-]?(?:\d+(?:[.,]\d{1,2})?|\d{1,3}(?:\.\d{3})+,\d{1,2}|\d{1,3}(?:,\d{3})+\.\d{1,2})$"
)
REQUIRED_COLUMNS = frozenset({"competencia", "loja_id", "valor", "impacto_no_repasse"})
DISCONTINUED = frozenset({"discontinued column", "coluna descontinuada"})
OPEN_PERIOD = frozenset(
    {
        "settlement period open",
        "período de apuração aberto",
        "periodo de apuracao aberto",
    }
)

# Only documented technical vocabulary survives. Free-text occurrences, names,
# CNPJ, bank details, order details and unknown CSV columns never leave parser.
FACTS = frozenset(
    {
        "Venda",
        "Cancelamento Total",
        "Cancelamento Parcial",
        "Processamento Manual",
        "Ressarcimento/Indenização",
        "Ocorrência Venda",
        "Solicitação frete",
        "Cancelamento Solicitação frete",
        "Ocorrência Avulsa",
        "Fechamento",
        "Carregamento de Saldo Devedor",
    }
)
TYPES = frozenset(
    {
        "Retenção",
        "Subsídio",
        "Entrada Financeira",
        "Reembolso",
        "Ajuste Pontual",
        "Ressarcimento",
        "Cobrança",
        "Ocorrência",
        "Estorno",
        "Crédito",
        "Restituição",
        "TBD",
    }
)
DESCRIPTIONS = frozenset(
    {
        "Entrada Financeira",
        "Entrada financeira",
        "Comissão do iFood",
        "Comissão iFood",
        "Taxa entrega iFood",
        "Taxa de entrega iFood",
        "Taxas cobradas do usuário devidas ao iFood",
        "Promoção incentivada pelo iFood",
        "Promoção incentivada pela loja",
        "Reembolso ifood",
        "Solicitação de Frete (iFood entrega)",
        "Solicitação de entrega Sob Demanda On",
        "Solicitação de entrega Sob Demanda Off",
        "Taxa transação iFood benefícios",
        "Desconto da taxa transação iFood benefícios",
        "Ajuste falha sistêmica",
        "Cobrança meses anteriores",
        "Restituição I.R.",
        "TBD",
        "ORDER_PAYMENT",
        "ORDER_COMMISSION",
        "PAYMENT_TRANSACTION_FEE",
        "IFOOD_SUBSIDY",
        "STORE_SUBSIDY",
        "CHAIN_SUBSIDY",
        "INDUSTRY_SUBSIDY",
        "SERVICE_FEE",
        "DELIVERY_FEE_IFOOD",
        "ANTICIPATION_FEE",
        "STORE_REFUND",
        "COMMISSION_EXEMPTION",
    }
)


class IfoodStatementError(ValueError):
    status_code = 422


def _error():
    return IfoodStatementError(
        "Arquivo de conciliacao invalido ou fora do escopo; nenhum dado parcial foi importado."
    )


def _uuid(value):
    try:
        if not isinstance(value, str):
            raise ValueError
        return str(UUID(value))
    except (ValueError, TypeError, AttributeError):
        raise _error() from None


def _money(value, *, nullable=False):
    value = value.strip()
    if not value and nullable:
        return None
    if len(value) > 40 or not MONEY.fullmatch(value):
        raise _error()
    # Separators with groups are accepted only when the decimal separator is
    # explicit. A lone 1.234 is rejected instead of guessing 1234 vs 1.234.
    if "," in value and "." in value:
        decimal = "," if value.rfind(",") > value.rfind(".") else "."
        value = value.replace("." if decimal == "," else ",", "").replace(decimal, ".")
    else:
        value = value.replace(",", ".")
    try:
        result = Decimal(value)
        if (
            not result.is_finite()
            or abs(result) > MONEY_LIMIT
            or result != result.quantize(CENT)
        ):
            raise ValueError
        return format(Decimal("0") if result == 0 else result.quantize(CENT), ".2f")
    except (ValueError, InvalidOperation):
        raise _error() from None


def _optional_id(value):
    value = value.strip()
    if not value or value.casefold() in DISCONTINUED:
        return None
    if not ID.fullmatch(value):
        raise _error()
    return value


def _optional_date(value):
    value = value.strip()
    if not value:
        return None
    try:
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
            raise ValueError
        return date.fromisoformat(value).isoformat()
    except ValueError:
        raise _error() from None


def parse_statement(content: bytes, merchant_id: str, competence: str) -> dict:
    """Return a sanitized complete envelope, keeping duplicate rows/positions.

    Missing amounts are never zero. A still-open transaction is unknown. Rows
    without an order remain unallocated. title_id and balance_id never alias.
    """
    merchant = _uuid(merchant_id)
    if not isinstance(competence, str) or not re.fullmatch(
        r"\d{4}-(0[1-9]|1[0-2])", competence
    ):
        raise _error()
    try:
        date.fromisoformat(competence + "-01")
    except ValueError:
        raise _error() from None
    if (
        not isinstance(content, bytes)
        or not content
        or len(content) > MAX_COMPRESSED_BYTES
    ):
        raise _error()
    try:
        if content.startswith(b"\x1f\x8b"):
            with gzip.GzipFile(fileobj=io.BytesIO(content)) as source:
                content = source.read(MAX_UNCOMPRESSED_BYTES + 1)
        if len(content) > MAX_UNCOMPRESSED_BYTES or b"\0" in content:
            raise _error()
        try:
            decoded = content.decode("utf-8-sig")
        except UnicodeDecodeError:
            decoded = content.decode("cp1252")
        reader = csv.reader(
            io.StringIO(decoded, newline=""), delimiter=";", strict=True
        )
        headers = [value.strip() for value in next(reader)]
        if (
            len(headers) > 128
            or len(headers) != len(set(headers))
            or not REQUIRED_COLUMNS.issubset(headers)
        ):
            raise _error()
        rows = []
        for values in reader:
            if not values or not any(value.strip() for value in values):
                continue
            if (
                len(values) != len(headers)
                or any(len(value) > MAX_CELL for value in values)
                or len(rows) >= MAX_ROWS
            ):
                raise _error()
            raw = dict(zip(headers, values))

            def get(key):
                return raw.get(key, "").strip()

            if _uuid(get("loja_id")) != merchant or get("competencia") != competence:
                raise _error()
            impact = get("impacto_no_repasse")
            if impact not in {"SIM", "NAO", "NÃO"}:
                raise _error()
            begin, end = (
                _optional_date(get("data_apuracao_inicio")),
                _optional_date(get("data_apuracao_fim")),
            )
            if (begin is None) != (end is None) or (begin and end < begin):
                raise _error()
            transaction = get("valor_transacao")
            transaction_open = transaction.casefold() in OPEN_PERIOD
            order_reference = get("pedido_associado_ifood")
            order_id = None
            if order_reference:
                try:
                    order_id = _uuid(order_reference)
                except IfoodStatementError:
                    pass
            description = get("descricao_lancamento")
            rows.append(
                {
                    "position": len(rows) + 1,
                    "competence": competence,
                    "amount": _money(get("valor")),
                    "has_transfer_impact": impact == "SIM",
                    "title_id": _optional_id(get("titulo")),
                    "balance_id": _optional_id(get("id_saldo")),
                    "transaction_amount": None
                    if transaction_open
                    else _money(transaction, nullable=True),
                    "transaction_open": transaction_open,
                    "order_id": order_id,
                    "unknown_order_reference": bool(
                        order_reference and order_id is None
                    ),
                    "period_begin": begin,
                    "period_end": end,
                    "expected_payment_date": _optional_date(
                        get("data_repasse_esperada")
                    ),
                    "description": description if description in DESCRIPTIONS else None,
                    "unknown_description": bool(
                        description and description not in DESCRIPTIONS
                    ),
                    "generating_fact": get("fato_gerador")
                    if get("fato_gerador") in FACTS
                    else None,
                    "entry_type": get("tipo_lancamento")
                    if get("tipo_lancamento") in TYPES
                    else None,
                }
            )
        return {
            "merchant_id": merchant,
            "competence": competence,
            "row_count": len(rows),
            "rows": rows,
        }
    except IfoodStatementError:
        raise
    except (
        OSError,
        EOFError,
        UnicodeError,
        csv.Error,
        StopIteration,
        ValueError,
        OverflowError,
        zlib.error,
    ):
        raise _error() from None
