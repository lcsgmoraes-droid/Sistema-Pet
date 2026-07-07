from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def _non_empty_lines(path: Path) -> int:
    return sum(
        1 for line in path.read_text(encoding="utf-8").splitlines() if line.strip()
    )


def test_importar_simplesvet_facade_stays_below_operational_threshold():
    facade = ROOT / "importar_simplesvet.py"

    assert _non_empty_lines(facade) < 700


def test_importar_simplesvet_refactor_modules_exist():
    expected_exports = {
        "importar_simplesvet_utils.py": [
            "def ler_csv(",
            "def limpar_cpf(",
            "def carregar_contatos(",
            "def parse_decimal(",
            "def log(",
        ],
        "importar_simplesvet_summary.py": ["def exibir_resumo("],
        "importar_simplesvet_state.py": ["ID_MAP = {", "STATS = {", "USER_ID = 1"],
    }

    for filename, snippets in expected_exports.items():
        source = (ROOT / filename).read_text(encoding="utf-8")
        for snippet in snippets:
            assert snippet in source
