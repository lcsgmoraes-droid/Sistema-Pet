"""Validacao offline do CSV V2 do Portal; nao e conciliacao da API ou do banco.

Somente metadados financeiros permitidos sao interpretados. Campos de loja,
documentos, clientes e dados bancarios nao entram no resultado nem nos erros.
"""

from collections import Counter, defaultdict
import csv
from datetime import date, datetime
from decimal import Decimal
from hashlib import sha256
import io
import re
from uuid import UUID

from .financial_statement import IfoodStatementError, _money

MAX_BYTES = 8_000_000
MAX_ROWS = 100_000
MAX_CELL = 4096
MAX_COLUMNS = 128
SOURCE = "ifood_partner_portal_v2"
CONSISTENT = "consistent_within_file"
PENDING = "needs_review"
ID = re.compile(r"^[A-Za-z0-9_-]{1,100}$")
REQUIRED = frozenset(
    {
        "merchant_id",
        "competencia",
        "valor",
        "impacto_no_repasse",
        "data_do_faturamento",
    }
)
FINANCIAL_COLUMNS = REQUIRED | {
    "id_lancamento",
    "titulo",
    "valor_total_do_repasse",
    "data_pagamento_esperado",
    "data_pagamento_efetivado",
}


class IfoodPortalStatementError(ValueError):
    status_code = 422


def _error():
    return IfoodPortalStatementError(
        "Extrato do Portal inválido, incompleto ou fora da loja, competência e cobertura informadas."
    )


def _uuid(value):
    try:
        if not isinstance(value, str):
            raise ValueError
        return str(UUID(value))
    except (ValueError, TypeError, AttributeError):
        raise _error() from None


def _date(value, *, optional=False):
    if optional and value in (None, ""):
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    try:
        if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
            raise ValueError
        return date.fromisoformat(value)
    except (TypeError, ValueError):
        raise _error() from None


def _id(value):
    if value == "":
        return None
    if not ID.fullmatch(value):
        raise _error()
    return value


def _amount(value, *, optional=False):
    if optional and value == "":
        return None
    try:
        return Decimal(_money(value))
    except IfoodStatementError:
        raise _error() from None


def _text(value):
    return format(value, ".2f") if value is not None else None


def validate_portal_statement(
    content, merchant_id, competence, export_begin, export_end
):
    """Confere apenas coerencia interna, preservando duplicados e linhas NAO.

    A cobertura e declarada pela exportacao do Portal e nao e convertida em
    apuracao Financial. Nao ha rede, DB, importacao de jobs ou dados operacionais.
    """
    merchant = _uuid(merchant_id)
    if not isinstance(competence, str) or not re.fullmatch(
        r"\d{4}-(0[1-9]|1[0-2])", competence
    ):
        raise _error()
    _date(competence + "-01")
    begin, end = _date(export_begin), _date(export_end)
    if (
        end < begin
        or not isinstance(content, bytes)
        or not content
        or len(content) > MAX_BYTES
    ):
        raise _error()
    try:
        decoded = content.decode("utf-8-sig")
        if "\0" in decoded:
            raise _error()
        reader = csv.reader(
            io.StringIO(decoded, newline=""), delimiter=",", strict=True
        )
        headers = [value.strip() for value in next(reader)]
        if (
            len(headers) > MAX_COLUMNS
            or len(headers) != len(set(headers))
            or any(len(value) > MAX_CELL for value in headers)
            or not REQUIRED <= set(headers)
        ):
            raise _error()
        indices = {
            key: index for index, key in enumerate(headers) if key in FINANCIAL_COLUMNS
        }
        rows = []
        for values in reader:
            if not values:
                continue
            if (
                len(values) != len(headers)
                or any(len(value) > MAX_CELL for value in values)
                or len(rows) >= MAX_ROWS
            ):
                raise _error()
            if not any(value.strip() for value in values):
                continue
            # Nunca interpretar nem serializar as demais colunas do arquivo.
            fields = {key: values[index].strip() for key, index in indices.items()}
            if (
                _uuid(fields["merchant_id"]) != merchant
                or fields["competencia"] != competence
            ):
                raise _error()
            invoice_date = _date(fields["data_do_faturamento"])
            if not begin <= invoice_date <= end:
                raise _error()
            for key in ("data_pagamento_esperado", "data_pagamento_efetivado"):
                _date(fields.get(key), optional=True)
            impact = fields["impacto_no_repasse"]
            if impact not in {"SIM", "NAO", "NÃO"}:
                raise _error()
            rows.append(
                {
                    "entry_id": _id(fields.get("id_lancamento", "")),
                    "title_id": _id(fields.get("titulo", "")),
                    "amount": _amount(fields["valor"]),
                    "declared": _amount(
                        fields.get("valor_total_do_repasse", ""), optional=True
                    ),
                    "impact": impact == "SIM",
                }
            )
    except IfoodPortalStatementError:
        raise
    except (
        UnicodeError,
        csv.Error,
        StopIteration,
        TypeError,
        ValueError,
        OverflowError,
    ):
        raise _error() from None

    counts = Counter(row["entry_id"] for row in rows if row["entry_id"] is not None)
    duplicated = {entry for entry, count in counts.items() if count > 1}
    groups = defaultdict(list)
    for row in rows:
        groups[row["title_id"]].append(row)
    totals = []
    warnings = [
        "Conferência interna do CSV do Portal; não comprova arquivo On-demand processado nem conciliação com a API.",
        "A cobertura informada pertence à exportação do Portal; não é período de apuração Financial.",
        "Linhas sem impacto no repasse ficam separadas; não somar seus valores novamente como taxas ou receita.",
        "Datas de pagamento no arquivo não comprovam crédito bancário. A margem depende dos custos da venda.",
    ]
    for title_id, entries in groups.items():
        issues = []
        if title_id is None:
            issues.append("Há linhas sem identificação de título.")
        if any(row["entry_id"] is None for row in entries):
            issues.append("Há linhas sem identificação de lançamento.")
        if any(
            row["entry_id"] in duplicated
            for row in entries
            if row["entry_id"] is not None
        ):
            issues.append(
                "Há identificadores de lançamento repetidos; todas as linhas foram preservadas."
            )
        declarations = {
            row["declared"] for row in entries if row["declared"] is not None
        }
        declared = (
            next(iter(declarations))
            if len(declarations) == 1
            and all(row["declared"] is not None for row in entries)
            else None
        )
        if declared is None:
            issues.append(
                "Total declarado do título ausente ou inconsistente entre as linhas."
            )
        impact_sum = sum(
            (row["amount"] for row in entries if row["impact"]), Decimal(0)
        )
        difference = declared - impact_sum if declared is not None else None
        if difference is not None and difference != 0:
            issues.append(
                "O total declarado do título difere da soma das linhas com impacto no repasse."
            )
        totals.append(
            {
                "title_id": title_id,
                "declared_amount": _text(declared),
                "impact_sum": _text(impact_sum),
                "difference": _text(difference),
                "rows": len(entries),
                "status": PENDING if issues else CONSISTENT,
                "issues": issues,
            }
        )
    if not rows:
        warnings.append(
            "O arquivo não contém lançamentos; isso não comprova saldo zero ou conciliação concluída."
        )
    if duplicated:
        warnings.append(
            "Identificadores repetidos exigem revisão; nenhum lançamento foi deduplicado ou descartado."
        )
    if any(title["status"] == PENDING for title in totals):
        warnings.append(
            "Existem identificações ou totais pendentes de revisão no arquivo."
        )
    transfer = sum((row["amount"] for row in rows if row["impact"]), Decimal(0))
    excluded = sum((row["amount"] for row in rows if not row["impact"]), Decimal(0))
    return {
        "source": SOURCE,
        "hash": sha256(content).hexdigest(),
        "row_count": len(rows),
        "impact_count": sum(row["impact"] for row in rows),
        "excluded_count": sum(not row["impact"] for row in rows),
        "transfer_sum": _text(transfer),
        "excluded_sum": _text(excluded),
        "all_sum": _text(transfer + excluded),
        "totals_by_title": totals,
        "export_coverage": {
            "begin_date": str(begin),
            "end_date": str(end),
            "basis": "declared_portal_export",
        },
        "validation_status": CONSISTENT
        if rows and all(title["status"] == CONSISTENT for title in totals)
        else PENDING,
        "api_reconciliation_status": "pending",
        "bank_status": "not_checked",
        "margin_status": "pending_costs",
        "warnings": warnings,
    }
