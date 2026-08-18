from app.services.base_catalog_enrichment_service import (
    _unique_rows_by_gtin,
    normalize_gtin,
    plan_product_scalar_updates,
)


def test_normalize_gtin_valida_digito_e_preserva_identificador_textual():
    assert normalize_gtin("7898242036467") == "7898242036467"
    assert normalize_gtin("07898242036467") == "07898242036467"
    assert normalize_gtin("7898242036468") is None
    assert normalize_gtin("SEM GTIN") is None


def test_unique_rows_by_gtin_exclui_duplicados_invalidos_e_excluidos():
    rows = [
        {"id": 1, "codigo_barras": "7898242036467", "deleted_at": None},
        {"id": 2, "codigo_barras": "7898242036009", "deleted_at": None},
        {"id": 3, "codigo_barras": "7898242036009", "deleted_at": None},
        {"id": 4, "codigo_barras": "123", "deleted_at": None},
        {"id": 5, "codigo_barras": "7898242035200", "deleted_at": "agora"},
    ]

    unique, ambiguous, invalid = _unique_rows_by_gtin(rows)

    assert list(unique) == ["7898242036467"]
    assert ambiguous == 1
    assert invalid == 1


def test_planejamento_preenche_so_campos_cadastrais_ausentes():
    source = {
        "descricao_curta": "Racao completa para caes adultos.",
        "descricao_completa": "Descricao detalhada.",
        "ncm": "2309.90.10",
        "cest": "22.001.00",
        "origem": "0",
        "cfop": "5102",
        "preco_custo": 10,
        "preco_venda": 20,
        "estoque_atual": 50,
    }
    target = {
        "descricao_curta": None,
        "descricao_completa": "Descricao do cliente",
        "ncm": None,
        "cest": None,
        "origem": None,
        "cfop": None,
        "preco_custo": 99,
        "preco_venda": 199,
        "estoque_atual": 7,
    }

    updates = plan_product_scalar_updates(source, target)

    assert updates == {
        "descricao_curta": "Racao completa para caes adultos.",
        "ncm": "23099010",
        "cest": "2200100",
        "origem": "0",
        "cfop": "5102",
    }
    assert "descricao_completa" not in updates
    assert "preco_custo" not in updates
    assert "preco_venda" not in updates
    assert "estoque_atual" not in updates
