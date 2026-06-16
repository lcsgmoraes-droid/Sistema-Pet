from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]


def test_analise_pagamento_usa_configuracao_real_de_comissao():
    source = (REPO_ROOT / "backend/app/formas_pagamento_routes.py").read_text(
        encoding="utf-8"
    )

    assert "buscar_configuracao_comissao" in source
    assert "dados.vendedor_id" in source
    assert "percentual_comissao = 10.0" not in source


def test_modal_pagamento_envia_vendedor_para_analise_de_margem():
    source = (REPO_ROOT / "frontend/src/components/ModalPagamento.jsx").read_text(
        encoding="utf-8"
    )

    assert "vendedor_id: venda.funcionario_id || null" in source
