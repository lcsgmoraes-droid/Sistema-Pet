from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = BACKEND_ROOT.parent


def read_backend(path: str) -> str:
    return (BACKEND_ROOT / path).read_text(encoding="utf-8")


def read_repo(path: str) -> str:
    return (REPO_ROOT / path).read_text(encoding="utf-8")


def test_funcionarios_backend_exposes_explicit_activate_endpoint():
    source = read_backend("app/funcionarios_routes.py")

    assert '@router.post("/{funcionario_id}/ativar"' in source
    assert "funcionario.ativo = True" in source


def test_funcionarios_page_shows_activate_button_for_inactive_rows():
    source = read_repo("frontend/src/pages/RH/Funcionarios.jsx")

    assert "const ativar = async" in source
    assert "Ativar" in source
    assert "!f.ativo" in source
    assert "/ativar" in source


def test_funcionarios_rh_exposes_app_access_controls():
    backend_source = read_backend("app/funcionarios_routes.py")
    page_source = read_repo("frontend/src/pages/RH/Funcionarios.jsx")

    assert "app_access_profiles" in backend_source
    assert "sync_cliente_app_access_profiles" in backend_source
    assert "Acessos do app" in page_source
    assert "app_access_profiles" in page_source
    assert "Cliente" in page_source
    assert "Funcionario" in page_source
    assert "Entregador" in page_source
    assert "Veterinario" in page_source
