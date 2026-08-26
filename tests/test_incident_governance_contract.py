from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / "docs" / "GESTAO_INCIDENTES_SUSTENTACAO.md"
TEMPLATE = ROOT / "docs" / "templates" / "REGISTRO_INCIDENTE.md"
INDEX = ROOT / "docs" / "INDICE_OPERACIONAL.md"
GOVERNANCE = ROOT / "docs" / "GOVERNANCA_ENTERPRISE.md"


def test_incident_policy_defines_the_operating_contract():
    source = POLICY.read_text(encoding="utf-8")

    for required in (
        "P0 crítico",
        "P1 alto",
        "P2 normal",
        "P3 baixo",
        "MTTD",
        "MTTA",
        "MTTC",
        "MTTR",
        "Causa raiz e melhoria estrutural",
        "Critério de encerramento",
        "autorização explícita e separada",
    ):
        assert required in source


def test_incident_template_preserves_traceability_without_secrets():
    source = TEMPLATE.read_text(encoding="utf-8")

    for required in (
        "INC-AAAAMMDD-NN",
        "request_id",
        "correlation_id",
        "PR e commit",
        "Ações preventivas",
        "Não há segredos ou dados pessoais desnecessários",
    ):
        assert required in source


def test_official_indexes_reference_incident_policy_and_template():
    index = INDEX.read_text(encoding="utf-8")
    governance = GOVERNANCE.read_text(encoding="utf-8")

    assert "docs/GESTAO_INCIDENTES_SUSTENTACAO.md" in index
    assert "docs/templates/REGISTRO_INCIDENTE.md" in index
    assert "docs/GESTAO_INCIDENTES_SUSTENTACAO.md" in governance
    assert "docs/templates/REGISTRO_INCIDENTE.md" in governance
