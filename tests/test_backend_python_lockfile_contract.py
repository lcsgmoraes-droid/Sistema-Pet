from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
REQUIREMENTS = BACKEND / "requirements.txt"
LOCKFILE = BACKEND / "requirements.lock"


def _requirement_lines(path: Path) -> list[str]:
    return [
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]


def _package_name(requirement: str) -> str:
    return re.split(r"\[|==|>=|<=|~=|!=|>|<", requirement, maxsplit=1)[0].lower()


def _normalized_exact_pin(requirement: str) -> str | None:
    if "==" not in requirement:
        return None

    name, version = requirement.split("==", maxsplit=1)
    return f"{_package_name(name)}=={version}"


def test_backend_has_generated_python_lockfile_with_transitive_pins():
    assert LOCKFILE.exists()

    requirement_lines = _requirement_lines(REQUIREMENTS)
    lock_lines = _requirement_lines(LOCKFILE)

    direct_packages = {_package_name(line) for line in requirement_lines}
    locked_packages = {_package_name(line) for line in lock_lines}
    direct_exact_pins = {
        pin for line in requirement_lines if (pin := _normalized_exact_pin(line))
    }
    locked_exact_pins = {
        pin for line in lock_lines if (pin := _normalized_exact_pin(line))
    }

    assert len(lock_lines) > len(requirement_lines)
    assert direct_packages <= locked_packages
    assert direct_exact_pins <= locked_exact_pins
    assert all("==" in line for line in lock_lines)


def test_backend_dockerfiles_install_from_lockfile():
    dev_dockerfile = (BACKEND / "Dockerfile").read_text(encoding="utf-8")
    prod_dockerfile = (BACKEND / "Dockerfile.prod").read_text(encoding="utf-8")

    for source in (dev_dockerfile, prod_dockerfile):
        assert "COPY requirements.txt requirements.lock ./" in source
        assert "pip install" in source
        assert "-r requirements.txt -c requirements.lock" in source


def test_ci_installs_and_audits_backend_lockfile():
    backend_ci = (ROOT / ".github" / "workflows" / "backend-ci.yml").read_text(
        encoding="utf-8"
    )
    smoke_ci = (ROOT / ".github" / "workflows" / "smoke-ci.yml").read_text(
        encoding="utf-8"
    )
    e2e_long = (ROOT / ".github" / "workflows" / "e2e-long.yml").read_text(
        encoding="utf-8"
    )
    bootstrap = (ROOT / "scripts" / "bootstrap_dev_environment.ps1").read_text(
        encoding="utf-8"
    )

    assert "pip install -r requirements.txt -c requirements.lock" in backend_ci
    assert "pip-audit -r requirements.lock" in backend_ci
    assert "pip install -r backend/requirements.txt -c backend/requirements.lock" in (
        backend_ci
    )
    assert (
        "python -m pip install -r backend/requirements.txt -c backend/requirements.lock"
        in smoke_ci
    )
    assert (
        "python -m pip install -r backend/requirements.txt -c backend/requirements.lock"
        in e2e_long
    )
    assert (
        r".\backend\.venv\Scripts\python.exe -m pip install -r .\backend\requirements.txt -c .\backend\requirements.lock"
        in bootstrap
    )
