from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MIGRATION = (
    ROOT
    / "backend"
    / "alembic"
    / "versions"
    / "zxb20260826a1_repair_tenant_ecommerce_slug.py"
)
ENUM_MIGRATION = (
    ROOT
    / "backend"
    / "alembic"
    / "versions"
    / "zxc20260826a1_normalize_naturezadre_labels.py"
)


def test_ecommerce_slug_repair_is_in_the_official_alembic_chain():
    source = MIGRATION.read_text(encoding="utf-8")

    assert 'revision = "zxb20260826a1"' in source
    assert 'down_revision = "zxa20260824a1"' in source
    assert 'COLUMN_NAME = "ecommerce_slug"' in source
    assert "op.add_column" in source
    assert "op.create_index" in source
    assert "unique=True" in source


def test_ecommerce_slug_repair_preserves_preexisting_schema():
    source = MIGRATION.read_text(encoding="utf-8")

    assert "if COLUMN_NAME not in columns" in source
    assert "if _has_unique_slug(inspector)" in source
    assert "Forward-only repair" in source


def test_naturezadre_uses_the_same_values_as_the_orm():
    source = ENUM_MIGRATION.read_text(encoding="utf-8")

    assert 'revision = "zxc20260826a1"' in source
    assert 'down_revision = "zxb20260826a1"' in source
    for old_label, new_label in (
        ("RECEITA", "receita"),
        ("CUSTO", "custo"),
        ("DESPESA", "despesa"),
        ("RESULTADO", "resultado"),
    ):
        assert f'("{old_label}", "{new_label}")' in source

    assert "ALTER TYPE {ENUM_TYPE}" in source
    assert "RENAME VALUE" in source
