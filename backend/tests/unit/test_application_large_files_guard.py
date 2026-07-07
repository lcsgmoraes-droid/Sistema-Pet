from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
MAX_NON_EMPTY_LINES = 700
APPLICATION_ROOTS = (
    REPO_ROOT / "backend" / "app",
    REPO_ROOT / "frontend" / "src",
    REPO_ROOT / "app-mobile" / "src",
)
APPLICATION_EXTENSIONS = {".py", ".js", ".jsx", ".ts", ".tsx"}
IGNORED_PARTS = {
    "__pycache__",
    "__tests__",
    "tests",
    "dist",
    "build",
    "coverage",
}


def _is_application_file(path: Path) -> bool:
    if path.suffix not in APPLICATION_EXTENSIONS:
        return False
    relative_parts = set(path.relative_to(REPO_ROOT).parts)
    return not (relative_parts & IGNORED_PARTS)


def _non_empty_line_count(path: Path) -> int:
    return sum(
        1 for line in path.read_text(encoding="utf-8").splitlines() if line.strip()
    )


def test_application_files_stay_below_large_file_threshold():
    oversized = {
        path.relative_to(REPO_ROOT).as_posix(): _non_empty_line_count(path)
        for root in APPLICATION_ROOTS
        for path in root.rglob("*")
        if path.is_file() and _is_application_file(path)
        if _non_empty_line_count(path) >= MAX_NON_EMPTY_LINES
    }

    assert oversized == {}


def test_enterprise_refactor_inventory_documents_current_guard():
    source = (REPO_ROOT / "docs" / "EVOLUCAO_ENTERPRISE_UI_REFATORACAO.md").read_text(
        encoding="utf-8"
    )

    assert "Inventario atualizado em 2026-07-07" in source
    assert "- 0 arquivos de aplicacao backend/web/mobile acima de 700 linhas" in source
