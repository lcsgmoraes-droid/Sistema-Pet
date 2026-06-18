from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BACKEND_REQUIREMENTS = ROOT / "backend" / "requirements.txt"

EXPECTED_CORE_PINS = {
    "sqlalchemy": "2.0.51",
    "alembic": "1.18.4",
    "psycopg2-binary": "2.9.12",
}


def _requirements_pins() -> dict[str, str]:
    pins: dict[str, str] = {}
    for raw_line in BACKEND_REQUIREMENTS.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "==" not in line:
            continue
        name, version = line.split("==", maxsplit=1)
        pins[name.lower()] = version
    return pins


def test_backend_orm_and_migration_core_dependencies_are_currently_pinned():
    pins = _requirements_pins()

    for package, expected_version in EXPECTED_CORE_PINS.items():
        assert pins[package] == expected_version
