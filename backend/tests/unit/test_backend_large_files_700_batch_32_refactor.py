from pathlib import Path

import app.calculadora_racao as calculadora_facade
from app.racao_calculadora import core, options, routes, schemas


REPO_ROOT = Path(__file__).resolve().parents[3]


def _non_empty_lines(path: Path) -> int:
    return sum(
        1 for line in path.read_text(encoding="utf-8").splitlines() if line.strip()
    )


def test_calculadora_racao_facade_reexports_split_modules():
    assert calculadora_facade.router is routes.router
    assert calculadora_facade.calcular_racao is routes.calcular_racao
    assert calculadora_facade.comparar_racoes is routes.comparar_racoes
    assert (
        calculadora_facade.listar_opcoes_calculadora_racao
        is routes.listar_opcoes_calculadora_racao
    )

    assert calculadora_facade.CalculadoraRacaoRequest is schemas.CalculadoraRacaoRequest
    assert calculadora_facade.ResultadoCalculoRacao is schemas.ResultadoCalculoRacao
    assert (
        calculadora_facade.RacoesCalculadoraOptionsResponse
        is schemas.RacoesCalculadoraOptionsResponse
    )

    assert (
        calculadora_facade.calcular_quantidade_diaria is core.calcular_quantidade_diaria
    )
    assert calculadora_facade.calcular_resultado is core.calcular_resultado
    assert (
        calculadora_facade._avaliar_aptidao_calculadora
        is core._avaliar_aptidao_calculadora
    )
    assert calculadora_facade._serializar_opcao_racao is options._serializar_opcao_racao


def test_calculadora_racao_refactor_keeps_files_below_large_file_threshold():
    paths = [
        REPO_ROOT / "backend/app/calculadora_racao.py",
        REPO_ROOT / "backend/app/racao_calculadora/core.py",
        REPO_ROOT / "backend/app/racao_calculadora/options.py",
        REPO_ROOT / "backend/app/racao_calculadora/routes.py",
        REPO_ROOT / "backend/app/racao_calculadora/schemas.py",
    ]

    counts = {path.name: _non_empty_lines(path) for path in paths}

    assert all(lines < 700 for lines in counts.values())
    assert counts["calculadora_racao.py"] < 100
    assert counts["routes.py"] < 350
    assert counts["core.py"] < 350


def test_versioned_backup_artifacts_were_removed_from_application_tree():
    removed_paths = [
        REPO_ROOT / "backend/app/vendas_routes.py.backup_indent",
        REPO_ROOT / "backend/app/whatsapp/analytics_backup.py",
    ]

    assert [path for path in removed_paths if path.exists()] == []
