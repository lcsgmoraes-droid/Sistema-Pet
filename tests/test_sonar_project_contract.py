from __future__ import annotations

from pathlib import Path


SONAR_PROJECT = Path(__file__).resolve().parents[1] / "sonar-project.properties"


def _sonar_property(name: str) -> str:
    for line in SONAR_PROJECT.read_text(encoding="utf-8").splitlines():
        if line.startswith(f"{name}="):
            return line.split("=", 1)[1]
    raise AssertionError(f"Missing Sonar property: {name}")


def test_sonar_cpd_excludes_generated_alembic_migrations():
    exclusions = {
        item.strip() for item in _sonar_property("sonar.cpd.exclusions").split(",")
    }

    assert "backend/alembic/**" in exclusions
    assert "**/backend/alembic/**" in exclusions
