from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ADR_INDEX = ROOT / "docs" / "adr" / "README.md"
ARCHITECTURE = ROOT / "docs" / "ARQUITETURA.md"
GOVERNANCE = ROOT / "docs" / "GOVERNANCA_ENTERPRISE.md"
OPERATIONAL_INDEX = ROOT / "docs" / "INDICE_OPERACIONAL.md"


def test_initial_architecture_decisions_are_indexed_and_exist():
    source = ADR_INDEX.read_text(encoding="utf-8")
    decisions = (
        "0001-monolito-modular.md",
        "0002-isolamento-multitenant-em-camadas.md",
        "0003-escala-orientada-por-medicao.md",
    )

    for decision in decisions:
        assert decision in source
        assert (ADR_INDEX.parent / decision).is_file()


def test_every_initial_adr_records_tradeoffs_and_review_triggers():
    for path in ADR_INDEX.parent.glob("[0-9][0-9][0-9][0-9]-*.md"):
        source = path.read_text(encoding="utf-8")
        for section in (
            "## Contexto",
            "## Decisão",
            "## Alternativas consideradas",
            "## Consequências",
            "## Gatilhos para revisão",
            "## Evidências relacionadas",
        ):
            assert section in source, f"{path.name}: missing {section}"


def test_official_navigation_links_architecture_decisions():
    expected = "docs/adr/README.md"
    for document in (ARCHITECTURE, GOVERNANCE, OPERATIONAL_INDEX):
        assert expected in document.read_text(encoding="utf-8")
