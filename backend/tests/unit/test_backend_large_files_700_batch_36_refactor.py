from pathlib import Path

from app import estoque_transferencia_parceiro_routes
from app.estoque import transferencia_parceiro_mutacao_routes


REPO_ROOT = Path(__file__).resolve().parents[3]


def _source(relative_path: str) -> str:
    return (REPO_ROOT / relative_path).read_text(encoding="utf-8")


def _non_empty_line_count(relative_path: str) -> int:
    return sum(1 for line in _source(relative_path).splitlines() if line.strip())


def test_transferencia_parceiro_mutacoes_fatia_36_preservam_api_publica():
    assert (
        estoque_transferencia_parceiro_routes.transferir_estoque_para_parceiro
        is transferencia_parceiro_mutacao_routes.transferir_estoque_para_parceiro
    )
    assert (
        estoque_transferencia_parceiro_routes.editar_transferencia_parceiro
        is transferencia_parceiro_mutacao_routes.editar_transferencia_parceiro
    )


def test_transferencia_parceiro_routes_agrega_mutacoes_extraidas():
    source = _source("backend/app/estoque_transferencia_parceiro_routes.py")
    mutacao_source = _source(
        "backend/app/estoque/transferencia_parceiro_mutacao_routes.py"
    )

    assert "transferencia_parceiro_mutacao_routes" in source
    assert "router.include_router(transferencia_parceiro_mutacao_router)" in source
    assert "EstoqueService.baixar_estoque(" not in source
    assert "EstoqueMovimentacao" not in source
    assert "EstoqueService.baixar_estoque(" in mutacao_source
    assert "EstoqueMovimentacao" in mutacao_source


def test_transferencia_parceiro_fatia_36_fica_abaixo_de_700_linhas_nao_vazias():
    counts = {
        "backend/app/estoque_transferencia_parceiro_routes.py": _non_empty_line_count(
            "backend/app/estoque_transferencia_parceiro_routes.py"
        ),
        "backend/app/estoque/transferencia_parceiro_mutacao_routes.py": _non_empty_line_count(
            "backend/app/estoque/transferencia_parceiro_mutacao_routes.py"
        ),
    }

    assert counts["backend/app/estoque_transferencia_parceiro_routes.py"] < 430
    assert all(lines < 700 for lines in counts.values())
