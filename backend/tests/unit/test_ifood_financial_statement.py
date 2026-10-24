import csv
import gzip
import io
from uuid import uuid4

import pytest

from app.integrations.ifood import financial_statement as statement
from app.integrations.ifood.financial_statement import (
    IfoodStatementError,
    parse_statement,
)

MERCHANT, ORDER = str(uuid4()), str(uuid4())
MONTH = "2025-08"


def document(rows=None, *, encoding="utf-8", compressed=False):
    base = dict(
        competencia=MONTH,
        loja_id=MERCHANT,
        valor="-12.00",
        impacto_no_repasse="SIM",
        titulo="111",
        id_saldo="999",
        valor_transacao="88.00",
        pedido_associado_ifood=ORDER,
        data_apuracao_inicio="2025-08-04",
        data_apuracao_fim="2025-08-10",
        data_repasse_esperada="2025-09-10",
        descricao_lancamento="Comissão do iFood",
        fato_gerador="Venda",
        tipo_lancamento="Cobrança",
    )
    rows = [{}] if rows is None else rows
    records = [base | values for values in rows]
    headers = list(dict.fromkeys(key for record in records or [base] for key in record))
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, headers, delimiter=";")
    writer.writeheader()
    writer.writerows(records)
    data = output.getvalue().encode(encoding)
    return gzip.compress(data) if compressed else data


def test_keeps_identical_rows_and_separate_title_balance_ids_without_summing_transaction():
    result = parse_statement(document([{}, {}], compressed=True), MERCHANT, MONTH)
    assert result["merchant_id"] == MERCHANT and result["row_count"] == 2
    first, second = result["rows"]
    assert first["amount"] == second["amount"] == "-12.00"
    assert first["transaction_amount"] == second["transaction_amount"] == "88.00"
    assert (first["title_id"], first["balance_id"]) == ("111", "999")
    assert [row["position"] for row in result["rows"]] == [1, 2]
    assert first["has_transfer_impact"] is True
    assert first["order_id"] == ORDER
    assert first["period_begin"] == "2025-08-04"


@pytest.mark.parametrize(
    "value,expected",
    [
        ("0", "0.00"),
        ("-0.00", "0.00"),
        ("-1,23", "-1.23"),
        ("1.234,56", "1234.56"),
        ("1,234.56", "1234.56"),
        ("+0.50", "0.50"),
    ],
)
def test_decimal_locale_and_signed_zero_are_explicit(value, expected):
    row = parse_statement(document([dict(valor=value)]), MERCHANT, MONTH)["rows"][0]
    assert row["amount"] == expected


@pytest.mark.parametrize(
    "value",
    ["", "NaN", "Infinity", "1.234", "1,234", "1,23.45", "R$ 10,00", "=1+2", "1e2"],
)
def test_missing_malformed_or_ambiguous_money_is_never_zero(value):
    with pytest.raises(IfoodStatementError):
        parse_statement(document([dict(valor=value)]), MERCHANT, MONTH)


@pytest.mark.parametrize(
    "value", ["Settlement period open", "Período de apuração aberto"]
)
def test_open_transaction_is_unknown_and_not_a_zero_or_title(value):
    row = parse_statement(
        document(
            [dict(valor_transacao=value, titulo="Discontinued column", id_saldo="123")]
        ),
        MERCHANT,
        MONTH,
    )["rows"][0]
    assert row["transaction_amount"] is None and row["transaction_open"] is True
    assert row["title_id"] is None and row["balance_id"] == "123"


def test_unknown_and_zero_transaction_values_remain_distinct():
    rows = parse_statement(
        document([dict(valor_transacao=""), dict(valor_transacao="0")]), MERCHANT, MONTH
    )["rows"]
    assert [row["transaction_amount"] for row in rows] == [None, "0.00"]
    assert not any(row["transaction_open"] for row in rows)


def test_nonimpact_rows_and_legitimate_no_order_rows_are_kept_unallocated():
    row = parse_statement(
        document(
            [
                dict(
                    impacto_no_repasse="NAO",
                    pedido_associado_ifood="",
                    titulo="",
                    id_saldo="",
                )
            ]
        ),
        MERCHANT,
        MONTH,
    )["rows"][0]
    assert row["has_transfer_impact"] is False
    assert row["order_id"] is row["title_id"] is row["balance_id"] is None


def test_no_free_text_personal_fields_documents_or_untrusted_order_ids_survive():
    row = parse_statement(
        document(
            [
                dict(
                    cnpj="99999999999999",
                    pedido_detalhes="PRIVATE_PERSON",
                    descricao_ocorrencia="PRIVATE_SECRET",
                    descricao_lancamento="PRIVATE_PERSON",
                    pedido_associado_ifood="customer@example.com",
                    fato_gerador="PRIVATE_PERSON",
                    tipo_lancamento="PRIVATE_PERSON",
                )
            ]
        ),
        MERCHANT,
        MONTH,
    )["rows"][0]
    assert "PRIVATE" not in repr(row) and "99999999999999" not in repr(row)
    assert row["description"] is row["generating_fact"] is row["entry_type"] is None
    assert row["order_id"] is None and row["unknown_order_reference"]
    assert row["unknown_description"]


@pytest.mark.parametrize(
    "overrides",
    [
        {"loja_id": str(uuid4())},
        {"competencia": "2025-07"},
        {"impacto_no_repasse": "UNKNOWN"},
        {"titulo": "../other"},
        {"data_apuracao_inicio": "2025-08-11"},
        {"data_apuracao_fim": ""},
        {"data_apuracao_inicio": "2025-02-30"},
        {"data_repasse_esperada": "not-a-date"},
    ],
)
def test_scope_and_structure_errors_abort_all_rows(overrides):
    with pytest.raises(IfoodStatementError):
        parse_statement(document([{}, overrides]), MERCHANT, MONTH)


@pytest.mark.parametrize("encoding", ["utf-8-sig", "cp1252"])
def test_brazilian_csv_encoding_and_quoted_semicolons_do_not_shift_columns(encoding):
    row = parse_statement(
        document([dict(descricao_ocorrencia="ignored; private")], encoding=encoding),
        MERCHANT,
        MONTH,
    )["rows"][0]
    assert row["amount"] == "-12.00" and row["description"] == "Comissão do iFood"


def test_empty_complete_file_is_distinct_from_invalid_empty_body():
    assert parse_statement(document([]), MERCHANT, MONTH)["row_count"] == 0
    with pytest.raises(IfoodStatementError):
        parse_statement(b"", MERCHANT, MONTH)


@pytest.mark.parametrize(
    "content",
    [
        b"competencia;competencia;loja_id;valor;impacto_no_repasse\n",
        b"competencia;valor\n2025-08;1\n",
        b'competencia;loja_id;valor;impacto_no_repasse\n"unterminated',
        b"\x1f\x8bnot-a-valid-gzip",
        b"competencia;loja_id;valor;impacto_no_repasse\0\n",
    ],
)
def test_malformed_csv_and_gzip_fail_safely(content):
    with pytest.raises(IfoodStatementError):
        parse_statement(content, MERCHANT, MONTH)


def test_decompression_rows_and_input_size_limits_fail_without_partial_result(
    monkeypatch,
):
    content = document([{}, {}], compressed=True)
    monkeypatch.setattr(statement, "MAX_UNCOMPRESSED_BYTES", 50)
    with pytest.raises(IfoodStatementError):
        parse_statement(content, MERCHANT, MONTH)
    monkeypatch.setattr(statement, "MAX_UNCOMPRESSED_BYTES", 32_000_000)
    monkeypatch.setattr(statement, "MAX_ROWS", 1)
    with pytest.raises(IfoodStatementError):
        parse_statement(content, MERCHANT, MONTH)
    monkeypatch.setattr(statement, "MAX_ROWS", 100_000)
    monkeypatch.setattr(statement, "MAX_COMPRESSED_BYTES", 10)
    with pytest.raises(IfoodStatementError):
        parse_statement(content, MERCHANT, MONTH)
