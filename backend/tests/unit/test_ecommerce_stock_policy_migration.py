from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
MIGRATION = (
    ROOT / "backend/alembic/versions/zza20260901a1_estoque_online_e_esgotados.py"
)


def test_online_stock_policy_migration_follows_current_head_without_rewriting_rows():
    source = MIGRATION.read_text(encoding="utf-8")

    assert 'down_revision = "zyx20260831a1"' in source
    assert '"permite_estoque_negativo_online"' in source
    assert '"ecommerce_ocultar_sem_estoque"' in source
    assert '"reserva_estoque_iniciada_at"' in source
    assert "UPDATE tenants" not in source
