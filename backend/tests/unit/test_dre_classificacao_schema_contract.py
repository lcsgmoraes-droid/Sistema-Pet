from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]


def _source(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def _versioned_migration_sources() -> str:
    versions_dir = ROOT / "backend" / "alembic" / "versions"
    return "\n".join(
        migration.read_text(encoding="utf-8")
        for migration in sorted(versions_dir.glob("*.py"))
    )


def test_alembic_env_carrega_modelos_de_regras_dre():
    source = _source("backend/alembic/env.py")

    assert "import app.dre_regras_models" in source


def test_regras_classificacao_dre_tem_migration_versionada():
    migrations = _versioned_migration_sources()

    assert "regras_classificacao_dre" in migrations
    assert "historico_classificacao_dre" in migrations
    assert "beneficiario" in migrations
    assert "tipo_documento" in migrations
    assert "afeta_dre" in migrations
    assert "idx_regras_classificacao_criterios" in migrations
    assert "idx_contas_pagar_beneficiario" in migrations
