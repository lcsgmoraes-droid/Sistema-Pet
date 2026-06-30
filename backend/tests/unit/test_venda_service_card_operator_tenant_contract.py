from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_finalizar_venda_validates_card_operator_with_explicit_tenant_filter():
    source = (ROOT / "app" / "vendas" / "finalizacao_pagamentos.py").read_text(
        encoding="utf-8"
    )

    query_start = source.index("db.query(OperadoraCartao)")
    query_block = source[query_start : source.index("if not operadora:", query_start)]

    assert "OperadoraCartao.tenant_id == tenant_id" in query_block
