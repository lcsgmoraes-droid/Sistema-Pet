import os
import subprocess
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT_DIR = REPO_ROOT / "backend" / "scripts"

ENRIQUECER_BLING_FILES = [
    "backend/scripts/enriquecer_produtos_bling_sku.py",
    "backend/scripts/enriquecer_produtos_bling_types.py",
    "backend/scripts/enriquecer_produtos_bling_utils.py",
    "backend/scripts/enriquecer_produtos_bling_loaders.py",
    "backend/scripts/enriquecer_produtos_bling_classification.py",
    "backend/scripts/enriquecer_produtos_bling_db.py",
    "backend/scripts/enriquecer_produtos_bling_processing.py",
]


def _source(relative_path: str) -> str:
    return (REPO_ROOT / relative_path).read_text(encoding="utf-8")


def _non_empty_line_count(relative_path: str) -> int:
    return sum(1 for line in _source(relative_path).splitlines() if line.strip())


def test_enriquecer_bling_fatia_55_divide_script_em_modulos_focados():
    facade_source = _source("backend/scripts/enriquecer_produtos_bling_sku.py")

    for relative_path in ENRIQUECER_BLING_FILES:
        assert (REPO_ROOT / relative_path).exists(), relative_path

    assert "from enriquecer_produtos_bling_processing import run" in facade_source
    assert "from app.db import SessionLocal" not in facade_source
    assert "def get_or_create_marca(" not in facade_source
    assert "def load_bling_rows(" not in facade_source


def test_enriquecer_bling_fatia_55_fica_abaixo_de_700_linhas_nao_vazias():
    counts = {
        relative_path: _non_empty_line_count(relative_path)
        for relative_path in ENRIQUECER_BLING_FILES
    }

    assert all(lines < 700 for lines in counts.values()), counts


def test_enriquecer_bling_fatia_55_preserva_exports_compatibilidade():
    sys.path.insert(0, str(SCRIPT_DIR))
    try:
        import enriquecer_produtos_bling_sku as facade
        import enriquecer_produtos_bling_loaders as loaders
        import enriquecer_produtos_bling_processing as processing
        import enriquecer_produtos_bling_types as types
        import enriquecer_produtos_bling_utils as utils

        assert facade.BlingRow is types.BlingRow
        assert facade.FamilyDefaults is types.FamilyDefaults
        assert facade.normalize_text is utils.normalize_text
        assert facade.load_bling_rows is loaders.load_bling_rows
        assert facade.run is processing.run
    finally:
        sys.path.remove(str(SCRIPT_DIR))


def test_enriquecer_bling_fatia_55_valida_csv_dentro_da_raiz(tmp_path):
    sys.path.insert(0, str(SCRIPT_DIR))
    try:
        from enriquecer_produtos_bling_processing import resolve_existing_csv_path

        repo_root = tmp_path / "repo"
        repo_root.mkdir()
        valid_csv = repo_root / "bling.csv"
        valid_csv.write_text("Codigo;Descricao\n1;Produto\n", encoding="utf-8")
        outside_csv = tmp_path / "fora.csv"
        outside_csv.write_text("Codigo;Descricao\n1;Produto\n", encoding="utf-8")

        assert (
            resolve_existing_csv_path(repo_root, "bling.csv", "CSV Bling") == valid_csv
        )
        with pytest.raises(ValueError, match="fora da raiz permitida"):
            resolve_existing_csv_path(repo_root, str(outside_csv), "CSV Bling")
    finally:
        sys.path.remove(str(SCRIPT_DIR))


def test_enriquecer_bling_fatia_55_help_nao_exige_database_url():
    env = os.environ.copy()
    env.pop("DATABASE_URL", None)
    env.pop("APP_ENV", None)
    env.pop("ENVIRONMENT", None)

    result = subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "backend" / "scripts" / "enriquecer_produtos_bling_sku.py"),
            "--help",
        ],
        cwd=REPO_ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "--bling-csv" in result.stdout
    assert "--apply" in result.stdout
