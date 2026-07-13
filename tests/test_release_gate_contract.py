from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_release_check_executes_technical_gate() -> None:
    flow = (ROOT / "scripts" / "fluxo_unico.ps1").read_text(encoding="utf-8")

    assert "validar_release.ps1" in flow
    assert "& $releaseValidatorScript -Nivel completo" in flow
    assert "Gate tecnico de release falhou" in flow


def test_release_gate_covers_blocking_product_checks() -> None:
    gate = (ROOT / "scripts" / "validar_release.ps1").read_text(encoding="utf-8")

    required_checks = (
        "Backend dependency sync",
        "Backend lint",
        "Backend format",
        "Root smoke tests",
        "Multitenant hardening suite",
        "Backend import smoke",
        "Backend dependency audit",
        "Frontend dependency audit",
        "Frontend lint",
        "Frontend format",
        "Frontend production build",
        "Mobile dependency audit",
        "Mobile typecheck",
        "Mobile tests",
    )

    for check in required_checks:
        assert check in gate

    assert "check_python_requirements.py" in gate


def test_release_gate_does_not_deploy() -> None:
    gate = (ROOT / "scripts" / "validar_release.ps1").read_text(encoding="utf-8")

    forbidden_commands = (
        "docker compose up",
        "git push",
        "ssh ",
        "deploy_producao",
    )

    for command in forbidden_commands:
        assert command not in gate.lower()
