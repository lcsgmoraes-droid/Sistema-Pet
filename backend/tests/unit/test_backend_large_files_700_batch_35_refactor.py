from pathlib import Path

from app.vendas import finalizacao, finalizacao_pagamentos


REPO_ROOT = Path(__file__).resolve().parents[3]


def _source(relative_path: str) -> str:
    return (REPO_ROOT / relative_path).read_text(encoding="utf-8")


def _non_empty_line_count(relative_path: str) -> int:
    return sum(1 for line in _source(relative_path).splitlines() if line.strip())


def test_finalizacao_pagamentos_fatia_35_preserva_api_publica():
    assert (
        finalizacao._calcular_pagamentos_finalizacao
        is finalizacao_pagamentos._calcular_pagamentos_finalizacao
    )
    assert callable(finalizacao_pagamentos.consumir_cupom_finalizacao)
    assert callable(finalizacao_pagamentos.processar_pagamentos_finalizacao)


def test_finalizacao_delega_pagamentos_sem_manter_blocos_operacionais():
    finalizacao_source = _source("backend/app/vendas/finalizacao.py")
    pagamentos_source = _source("backend/app/vendas/finalizacao_pagamentos.py")

    assert "processar_pagamentos_finalizacao(" in finalizacao_source
    assert "consumir_cupom_finalizacao(" in finalizacao_source
    assert "db.query(OperadoraCartao)" not in finalizacao_source
    assert "CashbackTransaction(" not in finalizacao_source
    assert "CaixaService.registrar_movimentacao_venda(" in pagamentos_source
    assert "OperadoraCartao.tenant_id == tenant_id" in pagamentos_source


def test_finalizacao_fatia_35_fica_abaixo_de_700_linhas_nao_vazias():
    counts = {
        "backend/app/vendas/finalizacao.py": _non_empty_line_count(
            "backend/app/vendas/finalizacao.py"
        ),
        "backend/app/vendas/finalizacao_pagamentos.py": _non_empty_line_count(
            "backend/app/vendas/finalizacao_pagamentos.py"
        ),
    }

    assert counts["backend/app/vendas/finalizacao.py"] < 560
    assert all(lines < 700 for lines in counts.values())
