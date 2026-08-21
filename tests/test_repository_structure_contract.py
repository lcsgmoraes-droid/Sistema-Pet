from __future__ import annotations

import importlib.util
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "validate_repository_structure.py"


def load_validator():
    spec = importlib.util.spec_from_file_location(
        "validate_repository_structure", SCRIPT
    )
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


def test_root_operational_entrypoints_only_delegate_to_safe_flow():
    module = load_validator()
    assert module.operational_entrypoint_errors(ROOT) == []


def test_destructive_operation_in_root_entrypoint_is_rejected():
    module = load_validator()
    content = "git reset --hard origin/main\nDROP TABLE IF EXISTS alembic_version"

    assert module.forbidden_operational_snippets(content) == [
        "drop table if exists alembic_version",
        "git reset --hard",
    ]
