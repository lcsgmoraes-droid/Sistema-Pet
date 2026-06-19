from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SONARCLOUD_CONFIG = ROOT / ".sonarcloud.properties"
TRANSACTION_TESTS = (
    "backend/tests/integration/test_transaction_cancelar_venda.py",
    "backend/tests/integration/test_transaction_estornar_comissoes.py",
    "backend/tests/integration/test_transaction_excluir_venda.py",
)


def _property_value(source: str, key: str) -> str:
    prefix = f"{key}="
    for line in source.splitlines():
        if line.startswith(prefix):
            return line.removeprefix(prefix)
    raise AssertionError(f"{key} nao encontrado em .sonarcloud.properties")


def test_sonarcloud_automatic_analysis_ignores_legacy_transaction_tests():
    source = SONARCLOUD_CONFIG.read_text(encoding="utf-8")

    exclusions = _property_value(source, "sonar.exclusions")
    cpd_exclusions = _property_value(source, "sonar.cpd.exclusions")

    for path in TRANSACTION_TESTS:
        assert path in exclusions
        assert path in cpd_exclusions
