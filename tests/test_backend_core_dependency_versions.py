from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BACKEND_REQUIREMENTS = ROOT / "backend" / "requirements.txt"

EXPECTED_CORE_PINS = {
    "sqlalchemy": "2.0.51",
    "alembic": "1.18.4",
    "psycopg2-binary": "2.9.12",
}

EXPECTED_RUNTIME_PINS = {
    "uvicorn[standard]": "0.49.0",
    "pydantic-settings": "2.14.2",
    "email-validator": "2.3.0",
    "bcrypt": "4.1.2",
    "slowapi": "0.1.10",
    "httpx": "0.28.1",
    "chardet": "7.4.3",
    "boto3": "1.43.32",
    "pycryptodome": "3.23.0",
    "openai": "2.43.0",
    "python-dateutil": "2.9.0.post0",
    "openpyxl": "3.1.5",
    "pandas": "3.0.3",
    "reportlab": "5.0.0",
    "matplotlib": "3.11.0",
    "plotly": "6.8.0",
    "colorlog": "6.10.1",
    "psutil": "7.2.2",
    "celery": "5.6.3",
    "redis": "8.0.0",
    "pytz": "2026.2",
    "tzlocal": "5.4.3",
    "prophet": "1.3.0",
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


def test_backend_runtime_dependencies_are_currently_pinned_for_leva_3():
    pins = _requirements_pins()

    for package, expected_version in EXPECTED_RUNTIME_PINS.items():
        assert pins[package] == expected_version

    requirements_source = BACKEND_REQUIREMENTS.read_text(encoding="utf-8")
    assert "APScheduler>=3.11.2" in requirements_source
