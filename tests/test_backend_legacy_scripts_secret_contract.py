from __future__ import annotations

from pathlib import Path

from backend_legacy_root_scripts import CLEANED_LEGACY_ROOT_SCRIPTS


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"


def test_legacy_root_scripts_do_not_embed_known_credentials():
    secret_key = "pass" + "word"
    forbidden_fragments = (
        "petshop_pass" + "_2026",
        "admin-dev" + "-token",
        "postgresql://postgres:" + "sua_senha",
        f"{secret_key}='postgres'",
        f'{secret_key}="postgres"',
        f"'{secret_key}': 'admin'",
        f'"{secret_key}": "postgres"',
        f"'{secret_key}': 'senha'",
        "$2b$12$" + "LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY.6GZjMe/.hizq",
    )

    offenders: list[str] = []
    for script in CLEANED_LEGACY_ROOT_SCRIPTS:
        source = (BACKEND / script).read_text(encoding="utf-8")
        for fragment in forbidden_fragments:
            if fragment in source:
                offenders.append(f"{script}: {fragment[:24]}")

    assert offenders == []
