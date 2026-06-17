from __future__ import annotations

import ast
from pathlib import Path

import pytest

from app import bling_routes


BACKEND_ROOT = Path(__file__).resolve().parents[2]
BLING_ROUTES = BACKEND_ROOT / "app" / "bling_routes.py"


def _find_async_function(tree: ast.AST, name: str) -> ast.AsyncFunctionDef:
    for node in ast.walk(tree):
        if isinstance(node, ast.AsyncFunctionDef) and node.name == name:
            return node
    raise AssertionError(f"async function {name!r} not found")


def test_testar_conexao_does_not_use_sync_open_inside_async_route():
    tree = ast.parse(BLING_ROUTES.read_text(encoding="utf-8"))
    route = _find_async_function(tree, "testar_conexao")

    sync_open_calls = [
        node
        for node in ast.walk(route)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "open"
    ]

    assert sync_open_calls == []


def test_carregar_controle_token_bling_returns_defaults_when_file_is_absent(tmp_path):
    token_info = bling_routes._carregar_controle_token_bling(
        tmp_path / "bling_token_control.json"
    )

    assert token_info == {
        "ultima_renovacao": None,
        "proxima_renovacao": None,
        "renovacoes_automaticas": 0,
    }


def test_carregar_controle_token_bling_loads_json(tmp_path):
    token_control_file = tmp_path / "bling_token_control.json"
    token_control_file.write_text(
        (
            '{"ultima_renovacao":"2026-06-17T10:00:00",'
            '"proxima_renovacao":"2026-06-17T16:00:00",'
            '"renovacoes_automaticas":2}'
        ),
        encoding="utf-8",
    )

    token_info = bling_routes._carregar_controle_token_bling(token_control_file)

    assert token_info["ultima_renovacao"] == "2026-06-17T10:00:00"
    assert token_info["proxima_renovacao"] == "2026-06-17T16:00:00"
    assert token_info["renovacoes_automaticas"] == 2


@pytest.mark.asyncio
async def test_testar_conexao_loads_token_control_via_helper(monkeypatch):
    calls: list[Path] = []

    class FakeBlingAPI:
        def listar_naturezas_operacoes(self):
            return {"data": [{"id": 1}, {"id": 2}]}

    def fake_carregar_controle_token_bling(token_control_file: Path):
        calls.append(token_control_file)
        return {
            "ultima_renovacao": "agora",
            "proxima_renovacao": "depois",
            "renovacoes_automaticas": 3,
        }

    monkeypatch.setattr(bling_routes, "BlingAPI", FakeBlingAPI)
    monkeypatch.setattr(
        bling_routes,
        "_carregar_controle_token_bling",
        fake_carregar_controle_token_bling,
    )

    response = await bling_routes.testar_conexao()

    assert calls == [Path("bling_token_control.json")]
    assert response["conectado"] is True
    assert response["total_produtos_bling"] == 2
    assert response["ultima_renovacao"] == "agora"
    assert response["proxima_renovacao"] == "depois"
    assert response["renovacoes_automaticas"] == 3
