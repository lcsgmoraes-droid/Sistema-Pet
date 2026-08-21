from __future__ import annotations

import importlib.util
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "validate_repository_structure.py"
E2E_SAFETY = ROOT / "backend" / "tests" / "e2e_safety.py"


def load_validator():
    spec = importlib.util.spec_from_file_location(
        "validate_repository_structure", SCRIPT
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def load_e2e_safety_module():
    spec = importlib.util.spec_from_file_location("e2e_safety_contract", E2E_SAFETY)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_current_repository_structure_is_valid():
    module = load_validator()
    assert module.validate_repository_structure(ROOT) == []


def test_new_source_in_legacy_root_is_rejected():
    module = load_validator()
    tracked = module.tracked_files(ROOT)
    tracked.add("src/pages/NovaTela.jsx")

    assert module.unexpected_legacy_source(tracked) == ["src/pages/NovaTela.jsx"]


def test_legacy_source_allowlist_is_empty():
    module = load_validator()
    assert module.KNOWN_LEGACY_SOURCE == frozenset()


def test_untracked_source_in_legacy_root_is_rejected(tmp_path):
    module = load_validator()
    legacy_page = tmp_path / "src" / "pages" / "NovaTela.jsx"
    legacy_page.parent.mkdir(parents=True)
    legacy_page.write_text("export default function NovaTela() {}", encoding="utf-8")

    assert module.legacy_source_files_on_disk(tmp_path) == {"src/pages/NovaTela.jsx"}
    assert module.unexpected_legacy_source(
        module.legacy_source_files_on_disk(tmp_path)
    ) == ["src/pages/NovaTela.jsx"]


def test_generated_runtime_artifact_is_rejected():
    module = load_validator()
    tracked = {"backend/app/main.py", "runtime/frontend/dist/index.html"}

    assert module.forbidden_generated_artifacts(tracked) == [
        "runtime/frontend/dist/index.html"
    ]


def test_new_root_markdown_is_rejected():
    module = load_validator()
    tracked = {
        "README.md",
        "docs/ARQUITETURA.md",
        "NOVO_GUIA_SOLTO.md",
    }

    assert module.unexpected_root_markdown(tracked) == ["NOVO_GUIA_SOLTO.md"]


def test_root_markdown_allowlist_matches_current_repository():
    module = load_validator()
    current = {
        path
        for path in module.tracked_files(ROOT)
        if "/" not in path and path.casefold().endswith(".md")
    }

    assert current == module.ALLOWED_ROOT_MARKDOWN


def test_new_root_operational_entrypoint_is_rejected():
    module = load_validator()
    tracked = {"FLUXO_UNICO.bat", "NOVO_DEPLOY.bat", "scripts/seguro.ps1"}

    assert module.unexpected_root_operational_entrypoints(tracked) == [
        "NOVO_DEPLOY.bat"
    ]


def test_root_operational_allowlist_matches_current_repository():
    module = load_validator()
    current = {
        path
        for path in module.tracked_files(ROOT)
        if "/" not in path
        and Path(path).suffix.casefold() in module.ROOT_OPERATIONAL_SUFFIXES
    }

    assert current == module.ALLOWED_ROOT_OPERATIONAL_ENTRYPOINTS


def test_root_operational_entrypoints_only_delegate_to_safe_flow():
    module = load_validator()
    assert module.operational_entrypoint_errors(ROOT) == []


def test_legacy_root_documents_only_redirect_to_current_guides():
    module = load_validator()
    assert module.legacy_document_redirect_errors(ROOT) == []


def test_destructive_operation_in_root_entrypoint_is_rejected():
    module = load_validator()
    content = "git reset --hard origin/main\nDROP TABLE IF EXISTS alembic_version"

    assert module.forbidden_operational_snippets(content) == [
        "drop table if exists alembic_version",
        "git reset --hard",
    ]


def test_old_local_machine_and_example_password_are_rejected():
    module = load_validator()
    content = "curl http://192.168.15.138:8000/health\nSenha: admin123"

    assert module.forbidden_operational_snippets(content) == [
        "192.168.15.138",
        "admin123",
    ]


def test_blocked_batch_entrypoint_requires_batch_exit_code():
    module = load_validator()

    assert module.has_blocking_exit("antigo.bat", "exit /b 1") is True
    assert module.has_blocking_exit("antigo.bat", "exit 1") is False
    assert module.has_blocking_exit("antigo.sh", "exit 1") is True


def test_root_shortcuts_cannot_start_local_production():
    module = load_validator()

    assert module.forbidden_operational_snippets('call "FLUXO_UNICO.bat" prod-up') == [
        "prod-up"
    ]


def test_root_shortcuts_cannot_restore_machine_specific_or_direct_db_logic():
    module = load_validator()
    content = (
        "copy /Y .env.piloto .env\n"
        "docker exec -i banco psql\n"
        "C:/Users/alguem/Downloads/dados"
    )

    assert module.forbidden_operational_snippets(content) == [
        "c:/users/",
        "copy /y .env",
        "docker exec",
    ]


def test_e2e_recognizes_current_production_domain_without_substring_false_positive():
    module = load_e2e_safety_module()

    assert module.is_production_base_url("https://corepet.com.br") is True
    assert module.is_production_base_url("https://www.corepet.com.br/api") is True
    assert module.is_production_base_url("https://api.corepet.com.br") is True
    assert module.is_production_base_url("https://mlprohub.com.br") is True
    assert module.is_production_base_url("http://127.0.0.1:8000") is False
    assert module.is_production_base_url("https://corepet.com.br.example.test") is False
