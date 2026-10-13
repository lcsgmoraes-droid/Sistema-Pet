from types import SimpleNamespace

import pytest

from app.intnfe import rejection_diagnostics as diagnostics
from app.intnfe.emission import _provider_validation


def rejected_sale():
    items = []
    for index in range(1, 26):
        product = SimpleNamespace(
            id=1000 + index,
            nome=(
                "LUVA DE PROCEDIMENTO LATEX C/100"
                if index == 23
                else f"Produto {index}"
            ),
            codigo="9405" if index == 23 else str(index),
            codigo_barras=None,
            tipo_produto="SIMPLES",
        )
        items.append(
            SimpleNamespace(
                id=2000 + index,
                tipo="produto",
                produto_id=product.id,
                produto=product,
                lote=None,
            )
        )
    return SimpleNamespace(
        itens=items,
        tenant_id="11111111-1111-1111-1111-111111111111",
        nfe_status="rejeitada",
        nfe_codigo_erro="778",
        nfe_motivo_rejeicao="Rejeição: Informado NCM inexistente [nItem:23]",
    )


@pytest.fixture(autouse=True)
def fiscal_context(monkeypatch):
    monkeypatch.setattr(
        diagnostics,
        "effective_fiscal_context",
        lambda _db, _venda, item: (
            {"ncm": "29007158" if item.id == 2023 else "23091000"},
            SimpleNamespace(id=5023) if item.id == 2023 else None,
        ),
    )


def test_rejection_778_selects_only_item_23_in_sale_with_25_items():
    sale = rejected_sale()
    result = diagnostics.rejection_diagnostics(sale)
    assert len(result["correcoes"]) == 1
    correction = result["correcoes"][0]
    assert correction["produto_id"] == 1023
    assert correction["item_id"] == 2023
    assert correction["item_numero"] == 23
    assert correction["lote_id"] == 5023
    assert correction["sku"] == "9405"
    assert correction["campo"] == "ncm"
    assert correction["valor_atual"] == "29007158"
    assert correction["valor_sugerido"] == "40151200"
    assert correction["confianca"] == "baixa"
    assert correction["preenchimento_automatico"] is False
    assert correction["historico"] is True
    assert "valor_invalido" not in correction
    assert "RC31692_2025" in correction["fonte_url"]


@pytest.mark.parametrize("index", ["0", "-1", "26", "999999", "23.5", "abc"])
def test_invalid_item_index_never_selects_a_product(index):
    sale = rejected_sale()
    sale.nfe_motivo_rejeicao = f"Informado NCM inexistente [nItem:{index}]"
    correction = diagnostics.rejection_diagnostics(sale)["correcoes"][0]
    assert "produto_id" not in correction
    assert "item_id" not in correction
    assert "valor_sugerido" not in correction


def test_unknown_rejection_does_not_invent_a_field_or_item():
    sale = rejected_sale()
    sale.nfe_codigo_erro = "999"
    sale.nfe_motivo_rejeicao = "Falha informada pelo emissor"
    correction = diagnostics.rejection_diagnostics(sale)["correcoes"][0]
    assert correction["campo"] == "intnfe"
    assert "produto_id" not in correction
    assert "item_numero" not in correction


def test_error_without_item_index_does_not_choose_among_multiple_products():
    sale = rejected_sale()
    sale.nfe_motivo_rejeicao = "Informado NCM inexistente"
    assert "produto_id" not in diagnostics.rejection_diagnostics(sale)["correcoes"][0]


def test_invalid_explicit_index_does_not_fall_back_to_single_product():
    sale = rejected_sale()
    sale.itens = [sale.itens[22]]
    sale.nfe_motivo_rejeicao = "Informado NCM inexistente [nItem:23]"
    assert "produto_id" not in diagnostics.rejection_diagnostics(sale)["correcoes"][0]


def test_service_item_does_not_shift_rejection_to_another_product():
    sale = rejected_sale()
    sale.itens[22].tipo = "servico"
    assert "produto_id" not in diagnostics.rejection_diagnostics(sale)["correcoes"][0]


def test_provider_validation_uses_item_index_with_multiple_products():
    sale = rejected_sale()
    result = _provider_validation(sale, [sale.nfe_motivo_rejeicao])
    assert result["bloqueios"][0]["produto_id"] == 1023
    assert result["bloqueios"][0]["item_numero"] == 23
    assert result["bloqueios"][0]["historico"] is False


def test_current_value_changed_after_rejection_is_advisory(monkeypatch):
    sale = rejected_sale()
    monkeypatch.setattr(
        diagnostics,
        "effective_fiscal_context",
        lambda *_args: ({"ncm": "40151200"}, None),
    )
    correction = diagnostics.rejection_diagnostics(sale)["correcoes"][0]
    assert correction["valor_atual"] == "40151200"
    assert "valor_invalido" not in correction
    assert "valor_sugerido" not in correction


def test_authorized_document_has_no_active_rejection_diagnosis():
    sale = rejected_sale()
    sale.nfe_status = "autorizada"
    assert diagnostics.rejection_diagnostics(sale) is None


def test_reuses_existing_correction_suggestion_for_matching_product_and_field():
    sale = rejected_sale()
    validation = {
        "correcoes": [
            {
                "produto_id": 1023,
                "campo": "ncm",
                "valor_sugerido": "40151200",
                "fonte_sugestao": "catalogo",
            }
        ],
        "bloqueios": [],
    }
    correction = diagnostics.rejection_diagnostics(sale, validation=validation)[
        "correcoes"
    ][0]
    assert correction["fonte_sugestao"] == "catalogo"


def test_enrich_validation_preserves_separate_lines_for_repeated_product():
    sale = rejected_sale()
    sale.itens[24].produto = sale.itens[22].produto
    sale.itens[24].produto_id = 1023
    validation = {"correcoes": [{"campo": "ncm", "produto_id": 1023}], "bloqueios": []}
    diagnostics.enrich_validation_items(sale, validation)
    assert [
        (row["item_numero"], row["item_id"]) for row in validation["correcoes"]
    ] == [(23, 2023), (25, 2025)]


def test_enrich_validation_respects_explicit_line_for_repeated_product():
    sale = rejected_sale()
    sale.itens[24].produto = sale.itens[22].produto
    sale.itens[24].produto_id = 1023
    validation = {
        "correcoes": [],
        "bloqueios": [{"campo": "ncm", "produto_id": 1023, "item_numero": 25}],
    }
    diagnostics.enrich_validation_items(sale, validation)
    assert len(validation["bloqueios"]) == 1
    assert validation["bloqueios"][0]["item_id"] == 2025


def test_advisory_does_not_reuse_rejected_value_as_suggestion():
    sale = rejected_sale()
    validation = {
        "correcoes": [
            {
                "produto_id": 1023,
                "campo": "ncm",
                "valor_sugerido": "29007158",
                "preenchimento_automatico": True,
            }
        ],
        "bloqueios": [],
    }
    correction = diagnostics.rejection_diagnostics(sale, validation=validation)[
        "correcoes"
    ][0]
    assert correction["valor_sugerido"] == "40151200"
    assert correction["preenchimento_automatico"] is False


def test_suggestion_does_not_use_another_line_of_repeated_product():
    sale = rejected_sale()
    validation = {
        "correcoes": [
            {
                "produto_id": 1023,
                "item_id": 9999,
                "item_numero": 25,
                "campo": "ncm",
                "valor_sugerido": "23091000",
            }
        ],
        "bloqueios": [],
    }
    correction = diagnostics.rejection_diagnostics(sale, validation=validation)[
        "correcoes"
    ][0]
    assert correction["valor_sugerido"] == "40151200"


def test_latex_procedure_glove_does_not_use_broad_category_history(monkeypatch):
    sale = rejected_sale()
    monkeypatch.setattr(
        diagnostics,
        "_sugerir_ncm",
        lambda *_args: pytest.fail("não consultar categoria genérica"),
    )
    correction = diagnostics.rejection_diagnostics(sale, db=SimpleNamespace())[
        "correcoes"
    ][0]
    assert correction["valor_sugerido"] == "40151200"
