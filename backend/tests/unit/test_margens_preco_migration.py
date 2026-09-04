from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
MIGRATION = ROOT / "backend/alembic/versions/zzc20260903a1_margens_preco_sugeridas.py"


def test_migration_apenas_adiciona_preferencias_sem_recalcular_produtos():
    source = MIGRATION.read_text(encoding="utf-8")

    assert 'down_revision = "zzb20260903a1"' in source
    assert source.count('"empresa_config_geral"') == 4
    assert '"margem_preco_sugestao_1"' in source
    assert '"margem_preco_sugestao_2"' in source
    assert "UPDATE PRODUTOS" not in source.upper()
