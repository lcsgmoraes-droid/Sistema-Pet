"""CSV Portal V2 sintético; nenhum dado ou linha de extrato real neste arquivo."""

import csv
from datetime import date
from hashlib import sha256
import io
import json
from uuid import uuid4

import pytest

from app.integrations.ifood.portal_statement import (
    IfoodPortalStatementError,
    validate_portal_statement,
)

MERCHANT = str(uuid4())
MONTH = "2025-03"
BEGIN, END = "2025-03-01", "2025-03-07"
CORE = [
    "merchant_id",
    "competencia",
    "data_do_faturamento",
    "id_lancamento",
    "titulo",
    "valor",
    "impacto_no_repasse",
    "valor_total_do_repasse",
]
HEADERS = (
    CORE
    + ["data_pagamento_esperado", "data_pagamento_efetivado"]
    + [f"ignored_{index}" for index in range(28)]
)


def document(rows=None, headers=None, *, bom=False, delimiter=","):
    rows = [{}] if rows is None else rows
    headers = HEADERS if headers is None else headers
    base = dict(
        merchant_id=MERCHANT,
        competencia=MONTH,
        data_do_faturamento="2025-03-03",
        id_lancamento="synthetic-entry-1",
        titulo="synthetic-title-1",
        valor="100.00",
        impacto_no_repasse="SIM",
        valor_total_do_repasse="100.00",
        data_pagamento_esperado="2025-04-07",
        data_pagamento_efetivado="2025-04-07",
    )
    output = io.StringIO(newline="")
    writer = csv.writer(output, delimiter=delimiter)
    writer.writerow(headers)
    for changes in rows:
        values = base | changes
        writer.writerow(
            [
                values.get(
                    header,
                    "PRIVATE customer@example.test https://signed.invalid/?secret=PRIVATE",
                )
                for header in headers
            ]
        )
    return ("\ufeff" if bom else "").encode() + output.getvalue().encode("utf-8")


def validate(content, **kwargs):
    return validate_portal_statement(
        content,
        kwargs.get("merchant_id", MERCHANT),
        kwargs.get("competence", MONTH),
        kwargs.get("export_begin", BEGIN),
        kwargs.get("export_end", END),
    )


def test_portal_report_is_offline_source_hashed_and_never_api_bank_or_margin_confirmation():
    content = document(bom=True)
    result = validate(content)
    assert result["source"] == "ifood_partner_portal_v2"
    assert result["hash"] == sha256(content).hexdigest()
    assert result["row_count"] == result["impact_count"] == 1
    assert result["validation_status"] == "consistent_within_file"
    assert result["api_reconciliation_status"] == "pending"
    assert result["bank_status"] == "not_checked"
    assert result["margin_status"] == "pending_costs"
    assert result["export_coverage"] == {
        "begin_date": BEGIN,
        "end_date": END,
        "basis": "declared_portal_export",
    }
    serialized = json.dumps(result)
    assert (
        "PRIVATE" not in serialized
        and "@" not in serialized
        and "https://" not in serialized
    )
    assert MERCHANT not in serialized
    assert "data_apuracao" not in serialized and "calculation_period" not in result


def test_official_portal_format_cannot_be_used_as_an_api_v3_job_file():
    from app.integrations.ifood.financial_statement import (
        IfoodStatementError,
        parse_statement,
    )

    content = document()
    assert validate(content)["source"] == "ifood_partner_portal_v2"
    with pytest.raises(IfoodStatementError):
        parse_statement(content, MERCHANT, MONTH)


def test_signed_nonimpact_rows_are_preserved_separately_and_never_change_title_check():
    content = document(
        [
            dict(valor="100", valor_total_do_repasse="90"),
            dict(
                id_lancamento="synthetic-entry-2",
                valor="-10",
                valor_total_do_repasse="90",
            ),
            dict(
                id_lancamento="synthetic-entry-3",
                valor="-25",
                impacto_no_repasse="NAO",
                valor_total_do_repasse="90",
            ),
            dict(
                id_lancamento="synthetic-entry-4",
                titulo="synthetic-title-2",
                valor="20.05",
                valor_total_do_repasse="20.05",
            ),
        ]
    )
    result = validate(content)
    assert (result["row_count"], result["impact_count"], result["excluded_count"]) == (
        4,
        3,
        1,
    )
    assert result["transfer_sum"] == "110.05"
    assert result["excluded_sum"] == "-25.00"
    assert result["all_sum"] == "85.05"
    assert result["validation_status"] == "consistent_within_file"
    first, second = result["totals_by_title"]
    assert first["declared_amount"] == first["impact_sum"] == "90.00"
    assert first["difference"] == "0.00" and first["rows"] == 3
    assert second["impact_sum"] == "20.05"


def test_repeated_declared_title_total_is_not_summed_per_line():
    result = validate(
        document(
            [
                dict(valor="40", valor_total_do_repasse="100"),
                dict(
                    id_lancamento="second-entry",
                    valor="60",
                    valor_total_do_repasse="100",
                ),
            ]
        )
    )
    assert result["totals_by_title"][0]["declared_amount"] == "100.00"
    assert result["transfer_sum"] == "100.00"


@pytest.mark.parametrize("value", ["", None])
@pytest.mark.parametrize("field", ["id_lancamento", "titulo", "valor_total_do_repasse"])
def test_missing_technical_id_or_declared_total_is_pending_never_guessed(field, value):
    result = validate(document([{field: value}]))
    assert result["validation_status"] == "needs_review"
    assert result["totals_by_title"][0]["status"] == "needs_review"
    assert result["transfer_sum"] == "100.00"
    if field == "valor_total_do_repasse":
        assert result["totals_by_title"][0]["declared_amount"] is None
        assert result["totals_by_title"][0]["difference"] is None


@pytest.mark.parametrize(
    "missing", ["id_lancamento", "titulo", "valor_total_do_repasse"]
)
def test_missing_optional_identification_column_leaves_complete_amounts_pending(
    missing,
):
    result = validate(
        document(headers=[header for header in HEADERS if header != missing])
    )
    assert result["validation_status"] == "needs_review"


def test_duplicate_entry_ids_are_not_deduplicated_even_when_totals_would_close():
    result = validate(
        document(
            [
                dict(valor="40", valor_total_do_repasse="100"),
                dict(valor="60", valor_total_do_repasse="100"),
            ]
        )
    )
    assert result["row_count"] == 2 and result["transfer_sum"] == "100.00"
    assert result["validation_status"] == "needs_review"
    assert any("repetidos" in warning for warning in result["warnings"])
    assert result["totals_by_title"][0]["difference"] == "0.00"


def test_same_entry_id_in_different_titles_flags_both_title_groups():
    result = validate(document([{}, dict(titulo="another-title")]))
    assert result["row_count"] == 2 and result["transfer_sum"] == "200.00"
    assert all(title["status"] == "needs_review" for title in result["totals_by_title"])


@pytest.mark.parametrize("declared", ["99.99", "100.01"])
def test_one_cent_difference_is_not_tolerated(declared):
    result = validate(document([dict(valor_total_do_repasse=declared)]))
    assert result["validation_status"] == "needs_review"
    assert result["totals_by_title"][0]["difference"] in {"-0.01", "0.01"}


def test_conflicting_or_partly_missing_declarations_are_unknown():
    for declaration in ("99", ""):
        result = validate(
            document(
                [
                    dict(valor="50"),
                    dict(
                        id_lancamento="second",
                        valor="50",
                        valor_total_do_repasse=declaration,
                    ),
                ]
            )
        )
        assert result["totals_by_title"][0]["declared_amount"] is None
        assert result["validation_status"] == "needs_review"


@pytest.mark.parametrize(
    "change",
    [
        dict(merchant_id=str(uuid4())),
        dict(competencia="2025-02"),
        dict(data_do_faturamento="2025-02-28"),
        dict(data_do_faturamento="2025-03-08"),
        dict(data_do_faturamento="03/03/2025"),
        dict(data_do_faturamento=""),
        dict(data_pagamento_esperado="2025-02-30"),
        dict(data_pagamento_efetivado="not-a-date"),
        dict(impacto_no_repasse="UNKNOWN"),
        dict(valor=""),
        dict(valor="NaN"),
        dict(valor="1.234"),
        dict(valor="0.001"),
        dict(valor="R$ 1,00"),
        dict(valor_total_do_repasse="Infinity"),
    ],
)
def test_invalid_scope_dates_or_money_abort_entire_file_without_raw_data(change):
    with pytest.raises(IfoodPortalStatementError) as caught:
        validate(document([{}, dict(id_lancamento="second") | change]))
    message = str(caught.value)
    assert MERCHANT not in message and "PRIVATE" not in message


@pytest.mark.parametrize(
    "kwargs",
    [
        dict(merchant_id="bad-id"),
        dict(competence="2025-13"),
        dict(competence="0000-03"),
        dict(export_begin="2025-03-08"),
        dict(export_end="03/07/2025"),
    ],
)
def test_invalid_caller_scope_is_rejected(kwargs):
    with pytest.raises(IfoodPortalStatementError):
        validate(document(), **kwargs)


def test_explicit_zero_is_known_but_missing_value_is_not_zero():
    result = validate(document([dict(valor="0", valor_total_do_repasse="0")]))
    assert (
        result["transfer_sum"] == "0.00"
        and result["validation_status"] == "consistent_within_file"
    )
    with pytest.raises(IfoodPortalStatementError):
        validate(document([dict(valor="")]))


def test_payment_dates_can_follow_export_and_never_become_bank_confirmation():
    result = validate(document())
    assert result["bank_status"] == "not_checked"
    assert result["validation_status"] == "consistent_within_file"
    assert (
        validate_portal_statement(
            document(), MERCHANT, MONTH, date(2025, 3, 1), date(2025, 3, 7)
        )["export_coverage"]["end_date"]
        == END
    )


def test_empty_complete_export_is_pending_not_zero_balance_confirmation():
    result = validate(document([]))
    assert result["row_count"] == 0 and result["validation_status"] == "needs_review"
    assert result["totals_by_title"] == [] and result["bank_status"] == "not_checked"
    assert any("saldo zero" in warning for warning in result["warnings"])


@pytest.mark.parametrize(
    "content",
    [b"", b'a,b\n"unclosed', b"\xff\xfe", b"\0", b"merchant_id;competencia;valor\n"],
)
def test_malformed_bytes_and_wrong_delimiter_are_rejected(content):
    with pytest.raises(IfoodPortalStatementError):
        validate(content)


def test_duplicate_headers_and_row_width_mismatch_are_rejected():
    with pytest.raises(IfoodPortalStatementError):
        validate(document(headers=HEADERS + ["valor"]))
    content = document().decode()
    lines = content.splitlines()
    with pytest.raises(IfoodPortalStatementError):
        validate((lines[0] + "\n" + lines[1] + ",unexpected\n").encode())


def test_oversized_whitespace_cell_is_checked_before_ignoring_blank_rows():
    content = document() + ((" " * 5000) + "," * (len(HEADERS) - 1) + "\n").encode()
    with pytest.raises(IfoodPortalStatementError):
        validate(content)


def test_empty_cells_with_wrong_row_width_are_not_silently_ignored():
    content = document() + ("," * (len(HEADERS) + 2) + "\n").encode()
    with pytest.raises(IfoodPortalStatementError):
        validate(content)


def test_bounded_bytes_rows_cells_and_columns(monkeypatch):
    from app.integrations.ifood import portal_statement as module

    content = document()
    monkeypatch.setattr(module, "MAX_BYTES", len(content) - 1)
    with pytest.raises(IfoodPortalStatementError):
        validate(content)
    monkeypatch.setattr(module, "MAX_BYTES", 8_000_000)
    monkeypatch.setattr(module, "MAX_ROWS", 1)
    with pytest.raises(IfoodPortalStatementError):
        validate(document([{}, dict(id_lancamento="second")]))
    monkeypatch.setattr(module, "MAX_ROWS", 100_000)
    with pytest.raises(IfoodPortalStatementError):
        validate(document([dict(ignored_0="x" * 4097)]))
    with pytest.raises(IfoodPortalStatementError):
        validate(document(headers=HEADERS + [f"extra{i}" for i in range(100)]))
