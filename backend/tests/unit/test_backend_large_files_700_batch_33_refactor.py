from pathlib import Path

import app.funcionarios_routes as funcionarios_facade
from app.funcionarios import base_routes, eventos_routes, helpers, routes, schemas


REPO_ROOT = Path(__file__).resolve().parents[3]


def _non_empty_lines(path: Path) -> int:
    return sum(
        1 for line in path.read_text(encoding="utf-8").splitlines() if line.strip()
    )


def test_funcionarios_facade_reexports_split_modules():
    assert funcionarios_facade.router is routes.router

    assert funcionarios_facade.FuncionarioCreate is schemas.FuncionarioCreate
    assert funcionarios_facade.FuncionarioUpdate is schemas.FuncionarioUpdate
    assert funcionarios_facade.FuncionarioResponse is schemas.FuncionarioResponse
    assert funcionarios_facade.ConcederFeriasRequest is schemas.ConcederFeriasRequest
    assert funcionarios_facade.ProvisoesResponse is schemas.ProvisoesResponse

    assert funcionarios_facade._cargo_dict is helpers._cargo_dict
    assert (
        funcionarios_facade._funcionario_response_dict
        is helpers._funcionario_response_dict
    )
    assert (
        funcionarios_facade._aplicar_app_access_profiles
        is helpers._aplicar_app_access_profiles
    )

    assert funcionarios_facade.listar_funcionarios is base_routes.listar_funcionarios
    assert funcionarios_facade.obter_funcionario is base_routes.obter_funcionario
    assert (
        funcionarios_facade.obter_remuneracao_funcionario
        is base_routes.obter_remuneracao_funcionario
    )
    assert funcionarios_facade.criar_funcionario is base_routes.criar_funcionario
    assert (
        funcionarios_facade.atualizar_funcionario is base_routes.atualizar_funcionario
    )
    assert funcionarios_facade.ativar_funcionario is base_routes.ativar_funcionario
    assert funcionarios_facade.deletar_funcionario is base_routes.deletar_funcionario

    assert funcionarios_facade.api_conceder_ferias is eventos_routes.api_conceder_ferias
    assert (
        funcionarios_facade.api_pagar_decimo_terceiro
        is eventos_routes.api_pagar_decimo_terceiro
    )
    assert (
        funcionarios_facade.api_obter_provisoes_funcionario
        is eventos_routes.api_obter_provisoes_funcionario
    )


def test_funcionarios_router_preserves_public_route_order():
    names = [route.name for route in routes.router.routes]

    assert names == [
        "listar_funcionarios",
        "obter_funcionario",
        "obter_remuneracao_funcionario",
        "criar_funcionario",
        "atualizar_funcionario",
        "ativar_funcionario",
        "deletar_funcionario",
        "api_conceder_ferias",
        "api_pagar_decimo_terceiro",
        "api_obter_provisoes_funcionario",
    ]


def test_funcionarios_refactor_keeps_files_below_large_file_threshold():
    paths = [
        REPO_ROOT / "backend/app/funcionarios_routes.py",
        REPO_ROOT / "backend/app/funcionarios/base_routes.py",
        REPO_ROOT / "backend/app/funcionarios/eventos_routes.py",
        REPO_ROOT / "backend/app/funcionarios/helpers.py",
        REPO_ROOT / "backend/app/funcionarios/routes.py",
        REPO_ROOT / "backend/app/funcionarios/schemas.py",
    ]

    counts = {path.name: _non_empty_lines(path) for path in paths}

    assert all(lines < 700 for lines in counts.values())
    assert counts["funcionarios_routes.py"] < 100
    assert counts["base_routes.py"] < 400
    assert counts["eventos_routes.py"] < 220
