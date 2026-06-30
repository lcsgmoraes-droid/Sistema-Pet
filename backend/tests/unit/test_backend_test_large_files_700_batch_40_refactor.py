from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]

ANALYTICS_TEST_FILES = [
    "backend/tests/analytics/__init__.py",
    "backend/tests/analytics/analytics_test_helpers.py",
    "backend/tests/analytics/conftest.py",
    "backend/tests/analytics/test_analytics_routes_endpoints.py",
    "backend/tests/analytics/test_analytics_routes_errors.py",
    "backend/tests/analytics/test_analytics_routes_security.py",
    "backend/tests/analytics/test_analytics_routes_contracts.py",
]


def _non_empty_line_count(relative_path: str) -> int:
    return sum(
        1
        for line in (REPO_ROOT / relative_path).read_text(encoding="utf-8").splitlines()
        if line.strip()
    )


def test_analytics_routes_tests_foram_divididos_por_responsabilidade():
    assert not (REPO_ROOT / "backend/tests/test_analytics_routes.py").exists()

    for relative_path in ANALYTICS_TEST_FILES:
        assert (REPO_ROOT / relative_path).exists(), relative_path


def test_analytics_routes_tests_ficam_abaixo_de_700_linhas_nao_vazias():
    counts = {
        relative_path: _non_empty_line_count(relative_path)
        for relative_path in ANALYTICS_TEST_FILES
    }

    assert all(lines < 700 for lines in counts.values()), counts
