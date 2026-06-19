from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SONAR_PROJECT = ROOT / "sonar-project.properties"
SONARCLOUD_CONFIG = ROOT / ".sonarcloud.properties"
TRANSACTION_TESTS = (
    "backend/tests/integration/test_transaction_cancelar_venda.py",
    "backend/tests/integration/test_transaction_estornar_comissoes.py",
    "backend/tests/integration/test_transaction_excluir_venda.py",
)
AUTOMATIC_ANALYSIS_EXCLUSIONS = (
    "backend/tests/**",
    "backend/alembic/**",
    "**/backend/alembic/**",
    "backend/migrations/**",
    "**/backend/migrations/**",
)


def _property_value(source: str, key: str) -> str:
    prefix = f"{key}="
    for line in source.splitlines():
        if line.startswith(prefix):
            return line.removeprefix(prefix)
    raise AssertionError(f"{key} nao encontrado em .sonarcloud.properties")


def _property_items(source: str, key: str) -> set[str]:
    return {item.strip() for item in _property_value(source, key).split(",")}


def _path_is_covered(path: str, exclusions: set[str]) -> bool:
    return path in exclusions or any(
        exclusion.endswith("/**") and path.startswith(exclusion.removesuffix("**"))
        for exclusion in exclusions
    )


def test_sonarcloud_excludes_non_runtime_paths_from_automatic_analysis():
    source = SONARCLOUD_CONFIG.read_text(encoding="utf-8")
    exclusions = _property_items(source, "sonar.exclusions")

    for exclusion in AUTOMATIC_ANALYSIS_EXCLUSIONS:
        assert exclusion in exclusions


def test_sonarcloud_automatic_analysis_ignores_legacy_transaction_tests():
    source = SONARCLOUD_CONFIG.read_text(encoding="utf-8")

    exclusions = _property_items(source, "sonar.exclusions")
    cpd_exclusions = _property_items(source, "sonar.cpd.exclusions")

    for path in TRANSACTION_TESTS:
        assert _path_is_covered(path, exclusions)
        assert _path_is_covered(path, cpd_exclusions)


def test_sonarcloud_cpd_exclusions_cover_shared_sonar_project_config():
    sonar_project_source = SONAR_PROJECT.read_text(encoding="utf-8")
    sonarcloud_source = SONARCLOUD_CONFIG.read_text(encoding="utf-8")

    sonar_project_exclusions = _property_items(
        sonar_project_source, "sonar.cpd.exclusions"
    )
    sonarcloud_exclusions = _property_items(sonarcloud_source, "sonar.cpd.exclusions")

    assert sonar_project_exclusions <= sonarcloud_exclusions
